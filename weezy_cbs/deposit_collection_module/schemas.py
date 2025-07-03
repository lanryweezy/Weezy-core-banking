# Pydantic schemas for Deposit & Collection Module
from pydantic import BaseModel, Field, validator, EmailStr, HttpUrl # Added EmailStr, HttpUrl
from typing import Optional, List, Dict, Any # Added Dict, Any
from datetime import datetime, date
import decimal
import enum # For Pydantic enums

# Import enums from models to ensure consistency
from .models import (
    DepositTypeEnum as ModelDepositTypeEnum,
    DepositStatusEnum as ModelDepositStatusEnum,
    CurrencyEnum as ModelCurrencyEnum
)

# Schema Enums
class CurrencySchema(str, enum.Enum): # Replicated for independence
    NGN = "NGN"; USD = "USD"

class DepositTypeSchema(str, enum.Enum):
    CASH = "CASH"; CHEQUE = "CHEQUE"; AGENT_DEPOSIT = "AGENT_DEPOSIT"
    POS_DEPOSIT = "POS_DEPOSIT"; DIRECT_DEBIT_COLLECTION = "DIRECT_DEBIT_COLLECTION"

class DepositStatusSchema(str, enum.Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"; PENDING_CLEARANCE = "PENDING_CLEARANCE"
    COMPLETED = "COMPLETED"; FAILED = "FAILED"; CANCELLED = "CANCELLED"

# --- Cash Deposit Schemas ---
class CashDepositBase(BaseModel):
    account_number: str = Field(..., min_length=10, max_length=20) # Increased length
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN
    depositor_name: Optional[str] = Field(None, min_length=2, max_length=150)
    depositor_phone: Optional[str] = Field(None, pattern=r"^\+?\d{10,15}$")
    notes: Optional[str] = None

class CashDepositCreateRequest(CashDepositBase):
    account_id: int # Added, as it's a FK in model
    # teller_id, branch_code usually from authenticated context
    agent_id_external: Optional[str] = Field(None, max_length=50)
    agent_terminal_id: Optional[str] = Field(None, max_length=30)

class CashDepositResponse(CashDepositBase):
    id: int
    financial_transaction_id: str = Field(..., max_length=40)
    account_id: int
    teller_id: Optional[str] = Field(None, max_length=50)
    branch_code: Optional[str] = Field(None, max_length=10)
    status: DepositStatusSchema
    deposit_date: datetime
    agent_id_external: Optional[str] = Field(None, max_length=50)
    agent_terminal_id: Optional[str] = Field(None, max_length=30)
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- Cheque Deposit Schemas ---
class ChequeDepositBase(BaseModel):
    account_number: str = Field(..., min_length=10, max_length=20)
    cheque_number: str = Field(..., min_length=6, max_length=20)
    drawee_bank_code: str = Field(..., max_length=10, description="CBN Bank code of the cheque's bank")
    drawee_account_number: Optional[str] = Field(None, max_length=20)
    drawer_name: Optional[str] = Field(None, max_length=150)
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN
    depositor_name: Optional[str] = Field(None, max_length=150)
    # cheque_image_front_url: Optional[HttpUrl] = None
    # cheque_image_back_url: Optional[HttpUrl] = None

class ChequeDepositCreateRequest(ChequeDepositBase):
    account_id: int # Added
    pass

class ChequeDepositResponse(ChequeDepositBase):
    id: int
    financial_transaction_id: Optional[str] = Field(None, max_length=40)
    account_id: int
    teller_id: Optional[str] = Field(None, max_length=50)
    branch_code: Optional[str] = Field(None, max_length=10)
    status: DepositStatusSchema
    deposit_date: date # Changed from datetime
    clearing_date_expected: Optional[date] = None # Changed
    cleared_date_actual: Optional[date] = None # Changed
    reason_for_failure: Optional[str] = Field(None, max_length=255)
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

class ChequeStatusUpdateRequest(BaseModel):
    new_status: DepositStatusSchema
    reason_for_failure: Optional[str] = Field(None, max_length=255)
    actual_cleared_date: Optional[date] = None # Changed

# --- Collection Service Schemas (Admin/Setup) ---
class CollectionServiceBase(BaseModel):
    service_name: str = Field(..., min_length=3, max_length=100)
    merchant_id_external: str = Field(..., max_length=50, description="Merchant's unique ID with the bank")
    merchant_account_id: int
    fee_config_code: Optional[str] = None # Link to FeeConfig by code
    is_active: bool = True

class CollectionServiceCreateRequest(CollectionServiceBase):
    pass

class CollectionServiceResponse(CollectionServiceBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: orm_mode = True

# --- Collection Payment Schemas ---
class CollectionPaymentBase(BaseModel):
    payer_name: Optional[str] = Field(None, max_length=150)
    payer_phone: Optional[str] = Field(None, max_length=15)
    payer_email: Optional[EmailStr] = None
    customer_identifier_at_merchant: str = Field(..., max_length=100, description="e.g., Student ID, Meter No")
    amount_paid: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN
    payment_channel: Optional[str] = Field(None, max_length=30)
    payment_reference_external: Optional[str] = Field(None, max_length=100, description="Ref from payment channel/gateway, should be unique if provided")

class CollectionPaymentCreateRequest(CollectionPaymentBase):
    collection_service_id: int # Usually from path parameter in API, but good for service layer
    financial_transaction_id: str # Must be created first by TransactionManagement

class CollectionPaymentResponse(CollectionPaymentBase):
    id: int
    collection_service_id: int
    financial_transaction_id: str = Field(..., max_length=40)
    status: str = Field(..., max_length=20)
    payment_date: datetime
    is_settled_to_merchant: bool
    settlement_batch_id: Optional[str] = Field(None, max_length=50)
    settlement_date: Optional[datetime] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- POS Reconciliation Schemas (Internal/Admin) ---
class POSReconciliationBatchCreateRequest(BaseModel): # Renamed
    batch_date: date
    source_file_name: Optional[str] = Field(None, max_length=255)

class POSReconciliationBatchResponse(BaseModel):
    id: int
    batch_date: date # Changed from datetime
    source_file_name: Optional[str] = None
    status: str = Field(..., max_length=30)
    total_transactions_in_file: Optional[int] = None
    total_amount_in_file: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    matched_transactions_count: int
    unmatched_transactions_count: int
    discrepancy_amount: decimal.Decimal = Field(..., decimal_places=2)
    processed_at: Optional[datetime] = None
    class Config: orm_mode = True; json_encoders = {decimal.Decimal: str}

class POSReconciliationDiscrepancyResponse(BaseModel):
    id: int
    batch_id: int
    financial_transaction_id: Optional[str] = Field(None, max_length=40)
    external_transaction_reference: Optional[str] = Field(None, max_length=50)
    discrepancy_type: str = Field(..., max_length=30)
    details: Optional[str] = None
    status: str = Field(..., max_length=20)
    resolved_at: Optional[datetime] = None
    class Config: orm_mode = True

# --- Paginated Responses ---
class PaginatedCashDepositResponse(BaseModel):
    items: List[CashDepositResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str} # If amounts are decimal

class PaginatedChequeDepositResponse(BaseModel):
    items: List[ChequeDepositResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str}

class PaginatedCollectionPaymentResponse(BaseModel):
    items: List[CollectionPaymentResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str}
