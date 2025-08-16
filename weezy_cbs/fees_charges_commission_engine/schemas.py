# Pydantic schemas for Fees, Charges & Commission Engine
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import decimal
import enum # For Pydantic enums

# Import enums from models to ensure consistency
from .models import (
    FeeTypeEnum as ModelFeeTypeEnum,
    FeeCalculationMethodEnum as ModelFeeCalculationMethodEnum,
    CurrencyEnum as ModelCurrencyEnum
)

# Schema Enums
class CurrencySchema(str, enum.Enum): # Replicated for independence
    NGN = "NGN"; USD = "USD"

class FeeTypeSchema(str, enum.Enum):
    TRANSACTION_FEE = "TRANSACTION_FEE"; SERVICE_CHARGE = "SERVICE_CHARGE"
    COMMISSION = "COMMISSION"; PENALTY = "PENALTY"; TAX = "TAX"
    GOVERNMENT_LEVY = "GOVERNMENT_LEVY"

class FeeCalculationMethodSchema(str, enum.Enum):
    FLAT = "FLAT"; PERCENTAGE = "PERCENTAGE"
    TIERED_FLAT = "TIERED_FLAT"; TIERED_PERCENTAGE = "TIERED_PERCENTAGE"

# --- FeeConfig Schemas (Admin/Setup) ---
class FeeTierSchema(BaseModel):
    min_transaction_amount: decimal.Decimal = Field(..., ge=0, decimal_places=2) # Renamed
    max_transaction_amount: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=2) # Renamed
    value: decimal.Decimal = Field(..., ge=0) # Renamed from fee_or_rate, can be amount or rate

    @validator('max_transaction_amount')
    def _max_must_be_gt_min(cls, v, values): # Renamed validator
        if v is not None and 'min_transaction_amount' in values and v < values['min_transaction_amount']:
            raise ValueError('max_transaction_amount in tier must be >= min_transaction_amount')
        return v

class FeeConfigBase(BaseModel):
    fee_code: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Z0-9_]+$")
    description: str = Field(..., max_length=255)
    fee_type: FeeTypeSchema # Use schema enum
    applicable_context_json: Optional[Dict[str, Any]] = Field({}, description="JSON defining when this fee applies")
    calculation_method: FeeCalculationMethodSchema # Use schema enum
    flat_amount: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=2)
    percentage_rate: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=6)
    tiers_json: Optional[List[FeeTierSchema]] = Field(None, min_items=1)
    currency: CurrencySchema # Use schema enum
    fee_income_gl_code: str = Field(..., max_length=20)
    tax_payable_gl_code: Optional[str] = Field(None, max_length=20)
    linked_tax_fee_code: Optional[str] = Field(None, max_length=50)
    is_active: bool = True
    valid_from: Optional[date] = Field(default_factory=date.today) # Default to today
    valid_to: Optional[date] = None

    # Validators refined to use updated field names and check method consistency
    @validator('flat_amount', always=True)
    def _validate_flat_amount(cls, v, values):
        if values.get('calculation_method') == FeeCalculationMethodSchema.FLAT and v is None:
            raise ValueError('flat_amount is required for FLAT method')
        return v
    @validator('percentage_rate', always=True)
    def _validate_percentage_rate(cls, v, values):
        if values.get('calculation_method') == FeeCalculationMethodSchema.PERCENTAGE and v is None:
            raise ValueError('percentage_rate is required for PERCENTAGE method')
        return v
    @validator('tiers_json', always=True)
    def _validate_tiers_json(cls, v, values):
        method = values.get('calculation_method')
        if method in [FeeCalculationMethodSchema.TIERED_FLAT, FeeCalculationMethodSchema.TIERED_PERCENTAGE] and not v:
            raise ValueError('tiers_json is required for TIERED methods')
        # TODO: Add validation for tier consistency (non-overlapping, sorted ranges)
        return v

class FeeConfigCreateRequest(FeeConfigBase):
    pass

class FeeConfigResponse(FeeConfigBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # created_by_user_id: Optional[str] = None # Add if exposing
    # updated_by_user_id: Optional[str] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- AppliedFeeLog Schemas ---
class AppliedFeeLogResponse(BaseModel):
    id: int
    fee_config_id: int
    fee_code_applied: str = Field(..., max_length=50)
    financial_transaction_id: str = Field(..., max_length=40)
    customer_id: Optional[int] = None
    account_id: Optional[int] = None
    source_transaction_reference: Optional[str] = Field(None, max_length=100)
    base_amount_for_calc: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    original_calculated_fee: decimal.Decimal = Field(..., decimal_places=2)
    net_fee_charged: decimal.Decimal = Field(..., decimal_places=2)
    tax_amount_on_fee: Optional[decimal.Decimal] = Field(decimal.Decimal("0.00"), decimal_places=2)
    total_charged_to_customer: decimal.Decimal = Field(..., decimal_places=2)
    currency: CurrencySchema
    status: str = Field(..., max_length=30)
    fee_ledger_transaction_id: Optional[str] = Field(None, max_length=40)
    tax_ledger_transaction_id: Optional[str] = Field(None, max_length=40)
    applied_at: datetime
    waiver_promo_id: Optional[int] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- FeeWaiverPromo Schemas (Admin/Setup) ---
class FeeWaiverPromoBase(BaseModel):
    promo_code: str = Field(..., min_length=3, max_length=30, pattern=r"^[A-Z0-9_]+$")
    description: str
    fee_config_id: Optional[int] = None # Link to specific FeeConfig.id
    # applicable_criteria_json: Optional[Dict[str, Any]] = Field({})
    waiver_type: str = Field("FULL_WAIVER", max_length=30) # Consider Enum
    discount_percentage: Optional[decimal.Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    discount_fixed_amount: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=2)
    is_active: bool = True
    start_date: datetime
    end_date: datetime
    max_waivers_total_limit: Optional[int] = Field(None, gt=0) # Renamed
    max_waivers_per_customer_limit: Optional[int] = Field(None, gt=0) # Renamed

class FeeWaiverPromoCreateRequest(FeeWaiverPromoBase):
    pass

class FeeWaiverPromoResponse(FeeWaiverPromoBase):
    id: int
    current_waivers_total_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # created_by_user_id: Optional[str] = None
    # updated_by_user_id: Optional[str] = None
    class Config: orm_mode = True; json_encoders = {decimal.Decimal: str}

# --- Fee Calculation Request/Response ---
class FeeCalculationContext(BaseModel):
    transaction_type: str
    transaction_amount: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    transaction_currency: CurrencySchema = CurrencySchema.NGN
    customer_id: Optional[int] = None # Added
    account_id: Optional[int] = None # Added
    product_code: Optional[str] = None # Added
    channel: Optional[str] = None # Added
    other_context_params: Optional[Dict[str, Any]] = None # Added

class CalculatedFeeDetail(BaseModel):
    fee_code: str
    description: str
    gross_fee_amount: decimal.Decimal = Field(..., decimal_places=2) # Renamed
    tax_amount_on_fee: decimal.Decimal = Field(decimal.Decimal("0.00"), decimal_places=2) # Added
    waiver_applied_promo_code: Optional[str] = None
    discount_amount: decimal.Decimal = Field(decimal.Decimal("0.00"), decimal_places=2)
    final_fee_amount_after_waiver: decimal.Decimal = Field(..., decimal_places=2) # Renamed
    total_deduction_for_this_item: decimal.Decimal = Field(..., decimal_places=2) # Renamed
    currency: CurrencySchema
    class Config: json_encoders = {decimal.Decimal: str}

class FeeCalculationResponse(BaseModel):
    context: FeeCalculationContext
    applicable_fees: List[CalculatedFeeDetail]
    overall_total_fees_after_waivers: decimal.Decimal = Field(..., decimal_places=2) # Renamed
    overall_total_taxes: decimal.Decimal = Field(..., decimal_places=2) # Renamed
    overall_grand_total_deducted: decimal.Decimal = Field(..., decimal_places=2) # Renamed
    class Config: json_encoders = {decimal.Decimal: str}

# --- Paginated Responses ---
class PaginatedFeeConfigResponse(BaseModel):
    items: List[FeeConfigResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str} # If FeeConfigResponse has Decimals

class PaginatedAppliedFeeLogResponse(BaseModel):
    items: List[AppliedFeeLogResponse]; total: int; page: int; size: int

class PaginatedFeeWaiverPromoResponse(BaseModel):
    items: List[FeeWaiverPromoResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str} # If FeeWaiverPromoResponse has Decimals
