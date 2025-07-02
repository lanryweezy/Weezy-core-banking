# Pydantic schemas for Deposit & Collection Module
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
import decimal

from .models import DepositTypeEnum, DepositStatusEnum, CurrencyEnum # Import enums

# --- Cash Deposit Schemas ---
class CashDepositBase(BaseModel):
    account_number: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{10}$")
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencyEnum = CurrencyEnum.NGN
    depositor_name: Optional[str] = Field(None, min_length=2)
    depositor_phone: Optional[str] = Field(None, pattern=r"^\+?\d{10,15}$") # Basic phone validation
    notes: Optional[str] = None

class CashDepositCreateRequest(CashDepositBase):
    # teller_id: str # Usually from authenticated teller/agent context
    # branch_code: str # Usually from teller/agent context
    agent_id_external: Optional[str] = None # For SANEF agent deposits
    agent_terminal_id: Optional[str] = None

class CashDepositResponse(CashDepositBase):
    id: int
    # financial_transaction_id: Optional[str] = None
    teller_id: Optional[str] = None
    branch_code: Optional[str] = None
    status: DepositStatusEnum
    deposit_date: datetime
    agent_id_external: Optional[str] = None
    agent_terminal_id: Optional[str] = None

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

# --- Cheque Deposit Schemas ---
class ChequeDepositBase(BaseModel):
    account_number: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{10}$") # Beneficiary account
    cheque_number: str = Field(..., min_length=6) # Basic length validation
    drawee_bank_code: str = Field(..., description="CBN Bank code of the cheque's bank")
    drawee_account_number: Optional[str] = None
    drawer_name: Optional[str] = None
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencyEnum = CurrencyEnum.NGN # Usually NGN for local cheques
    depositor_name: Optional[str] = None
    # cheque_image_front_url: Optional[HttpUrl] = None # If client uploads image and sends URL
    # cheque_image_back_url: Optional[HttpUrl] = None

class ChequeDepositCreateRequest(ChequeDepositBase):
    # teller_id: str
    # branch_code: str
    pass

class ChequeDepositResponse(ChequeDepositBase):
    id: int
    # financial_transaction_id: Optional[str] = None
    teller_id: Optional[str] = None
    branch_code: Optional[str] = None
    status: DepositStatusEnum
    deposit_date: datetime
    clearing_date_expected: Optional[datetime] = None
    cleared_date_actual: Optional[datetime] = None

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

class ChequeStatusUpdateRequest(BaseModel):
    new_status: DepositStatusEnum # e.g. COMPLETED, FAILED
    reason_for_failure: Optional[str] = None # If status is FAILED
    actual_cleared_date: Optional[datetime] = None # If status is COMPLETED

# --- Collection Service Schemas (Admin/Setup) ---
class CollectionServiceBase(BaseModel):
    service_name: str = Field(..., min_length=3)
    merchant_id_external: str = Field(..., description="Merchant's unique ID with the bank")
    # merchant_account_id: int # Bank account ID where funds are settled
    is_active: bool = True
    # validation_endpoint: Optional[HttpUrl] = None
    # fee_config_id: Optional[int] = None

class CollectionServiceCreateRequest(CollectionServiceBase):
    pass

class CollectionServiceResponse(CollectionServiceBase):
    id: int
    class Config:
        orm_mode = True

# --- Collection Payment Schemas ---
class CollectionPaymentBase(BaseModel):
    # collection_service_id: int # Usually from path parameter
    payer_name: Optional[str] = None
    payer_phone: Optional[str] = None
    payer_email: Optional[str] = None # Pydantic EmailStr for validation
    customer_identifier_at_merchant: str = Field(..., description="e.g., Student ID, Meter No")
    amount_paid: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencyEnum = CurrencyEnum.NGN
    payment_channel: Optional[str] = None # e.g. "BRANCH_TELLER", "AGENT_PORTAL"
    payment_reference_external: Optional[str] = None # Ref from payment channel/gateway

class CollectionPaymentCreateRequest(CollectionPaymentBase):
    pass

class CollectionPaymentResponse(CollectionPaymentBase):
    id: int
    # financial_transaction_id: Optional[str] = None
    collection_service_id: int
    status: str # PENDING, SUCCESSFUL, FAILED
    payment_date: datetime
    # is_settled_to_merchant: bool
    # settlement_date: Optional[datetime] = None

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

# --- POS Reconciliation Schemas (Internal/Admin) ---
class POSReconciliationBatchCreate(BaseModel):
    batch_date: date # The date for which reconciliation is being done
    source_file_name: Optional[str] = None # Name of uploaded file from acquirer
    # File content itself would be handled via file upload mechanism

class POSReconciliationBatchResponse(BaseModel):
    id: int
    batch_date: datetime # Changed to datetime to match model
    source_file_name: Optional[str] = None
    status: str
    total_transactions_in_file: Optional[int] = None
    total_amount_in_file: Optional[decimal.Decimal] = None
    matched_transactions_count: int
    unmatched_transactions_count: int
    discrepancy_amount: decimal.Decimal
    processed_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_encoders = { decimal.Decimal: str }

class POSReconciliationDiscrepancyResponse(BaseModel):
    id: int
    batch_id: int
    # financial_transaction_id: Optional[str] = None
    external_transaction_reference: Optional[str] = None
    discrepancy_type: str
    details: Optional[str] = None
    status: str
    resolved_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class PaginatedCashDepositResponse(BaseModel):
    items: List[CashDepositResponse]
    total: int
    page: int
    size: int

class PaginatedChequeDepositResponse(BaseModel):
    items: List[ChequeDepositResponse]
    total: int
    page: int
    size: int

class PaginatedCollectionPaymentResponse(BaseModel):
    items: List[CollectionPaymentResponse]
    total: int
    page: int
    size: int
