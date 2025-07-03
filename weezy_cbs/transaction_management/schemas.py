# Pydantic schemas for Transaction Management
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any # Added Any
from datetime import datetime, date # Added date
import decimal
import enum # For Pydantic enums

# Import enums from models to ensure consistency
from .models import (
    TransactionChannelEnum as ModelTransactionChannelEnum,
    TransactionStatusEnum as ModelTransactionStatusEnum,
    CurrencyEnum as ModelCurrencyEnum,
    TransactionTypeCategoryEnum as ModelTransactionTypeCategoryEnum
)

# Schema Enums
class CurrencySchema(str, enum.Enum): # Replicated from accounts for independence if needed
    NGN = "NGN"; USD = "USD"; EUR = "EUR"; GBP = "GBP"

class TransactionChannelSchema(str, enum.Enum):
    INTERNAL = "INTERNAL"; INTRA_BANK = "INTRA_BANK"; NIP = "NIP"; RTGS = "RTGS"
    USSD = "USSD"; POS = "POS"; ATM = "ATM"; WEB_BANKING = "WEB_BANKING"
    MOBILE_APP = "MOBILE_APP"; AGENT_BANKING = "AGENT_BANKING"
    BULK_PAYMENT = "BULK_PAYMENT"; STANDING_ORDER = "STANDING_ORDER"
    PAYMENT_GATEWAY = "PAYMENT_GATEWAY"; BILL_PAYMENT = "BILL_PAYMENT"

class TransactionTypeCategorySchema(str, enum.Enum):
    FUNDS_TRANSFER = "FUNDS_TRANSFER"; BILL_PAYMENT = "BILL_PAYMENT"; AIRTIME_PURCHASE = "AIRTIME_PURCHASE"
    MERCHANT_PAYMENT = "MERCHANT_PAYMENT"; LOAN_DISBURSEMENT = "LOAN_DISBURSEMENT"
    LOAN_REPAYMENT = "LOAN_REPAYMENT"; FEE_CHARGE = "FEE_CHARGE"; TAX_DUTY = "TAX_DUTY"
    ACCOUNT_OPENING_DEPOSIT = "ACCOUNT_OPENING_DEPOSIT"; CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"; INTEREST_APPLICATION = "INTEREST_APPLICATION"
    SYSTEM_POSTING = "SYSTEM_POSTING"

class TransactionStatusSchema(str, enum.Enum):
    PENDING = "PENDING"; PROCESSING = "PROCESSING"; SUCCESSFUL = "SUCCESSFUL"; FAILED = "FAILED"
    REVERSED = "REVERSED"; PENDING_APPROVAL = "PENDING_APPROVAL"
    FLAGGED_SUSPICION = "FLAGGED_SUSPICION"; TIMEOUT = "TIMEOUT"; UNKNOWN = "UNKNOWN"
    AWAITING_RETRY = "AWAITING_RETRY"; PARTIALLY_SUCCESSFUL = "PARTIALLY_SUCCESSFUL"


class TransactionBase(BaseModel):
    transaction_type: TransactionTypeCategorySchema
    channel: TransactionChannelSchema
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN

    debit_account_number: Optional[str] = Field(None, max_length=20)
    debit_bank_code: Optional[str] = Field(None, max_length=10)

    credit_account_number: str = Field(..., max_length=20)
    credit_bank_code: str = Field(..., max_length=10) # Required for interbank, can be own bank code for intrabank
    credit_account_name: Optional[str] = Field(None, max_length=150) # Can be fetched via name enquiry

    narration: str = Field(..., min_length=3, max_length=255)
    # initiator_user_id: Optional[str] = None # Set by system from auth context or system process ID

class TransactionCreateRequest(TransactionBase):
    # For specific transaction types like bill payments, additional fields would be needed.
    # This might be better handled by dedicated schemas per transaction_type if they vary significantly.
    # e.g., BillPaymentDetails, AirtimePurchaseDetails
    # For now, keeping it generic.
    # payment_details: Optional[Dict[str, Any]] = None # For type-specific data like biller_id, smartcard_no
    pass

class TransactionInitiateResponse(BaseModel):
    transaction_id: str
    status: TransactionStatusSchema
    message: str
    initiated_at: datetime
    external_transaction_id: Optional[str] = None

class TransactionStatusQueryResponse(BaseModel):
    transaction_id: str
    status: TransactionStatusSchema
    channel: TransactionChannelSchema
    amount: decimal.Decimal = Field(..., decimal_places=2)
    currency: CurrencySchema
    narration: str
    initiated_at: datetime
    processed_at: Optional[datetime] = None
    external_system_at: Optional[datetime] = None
    response_code: Optional[str] = None
    response_message: Optional[str] = None
    is_reversal: bool = False
    original_transaction_id: Optional[str] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

class NIPTransactionDetailsSchema(BaseModel): # For embedding in TransactionDetailResponse
    nibss_session_id: Optional[str] = None
    name_enquiry_ref: Optional[str] = None
    nip_channel_code: Optional[str] = None
    fee: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    class Config: orm_mode = True; json_encoders = {decimal.Decimal: str}

class TransactionDetailResponse(TransactionStatusQueryResponse):
    transaction_type: TransactionTypeCategorySchema
    debit_account_name: Optional[str] = None
    # debit_customer_id: Optional[int] = None
    # credit_customer_id: Optional[int] = None
    system_remarks: Optional[str] = None
    initiator_user_id: Optional[str] = None
    approver_user_id: Optional[str] = None
    fee_amount: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    vat_amount: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    stamp_duty_amount: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    charge_details_json: Optional[Dict[str, Any]] = None

    nip_details: Optional[NIPTransactionDetailsSchema] = None # Example for NIP
    # rtgs_details: Optional[RTGSTransactionDetailsSchema] = None # etc.
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}


class TransactionReversalRequest(BaseModel):
    original_transaction_id: str = Field(..., max_length=40)
    reason: str = Field(..., min_length=5)

class TransactionReversalResponse(TransactionInitiateResponse): # Reversal is also an initiated transaction
    original_transaction_id: str

# --- NIP Specific Schemas (as defined before, mostly fine) ---
class NIPNameEnquiryRequest(BaseModel):
    destination_institution_code: str = Field(..., description="Receiving bank's CBN code")
    account_number: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{10}$")
    channel_code: str = Field("1", description="NIP Channel Code (e.g., 1 for Internet Banking)")

class NIPNameEnquiryResponse(BaseModel):
    session_id: str
    destination_institution_code: str
    account_number: str
    account_name: str
    bank_verification_number: Optional[str] = None
    kyc_level: Optional[str] = None
    response_code: str

class NIPFundsTransferRequestDetails(BaseModel): # For the actual NIBSS call, distinct from our TransactionCreateRequest
    name_enquiry_ref: str
    destination_institution_code: str
    channel_code: str
    beneficiary_account_name: str
    beneficiary_account_number: str
    beneficiary_bvn: Optional[str] = None
    beneficiary_kyc_level: Optional[str] = None
    originator_account_name: str
    originator_account_number: str
    originator_bvn: Optional[str] = None
    originator_kyc_level: Optional[str] = None
    transaction_location: Optional[str] = None
    narration: str
    payment_reference: str # This is OUR FinancialTransaction.id typically
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2) # NIBSS expects kobo; service layer converts

class NIPFundsTransferAdviseResponse(BaseModel): # Renamed from NIPFundsTransferResponse
    session_id: str
    response_code: str
    # Other fields from NIBSS response like fee, etc.

# --- Bulk Payment Schemas ---
class BulkPaymentItem(BaseModel):
    credit_account_number: str = Field(..., max_length=20)
    credit_account_name: Optional[str] = Field(None, max_length=150)
    credit_bank_code: str = Field(..., max_length=10)
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    narration: str = Field(..., max_length=100)
    unique_item_ref: Optional[str] = Field(None, max_length=40) # Optional client ref for this item

class BulkPaymentBatchCreateRequest(BaseModel): # Renamed
    batch_name: Optional[str] = Field(None, max_length=100)
    debit_account_number: str = Field(..., max_length=20)
    items: List[BulkPaymentItem] = Field(..., min_items=1)

class BulkPaymentBatchResponse(BaseModel):
    batch_id: str
    status: str
    total_transactions: int
    total_amount: decimal.Decimal = Field(..., decimal_places=2)
    submitted_at: datetime
    class Config: json_encoders = {decimal.Decimal: str}

# --- Standing Order Schemas ---
class StandingOrderBase(BaseModel):
    customer_id: int
    debit_account_number: str = Field(..., max_length=20)
    credit_account_number: str = Field(..., max_length=20)
    credit_bank_code: Optional[str] = Field(None, max_length=10)
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN
    narration: str = Field(..., max_length=100)
    frequency: str = Field(..., description="e.g., 'DAILY', 'WEEKLY', 'MONTHLY'") # Consider Enum
    start_date: datetime
    end_date: Optional[datetime] = None

class StandingOrderCreateRequest(StandingOrderBase): # Renamed
    pass

class StandingOrderResponse(StandingOrderBase):
    id: int
    next_execution_date: datetime
    last_execution_date: Optional[datetime] = None
    is_active: bool
    failure_count: int
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

class StandingOrderUpdateRequest(BaseModel): # Renamed
    amount: Optional[decimal.Decimal] = Field(None, gt=0, decimal_places=2)
    narration: Optional[str] = Field(None, max_length=100)
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None

# --- Transaction Dispute Schemas ---
class TransactionDisputeCreateRequest(BaseModel): # Renamed
    financial_transaction_id: str = Field(..., max_length=40)
    customer_id: int # Who is logging the dispute
    dispute_reason: str = Field(..., min_length=10)

class TransactionDisputeResponse(BaseModel):
    id: int
    financial_transaction_id: str
    customer_id: int
    dispute_reason: str
    status: str
    logged_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_details: Optional[str] = None
    class Config: orm_mode = True

class TransactionDisputeUpdateRequest(BaseModel):
    status: str # From a defined set of dispute statuses
    resolution_details: Optional[str] = None
    # assigned_to_user_id: Optional[str] = None


class PaginatedTransactionResponse(BaseModel):
    items: List[TransactionDetailResponse]
    total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str}
