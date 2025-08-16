# Service layer for Fees, Charges & Commission Engine
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional, Dict, Any
import json
import decimal
from datetime import datetime, date

from . import models, schemas
# Enums imported directly from models for use in service logic
from .models import (
    FeeTypeEnum as ModelFeeTypeEnum,
    FeeCalculationMethodEnum as ModelFeeCalculationMethodEnum,
    CurrencyEnum as ModelCurrencyEnum
)

# Conceptual cross-module imports (replace with actual when available)
# from ..accounts_ledger_management.services import post_internal_transaction
# from ..accounts_ledger_management.schemas import InternalTransactionPostingRequest
# from ..transaction_management.services import get_financial_transaction_by_id # To link fees to original FT
# from ..core_infrastructure_config_engine.services import get_gl_account_by_code # To validate GL codes

# Placeholder for shared exceptions
class NotFoundException(Exception): pass
class InvalidOperationException(Exception): pass
class FeeCalculationException(Exception): pass

def _log_fee_event(db: Session, event_type: str, entity_id: Any, details: Optional[Dict[str, Any]] = None, user_id: str = "SYSTEM"):
    # print(f"AUDIT LOG (FeeEngine): Event='{event_type}', EntityID='{entity_id}', Details='{json.dumps(details, default=str)}', By='{user_id}'")
    pass # Placeholder for actual audit logging


# --- FeeConfig Services (Admin/Setup) ---
def create_fee_config(db: Session, fee_config_in: schemas.FeeConfigCreateRequest, created_by_user_id: str) -> models.FeeConfig:
    existing = db.query(models.FeeConfig).filter(models.FeeConfig.fee_code == fee_config_in.fee_code).first()
    if existing:
        raise InvalidOperationException(f"FeeConfig with code '{fee_config_in.fee_code}' already exists.")

    # Validate GL codes (conceptual)
    # if not get_gl_account_by_code(db, fee_config_in.fee_income_gl_code):
    #     raise NotFoundException(f"Fee income GL code '{fee_config_in.fee_income_gl_code}' not found.")
    # if fee_config_in.tax_payable_gl_code and not get_gl_account_by_code(db, fee_config_in.tax_payable_gl_code):
    #     raise NotFoundException(f"Tax payable GL code '{fee_config_in.tax_payable_gl_code}' not found.")
    # if fee_config_in.linked_tax_fee_code and not get_fee_config_by_code(db, fee_config_in.linked_tax_fee_code): # Recursive check
    #     raise NotFoundException(f"Linked tax fee code '{fee_config_in.linked_tax_fee_code}' not found.")

    fee_config_data = fee_config_in.dict(exclude_unset=True)
    # Map schema enums to model enums
    fee_config_data["fee_type"] = ModelFeeTypeEnum[fee_config_in.fee_type.value]
    fee_config_data["calculation_method"] = ModelFeeCalculationMethodEnum[fee_config_in.calculation_method.value]
    fee_config_data["currency"] = ModelCurrencyEnum[fee_config_in.currency.value]

    if fee_config_in.applicable_context_json is not None:
        fee_config_data["applicable_context_json"] = json.dumps(fee_config_in.applicable_context_json, default=str)
    if fee_config_in.tiers_json is not None:
        # Further validation on tiers structure could be done here
        fee_config_data["tiers_json"] = json.dumps([tier.dict() for tier in fee_config_in.tiers_json], default=str)

    db_fee_config = models.FeeConfig(**fee_config_data, created_by_user_id=created_by_user_id)
    db.add(db_fee_config)
    _log_fee_event(db, "FEE_CONFIG_CREATED", db_fee_config.fee_code, fee_config_in.dict(), created_by_user_id)
    db.commit()
    db.refresh(db_fee_config)
    return db_fee_config

def get_fee_config_by_code(db: Session, fee_code: str) -> Optional[models.FeeConfig]:
    return db.query(models.FeeConfig).filter(models.FeeConfig.fee_code == fee_code).first()

def list_fee_configs(db: Session, skip: int = 0, limit: int = 100) -> List[models.FeeConfig]:
    return db.query(models.FeeConfig).offset(skip).limit(limit).all()

# --- Fee Calculation and Application Services ---
def _calculate_single_fee(fee_config: models.FeeConfig, base_amount: Optional[decimal.Decimal]) -> decimal.Decimal:
    """Calculates fee amount based on a single FeeConfig and a base amount."""
    # Ensure base_amount is Decimal if provided
    if base_amount is not None:
        base_amount = decimal.Decimal(str(base_amount))

    if fee_config.calculation_method == ModelFeeCalculationMethodEnum.FLAT:
        return fee_config.flat_amount or decimal.Decimal("0.00")

    elif fee_config.calculation_method == ModelFeeCalculationMethodEnum.PERCENTAGE:
        if base_amount is None or fee_config.percentage_rate is None:
            raise FeeCalculationException(f"Base amount and percentage rate required for fee '{fee_config.fee_code}'.")
        # Ensure percentage_rate is Decimal
        rate = decimal.Decimal(str(fee_config.percentage_rate))
        return (base_amount * rate).quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)

    elif fee_config.calculation_method in [ModelFeeCalculationMethodEnum.TIERED_FLAT, ModelFeeCalculationMethodEnum.TIERED_PERCENTAGE]:
        if base_amount is None or not fee_config.tiers_json:
            raise FeeCalculationException(f"Base amount and tiers_json required for tiered fee '{fee_config.fee_code}'.")

        tiers = json.loads(fee_config.tiers_json)
        for tier in sorted(tiers, key=lambda x: decimal.Decimal(str(x.get('min_transaction_amount', '0')))):
            min_amt = decimal.Decimal(str(tier.get('min_transaction_amount', '0')))
            # Handle open-ended last tier: max_transaction_amount can be null or a very large number
            max_amt_str = tier.get('max_transaction_amount')
            max_amt = decimal.Decimal(str(max_amt_str)) if max_amt_str is not None else decimal.Decimal('Infinity')

            if min_amt <= base_amount and (base_amount <= max_amt): # max_amt being None means no upper bound for this tier
                tier_value = decimal.Decimal(str(tier.get('value', '0')))
                if fee_config.calculation_method == ModelFeeCalculationMethodEnum.TIERED_FLAT:
                    return tier_value.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)
                else: # TIERED_PERCENTAGE
                    return (base_amount * tier_value).quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)
        # If no tier matches (e.g., base_amount is below the first tier's min_amount, or above last tier's max if not open-ended)
        # This implies configuration error or unexpected base_amount. For safety, could return 0 or raise error.
        # print(f"Warning: No matching tier for base_amount {base_amount} in fee '{fee_config.fee_code}'. Defaulting to 0.")
        return decimal.Decimal("0.00")
    else:
        raise NotImplementedError(f"Calculation method {fee_config.calculation_method.value} not implemented.")

def calculate_fees_for_context(db: Session, context: schemas.FeeCalculationContext) -> schemas.FeeCalculationResponse:
    active_fee_configs = db.query(models.FeeConfig).filter(
        models.FeeConfig.is_active == True,
        models.FeeConfig.currency == ModelCurrencyEnum[context.transaction_currency.value],
        models.FeeConfig.valid_from <= date.today(),
        or_(models.FeeConfig.valid_to == None, models.FeeConfig.valid_to >= date.today()),
    ).all()

    calculated_details: List[schemas.CalculatedFeeDetail] = []
    overall_total_fees_after_waivers = decimal.Decimal("0.00")
    overall_total_taxes = decimal.Decimal("0.00")

    # Separate primary fees from tax fees to handle linked taxes correctly
    primary_fee_configs = []
    tax_fee_configs_map: Dict[str, models.FeeConfig] = {}

    for fc in active_fee_configs:
        if fc.fee_type == ModelFeeTypeEnum.TAX:
            tax_fee_configs_map[fc.fee_code] = fc
        else:
            primary_fee_configs.append(fc)

    for fee_conf in primary_fee_configs:
        # --- Applicability Check (Crucial & Complex) ---
        # This needs to parse fee_conf.applicable_context_json and match against context.*
        # Example:
        # context_match = True
        # if fee_conf.applicable_context_json:
        #     rules = json.loads(fee_conf.applicable_context_json)
        #     if rules.get("transaction_type") and rules["transaction_type"] != context.transaction_type:
        #         context_match = False
        #     # ... more rule checks for channel, customer_segment, amount ranges etc. ...
        # if not context_match:
        #     continue
        # For mock purposes, assume all primary_fee_configs fetched are applicable for now

        gross_fee = _calculate_single_fee(fee_conf, context.transaction_amount)

        # TODO: Apply Waivers (fetch FeeWaiverPromo, check criteria, calculate discount)
        net_fee_after_waiver = gross_fee
        waiver_promo_code_applied = None
        discount_amount_applied = decimal.Decimal("0.00")

        tax_on_this_fee = decimal.Decimal("0.00")
        if fee_conf.linked_tax_fee_code and fee_conf.linked_tax_fee_code in tax_fee_configs_map:
            tax_config = tax_fee_configs_map[fee_conf.linked_tax_fee_code]
            # Tax is usually calculated on the net fee (after discount/waiver)
            tax_on_this_fee = _calculate_single_fee(tax_config, net_fee_after_waiver)

        total_deduction_item = net_fee_after_waiver + tax_on_this_fee

        if total_deduction_item > decimal.Decimal("0.00"): # Only add if there's something to charge
            calculated_details.append(schemas.CalculatedFeeDetail(
                fee_code=fee_conf.fee_code,
                description=fee_conf.description,
                gross_fee_amount=gross_fee,
                tax_amount_on_fee=tax_on_this_fee,
                waiver_applied_promo_code=waiver_promo_code_applied,
                discount_amount=discount_amount_applied,
                final_fee_amount_after_waiver=net_fee_after_waiver,
                total_deduction_for_this_item=total_deduction_item,
                currency=schemas.CurrencySchema(fee_conf.currency.value) # Use schema enum
            ))
            overall_total_fees_after_waivers += net_fee_after_waiver
            overall_total_taxes += tax_on_this_fee

    # Handle standalone taxes (e.g. Stamp Duty not linked to another fee, but on transaction amount)
    for tax_code, tax_conf in tax_fee_configs_map.items():
        if not tax_conf.linked_tax_fee_code: # Process only if not already handled as a linked tax
            # TODO: Check applicability for this standalone tax based on its own applicable_context_json
            # Example: Stamp Duty on N10,000+ transactions
            # if tax_conf.fee_code == "STAMP_DUTY_NGN_10K_PLUS" and context.transaction_amount >= decimal.Decimal("10000.00"):
            #     stamp_duty_amount = _calculate_single_fee(tax_conf, context.transaction_amount) # Tiered flat N50
            #     if stamp_duty_amount > 0:
            #         calculated_details.append(schemas.CalculatedFeeDetail(...)) # Add as a fee item
            #         overall_total_taxes += stamp_duty_amount
            pass # Placeholder for standalone tax logic

    return schemas.FeeCalculationResponse(
        context=context,
        applicable_fees=calculated_details,
        overall_total_fees_after_waivers=overall_total_fees_after_waivers,
        overall_total_taxes=overall_total_taxes,
        overall_grand_total_deducted=overall_total_fees_after_waivers + overall_total_taxes
    )

def apply_and_log_fees(
    db: Session, financial_transaction_id: str,
    calculated_fees_response: schemas.FeeCalculationResponse, # Contains context and list of fees
    account_id_to_debit_fee: Optional[int], # DB ID of account
    applied_by_user_id: str
) -> List[models.AppliedFeeLog]:

    applied_fee_log_objects: List[models.AppliedFeeLog] = []
    # ft_main = get_financial_transaction_by_id(db, financial_transaction_id) # From TM
    # if not ft_main: raise NotFoundException(f"Main FT {financial_transaction_id} not found for fee application.")

    # debit_account_model = None
    # if account_id_to_debit_fee:
    #     debit_account_model = alm_get_account_by_id_internal(db, account_id_to_debit_fee, for_update=True) # From ALM
    #     if not debit_account_model: raise NotFoundException(f"Account ID {account_id_to_debit_fee} for fee debit not found.")
        # Check balance, status etc.

    for fee_detail in calculated_fees_response.applicable_fees:
        if fee_detail.total_deduction_for_this_item <= decimal.Decimal("0.00"):
            continue # Skip if nothing to charge for this item

        fee_config_model = get_fee_config_by_code(db, fee_detail.fee_code) # Fetch original FeeConfig
        if not fee_config_model: continue # Should not happen if calculate_fees worked

        fee_ft_id_actual, tax_ft_id_actual = None, None

        # Conceptual: Post Fee component to ledger
        # if fee_detail.final_fee_amount_after_waiver > 0 and account_id_to_debit_fee:
        #     fee_ft_id_actual = f"FEE_{financial_transaction_id}_{fee_detail.fee_code[:15]}" # Create unique FT ID for this fee posting
        #     ledger_req_fee = ALMInternalTransactionPostingRequest(
        #         financial_transaction_id=fee_ft_id_actual,
        #         debit_leg={"account_id": account_id_to_debit_fee, "narration": f"Fee: {fee_detail.description}"},
        #         credit_leg={"gl_code": fee_config_model.fee_income_gl_code, "narration": f"Fee Income: {fee_detail.description}"},
        #         amount=fee_detail.final_fee_amount_after_waiver, currency=schemas.CurrencySchema(fee_detail.currency.value),
        #         narration_overall=f"Fee for FT {financial_transaction_id}: {fee_detail.fee_code}", channel="SYSTEM_FEE"
        #     )
        #     # try: post_internal_transaction(db, ledger_req_fee)
        #     # except Exception as e: # Handle insufficient funds, log AppliedFeeLog as FAILED_INSUFFICIENT_FUNDS

        # Conceptual: Post Tax component to ledger
        # if fee_detail.tax_amount_on_fee > 0 and account_id_to_debit_fee:
        #     tax_ft_id_actual = f"TAX_{financial_transaction_id}_{fee_detail.fee_code[:15]}"
        #     # ... similar ledger_req_tax and post_internal_transaction ...

        log_entry = models.AppliedFeeLog(
            fee_config_id=fee_config_model.id, fee_code_applied=fee_detail.fee_code,
            financial_transaction_id=financial_transaction_id,
            customer_id=calculated_fees_response.context.customer_id, # From context
            account_id=account_id_to_debit_fee,
            base_amount_for_calc=calculated_fees_response.context.transaction_amount, # Base amount from context
            original_calculated_fee=fee_detail.gross_fee_amount,
            net_fee_charged=fee_detail.final_fee_amount_after_waiver,
            tax_amount_on_fee=fee_detail.tax_amount_on_fee,
            total_charged_to_customer=fee_detail.total_deduction_for_this_item,
            currency=ModelCurrencyEnum[fee_detail.currency.value], # Store model enum
            status="APPLIED_SUCCESSFULLY", # Update if ledger posting fails
            fee_ledger_transaction_id=fee_ft_id_actual,
            tax_ledger_transaction_id=tax_ft_id_actual,
            # waiver_promo_id = ... # If fee_detail contains waiver_promo_id
            applied_at=datetime.utcnow()
        )
        db.add(log_entry)
        applied_fee_log_objects.append(log_entry)

    if applied_fee_log_objects:
        _log_fee_event(db, "FEES_APPLIED_AND_LOGGED", financial_transaction_id, {"count": len(applied_fee_log_objects)}, applied_by_user_id)
        db.commit()
        # for log in applied_fee_log_objects: db.refresh(log)
    return applied_fee_log_objects

# --- FeeWaiverPromo Services (Admin/Setup) ---
# ... (CRUD services for FeeWaiverPromo: create, get, update, list) ...
# These would be similar to FeeConfig CRUD, handling JSON for applicable_criteria_json.
# The calculate_fees_for_context service needs to query active waivers and apply them.
# This part is complex and involves matching waiver criteria against fee context.
# For now, waiver application logic in calculate_fees_for_context is a placeholder.
