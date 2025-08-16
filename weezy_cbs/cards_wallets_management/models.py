# Database models for Cards & Wallets Management
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SQLAlchemyEnum, Index, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from weezy_cbs.database import Base # Use the shared Base

import enum

# Assuming CurrencyEnum will be shared, for now define locally or import if available
# from weezy_cbs.accounts_ledger_management.models import CurrencyEnum as SharedCurrencyEnum
class CurrencyEnum(enum.Enum):
    NGN = "NGN"
    USD = "USD"
    # Add other relevant currencies

class CardTypeEnum(enum.Enum):
    VIRTUAL = "VIRTUAL"
    PHYSICAL = "PHYSICAL"

class CardSchemeEnum(enum.Enum):
    VERVE = "VERVE"
    MASTERCARD = "MASTERCARD"
    VISA = "VISA"

class CardStatusEnum(enum.Enum):
    REQUESTED = "REQUESTED"
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    BLOCKED_TEMP = "BLOCKED_TEMP"
    BLOCKED_PERM = "BLOCKED_PERM"
    EXPIRED = "EXPIRED"
    HOTLISTED = "HOTLISTED"
    DAMAGED = "DAMAGED"

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    product_code = Column(String, ForeignKey("product_configs.product_code"), nullable=True) # Link to Card Product

    card_number_masked = Column(String(19), nullable=False, index=True)
    card_number_hashed = Column(String(64), nullable=False, unique=True) # SHA-256 hash hex digest
    card_processor_token = Column(String(255), unique=True, nullable=True, index=True)

    card_type = Column(SQLAlchemyEnum(CardTypeEnum), nullable=False)
    card_scheme = Column(SQLAlchemyEnum(CardSchemeEnum), nullable=False)

    expiry_date = Column(String(5), nullable=False) # MM/YY
    # cvv_encrypted = Column(String, nullable=True) # Highly sensitive, avoid storing if possible

    cardholder_name = Column(String(100), nullable=False)
    emboss_name = Column(String(26), nullable=True) # Name embossed on physical card
    status = Column(SQLAlchemyEnum(CardStatusEnum), default=CardStatusEnum.REQUESTED, nullable=False, index=True)

    is_pin_set = Column(Boolean, default=False)
    pin_change_required = Column(Boolean, default=False)
    failed_pin_attempts = Column(Integer, default=0)

    # dispatch_address_id = Column(Integer, ForeignKey("addresses.id"), nullable=True) # If using separate Address model
    is_primary_card_for_account = Column(Boolean, default=False)

    issued_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer") # Add back_populates in Customer model
    linked_account = relationship("Account") # Add back_populates in Account model
    card_product = relationship("ProductConfig") # Add back_populates in ProductConfig model
    # card_transactions = relationship("CardTransaction", back_populates="card")


    __table_args__ = (
        Index("idx_card_customer_account_status", "customer_id", "account_id", "status"),
    )

    def __repr__(self):
        return f"<Card(id={self.id}, masked_pan='{self.card_number_masked}', status='{self.status.value}')>"

class WalletAccountStatusEnum(enum.Enum):
    ACTIVE = "ACTIVE"; INACTIVE = "INACTIVE"; SUSPENDED = "SUSPENDED"; CLOSED = "CLOSED"

class WalletAccount(Base):
    __tablename__ = "wallet_accounts"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id_external = Column(String(30), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)

    # Option 1: Wallet has its own balance (simpler e-wallet model)
    balance = Column(Numeric(precision=18, scale=2), default=0.00, nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), default=CurrencyEnum.NGN, nullable=False)
    # Option 2: Wallet is a view/proxy to a real ledger account (more integrated CBS model)
    # linked_ledger_account_id = Column(Integer, ForeignKey("accounts.id"), unique=True, nullable=True)

    status = Column(SQLAlchemyEnum(WalletAccountStatusEnum), default=WalletAccountStatusEnum.ACTIVE, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer") # Add back_populates in Customer
    # linked_ledger_account = relationship("Account") # If using Option 2
    transactions = relationship("WalletTransaction", back_populates="wallet_account", order_by="WalletTransaction.id")

    def __repr__(self):
        return f"<WalletAccount(id_ext='{self.wallet_id_external}', balance='{self.balance} {self.currency.value}')>"

class WalletTransactionTypeEnum(enum.Enum):
    TOP_UP = "TOP_UP"; WITHDRAWAL = "WITHDRAWAL"; P2P_SEND = "P2P_SEND"
    P2P_RECEIVE = "P2P_RECEIVE"; PAYMENT = "PAYMENT"; FEE = "FEE"; REVERSAL = "REVERSAL"

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_account_id = Column(Integer, ForeignKey("wallet_accounts.id"), nullable=False, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True, index=True)

    transaction_type = Column(SQLAlchemyEnum(WalletTransactionTypeEnum), nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    narration = Column(String(255), nullable=True)
    reference = Column(String(50), unique=True, index=True, nullable=False)

    status = Column(String(20), default="SUCCESSFUL")

    balance_before = Column(Numeric(precision=18, scale=2), nullable=False)
    balance_after = Column(Numeric(precision=18, scale=2), nullable=False)
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())

    wallet_account = relationship("WalletAccount", back_populates="transactions")

class CardTransaction(Base):
    __tablename__ = "card_transactions"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True, index=True)

    transaction_type = Column(String(50), nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    merchant_name = Column(String(100), nullable=True)
    merchant_category_code = Column(String(4), nullable=True)
    terminal_id = Column(String(20), nullable=True)

    auth_code = Column(String(10), nullable=True)
    retrieval_reference_number = Column(String(20), nullable=True, index=True) # RRN

    status = Column(String(20), default="APPROVED")
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())

    card = relationship("Card") # Add back_populates="card_transactions" to Card model

class CardlessWithdrawalToken(Base):
    __tablename__ = "cardless_withdrawal_tokens"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    token = Column(String(20), unique=True, index=True, nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    status = Column(String(20), default="ACTIVE", index=True)
    expiry_date = Column(DateTime(timezone=True), nullable=False)

    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    # atm_id_used = Column(String(20), nullable=True)

    account = relationship("Account") # Add back_populates in Account model
