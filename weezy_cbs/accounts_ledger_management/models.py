# Database models for Accounts & Ledger Management
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Date, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# IMPORTANT: In a real multi-module setup, Base should be imported from a shared weezy_cbs.database module
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base() # Local Base for now

import enum

class AccountTypeEnum(enum.Enum):
    SAVINGS = "SAVINGS"
    CURRENT = "CURRENT"
    FIXED_DEPOSIT = "FIXED_DEPOSIT"
    DOMICILIARY = "DOMICILIARY"
    LOAN_ACCOUNT = "LOAN_ACCOUNT" # For loan disbursement/repayment tracking

class AccountStatusEnum(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"       # No transactions for a defined period (e.g. 6 months)
    DORMANT = "DORMANT"         # Inactive for a longer, legally defined period (e.g. 1-2 years)
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"         # General block
    # Specific block reasons can be stored in block_reason field or use more statuses
    # BLOCKED_PND = "BLOCKED_PND" # Post-No-Debit by regulatory order
    # BLOCKED_LIEN = "BLOCKED_LIEN" # Lien placed
    # BLOCKED_FRAUD = "BLOCKED_FRAUD" # Suspected fraud

class CurrencyEnum(enum.Enum): # Should ideally be a more comprehensive list or table from a shared module
    NGN = "NGN"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    # Add more as needed

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(10), unique=True, index=True, nullable=False) # Standard NUBAN
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    product_code = Column(String, ForeignKey("product_configs.product_code"), nullable=False, index=True) # Link to ProductConfig

    account_type = Column(SQLAlchemyEnum(AccountTypeEnum), nullable=False) # Derived from product_code usually
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False, default=CurrencyEnum.NGN) # Derived from product_code

    ledger_balance = Column(Numeric(precision=18, scale=2), default=0.00, nullable=False)
    available_balance = Column(Numeric(precision=18, scale=2), default=0.00, nullable=False)
    # available_balance = ledger_balance - uncleared_funds - lien_amount

    lien_amount = Column(Numeric(precision=18, scale=2), default=0.00)
    uncleared_funds = Column(Numeric(precision=18, scale=2), default=0.00)

    status = Column(SQLAlchemyEnum(AccountStatusEnum), default=AccountStatusEnum.ACTIVE, nullable=False, index=True)
    is_post_no_debit = Column(Boolean, default=False, nullable=False, index=True) # PND status
    block_reason = Column(String, nullable=True) # Reason if status is BLOCKED

    # For Fixed Deposits
    fd_maturity_date = Column(Date, nullable=True) # Changed to Date
    fd_interest_rate_pa = Column(Numeric(precision=5, scale=2), nullable=True) # e.g. 5.75%
    fd_principal_amount = Column(Numeric(precision=18, scale=2), nullable=True)
    # fd_rollover_instruction = Column(String, nullable=True) # e.g. "ROLLOVER_PRINCIPAL_INTEREST", "PAYOUT_TO_LINKED_ACCOUNT"

    # Interest accrual related
    last_interest_accrual_run_date = Column(Date, nullable=True) # Changed to Date
    accrued_interest_payable = Column(Numeric(precision=18, scale=2), default=0.00) # Interest accrued but not yet paid to account
    accrued_interest_receivable = Column(Numeric(precision=18, scale=2), default=0.00) # For loan accounts (asset)

    # Dormancy related
    last_customer_initiated_activity_date = Column(DateTime(timezone=True), server_default=func.now()) # Use DateTime for precision

    opened_date = Column(Date, server_default=func.current_date(), nullable=False) # Changed to Date
    closed_date = Column(Date, nullable=True) # Changed to Date

    # Relationships
    customer = relationship("Customer") # Add back_populates="accounts" in Customer model
    product_config = relationship("ProductConfig") # Add back_populates in ProductConfig model
    ledger_entries = relationship("LedgerEntry", back_populates="account", order_by="LedgerEntry.id")

    def __repr__(self):
        return f"<Account(account_number='{self.account_number}', type='{self.account_type.value}', balance='{self.ledger_balance}')>"

class TransactionTypeEnum(enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    # This should link to the master transaction record in transaction_management module
    financial_transaction_id = Column(String, index=True, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)

    entry_type = Column(SQLAlchemyEnum(TransactionTypeEnum), nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=False) # Standard 2 decimal places
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    narration = Column(String(255), nullable=False) # Max length for narration
    # Booking date (when it hits the ledger)
    transaction_date = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    # Value date (when funds are considered of value - important for interest, float)
    value_date = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)

    balance_before = Column(Numeric(precision=18, scale=2), nullable=False)
    balance_after = Column(Numeric(precision=18, scale=2), nullable=False)

    channel = Column(String(50), nullable=True, index=True) # e.g., ATM, POS, NIP, WEB, MOBILE, COUNTER
    # External reference, not necessarily unique across all entries (e.g. NIP session ID can appear for debit, credit, fees)
    # But can be indexed for faster lookups.
    external_reference_number = Column(String(100), index=True, nullable=True)

    is_reversal_entry = Column(Boolean, default=False)
    # original_ledger_entry_id = Column(Integer, ForeignKey("ledger_entries.id"), nullable=True) # If this entry reverses another

    account = relationship("Account", back_populates="ledger_entries")

    def __repr__(self):
        return f"<LedgerEntry(id={self.id}, acc_id={self.account_id}, type='{self.entry_type.value}', amt='{self.amount}')>"

class GeneralLedgerAccount(Base):
    __tablename__ = "gl_accounts"

    id = Column(Integer, primary_key=True, index=True)
    gl_code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    # gl_type = Column(String) # ASSET, LIABILITY, EQUITY, INCOME, EXPENSE (important for financial statements)
    # parent_gl_code = Column(String(20), ForeignKey("gl_accounts.gl_code"), nullable=True) # For hierarchical chart of accounts
    is_control_account = Column(Boolean, default=False) # If it's a control account for customer/subsidiary ledgers
    current_balance = Column(Numeric(precision=20, scale=2), default=0.00, nullable=False) # GLs also have balances

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Removed FinancialTransaction model from here, it belongs in transaction_management.

class InterestAccrualLog(Base): # Tracking daily accruals before posting
    __tablename__ = "interest_accrual_logs" # Renamed from interest_accrual_logs
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    accrual_date = Column(Date, nullable=False) # Accrual is typically daily
    amount_accrued = Column(Numeric(precision=18, scale=4), nullable=False) # Allow more precision for accrual calculation
    interest_rate_pa_used = Column(Numeric(precision=10, scale=4), nullable=False) # Store the rate used
    balance_subject_to_interest = Column(Numeric(precision=18, scale=2), nullable=False)

    is_posted_to_account_ledger = Column(Boolean, default=False) # True when this amount is credited to account's ledger_balance
    posting_date = Column(Date, nullable=True) # Date when it was posted
    # related_ledger_entry_id = Column(Integer, ForeignKey("ledger_entries.id"), nullable=True) # Link to the credit entry

    account = relationship("Account") # Add backref if needed

# Note: For relationships to tables in other modules (e.g. Customer, ProductConfig),
# ensure string foreign keys are used if Base is not shared, or use the shared Base.
# Example: customer_id = Column(Integer, ForeignKey("customers.id"), ...)
# This assumes 'customers' table is defined elsewhere but known to SQLAlchemy metadata.
# Proper setup involves all models registering with the same `Base` from `weezy_cbs.database`.
