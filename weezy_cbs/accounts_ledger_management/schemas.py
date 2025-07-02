# Pydantic schemas for Accounts & Ledger Management
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date # Use date for date-only fields
import decimal # For precise arithmetic with monetary values
import enum # For creating Pydantic enums

# Mirroring enums from models.py for validation and API consistency
# These should ideally match the string values of the SQLAlchemy enums
class AccountTypeSchema(str, enum.Enum):
    SAVINGS = "SAVINGS"
    CURRENT = "CURRENT"
    FIXED_DEPOSIT = "FIXED_DEPOSIT"
    DOMICILIARY = "DOMICILIARY"
    LOAN_ACCOUNT = "LOAN_ACCOUNT"

class AccountStatusSchema(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DORMANT = "DORMANT"
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"

class CurrencySchema(str, enum.Enum):
    NGN = "NGN"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

class TransactionTypeSchema(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class AccountBase(BaseModel):
    customer_id: int
    product_code: str = Field(..., description="Product code defining the account type and features")
    # account_type and currency will be derived from product_code by the service layer

    # For Fixed Deposits, these might be provided at creation or later update via specific FD services
    fd_maturity_date: Optional[date] = None
    fd_interest_rate_pa: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=2, description="Annual interest rate for FD")
    fd_principal_amount: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=2, description="Principal amount for FD")

class AccountCreateRequest(AccountBase): # Renamed from AccountCreate
    # NUBAN account_number is system-generated, not part of create request
    initial_deposit_amount: Optional[decimal.Decimal] = Field(decimal.Decimal('0.00'), ge=0, decimal_places=2)
    # Currency for initial deposit should match account currency (derived from product_code)

class AccountUpdateRequest(BaseModel): # For general updates by admin/system, not status changes typically
    # Status changes should go through a dedicated endpoint with more checks.
    # block_reason: Optional[str] = None
    # Direct balance updates are NOT exposed.
    # Lien amount updates are via specific lien services.
    # FD specific updates might have their own endpoints/services.
    pass # Keep minimal, specific update schemas for specific actions are better


class AccountResponse(BaseModel): # Base for what's returned, can be extended
    id: int
    account_number: str
    customer_id: int
    product_code: str
    account_type: AccountTypeSchema # Now using the schema enum
    currency: CurrencySchema

    ledger_balance: decimal.Decimal = Field(..., decimal_places=2)
    available_balance: decimal.Decimal = Field(..., decimal_places=2)
    lien_amount: decimal.Decimal = Field(..., decimal_places=2)
    uncleared_funds: decimal.Decimal = Field(..., decimal_places=2)

    status: AccountStatusSchema
    is_post_no_debit: bool
    block_reason: Optional[str] = None

    accrued_interest_payable: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    accrued_interest_receivable: Optional[decimal.Decimal] = Field(None, decimal_places=2) # For loan accounts

    last_customer_initiated_activity_date: Optional[datetime] = None
    opened_date: date
    closed_date: Optional[date] = None

    # FD fields if applicable
    fd_maturity_date: Optional[date] = None
    fd_interest_rate_pa: Optional[decimal.Decimal] = None
    fd_principal_amount: Optional[decimal.Decimal] = None

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

class AccountBalanceResponse(BaseModel):
    account_number: str
    ledger_balance: decimal.Decimal
    available_balance: decimal.Decimal
    currency: CurrencySchema
    class Config:
        orm_mode = True; use_enum_values = True; json_encoders = { decimal.Decimal: str }


class LedgerEntryBase(BaseModel):
    financial_transaction_id: str # Link to a master transaction record
    # account_id: int # This is usually implicit or path param when creating for an account
    entry_type: TransactionTypeSchema
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema
    narration: str = Field(..., min_length=3, max_length=255)
    value_date: Optional[datetime] = None # Defaults to now if not provided by system
    channel: Optional[str] = Field(None, max_length=50)
    external_reference_number: Optional[str] = Field(None, max_length=100)

class LedgerEntryCreate(LedgerEntryBase): # Used by services to create entries
    account_id: int # Explicitly needed when service creates this
    balance_before: decimal.Decimal # Must be provided by service during creation
    balance_after: decimal.Decimal  # Must be provided by service during creation

class LedgerEntryResponse(LedgerEntryBase):
    id: int
    account_id: int # Include account_id in response
    transaction_date: datetime # Booking date
    balance_before: decimal.Decimal
    balance_after: decimal.Decimal
    is_reversal_entry: bool

    class Config:
        orm_mode = True; use_enum_values = True; json_encoders = { decimal.Decimal: str }

# This request is for internal system use, typically by TransactionManagement or other modules
# to instruct ledger postings. It's not usually a direct public API for end-users.
class InternalTransactionPostingRequest(BaseModel):
    financial_transaction_id: str = Field(..., description="Master transaction ID from TransactionManagement")
    debit_leg: Optional[dict] = Field(None, description="{'account_number': str, 'amount': Decimal, 'narration': str} or {'gl_code': str, ...}")
    credit_leg: Optional[dict] = Field(None, description="{'account_number': str, 'amount': Decimal, 'narration': str} or {'gl_code': str, ...}")
    # For single leg posting (e.g. fee to GL, cash deposit from GL)
    # account_number_single_leg: Optional[str] = None
    # gl_code_single_leg: Optional[str] = None
    # entry_type_single_leg: Optional[TransactionTypeSchema] = None

    amount: decimal.Decimal # Amount of the transaction (used if single leg or if debit/credit amounts are implied same)
    currency: CurrencySchema
    narration_overall: str # Overall narration for the financial transaction
    channel: str
    value_date: Optional[datetime] = None
    external_reference: Optional[str] = None # e.g. NIP Session ID for the entire transaction

class InternalTransactionPostingResponse(BaseModel):
    financial_transaction_id: str
    status: str # e.g., "SUCCESSFUL_POSTING", "FAILED_POSTING"
    message: str
    debit_ledger_entry_id: Optional[int] = None
    credit_ledger_entry_id: Optional[int] = None
    timestamp: datetime

class UpdateAccountStatusRequest(BaseModel):
    status: AccountStatusSchema # The new status
    is_post_no_debit: Optional[bool] = None # Specifically for PND
    block_reason: Optional[str] = Field(None, description="Required if status is BLOCKED")
    closure_reason: Optional[str] = Field(None, description="Required if status is CLOSED")
    # Audit notes
    reason_for_change: str = Field(..., description="Reason for this status change, for audit trail.")

class PlaceLienRequest(BaseModel):
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    reason: str = Field(..., min_length=5)
    # expiry_date: Optional[datetime] = None # Optional: when the lien should auto-expire

class ReleaseLienRequest(BaseModel):
    # To release a specific lien, a lien_id would be better.
    # For simplicity, releasing by amount and reason.
    amount_to_release: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    reason: str # Should ideally match a reason for an existing lien or be generic like "RELEASE_ALL"

class LienResponse(BaseModel): # More detailed response for lien operations
    account_number: str
    lien_id: Optional[str] = None # If individual liens are tracked with IDs
    amount: decimal.Decimal
    reason: str
    status: str # e.g. "PLACED", "RELEASED", "PARTIALLY_RELEASED"
    remaining_lien_on_account: decimal.Decimal # Total lien remaining on account
    class Config: json_encoders = { decimal.Decimal: str }


# Schemas for Interest Accrual & Posting (mostly for internal/batch use)
class DailyInterestAccrualRequest(BaseModel): # For triggering daily accrual batch
    calculation_date: date # The date for which interest should be accrued (usually previous day)

class AccountInterestAccrualResponse(BaseModel): # Result for one account's accrual
    account_id: int
    account_number: str
    amount_accrued: decimal.Decimal # Retain precision for accrual calculation
    new_total_accrued_interest_payable: decimal.Decimal # Or _receivable for loan accounts
    class Config: json_encoders = { decimal.Decimal: str }

class MonthlyInterestPostingRequest(BaseModel): # For triggering posting of accrued interest
    posting_date: date # Date to post, typically month-end

class AccountInterestPostingResponse(BaseModel): # Result for one account's posting
    account_id: int
    account_number: str
    amount_posted: decimal.Decimal # Posted amount (usually 2 decimal places)
    new_ledger_balance: decimal.Decimal
    # related_ledger_entry_id: int
    class Config: json_encoders = { decimal.Decimal: str }


class PaginatedAccountResponse(BaseModel):
    items: List[AccountResponse]
    total: int
    page: int
    size: int
    class Config: json_encoders = { decimal.Decimal: str }

class PaginatedLedgerEntryResponse(BaseModel):
    items: List[LedgerEntryResponse]
    total: int
    page: int
    size: int
    class Config: json_encoders = { decimal.Decimal: str }
