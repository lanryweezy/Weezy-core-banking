# Database models for Transaction Management
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# from weezy_cbs.database import Base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base() # Local Base for now

import enum

# Re-use from accounts_ledger_management if possible, define locally for now
class CurrencyEnum(enum.Enum):
    NGN = "NGN"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

class TransactionChannelEnum(enum.Enum):
    INTERNAL = "INTERNAL" # System generated, e.g. interest posting
    INTRA_BANK = "INTRA_BANK" # Between two accounts in this bank
    NIP = "NIP" # NIBSS Instant Payment
    RTGS = "RTGS" # Real-Time Gross Settlement
    USSD = "USSD"
    POS = "POS"
    ATM = "ATM"
    WEB = "WEB_BANKING"
    MOBILE_APP = "MOBILE_APP"
    AGENT_BANKING = "AGENT_BANKING"
    BULK_PAYMENT = "BULK_PAYMENT"
    STANDING_ORDER = "STANDING_ORDER"
    # Add more as needed

class TransactionStatusEnum(enum.Enum):
    PENDING = "PENDING"             # Initial status, awaiting processing
    PROCESSING = "PROCESSING"       # Actively being processed (e.g. sent to NIBSS)
    SUCCESSFUL = "SUCCESSFUL"       # Completed successfully, funds moved
    FAILED = "FAILED"               # Processing failed, funds not moved or rolled back
    REVERSED = "REVERSED"           # A previously successful transaction that has been reversed
    PENDING_APPROVAL = "PENDING_APPROVAL" # Requires manual approval (e.g. large amount)
    FLAGGED = "FLAGGED"             # Flagged for review (e.g. AML suspicion)
    TIMEOUT = "TIMEOUT"             # Timed out waiting for response from external system
    UNKNOWN = "UNKNOWN"             # Status cannot be determined from external system

# This is the Master Transaction Record.
# Each transaction here might result in one or more LedgerEntry records
# in the accounts_ledger_management module.
class FinancialTransaction(Base):
    __tablename__ = "financial_transactions" # Renamed from Transaction to be more specific

    id = Column(String, primary_key=True, index=True) # Unique Transaction ID (e.g., UUID or bank-generated ref)

    transaction_type = Column(String, nullable=False) # e.g., 'FUNDS_TRANSFER', 'BILL_PAYMENT', 'AIRTIME_PURCHASE', 'SALARY_PAYMENT', 'LOAN_REPAYMENT'
    channel = Column(SQLAlchemyEnum(TransactionChannelEnum), nullable=False)
    status = Column(SQLAlchemyEnum(TransactionStatusEnum), default=TransactionStatusEnum.PENDING, nullable=False, index=True)

    amount = Column(Numeric(precision=18, scale=4), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    # Debitor Information
    debit_account_number = Column(String, nullable=True, index=True) # NUBAN if internal
    debit_account_name = Column(String, nullable=True)
    debit_bank_code = Column(String, nullable=True) # CBN Bank Code if interbank
    # debit_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True) # If internal debit

    # Creditor Information
    credit_account_number = Column(String, nullable=True, index=True) # NUBAN
    credit_account_name = Column(String, nullable=True)
    credit_bank_code = Column(String, nullable=True) # CBN Bank Code
    # credit_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True) # If internal credit

    narration = Column(String(255), nullable=False) # User/System provided narration
    system_remarks = Column(Text, nullable=True) # Internal remarks, error messages

    # Timestamps
    initiated_at = Column(DateTime(timezone=True), server_default=func.now()) # When the request was received
    processed_at = Column(DateTime(timezone=True), nullable=True) # When processing started/completed by our system
    external_system_at = Column(DateTime(timezone=True), nullable=True) # Timestamp from external system (e.g. NIBSS)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # External System References
    external_transaction_id = Column(String, unique=True, nullable=True, index=True) # e.g., NIBSS Session ID, Payment Gateway Ref
    response_code = Column(String, nullable=True) # Response code from external system (e.g. NIBSS '00')
    response_message = Column(String, nullable=True)

    # For reversals
    is_reversal = Column(Boolean, default=False)
    original_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, index=True) # If this is a reversal of another transaction

    # For bulk payments
    # bulk_payment_batch_id = Column(String, ForeignKey("bulk_payment_batches.id"), nullable=True, index=True)

    # For standing orders
    # standing_order_id = Column(Integer, ForeignKey("standing_orders.id"), nullable=True, index=True)

    # relationships
    # original_transaction = relationship("FinancialTransaction", remote_side=[id], backref="reversals")
    # ledger_entries = relationship("LedgerEntry", primaryjoin="foreign(LedgerEntry.transaction_id) == FinancialTransaction.id") # If LedgerEntry is in another module, this needs careful setup or an association table.

    def __repr__(self):
        return f"<FinancialTransaction(id='{self.id}', type='{self.transaction_type}', status='{self.status.value}')>"

class NIPTransaction(Base): # NIBSS Instant Payment specific details
    __tablename__ = "nip_transactions"

    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=False, unique=True)

    nibss_session_id = Column(String, unique=True, index=True)
    name_enquiry_ref = Column(String, nullable=True) # If name enquiry was done
    # NIP specific fields like ChannelCode, Fee, etc.
    # request_payload = Column(Text) # Store the XML/JSON sent to NIBSS
    # response_payload = Column(Text) # Store the XML/JSON received from NIBSS

    # transaction = relationship("FinancialTransaction", backref="nip_details")


class RTGSTransaction(Base): # RTGS specific details
    __tablename__ = "rtgs_transactions"
    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=False, unique=True)
    # RTGS specific fields like SWIFT message details, correspondent bank info, etc.
    # transaction = relationship("FinancialTransaction", backref="rtgs_details")

class USSDTransaction(Base):
    __tablename__ = "ussd_transactions"
    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=False, unique=True)
    telco_provider = Column(String, nullable=True) # MTN, GLO, etc.
    ussd_session_id = Column(String, unique=True, nullable=True) # Telco's session ID
    # transaction = relationship("FinancialTransaction", backref="ussd_details")

class BulkPaymentBatch(Base):
    __tablename__ = "bulk_payment_batches"
    id = Column(String, primary_key=True, index=True) # Batch ID
    batch_name = Column(String, nullable=True)
    # uploaded_by_user_id = Column(Integer, ForeignKey("users.id")) # User who uploaded
    total_amount = Column(Numeric(precision=18, scale=4))
    total_transactions = Column(Integer)
    status = Column(String) # PENDING_PROCESSING, PARTIALLY_PROCESSED, PROCESSED, FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # transactions = relationship("FinancialTransaction", backref="bulk_batch")

class StandingOrder(Base):
    __tablename__ = "standing_orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    debit_account_number = Column(String, nullable=False)
    credit_account_number = Column(String, nullable=False)
    credit_bank_code = Column(String, nullable=True) # For interbank standing orders

    amount = Column(Numeric(precision=18, scale=4), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    narration = Column(String, nullable=False)

    frequency = Column(String, nullable=False) # e.g., 'DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY'
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True) # Null if indefinite
    next_execution_date = Column(DateTime(timezone=True), nullable=False, index=True)
    last_execution_date = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=True, index=True)
    failure_count = Column(Integer, default=0) # Number of consecutive failures
    # max_failures = Column(Integer, default=3) # Deactivate after max_failures

    # transactions_executed = relationship("FinancialTransaction", backref="standing_order_source")

class TransactionDispute(Base):
    __tablename__ = "transaction_disputes"
    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=False)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    dispute_reason = Column(Text, nullable=False)
    status = Column(String, default="OPEN") # OPEN, UNDER_INVESTIGATION, RESOLVED_FAVOR_CUSTOMER, RESOLVED_FAVOR_BANK, CLOSED
    # logged_by_user_id = Column(Integer, ForeignKey("users.id"))
    logged_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_details = Column(Text, nullable=True)

    # transaction = relationship("FinancialTransaction", backref="disputes")

# Note: This module focuses on the orchestration and state management of transactions.
# The actual debit/credit to accounts (ledger posting) is handled by accounts_ledger_management,
# typically called by services in this module.
# Integration with NIBSS, Switches, Payment Gateways will be crucial.
# Fee calculation might also be triggered from here, calling fees_charges_commission_engine.
