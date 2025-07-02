# Database models for Accounts & Ledger Management
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# from weezy_cbs.database import Base # Assuming a shared declarative base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base() # Local Base for now

import enum

class AccountTypeEnum(enum.Enum):
    SAVINGS = "Savings"
    CURRENT = "Current"
    FIXED_DEPOSIT = "Fixed Deposit"
    # Add more as needed, e.g., DOMICILIARY, LOAN_ACCOUNT

class AccountStatusEnum(enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive" # No transactions for a defined period
    DORMANT = "Dormant"   # Inactive for a longer, legally defined period
    CLOSED = "Closed"
    BLOCKED = "Blocked"   # e.g., due to fraud suspicion, court order

class CurrencyEnum(enum.Enum): # Should ideally be a more comprehensive list or table
    NGN = "NGN"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(10), unique=True, index=True, nullable=False) # Standard NUBAN
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True) # Assuming 'customers' table from customer_identity_management

    account_type = Column(SQLAlchemyEnum(AccountTypeEnum), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False, default=CurrencyEnum.NGN)

    ledger_balance = Column(Numeric(precision=18, scale=4), default=0.0000, nullable=False)
    available_balance = Column(Numeric(precision=18, scale=4), default=0.0000, nullable=False)
    # available_balance = ledger_balance - uncleared_funds - lien_amount

    lien_amount = Column(Numeric(precision=18, scale=4), default=0.0000) # Funds earmarked, not spendable
    uncleared_funds = Column(Numeric(precision=18, scale=4), default=0.0000) # e.g. Cheque deposits not yet cleared

    status = Column(SQLAlchemyEnum(AccountStatusEnum), default=AccountStatusEnum.ACTIVE, nullable=False)

    # For Fixed Deposits
    fd_maturity_date = Column(DateTime(timezone=True), nullable=True)
    fd_interest_rate = Column(Numeric(precision=5, scale=2), nullable=True) # e.g. 5.75%
    fd_principal = Column(Numeric(precision=18, scale=4), nullable=True)

    # Interest accrual related
    last_interest_accrual_date = Column(DateTime(timezone=True), nullable=True)
    accrued_interest = Column(Numeric(precision=18, scale=4), default=0.0000)

    # Dormancy related
    last_activity_date = Column(DateTime(timezone=True), server_default=func.now())

    opened_date = Column(DateTime(timezone=True), server_default=func.now())
    closed_date = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    # customer = relationship("Customer", back_populates="accounts") # From customer_identity_management.models.Customer
    # transactions = relationship("LedgerTransaction", back_populates="account") # See LedgerTransaction below

    def __repr__(self):
        return f"<Account(account_number='{self.account_number}', type='{self.account_type.value}', balance='{self.ledger_balance}')>"

class TransactionTypeEnum(enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, index=True, nullable=False) # Link to a master transaction record
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)

    entry_type = Column(SQLAlchemyEnum(TransactionTypeEnum), nullable=False) # DEBIT or CREDIT
    amount = Column(Numeric(precision=18, scale=4), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False) # Ensure consistency with account currency

    narration = Column(String, nullable=False)
    transaction_date = Column(DateTime(timezone=True), server_default=func.now(), index=True) # When the transaction was booked
    value_date = Column(DateTime(timezone=True), server_default=func.now(), index=True) # When the funds are considered available/valued

    balance_before = Column(Numeric(precision=18, scale=4))
    balance_after = Column(Numeric(precision=18, scale=4)) # Ledger balance after this entry

    # Reference to other systems/details
    # e.g., NIP_session_id, reversal_of_transaction_id, teller_id, channel (ATM, POS, WEB, MOBILE)
    channel = Column(String, nullable=True)
    reference_number = Column(String, unique=True, index=True, nullable=True) # External ref, e.g., payment gateway ref

    # account = relationship("Account", back_populates="ledger_entries") # Relationship to Account

    def __repr__(self):
        return f"<LedgerEntry(id={self.id}, acc_id={self.account_id}, type='{self.entry_type.value}', amt='{self.amount}')>"

# This is a simplified General Ledger Account structure. A full GL is much more complex.
class GeneralLedgerAccount(Base):
    __tablename__ = "gl_accounts"

    id = Column(Integer, primary_key=True, index=True)
    gl_code = Column(String, unique=True, index=True, nullable=False) # e.g., "1001001" for Cash NGN
    name = Column(String, nullable=False) # e.g., "Cash Naira"
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    is_control_account = Column(Boolean, default=False) # If it's a control account for customer ledgers
    # Other GL properties like type (Asset, Liability, Equity, Income, Expense), parent_gl_code etc.

# Note: For a true double-entry system, each financial transaction would typically result
# in at least two LedgerEntry records (one DEBIT, one CREDIT) that must balance.
# A master "FinancialTransaction" table might orchestrate these entries.

# Example of a master transaction table (optional, can be part of transaction_management)
class FinancialTransaction(Base):
    __tablename__ = "financial_transactions" # Could be in transaction_management
    id = Column(String, primary_key=True, index=True) # Unique transaction ID (e.g. UUID)
    description = Column(String)
    status = Column(String) # PENDING, SUCCESSFUL, FAILED, REVERSED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # entries = relationship("LedgerEntry"...) # if LedgerEntry.transaction_id is a ForeignKey to this.
    # This table would hold the overall status of a transaction that might involve multiple ledger postings.

# InterestAccrualLog might be useful for tracking daily accruals before posting
class InterestAccrualLog(Base):
    __tablename__ = "interest_accrual_logs"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    accrual_date = Column(DateTime(timezone=True), nullable=False)
    amount_accrued = Column(Numeric(precision=18, scale=4), nullable=False)
    interest_rate_used = Column(Numeric(precision=5, scale=2), nullable=False)
    balance_subject_to_interest = Column(Numeric(precision=18, scale=4), nullable=False)
    is_posted_to_account = Column(Boolean, default=False) # True when this amount is credited to account.accrued_interest

# To run:
# from sqlalchemy import create_engine
# from weezy_cbs.database import DATABASE_URL
# engine = create_engine(DATABASE_URL)
# Base.metadata.create_all(bind=engine)
