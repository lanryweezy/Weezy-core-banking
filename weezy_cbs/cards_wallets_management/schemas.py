# Pydantic schemas for Cards & Wallets Management
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any # Added Any, Dict
from datetime import datetime, date
import decimal
import enum # For Pydantic enums

# Import enums from models to ensure consistency
from .models import (
    CardTypeEnum as ModelCardTypeEnum,
    CardSchemeEnum as ModelCardSchemeEnum,
    CardStatusEnum as ModelCardStatusEnum,
    WalletAccountStatusEnum as ModelWalletAccountStatusEnum,
    WalletTransactionTypeEnum as ModelWalletTransactionTypeEnum,
    CurrencyEnum as ModelCurrencyEnum
)

# Schema Enums
class CurrencySchema(str, enum.Enum): # Replicated for independence if needed
    NGN = "NGN"; USD = "USD"

class CardTypeSchema(str, enum.Enum):
    VIRTUAL = "VIRTUAL"; PHYSICAL = "PHYSICAL"

class CardSchemeSchema(str, enum.Enum):
    VERVE = "VERVE"; MASTERCARD = "MASTERCARD"; VISA = "VISA"

class CardStatusSchema(str, enum.Enum):
    REQUESTED = "REQUESTED"; INACTIVE = "INACTIVE"; ACTIVE = "ACTIVE"
    BLOCKED_TEMP = "BLOCKED_TEMP"; BLOCKED_PERM = "BLOCKED_PERM"
    EXPIRED = "EXPIRED"; HOTLISTED = "HOTLISTED"; DAMAGED = "DAMAGED"

class WalletAccountStatusSchema(str, enum.Enum):
    ACTIVE = "ACTIVE"; INACTIVE = "INACTIVE"; SUSPENDED = "SUSPENDED"; CLOSED = "CLOSED"

class WalletTransactionTypeSchema(str, enum.Enum):
    TOP_UP = "TOP_UP"; WITHDRAWAL = "WITHDRAWAL"; P2P_SEND = "P2P_SEND"
    P2P_RECEIVE = "P2P_RECEIVE"; PAYMENT = "PAYMENT"; FEE = "FEE"; REVERSAL = "REVERSAL"


# --- Card Schemas ---
class CardBase(BaseModel):
    card_type: CardTypeSchema
    card_scheme: CardSchemeSchema
    cardholder_name: str = Field(..., min_length=2, max_length=100)
    emboss_name: Optional[str] = Field(None, max_length=26)
    # product_code: Optional[str] = None # If linking to a card product

class CardCreateRequest(CardBase):
    customer_id: int
    account_id: int # Primary linked NUBAN account ID
    product_code: Optional[str] = None # Optional: card product code
    # For physical cards, dispatch address details might be here or fetched from customer profile

class CardResponse(CardBase):
    id: int
    customer_id: int
    account_id: int
    product_code: Optional[str] = None
    card_number_masked: str
    card_processor_token: Optional[str] = None # Only expose if absolutely necessary for specific client use cases
    expiry_date: str # MM/YY
    status: CardStatusSchema
    is_pin_set: bool
    is_primary_card_for_account: bool
    issued_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: orm_mode = True; use_enum_values = True

class CardActivationRequest(BaseModel):
    # card_id identified by path param typically
    activation_code: Optional[str] = None # e.g. OTP or code from card mailer

class CardPinSetRequest(BaseModel):
    new_pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")

class CardPinChangeRequest(BaseModel):
    current_pin_encrypted: str # Encrypted block of current PIN (HSM process)
    new_pin_encrypted: str   # Encrypted block of new PIN

class CardStatusUpdateRequest(BaseModel):
    new_status: CardStatusSchema
    reason: Optional[str] = None

class CardDetailResponse(CardResponse): # Could be same as CardResponse or add more
    # atm_daily_limit: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    # pos_daily_limit: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    pass


# --- Wallet Account Schemas ---
class WalletAccountBase(BaseModel):
    currency: CurrencySchema = CurrencySchema.NGN

class WalletAccountCreateRequest(WalletAccountBase):
    customer_id: int
    # linked_ledger_account_id: Optional[int] = None # If using Option 2 for balance

class WalletAccountResponse(WalletAccountBase):
    id: int
    customer_id: int
    wallet_id_external: str = Field(..., max_length=30)
    balance: decimal.Decimal = Field(..., decimal_places=2)
    status: WalletAccountStatusSchema
    # linked_ledger_account_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

class WalletTopUpRequest(BaseModel):
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN # Should match wallet currency
    funding_source_type: str = Field(..., description="e.g., CARD, BANK_TRANSFER")
    funding_source_reference: str = Field(..., description="Card token, FT reference")
    financial_transaction_id: Optional[str] = Field(None, description="Master FT ID if pre-created")


class WalletWithdrawalRequest(BaseModel):
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN # Should match wallet currency
    destination_type: str = Field(..., description="e.g., BANK_ACCOUNT")
    destination_reference: str = Field(..., description="NUBAN account number")
    financial_transaction_id: Optional[str] = Field(None, description="Master FT ID if pre-created")

class WalletP2PTransferRequest(BaseModel):
    destination_wallet_id_external: str = Field(..., max_length=30)
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN # Must match both wallets for simple P2P
    narration: Optional[str] = Field(None, max_length=100)
    financial_transaction_id: Optional[str] = Field(None, description="Master FT ID if pre-created")


# --- Wallet Transaction Schemas ---
class WalletTransactionResponse(BaseModel):
    id: int
    wallet_account_id: int
    financial_transaction_id: Optional[str] = None
    transaction_type: WalletTransactionTypeSchema
    amount: decimal.Decimal = Field(..., decimal_places=2)
    currency: CurrencySchema
    narration: Optional[str] = Field(None, max_length=255)
    reference: str = Field(..., max_length=50)
    status: str = Field(..., max_length=20)
    balance_before: decimal.Decimal = Field(..., decimal_places=2)
    balance_after: decimal.Decimal = Field(..., decimal_places=2)
    transaction_date: datetime
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- Card Transaction Schemas (for history/logging) ---
class CardTransactionResponse(BaseModel):
    id: int
    card_id: int
    financial_transaction_id: Optional[str] = None
    transaction_type: str = Field(..., max_length=50)
    amount: decimal.Decimal = Field(..., decimal_places=2)
    currency: CurrencySchema
    merchant_name: Optional[str] = Field(None, max_length=100)
    merchant_category_code: Optional[str] = Field(None, max_length=4)
    terminal_id: Optional[str] = Field(None, max_length=20)
    auth_code: Optional[str] = Field(None, max_length=10)
    retrieval_reference_number: Optional[str] = Field(None, max_length=20) # RRN
    status: str = Field(..., max_length=20)
    transaction_date: datetime
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- Cardless Withdrawal Schemas ---
class CardlessWithdrawalGenerateRequest(BaseModel): # Renamed
    account_id: int # Account to debit
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN
    # phone_number_for_notification: Optional[str] = None # If different from account holder's primary

class CardlessWithdrawalTokenResponse(BaseModel):
    token: str = Field(..., max_length=20)
    amount: decimal.Decimal = Field(..., decimal_places=2)
    currency: CurrencySchema
    expiry_date: datetime
    status: str = Field(..., max_length=20) # e.g. ACTIVE
    class Config: json_encoders = {decimal.Decimal: str}

class CardlessWithdrawalRedemptionRequest(BaseModel):
    token: str = Field(..., max_length=20)
    one_time_pin: str = Field(..., min_length=4, max_length=6) # ATM entered PIN
    terminal_id: str = Field(..., max_length=20)

class CardlessWithdrawalRedemptionResponse(BaseModel):
    status: str
    amount_dispensed: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    financial_transaction_id: Optional[str] = None # Renamed
    class Config: json_encoders = {decimal.Decimal: str}

class PaginatedCardResponse(BaseModel):
    items: List[CardResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str} # If any Decimal in CardResponse

class PaginatedWalletTransactionResponse(BaseModel):
    items: List[WalletTransactionResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str}

class PaginatedCardTransactionResponse(BaseModel):
    items: List[CardTransactionResponse]; total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str}
