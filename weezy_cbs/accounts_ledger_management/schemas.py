# Pydantic schemas for Accounts & Ledger Management
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import decimal # For precise arithmetic with monetary values

# Mirroring enums from models.py for validation and API consistency
from .models import AccountTypeEnum, AccountStatusEnum, CurrencyEnum, TransactionTypeEnum

class AccountBase(BaseModel):
    customer_id: int
    account_type: AccountTypeEnum
    currency: CurrencyEnum = CurrencyEnum.NGN

    # For Fixed Deposits, these might be required at creation or later update
    fd_maturity_date: Optional[datetime] = None
    fd_interest_rate: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=2)
    fd_principal: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=4)

class AccountCreate(AccountBase):
    initial_deposit_amount: Optional[decimal.Decimal] = Field(decimal.Decimal('0.00'), ge=0, decimal_places=4)
    account_number: Optional[str] = Field(None, min_length=10, max_length=10, pattern=r"^\d{10}$", description="NUBAN account number, auto-generated if not provided")

class AccountUpdate(BaseModel):
    status: Optional[AccountStatusEnum] = None
    # Other fields that can be updated, e.g., lien amount by system processes
    # Direct balance updates should NOT be exposed via a generic update endpoint
    # fd_maturity_date, fd_interest_rate for FD modifications if allowed

class AccountResponse(AccountBase):
    id: int
    account_number: str
    ledger_balance: decimal.Decimal = Field(..., decimal_places=4)
    available_balance: decimal.Decimal = Field(..., decimal_places=4)
    lien_amount: decimal.Decimal = Field(..., decimal_places=4)
    uncleared_funds: decimal.Decimal = Field(..., decimal_places=4)
    status: AccountStatusEnum
    accrued_interest: Optional[decimal.Decimal] = Field(None, decimal_places=4)
    last_activity_date: Optional[datetime] = None
    opened_date: datetime
    closed_date: Optional[datetime] = None

    class Config:
        orm_mode = True
        use_enum_values = True # Serialize enums to their string values
        json_encoders = {
            decimal.Decimal: lambda v: str(v) # Ensure Decimals are serialized as strings
        }

class AccountBalanceResponse(BaseModel):
    account_number: str
    ledger_balance: decimal.Decimal
    available_balance: decimal.Decimal
    currency: CurrencyEnum

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }


class LedgerEntryBase(BaseModel):
    transaction_id: str # Link to a master transaction record in FinancialTransaction
    account_id: int
    entry_type: TransactionTypeEnum
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=4) # Amount must be positive
    currency: CurrencyEnum
    narration: str = Field(..., min_length=5)
    value_date: Optional[datetime] = None # Defaults to now if not provided
    channel: Optional[str] = None
    reference_number: Optional[str] = None # External reference

class LedgerEntryCreate(LedgerEntryBase):
    # Specific fields for creation, if any
    pass

class LedgerEntryResponse(LedgerEntryBase):
    id: int
    transaction_date: datetime # When it was booked
    balance_before: decimal.Decimal
    balance_after: decimal.Decimal

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

class PostTransactionRequest(BaseModel):
    # This schema would be used for a high-level transaction posting API
    # that internally creates the necessary debit and credit LedgerEntry records.
    # This is more aligned with a double-entry system.
    from_account_number: Optional[str] = None # For debit leg
    to_account_number: Optional[str] = None   # For credit leg
    # Or use GL codes for posting to/from internal GLs
    from_gl_code: Optional[str] = None
    to_gl_code: Optional[str] = None

    amount: decimal.Decimal = Field(..., gt=0, decimal_places=4)
    currency: CurrencyEnum = CurrencyEnum.NGN
    narration: str
    transaction_reference: str = Field(..., description="Unique external reference for this transaction")
    channel: Optional[str] = "SYSTEM" # e.g., 'ATM', 'POS', 'WEB', 'MOBILE', 'SYSTEM'
    value_date: Optional[datetime] = None

class PostTransactionResponse(BaseModel):
    master_transaction_id: str
    status: str # e.g., "SUCCESSFUL", "PENDING"
    message: str
    debit_entry: Optional[LedgerEntryResponse] = None
    credit_entry: Optional[LedgerEntryResponse] = None
    timestamp: datetime

class UpdateAccountStatusRequest(BaseModel):
    status: AccountStatusEnum
    reason: Optional[str] = None # For audit purposes

class PlaceLienRequest(BaseModel):
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=4)
    reason: str
    # expiry_date: Optional[datetime] = None

class ReleaseLienRequest(BaseModel):
    amount: Optional[decimal.Decimal] = Field(None, gt=0, decimal_places=4) # If None, release all lien for the reason
    reason: str # Must match the reason for placing the lien, or a specific lien_id

class LienResponse(BaseModel):
    account_number: str
    total_lien_amount: decimal.Decimal
    # individual_liens: List[dict] # Detailed list of liens if tracked individually

    class Config:
        json_encoders = { decimal.Decimal: str }

# For Interest Calculation & Posting
class AccrueInterestRequest(BaseModel):
    account_id: Optional[int] = None # If for a specific account
    # Or run for all eligible accounts if account_id is None
    calculation_date: datetime # The date for which interest is being calculated

class AccrueInterestResponse(BaseModel):
    account_id: int
    amount_accrued: decimal.Decimal
    new_total_accrued_interest: decimal.Decimal
    class Config:
        json_encoders = { decimal.Decimal: str }

class PostAccruedInterestRequest(BaseModel):
    account_id: Optional[int] = None # If for a specific account
    posting_date: datetime

class PostAccruedInterestResponse(BaseModel):
    account_id: int
    amount_posted: decimal.Decimal
    new_ledger_balance: decimal.Decimal
    class Config:
        json_encoders = { decimal.Decimal: str }

class PaginatedAccountResponse(BaseModel):
    items: List[AccountResponse]
    total: int
    page: int
    size: int
    class Config:
        json_encoders = { decimal.Decimal: str }

class PaginatedLedgerEntryResponse(BaseModel):
    items: List[LedgerEntryResponse]
    total: int
    page: int
    size: int
    class Config:
        json_encoders = { decimal.Decimal: str }
