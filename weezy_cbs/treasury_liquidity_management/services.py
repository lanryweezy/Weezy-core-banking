# Service layer for Treasury & Liquidity Management Module
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from . import models, schemas
from .models import CurrencyEnum, FXTransactionTypeEnum # Direct enum access
import decimal
import uuid
from datetime import datetime, date, timedelta
from math import pow

# Placeholder for other service integrations & data sources
# from weezy_cbs.accounts_ledger_management.services import get_total_balance_for_gl_code, post_double_entry_transaction
# from weezy_cbs.accounts_ledger_management.schemas import PostTransactionRequest as LedgerPostRequest
# from weezy_cbs.shared import exceptions

class NotFoundException(Exception): pass
class InvalidOperationException(Exception): pass
class CalculationException(Exception): pass

def _generate_deal_reference(prefix="TRSYDEAL"):
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"

# --- Bank Cash Position Services ---
def record_daily_cash_position(db: Session, position_data: schemas.BankCashPositionCreate) -> models.BankCashPosition:
    existing_position = db.query(models.BankCashPosition).filter(
        models.BankCashPosition.position_date == position_data.position_date,
        models.BankCashPosition.currency == position_data.currency
    ).first()
    if existing_position:
        # Update existing record for the day or raise error, depending on policy
        # For now, let's assume we overwrite/update if called again for same day/currency
        for key, value in position_data.dict(exclude_unset=True).items():
            setattr(existing_position, key, value)
        existing_position.calculated_at = datetime.utcnow()
        db_position = existing_position
    else:
        db_position = models.BankCashPosition(**position_data.dict())
        db.add(db_position)

    db.commit()
    db.refresh(db_position)
    return db_position

def get_cash_position(db: Session, position_date: date, currency: CurrencyEnum) -> Optional[models.BankCashPosition]:
    return db.query(models.BankCashPosition).filter(
        models.BankCashPosition.position_date == position_date,
        models.BankCashPosition.currency == currency
    ).first()

def get_latest_cash_position(db: Session, currency: CurrencyEnum) -> Optional[models.BankCashPosition]:
    return db.query(models.BankCashPosition).filter(
        models.BankCashPosition.currency == currency
    ).order_by(models.BankCashPosition.position_date.desc()).first()

# --- FX Transaction Services ---
def create_fx_transaction(db: Session, fx_deal_in: schemas.FXTransactionCreateRequest, user_id: str) -> models.FXTransaction:
    # Basic validation: sell_amount should correspond to buy_amount * rate (or inverse)
    # This can be complex due to which currency is base in the pair and rounding.
    # For simplicity, assume inputs are consistent or one is calculated from others client-side.
    # A more robust validation would be:
    # pair_base, pair_quote = fx_deal_in.currency_pair.split('/')
    # if fx_deal_in.buy_currency.value == pair_base: # e.g. Buying USD in USD/NGN, rate is NGN per USD
    #    calculated_sell = fx_deal_in.buy_amount * fx_deal_in.rate
    #    if abs(calculated_sell - fx_deal_in.sell_amount) > decimal.Decimal('0.01'): # Tolerance for rounding
    #        raise InvalidOperationException("Sell amount does not match buy amount and rate.")
    # elif fx_deal_in.sell_currency.value == pair_base: # e.g. Selling USD in USD/NGN
    #    calculated_buy = fx_deal_in.sell_amount * fx_deal_in.rate
    #    # etc.

    deal_ref = fx_deal_in.deal_reference or _generate_deal_reference("FX")
    db_fx_deal = models.FXTransaction(
        deal_reference=deal_ref,
        created_by_user_id=user_id,
        **fx_deal_in.dict(exclude={"deal_reference"}) # Exclude if None, already handled
    )
    db.add(db_fx_deal)
    db.commit()
    db.refresh(db_fx_deal)

    # TODO: Trigger settlement process (ledger postings for value_date)
    # This might involve creating pending ledger entries or notifications.
    return db_fx_deal

def get_fx_transaction(db: Session, deal_id: Optional[int] = None, deal_reference: Optional[str] = None) -> Optional[models.FXTransaction]:
    if deal_id:
        return db.query(models.FXTransaction).filter(models.FXTransaction.id == deal_id).first()
    if deal_reference:
        return db.query(models.FXTransaction).filter(models.FXTransaction.deal_reference == deal_reference).first()
    return None

def update_fx_transaction_status(db: Session, deal_id: int, update_data: schemas.FXTransactionStatusUpdate) -> models.FXTransaction:
    deal = db.query(models.FXTransaction).filter(models.FXTransaction.id == deal_id).with_for_update().first()
    if not deal:
        raise NotFoundException(f"FX Deal with ID {deal_id} not found.")

    deal.status = update_data.new_status
    if update_data.new_status == "SETTLED":
        deal.settled_at = datetime.utcnow()
        # TODO: Confirm ledger postings for settlement are complete.
        # This status update might be triggered BY successful ledger posting.

    db.commit()
    db.refresh(deal)
    return deal

# --- Treasury Bill Investment Services ---
def _calculate_tbill_purchase_price(face_value: decimal.Decimal, discount_rate_pa: decimal.Decimal, tenor_days: int) -> decimal.Decimal:
    # Purchase Price = FaceValue / (1 + (DiscountRate * (TenorDays / 365))) -- if discount is like simple interest for period
    # Or more commonly for T-Bills (true discount): Price = FV * (1 - (DiscountRate * TenorDays / 365))
    # Using the true discount formula:
    if tenor_days <= 0 or face_value <= 0:
        raise CalculationException("Tenor and face value must be positive for T-Bill calculation.")

    # Convert discount_rate_pa from percentage to decimal
    discount_decimal = discount_rate_pa / decimal.Decimal('100')

    # purchase_price = face_value * (decimal.Decimal('1') - (discount_decimal * (decimal.Decimal(tenor_days) / decimal.Decimal('365'))))
    # Using the yield to maturity formula for price, which is more common for how T-Bills are quoted:
    # Price = FaceValue / (1 + (Yield * Tenor / DaysInYear))
    # If `discount_rate_pa` is actually a "discount rate" as in DBR (Discount Basis Rate):
    # Discount Amount = FaceValue * DiscountRate * Tenor / 360 (or 365/366)
    # Price = FaceValue - Discount Amount
    # Let's use the common market convention: Discount = FV * rate * (days/year_basis)
    # Assuming year_basis is 365 for NGN T-bills. CBN might specify 360 for some contexts.
    year_basis = decimal.Decimal('365')
    discount_amount = face_value * discount_decimal * (decimal.Decimal(tenor_days) / year_basis)
    purchase_price = face_value - discount_amount

    return purchase_price.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)


def create_tbill_investment(db: Session, tbill_in: schemas.TreasuryBillInvestmentCreateRequest) -> models.TreasuryBillInvestment:
    if tbill_in.purchase_price is None:
        purchase_price = _calculate_tbill_purchase_price(
            tbill_in.face_value, tbill_in.discount_rate_pa, tbill_in.tenor_days
        )
    else:
        purchase_price = tbill_in.purchase_price
        # Optionally, validate provided purchase_price against calculated one with a tolerance

    ref = tbill_in.investment_reference or _generate_deal_reference("TBILL")
    db_tbill = models.TreasuryBillInvestment(
        investment_reference=ref,
        purchase_price=purchase_price,
        **tbill_in.dict(exclude={"investment_reference", "purchase_price"}) # Exclude already handled fields
    )
    db.add(db_tbill)

    # TODO: Trigger ledger posting for purchase (Debit Investment GL, Credit Nostro/CBN account)
    # post_ledger_for_tbill_purchase(db, db_tbill)

    db.commit()
    db.refresh(db_tbill)
    return db_tbill

def get_tbill_investment(db: Session, investment_id: Optional[int] = None, reference: Optional[str] = None) -> Optional[models.TreasuryBillInvestment]:
    if investment_id:
        return db.query(models.TreasuryBillInvestment).filter(models.TreasuryBillInvestment.id == investment_id).first()
    if reference:
        return db.query(models.TreasuryBillInvestment).filter(models.TreasuryBillInvestment.investment_reference == reference).first()
    return None

def mark_tbill_matured(db: Session, investment_id: int) -> models.TreasuryBillInvestment:
    tbill = db.query(models.TreasuryBillInvestment).filter(models.TreasuryBillInvestment.id == investment_id).with_for_update().first()
    if not tbill:
        raise NotFoundException(f"T-Bill investment {investment_id} not found.")
    if tbill.status != "ACTIVE":
        raise InvalidOperationException(f"T-Bill is not active, current status: {tbill.status}")
    if tbill.maturity_date > date.today(): # Check if it's actually matured
        raise InvalidOperationException(f"T-Bill maturity date {tbill.maturity_date} is in the future.")

    tbill.status = "MATURED"
    tbill.matured_at = datetime.utcnow()

    # TODO: Trigger ledger posting for maturity (Debit Nostro/CBN account, Credit Investment GL, Credit P&L for interest/gain)
    # post_ledger_for_tbill_maturity(db, tbill)

    db.commit()
    db.refresh(tbill)
    return tbill

# --- Interbank Placement Services ---
def create_interbank_placement(db: Session, placement_in: schemas.InterbankPlacementCreateRequest) -> models.InterbankPlacement:
    # Calculate tenor_days if not provided but start/end dates are
    if not placement_in.tenor_days and placement_in.placement_date and placement_in.maturity_date:
        placement_in.tenor_days = (placement_in.maturity_date - placement_in.placement_date).days
    elif placement_in.tenor_days and placement_in.placement_date and not placement_in.maturity_date:
         placement_in.maturity_date = placement_in.placement_date + timedelta(days=placement_in.tenor_days)
    # Add more date logic/validation as needed

    ref = placement_in.deal_reference or _generate_deal_reference("IBP")
    db_placement = models.InterbankPlacement(
        deal_reference=ref,
        **placement_in.dict(exclude={"deal_reference"})
    )
    db.add(db_placement)

    # TODO: Trigger ledger posting for placement
    # If LENDING: Debit Interbank Placement Asset GL, Credit Nostro/CBN
    # If BORROWING: Debit Nostro/CBN, Credit Interbank Borrowing Liability GL
    # post_ledger_for_interbank_placement(db, db_placement)

    db.commit()
    db.refresh(db_placement)
    return db_placement

# --- Liquidity Forecasting (Conceptual) ---
def generate_liquidity_forecast(db: Session, forecast_request: schemas.LiquidityForecastRequest) -> schemas.LiquidityForecastResponse:
    """
    Generates a simplified liquidity gap forecast.
    This is highly conceptual and would involve complex data gathering in a real system.
    """
    gaps = []
    # Example tenor buckets
    tenor_buckets_days = {"Overnight": 1, "2D-7D": 7, "8D-1M": 30, "1M-3M": 90}

    cumulative_gap = decimal.Decimal("0.0")

    for bucket_name, max_days in tenor_buckets_days.items():
        if max_days > forecast_request.projection_days and bucket_name != "Overnight": # Adjust if projection is shorter
            if forecast_request.projection_days <= 1 and bucket_name != "Overnight": continue # Skip if projection is only overnight
            # max_days = forecast_request.projection_days # This logic needs refinement for ranges

        start_date_bucket = forecast_request.forecast_date
        if bucket_name != "Overnight": # For > overnight, start from day after previous bucket
            # This logic is too simple for actual gap analysis which uses specific maturity dates of items
            # For a real system, you'd query all assets/liabilities maturing in each bucket's date range.
            pass

        # Mock inflows/outflows for the bucket
        # Inflows: maturing T-Bills, maturing interbank lending, expected loan repayments, new deposits (projected)
        # Outflows: maturing interbank borrowing, maturing repos, expected loan disbursements, deposit withdrawals (projected)
        mock_inflows = decimal.Decimal(random.uniform(1000000, 50000000))
        mock_outflows = decimal.Decimal(random.uniform(1000000, 45000000))

        net_gap_bucket = mock_inflows - mock_outflows
        cumulative_gap += net_gap_bucket

        gaps.append(schemas.LiquidityGap(
            tenor_bucket=bucket_name,
            inflows=mock_inflows,
            outflows=mock_outflows,
            net_gap=net_gap_bucket,
            cumulative_gap=cumulative_gap
        ))

        if max_days >= forecast_request.projection_days: # Stop if we've covered the projection period
            break

    return schemas.LiquidityForecastResponse(
        forecast_as_of_date=forecast_request.forecast_date,
        gaps=gaps
    )

# Other services:
# - CBN Repo operations management
# - Reconciliation with CBN statements (RTGS, CRR) - this is a batch process.
# - Managing limits with correspondent banks.
# - FX position monitoring and revaluation.
# - Interest rate risk / ALM reporting data feeds.
