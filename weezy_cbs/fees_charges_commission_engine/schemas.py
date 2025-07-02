# Pydantic schemas for Fees, Charges & Commission Engine
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import decimal

from .models import FeeTypeEnum, FeeCalculationMethodEnum, CurrencyEnum # Import enums

# --- FeeConfig Schemas (Admin/Setup) ---
class FeeTierSchema(BaseModel): # For TIERED_FLAT or TIERED_PERCENTAGE
    min_amount: decimal.Decimal = Field(..., ge=0)
    max_amount: Optional[decimal.Decimal] = Field(None, ge=0) # Null for last tier's max
    fee_or_rate: decimal.Decimal = Field(..., ge=0) # Actual fee for TIERED_FLAT, rate for TIERED_PERCENTAGE

    @validator('max_amount')
    def max_must_be_gt_min(cls, v, values):
        if v is not None and 'min_amount' in values and v < values['min_amount']:
            raise ValueError('max_amount in tier must be greater than or equal to min_amount')
        return v

class FeeConfigBase(BaseModel):
    fee_code: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Z0-9_]+$")
    description: str
    fee_type: FeeTypeEnum
    # applicable_context_json: Optional[Dict[str, Any]] = Field({}, description="JSON defining when this fee applies")
    calculation_method: FeeCalculationMethodEnum
    flat_amount: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=2)
    percentage_rate: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=6, description="e.g., 0.005 for 0.5%") # Allow more precision for rates
    tiers_json: Optional[List[FeeTierSchema]] = Field(None, min_items=1) # List of tier definitions
    currency: CurrencyEnum
    # fee_income_gl_code: str
    # tax_payable_gl_code: Optional[str] = None
    is_active: bool = True
    valid_from: Optional[date] = None # Defaults to today if not provided
    valid_to: Optional[date] = None

    @validator('flat_amount', always=True)
    def validate_flat_amount(cls, v, values):
        if values.get('calculation_method') == FeeCalculationMethodEnum.FLAT and v is None:
            raise ValueError('flat_amount is required for FLAT calculation method')
        return v

    @validator('percentage_rate', always=True)
    def validate_percentage_rate(cls, v, values):
        if values.get('calculation_method') == FeeCalculationMethodEnum.PERCENTAGE and v is None:
            raise ValueError('percentage_rate is required for PERCENTAGE calculation method')
        return v

    @validator('tiers_json', always=True)
    def validate_tiers_json(cls, v, values):
        method = values.get('calculation_method')
        if method in [FeeCalculationMethodEnum.TIERED_FLAT, FeeCalculationMethodEnum.TIERED_PERCENTAGE] and not v:
            raise ValueError('tiers_json is required for TIERED calculation methods')
        if v: # Further validation for tiers (e.g., non-overlapping, sorted) can be added
            # Ensure max_amount of a tier is not less than min_amount
            # Ensure min_amount of next tier starts after max_amount of previous (or is contiguous)
            pass
        return v

class FeeConfigCreateRequest(FeeConfigBase):
    pass

class FeeConfigResponse(FeeConfigBase):
    id: int
    # applicable_context_json: Dict[str, Any] # Already in base, will be parsed from Text by Pydantic
    # tiers_json: Optional[List[FeeTierSchema]] # Already in base, parsed from Text
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

# --- AppliedFeeLog Schemas ---
class AppliedFeeLogResponse(BaseModel):
    id: int
    fee_code_applied: str
    source_transaction_reference: Optional[str] = None
    customer_bvn_or_id: Optional[str] = None
    account_number_debited: Optional[str] = None
    base_amount_for_calc: Optional[decimal.Decimal] = None
    calculated_fee_amount: decimal.Decimal
    # calculated_tax_amount: Optional[decimal.Decimal] = None
    # total_charged_amount: decimal.Decimal
    currency: CurrencyEnum
    status: str
    # fee_ledger_tx_id: Optional[str] = None
    # tax_ledger_tx_id: Optional[str] = None
    applied_at: datetime
    # waiver_id: Optional[int] = None

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

# --- FeeWaiverPromo Schemas (Admin/Setup) ---
class FeeWaiverPromoBase(BaseModel):
    promo_code: str = Field(..., min_length=3, pattern=r"^[A-Z0-9_]+$")
    description: str
    # fee_code_to_waive: Optional[str] = None # Specific fee code
    # applicable_criteria_json: Optional[Dict[str, Any]] = Field({}, description="Criteria for waiver applicability")
    waiver_type: str = "FULL_WAIVER" # FULL_WAIVER, PERCENTAGE_DISCOUNT, FIXED_AMOUNT_DISCOUNT
    discount_percentage: Optional[decimal.Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    discount_fixed_amount: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=2)
    is_active: bool = True
    start_date: datetime
    end_date: datetime
    # max_waivers_total: Optional[int] = Field(None, gt=0)
    # max_waivers_per_customer: Optional[int] = Field(None, gt=0)

class FeeWaiverPromoCreateRequest(FeeWaiverPromoBase):
    pass

class FeeWaiverPromoResponse(FeeWaiverPromoBase):
    id: int
    # current_waivers_total_count: int
    created_at: datetime

    class Config:
        orm_mode = True
        json_encoders = { decimal.Decimal: str }


# --- Fee Calculation Request/Response (Conceptual for a fee calculation endpoint) ---
class FeeCalculationContext(BaseModel): # Data provided to the engine to calculate fees
    transaction_type: str # e.g., "NIP_TRANSFER", "SMS_NOTIFICATION", "ACCOUNT_MAINTENANCE"
    transaction_amount: Optional[decimal.Decimal] = None # Base amount for percentage fees
    transaction_currency: CurrencyEnum = CurrencyEnum.NGN
    # customer_id: Optional[int] = None
    # account_id: Optional[int] = None
    # product_code: Optional[str] = None # e.g., for account product specific fees
    # channel: Optional[str] = None # e.g., "MOBILE_APP", "USSD", "BRANCH"
    # other_context_params: Optional[Dict[str, Any]] = None # For very specific rules

class CalculatedFeeDetail(BaseModel):
    fee_code: str
    description: str
    original_fee_amount: decimal.Decimal
    # tax_on_fee_amount: Optional[decimal.Decimal] = decimal.Decimal("0.0")
    waiver_applied_promo_code: Optional[str] = None
    discount_amount: Optional[decimal.Decimal] = decimal.Decimal("0.0")
    net_fee_charged: decimal.Decimal # Original_fee - discount
    # total_charge_to_customer: decimal.Decimal # net_fee_charged + tax_on_fee_amount
    currency: CurrencyEnum

    class Config:
        json_encoders = { decimal.Decimal: str }

class FeeCalculationResponse(BaseModel):
    context: FeeCalculationContext
    applicable_fees: List[CalculatedFeeDetail]
    total_fees_charged: decimal.Decimal # Sum of net_fee_charged for all items
    # total_taxes_charged: decimal.Decimal # Sum of tax_on_fee_amount
    # grand_total_deducted: decimal.Decimal # Sum of total_charge_to_customer

    class Config:
        json_encoders = { decimal.Decimal: str }

class PaginatedFeeConfigResponse(BaseModel):
    items: List[FeeConfigResponse]
    total: int
    page: int
    size: int

class PaginatedAppliedFeeLogResponse(BaseModel):
    items: List[AppliedFeeLogResponse]
    total: int
    page: int
    size: int

class PaginatedFeeWaiverPromoResponse(BaseModel):
    items: List[FeeWaiverPromoResponse]
    total: int
    page: int
    size: int
