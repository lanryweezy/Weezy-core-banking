# Pydantic schemas for Treasury & Liquidity Management Module
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any # Added Dict, Any
from datetime import datetime, date
import decimal
import enum # For Pydantic enums

# Import enums from models to ensure consistency
from .models import (
    CurrencyEnum as ModelCurrencyEnum,
    FXTransactionTypeEnum as ModelFXTransactionTypeEnum
)

# Schema Enums
class CurrencySchema(str, enum.Enum):
    NGN = "NGN"; USD = "USD"; EUR = "EUR"; GBP = "GBP"

class FXTransactionTypeSchema(str, enum.Enum):
    SPOT = "SPOT"; FORWARD = "FORWARD"; SWAP = "SWAP"


# --- Bank Cash Position Schemas ---
class BankCashPositionBase(BaseModel):
    position_date: date
    currency: CurrencySchema # Use schema enum
    total_cash_at_vault: decimal.Decimal = Field(..., ge=0, decimal_places=2)
    total_cash_at_cbn: decimal.Decimal = Field(..., ge=0, decimal_places=2)
    total_cash_at_correspondent_banks: decimal.Decimal = Field(..., ge=0, decimal_places=2)

class BankCashPositionCreateRequest(BankCashPositionBase): # Renamed
    pass

class BankCashPositionResponse(BankCashPositionBase):
    id: int
    calculated_at: datetime
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- FX Transaction Schemas ---
class FXTransactionBase(BaseModel):
    transaction_type: FXTransactionTypeSchema # Use schema enum
    trade_date: date
    value_date: date
    currency_pair: str = Field(..., min_length=7, max_length=7, pattern=r"^[A-Z]{3}/[A-Z]{3}$")
    rate: decimal.Decimal = Field(..., gt=0, decimal_places=8)
    buy_currency: CurrencySchema
    buy_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    sell_currency: CurrencySchema
    sell_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    counterparty_name: str = Field(..., max_length=100)
    settlement_type: Optional[str] = Field(None, max_length=20)
    status: str = Field("PENDING_SETTLEMENT", max_length=30) # Default for new deals

    @validator('sell_currency')
    def _check_currency_pair_consistency_sell(cls, v, values): # Renamed validator
        if 'currency_pair' in values and 'buy_currency' in values:
            pair_parts = values['currency_pair'].split('/')
            # Ensure buy_currency and sell_currency correctly form the pair
            if not ((values['buy_currency'].value == pair_parts[0] and v.value == pair_parts[1]) or \
                    (values['buy_currency'].value == pair_parts[1] and v.value == pair_parts[0]) ):
                raise ValueError("Buy/Sell currencies must match the currency pair order or inverse.")
            if values['buy_currency'].value == v.value:
                raise ValueError("Buy and Sell currencies cannot be the same in an FX transaction.")
        return v

class FXTransactionCreateRequest(FXTransactionBase):
    deal_reference: Optional[str] = Field(None, max_length=30)

class FXTransactionResponse(FXTransactionBase):
    id: int
    deal_reference: str = Field(..., max_length=30)
    settled_at: Optional[datetime] = None
    created_by_user_id: Optional[str] = Field(None, max_length=50)
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

class FXTransactionStatusUpdateRequest(BaseModel): # Renamed
    new_status: str = Field(..., description="e.g. PENDING_SETTLEMENT, SETTLED, CANCELLED") # Consider an Enum
    settlement_reference: Optional[str] = Field(None, max_length=50)

# --- Treasury Bill Investment Schemas ---
class TreasuryBillInvestmentBase(BaseModel):
    issue_date: date
    maturity_date: date
    tenor_days: int = Field(..., gt=0)
    face_value: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    discount_rate_pa: decimal.Decimal = Field(..., ge=0, le=100, decimal_places=4)
    currency: CurrencySchema = CurrencySchema.NGN
    status: str = Field("ACTIVE", max_length=30)

    @validator('maturity_date')
    def _maturity_must_be_after_issue(cls, v, values): # Renamed
        if 'issue_date' in values and v <= values['issue_date']:
            raise ValueError('Maturity date must be after issue date.')
        return v

class TreasuryBillInvestmentCreateRequest(TreasuryBillInvestmentBase):
    investment_reference: Optional[str] = Field(None, max_length=30)
    purchase_price: Optional[decimal.Decimal] = Field(None, gt=0, decimal_places=2)

class TreasuryBillInvestmentResponse(TreasuryBillInvestmentBase):
    id: int
    investment_reference: str = Field(..., max_length=30)
    purchase_price: decimal.Decimal = Field(..., decimal_places=2)
    matured_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- Interbank Placement Schemas ---
class InterbankPlacementBase(BaseModel):
    placement_type: str = Field(..., max_length=20, description="LENDING or BORROWING")
    counterparty_bank_code: str = Field(..., max_length=10)
    counterparty_bank_name: str = Field(..., max_length=100)
    principal_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema
    interest_rate_pa: decimal.Decimal = Field(..., ge=0, decimal_places=4)
    placement_date: date
    maturity_date: date
    tenor_days: int = Field(..., gt=0)
    status: str = Field("ACTIVE", max_length=30)

class InterbankPlacementCreateRequest(InterbankPlacementBase):
    deal_reference: Optional[str] = Field(None, max_length=30)

class InterbankPlacementResponse(InterbankPlacementBase):
    id: int
    deal_reference: str = Field(..., max_length=30)
    matured_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- CBN Repo Operation Schemas ---
class CBNRepoOperationBase(BaseModel):
    operation_type: str = Field(..., max_length=20, description="REPO or REVERSE_REPO")
    loan_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN
    interest_rate_pa: decimal.Decimal = Field(..., ge=0, decimal_places=4)
    start_date: date
    end_date: date
    tenor_days: int = Field(..., gt=0)
    status: str = Field("ACTIVE", max_length=20)

class CBNRepoOperationCreateRequest(CBNRepoOperationBase):
    operation_reference: Optional[str] = Field(None, max_length=30)

class CBNRepoOperationResponse(CBNRepoOperationBase):
    id: int
    operation_reference: str = Field(..., max_length=30)
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- Liquidity Forecast/Monitoring Schemas ---
class LiquidityForecastRequest(BaseModel):
    forecast_date: date
    projection_days: int = Field(7, gt=0, le=90)

class LiquidityGap(BaseModel):
    tenor_bucket: str
    inflows: decimal.Decimal = Field(..., decimal_places=2)
    outflows: decimal.Decimal = Field(..., decimal_places=2)
    net_gap: decimal.Decimal = Field(..., decimal_places=2)
    cumulative_gap: decimal.Decimal = Field(..., decimal_places=2)
    class Config: json_encoders = {decimal.Decimal: str}


class LiquidityForecastResponse(BaseModel):
    forecast_as_of_date: date
    gaps: List[LiquidityGap]
    # lcr_ratio: Optional[decimal.Decimal] = Field(None, decimal_places=4)
    class Config: json_encoders = {decimal.Decimal: str}

# --- Paginated Responses ---
class PaginatedFXTransactionResponse(BaseModel):
    items: List[FXTransactionResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str}

class PaginatedTreasuryBillInvestmentResponse(BaseModel):
    items: List[TreasuryBillInvestmentResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str}

class PaginatedInterbankPlacementResponse(BaseModel):
    items: List[InterbankPlacementResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str}

# --- Conceptual Schemas for CBN Reconciliation ---
class CBNSettlementStatementEntrySchema(BaseModel):
    statement_date: date
    cbn_reference: str = Field(..., max_length=50)
    narration: Optional[str] = None
    debit_amount: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    credit_amount: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    balance: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    value_date: Optional[date] = None
    # internal_financial_transaction_id: Optional[str] = Field(None, max_length=40)
    # reconciliation_status: str = Field("UNRECONCILED", max_length=20)
    class Config: orm_mode = True; json_encoders = {decimal.Decimal: str}

class CBNReconciliationDiscrepancySchema(BaseModel):
    # settlement_entry_id: Optional[int] = None
    # internal_financial_transaction_id: Optional[str] = None
    discrepancy_type: str = Field(..., max_length=50)
    details: Optional[str] = None
    status: str = Field("OPEN", max_length=20)
    reported_at: datetime
    resolved_at: Optional[datetime] = None
    class Config: orm_mode = True
