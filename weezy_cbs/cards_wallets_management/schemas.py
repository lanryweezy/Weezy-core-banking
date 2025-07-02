# Pydantic schemas for Cards & Wallets Management
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
import decimal

from .models import CardTypeEnum, CardSchemeEnum, CardStatusEnum, WalletAccountStatusEnum, WalletTransactionTypeEnum, CurrencyEnum # Import enums

# --- Card Schemas ---
class CardBase(BaseModel):
    # customer_id: int # Usually from authenticated context or path parameter
    # account_id: int # Primary linked bank account ID
    card_type: CardTypeEnum
    card_scheme: CardSchemeEnum
    cardholder_name: str = Field(..., min_length=2)

class CardCreateRequest(CardBase):
    # For physical cards, address for delivery might be needed or fetched from customer profile
    pass

class CardResponse(CardBase):
    id: int
    customer_id: int
    account_id: int
    card_number_masked: str
    # card_processor_token: Optional[str] = None # Sent only if needed by specific clients
    expiry_date: str # MM/YY
    status: CardStatusEnum
    is_pin_set: bool
    issued_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True

class CardActivationRequest(BaseModel):
    # card_id: int # Usually path parameter
    # last4digits_pan: Optional[str] = Field(None, min_length=4, max_length=4) # For verification
    # date_of_birth: Optional[date] = None # For verification
    activation_code: Optional[str] = None # If an OTP or code is sent for activation

class CardPinSetRequest(BaseModel):
    # card_id: int # Usually path parameter
    new_pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    # confirm_new_pin: str # Optional, for UI confirmation

class CardPinChangeRequest(BaseModel):
    current_pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    new_pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")

class CardStatusUpdateRequest(BaseModel):
    new_status: CardStatusEnum # e.g., BLOCKED_TEMP, BLOCKED_PERM (user initiated)
    reason: Optional[str] = None

class CardDetailResponse(CardResponse):
    # Include more details if needed, e.g., specific limits if set on card
    # atm_daily_limit: Optional[decimal.Decimal] = None
    # pos_daily_limit: Optional[decimal.Decimal] = None
    pass


# --- Wallet Account Schemas ---
class WalletAccountBase(BaseModel):
    # customer_id: int # Usually from authenticated context
    currency: CurrencyEnum = CurrencyEnum.NGN

class WalletAccountCreateRequest(WalletAccountBase):
    # Initial funding details if applicable
    # initial_top_up_amount: Optional[decimal.Decimal] = Field(None, ge=0)
    # funding_source_ref: Optional[str] = None # e.g. linked card token or bank account for initial top-up
    pass

class WalletAccountResponse(WalletAccountBase):
    id: int
    customer_id: int
    wallet_id_external: str
    balance: decimal.Decimal
    status: WalletAccountStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

class WalletTopUpRequest(BaseModel):
    # wallet_id_external: str # Usually path parameter
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencyEnum = CurrencyEnum.NGN
    funding_source_type: str # e.g., "CARD", "BANK_TRANSFER", "USSD_CODE"
    funding_source_reference: str # e.g., Card token, transaction ID of bank transfer, NIP Session ID

class WalletWithdrawalRequest(BaseModel):
    # wallet_id_external: str # Usually path parameter
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencyEnum = CurrencyEnum.NGN
    destination_type: str # e.g., "BANK_ACCOUNT"
    destination_reference: str # e.g., NUBAN account number

class WalletP2PTransferRequest(BaseModel):
    # source_wallet_id_external: str # Usually path parameter or from auth context
    destination_wallet_id_external: str
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencyEnum = CurrencyEnum.NGN
    narration: Optional[str] = None

# --- Wallet Transaction Schemas ---
class WalletTransactionResponse(BaseModel):
    id: int
    wallet_account_id: int # Internal DB ID of the wallet
    # financial_transaction_id: Optional[str] = None # If linked to a master FT
    transaction_type: WalletTransactionTypeEnum
    amount: decimal.Decimal
    currency: CurrencyEnum
    narration: Optional[str] = None
    reference: str
    status: str # PENDING, SUCCESSFUL, FAILED
    balance_before: decimal.Decimal
    balance_after: decimal.Decimal
    transaction_date: datetime

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

# --- Card Transaction Schemas (for history/logging) ---
class CardTransactionResponse(BaseModel):
    id: int
    card_id: int
    # financial_transaction_id: Optional[str] = None
    transaction_type: str # e.g., 'ATM_WITHDRAWAL', 'POS_PURCHASE'
    amount: decimal.Decimal
    currency: CurrencyEnum
    merchant_name: Optional[str] = None
    merchant_category_code: Optional[str] = None
    terminal_id: Optional[str] = None
    auth_code: Optional[str] = None
    retrieval_reference_number: Optional[str] = None # RRN
    status: str # APPROVED, DECLINED, REVERSED
    transaction_date: datetime

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

# --- Cardless Withdrawal Schemas ---
class CardlessWithdrawalRequest(BaseModel):
    # account_id: int # Account to debit, usually from authenticated user context
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2) # Ensure amount is multiple of ATM dispensable value (e.g. 500, 1000)
    currency: CurrencyEnum = CurrencyEnum.NGN
    # phone_number_for_otp: Optional[str] = None # If OTP sent to a specific number

class CardlessWithdrawalTokenResponse(BaseModel):
    token: str # The generated one-time token for withdrawal
    amount: decimal.Decimal
    currency: CurrencyEnum
    expiry_date: datetime
    # one_time_pin: Optional[str] = None # If PIN is also generated and returned (less secure if via same channel as token)
    status: str # e.g. ACTIVE

    class Config:
        json_encoders = { decimal.Decimal: str }

class CardlessWithdrawalRedemptionRequest(BaseModel):
    token: str
    one_time_pin: str # PIN entered by user at ATM
    terminal_id: str # ATM ID

class CardlessWithdrawalRedemptionResponse(BaseModel):
    status: str # e.g. SUCCESSFUL, FAILED_INVALID_TOKEN, FAILED_INVALID_PIN, FAILED_EXPIRED
    amount_dispensed: Optional[decimal.Decimal] = None
    transaction_reference: Optional[str] = None # Reference for the successful withdrawal transaction

class PaginatedCardResponse(BaseModel):
    items: List[CardResponse]
    total: int
    page: int
    size: int

class PaginatedWalletTransactionResponse(BaseModel):
    items: List[WalletTransactionResponse]
    total: int
    page: int
    size: int
    class Config:
        json_encoders = { decimal.Decimal: str }

class PaginatedCardTransactionResponse(BaseModel):
    items: List[CardTransactionResponse]
    total: int
    page: int
    size: int
    class Config:
        json_encoders = { decimal.Decimal: str }
