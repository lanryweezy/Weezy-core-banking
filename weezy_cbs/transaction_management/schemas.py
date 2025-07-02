# Pydantic schemas for Transaction Management
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
import decimal

from .models import TransactionChannelEnum, TransactionStatusEnum, CurrencyEnum # Import enums

class TransactionBase(BaseModel):
    transaction_type: str = Field(..., description="e.g., 'FUNDS_TRANSFER', 'BILL_PAYMENT'")
    channel: TransactionChannelEnum
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2) # Ensure amount is positive
    currency: CurrencyEnum = CurrencyEnum.NGN

    debit_account_number: Optional[str] = Field(None, min_length=10, max_length=10, pattern=r"^\d{10}$")
    # debit_account_name: Optional[str] = None # Usually fetched, not input by user for their own account
    debit_bank_code: Optional[str] = None # Required for interbank debit if not our bank

    credit_account_number: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{10}$")
    credit_account_name: Optional[str] = None # Can be fetched via name enquiry for interbank
    credit_bank_code: str # Required for interbank, can be own bank code for intrabank

    narration: str = Field(..., min_length=3, max_length=100)

class TransactionCreateRequest(TransactionBase):
    # customer_id: Optional[int] = None # Who is initiating this? Usually from auth context.
    # For USSD, this might be passed if session is not tied to authenticated user.
    pass

class TransactionInitiateResponse(BaseModel):
    transaction_id: str # Our internal master transaction ID
    status: TransactionStatusEnum
    message: str
    initiated_at: datetime
    # May include external reference if immediately available (e.g. for direct gateway call)
    external_transaction_id: Optional[str] = None

class TransactionStatusQueryResponse(BaseModel):
    transaction_id: str
    status: TransactionStatusEnum
    channel: TransactionChannelEnum
    amount: decimal.Decimal
    currency: CurrencyEnum
    narration: str
    initiated_at: datetime
    processed_at: Optional[datetime] = None
    external_system_at: Optional[datetime] = None
    response_code: Optional[str] = None
    response_message: Optional[str] = None
    is_reversal: bool = False
    original_transaction_id: Optional[str] = None

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

class TransactionDetailResponse(TransactionStatusQueryResponse):
    # Includes more details than just status
    debit_account_number: Optional[str] = None
    debit_account_name: Optional[str] = None
    debit_bank_code: Optional[str] = None
    credit_account_number: Optional[str] = None
    credit_account_name: Optional[str] = None
    credit_bank_code: Optional[str] = None
    system_remarks: Optional[str] = None

    # NIP specific details if applicable (example)
    nip_session_id: Optional[str] = None

    # ledger_entries: List[dict] = [] # Could include ledger entry summaries if needed

    class Config:
        orm_mode = True # Important for converting SQLAlchemy models
        use_enum_values = True # Serialize enums to their string values
        json_encoders = {
            decimal.Decimal: lambda v: str(v) # Ensure Decimals are serialized as strings
        }


class TransactionReversalRequest(BaseModel):
    original_transaction_id: str
    reason: str

class TransactionReversalResponse(TransactionInitiateResponse):
    # Similar to initiate response, but for the reversal transaction
    original_transaction_id: str

# --- NIP Specific Schemas ---
class NIPNameEnquiryRequest(BaseModel):
    destination_institution_code: str = Field(..., description="Receiving bank's CBN code")
    account_number: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{10}$")
    channel_code: str = Field("1", description="NIP Channel Code (e.g., 1 for Internet Banking, 2 for Mobile)") # Default to '1' or make configurable

class NIPNameEnquiryResponse(BaseModel):
    session_id: str
    destination_institution_code: str
    account_number: str
    account_name: str
    bank_verification_number: Optional[str] = None # BVN
    kyc_level: Optional[str] = None # e.g. "1", "2", "3"
    response_code: str # NIBSS response code, e.g., "00" for success

class NIPFundsTransferRequest(BaseModel):
    name_enquiry_ref: str # SessionID from Name Enquiry
    destination_institution_code: str
    channel_code: str # "1", "2", "7" (Mobile), "12" (USSD) etc.
    beneficiary_account_name: str
    beneficiary_account_number: str
    beneficiary_bvn: Optional[str] = None
    beneficiary_kyc_level: Optional[str] = None

    originator_account_name: str
    originator_account_number: str
    originator_bvn: Optional[str] = None
    originator_kyc_level: Optional[str] = None

    transaction_location: Optional[str] = None # e.g., "LAGOS,NG"
    narration: str
    payment_reference: str # Unique reference for this specific FT advice
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)

class NIPFundsTransferResponse(BaseModel):
    session_id: str # NIBSS Session ID for the FT
    response_code: str # NIBSS response code
    # Potentially other fields like fee, commission, etc.

# --- Bulk Payment Schemas ---
class BulkPaymentItem(BaseModel):
    credit_account_number: str
    credit_account_name: Optional[str] = None # Can be auto-fetched if NIP
    credit_bank_code: str
    amount: decimal.Decimal
    narration: str
    # unique_item_ref: str # Optional reference for this specific item in the batch

class BulkPaymentBatchRequest(BaseModel):
    batch_name: Optional[str] = None
    debit_account_number: str # Account to debit for all payments
    # currency: CurrencyEnum = CurrencyEnum.NGN # Assuming all items in batch have same currency as debit account
    items: List[BulkPaymentItem] = Field(..., min_items=1)

class BulkPaymentBatchResponse(BaseModel):
    batch_id: str
    status: str # e.g., "ACCEPTED_FOR_PROCESSING"
    total_transactions: int
    total_amount: decimal.Decimal
    submitted_at: datetime

# --- Standing Order Schemas ---
class StandingOrderBase(BaseModel):
    customer_id: int
    debit_account_number: str
    credit_account_number: str
    credit_bank_code: Optional[str] = None # Required for interbank
    amount: decimal.Decimal
    currency: CurrencyEnum = CurrencyEnum.NGN
    narration: str
    frequency: str = Field(..., description="e.g., 'DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY'")
    start_date: datetime # Use date if time component not needed, but datetime for precision
    end_date: Optional[datetime] = None

class StandingOrderCreate(StandingOrderBase):
    pass

class StandingOrderResponse(StandingOrderBase):
    id: int
    next_execution_date: datetime
    last_execution_date: Optional[datetime] = None
    is_active: bool
    failure_count: int

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

class StandingOrderUpdate(BaseModel):
    amount: Optional[decimal.Decimal] = None
    narration: Optional[str] = None
    end_date: Optional[datetime] = None # Allow setting or clearing end date
    is_active: Optional[bool] = None


# --- Transaction Dispute Schemas ---
class TransactionDisputeCreate(BaseModel):
    financial_transaction_id: str
    # customer_id: int # Usually from auth context
    dispute_reason: str = Field(..., min_length=10)

class TransactionDisputeResponse(BaseModel):
    id: int
    financial_transaction_id: str
    # customer_id: int
    dispute_reason: str
    status: str
    logged_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_details: Optional[str] = None

    class Config:
        orm_mode = True

class PaginatedTransactionResponse(BaseModel):
    items: List[TransactionDetailResponse]
    total: int
    page: int
    size: int
    class Config:
        json_encoders = { decimal.Decimal: str }
