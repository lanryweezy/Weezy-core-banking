# Database models for Cards & Wallets Management
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SQLAlchemyEnum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# from weezy_cbs.database import Base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base() # Local Base for now

import enum

# from weezy_cbs.accounts_ledger_management.models import CurrencyEnum # Ideally reuse
class CurrencyEnum(enum.Enum):
    NGN = "NGN"
    USD = "USD"

class CardTypeEnum(enum.Enum):
    VIRTUAL = "VIRTUAL"
    PHYSICAL = "PHYSICAL"

class CardSchemeEnum(enum.Enum):
    VERVE = "VERVE"
    MASTERCARD = "MASTERCARD"
    VISA = "VISA"
    # Add others like AMEX if supported

class CardStatusEnum(enum.Enum):
    REQUESTED = "REQUESTED"     # Card has been requested but not yet processed/issued
    INACTIVE = "INACTIVE"       # Issued but not yet activated by the user
    ACTIVE = "ACTIVE"           # Card is active and can be used for transactions
    BLOCKED_TEMP = "BLOCKED_TEMP" # Temporarily blocked by user or system
    BLOCKED_PERM = "BLOCKED_PERM" # Permanently blocked (e.g., lost, stolen, fraud)
    EXPIRED = "EXPIRED"         # Card has passed its expiry date
    HOTLISTED = "HOTLISTED"     # Reported lost or stolen, on a global hotlist
    DAMAGED = "DAMAGED"         # Reported as damaged, awaiting replacement

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    # account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True) # Primary linked account

    card_number_masked = Column(String(19), nullable=False, index=True) # e.g., 5399********1234 (PAN)
    card_number_hashed = Column(String, nullable=False, unique=True) # Hashed full PAN for lookup if needed by processor
    # Full PAN should NOT be stored directly unless PCI-DSS compliant and encrypted at rest.
    # For integration, you'd typically store a token from the card processor.
    card_processor_token = Column(String, unique=True, nullable=True, index=True) # Token from Interswitch/UnifiedPayments/etc.

    card_type = Column(SQLAlchemyEnum(CardTypeEnum), nullable=False)
    card_scheme = Column(SQLAlchemyEnum(CardSchemeEnum), nullable=False)

    expiry_date = Column(String(5), nullable=False) # MM/YY format
    cvv_encrypted = Column(String, nullable=True) # Encrypted CVV (if stored, usually not for long)

    cardholder_name = Column(String, nullable=False)
    status = Column(SQLAlchemyEnum(CardStatusEnum), default=CardStatusEnum.REQUESTED, nullable=False)

    # PIN management - actual PIN not stored, only status or encrypted block for HSM
    is_pin_set = Column(Boolean, default=False)
    pin_change_required = Column(Boolean, default=False)
    failed_pin_attempts = Column(Integer, default=0)

    # Limits (can be card-specific, overriding account or product limits)
    # atm_daily_limit = Column(Numeric(precision=18, scale=2), nullable=True)
    # pos_daily_limit = Column(Numeric(precision=18, scale=2), nullable=True)
    # web_daily_limit = Column(Numeric(precision=18, scale=2), nullable=True)

    issued_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    # customer = relationship("Customer")
    # linked_account = relationship("Account")
    # wallet_account = relationship("WalletAccount", back_populates="linked_card") # If a card is specifically for a wallet

    __table_args__ = (
        Index("idx_card_customer_status", "customer_id", "status"),
    )

    def __repr__(self):
        return f"<Card(masked_pan='{self.card_number_masked}', scheme='{self.card_scheme.value}', status='{self.status.value}')>"


class WalletAccountStatusEnum(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"

class WalletAccount(Base): # Represents a stored value account (e-wallet)
    __tablename__ = "wallet_accounts"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id_external = Column(String, unique=True, index=True, nullable=False) # Publicly visible wallet ID
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)

    # This wallet might be a shadow account in the main ledger or have its own mini-ledger
    # For simplicity, let's assume it has a balance field.
    # In a real system, this balance would be derived from a ledger account.
    balance = Column(Numeric(precision=18, scale=4), default=0.0000, nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), default=CurrencyEnum.NGN, nullable=False)

    status = Column(SQLAlchemyEnum(WalletAccountStatusEnum), default=WalletAccountStatusEnum.ACTIVE)

    # linked_card_id = Column(Integer, ForeignKey("cards.id"), nullable=True) # Optional: if a card is primarily for this wallet
    # linked_bank_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True) # Optional: for funding/withdrawal

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # customer = relationship("Customer")
    # linked_card = relationship("Card", back_populates="wallet_account")
    # linked_bank_account = relationship("Account")
    # transactions = relationship("WalletTransaction", back_populates="wallet_account")

    def __repr__(self):
        return f"<WalletAccount(id='{self.wallet_id_external}', balance='{self.balance} {self.currency.value}')>"

class WalletTransactionTypeEnum(enum.Enum):
    TOP_UP = "TOP_UP"           # Funding the wallet
    WITHDRAWAL = "WITHDRAWAL"   # Moving funds out of wallet
    P2P_SEND = "P2P_SEND"       # Sending to another wallet user
    P2P_RECEIVE = "P2P_RECEIVE" # Receiving from another wallet user
    PAYMENT = "PAYMENT"         # Paying for goods/services
    FEE = "FEE"                 # Wallet transaction fee
    REVERSAL = "REVERSAL"

class WalletTransaction(Base): # Transactions specific to wallet operations
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    # wallet_account_id = Column(Integer, ForeignKey("wallet_accounts.id"), nullable=False, index=True)
    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, unique=True) # Link to master FT if applicable

    transaction_type = Column(SQLAlchemyEnum(WalletTransactionTypeEnum), nullable=False)
    amount = Column(Numeric(precision=18, scale=4), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    narration = Column(String, nullable=True)
    reference = Column(String, unique=True, index=True, nullable=False) # Unique reference for this wallet tx

    # For P2P or external interactions
    # counterparty_wallet_id = Column(String, nullable=True)
    # counterparty_name = Column(String, nullable=True)
    # external_source_sink_ref = Column(String, nullable=True) # e.g. Bank account for top-up/withdrawal

    status = Column(String, default="SUCCESSFUL") # PENDING, SUCCESSFUL, FAILED (Simplified status for wallet tx itself)

    balance_before = Column(Numeric(precision=18, scale=4))
    balance_after = Column(Numeric(precision=18, scale=4))

    transaction_date = Column(DateTime(timezone=True), server_default=func.now())

    # wallet_account = relationship("WalletAccount", back_populates="transactions")

class CardTransaction(Base): # Record of transactions made using a card
    __tablename__ = "card_transactions"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False, index=True)
    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, unique=True) # Link to master FT

    transaction_type = Column(String, nullable=False) # e.g., 'ATM_WITHDRAWAL', 'POS_PURCHASE', 'ONLINE_PURCHASE'
    amount = Column(Numeric(precision=18, scale=2), nullable=False) # Usually 2 decimal places for card txns
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False) # Transaction currency
    # original_amount = Column(Numeric(precision=18, scale=2), nullable=True) # If DCC was involved
    # original_currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=True)

    merchant_name = Column(String, nullable=True)
    merchant_category_code = Column(String, nullable=True) # MCC
    terminal_id = Column(String, nullable=True) # POS or ATM Terminal ID

    auth_code = Column(String, nullable=True) # Authorization code from switch/scheme
    retrieval_reference_number = Column(String, nullable=True, index=True) # RRN

    status = Column(String, default="APPROVED") # APPROVED, DECLINED, REVERSED
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())

    # card = relationship("Card")

# ATM/POS Integration:
# Actual integration involves communicating with switches (Interswitch, UPSL).
# This module would store card details (securely tokenized/masked) and perhaps transaction logs from these integrations.
# PIN Management: Secure PIN block generation/validation via HSM, not storing PINs directly.
# Cardless Withdrawals: Generate tokens/codes, track their status.

class CardlessWithdrawalToken(Base):
    __tablename__ = "cardless_withdrawal_tokens"
    id = Column(Integer, primary_key=True, index=True)
    # account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False) # Account to debit
    token = Column(String, unique=True, index=True, nullable=False) # The generated one-time token
    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    status = Column(String, default="ACTIVE") # ACTIVE, USED, EXPIRED, CANCELLED
    expiry_date = Column(DateTime(timezone=True), nullable=False)

    # For security, a one-time PIN might be associated or sent to user
    # one_time_pin_hashed = Column(String, nullable=True)

    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    # atm_id_used = Column(String, nullable=True) # ATM where it was redeemed

    # account = relationship("Account")

# Note: PCI-DSS compliance is paramount when handling card data.
# Storing full PAN, CVV, or track data requires stringent security measures.
# Tokenization with a compliant processor is the recommended approach.
