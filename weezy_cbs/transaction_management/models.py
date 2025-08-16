# Database models for Transaction Management
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

# Assuming CurrencyEnum will be shared, for now define locally or import if available
# from weezy_cbs.accounts_ledger_management.models import CurrencyEnum as SharedCurrencyEnum
class CurrencyEnum(enum.Enum):
    NGN = "NGN"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

class TransactionChannelEnum(enum.Enum):
    INTERNAL = "INTERNAL"
    INTRA_BANK = "INTRA_BANK"
    NIP = "NIP"
    RTGS = "RTGS"
    USSD = "USSD"
    POS = "POS"
    ATM = "ATM"
    WEB_BANKING = "WEB_BANKING" # Renamed
    MOBILE_APP = "MOBILE_APP"
    AGENT_BANKING = "AGENT_BANKING"
    BULK_PAYMENT = "BULK_PAYMENT"
    STANDING_ORDER = "STANDING_ORDER"
    PAYMENT_GATEWAY = "PAYMENT_GATEWAY" # e.g. Paystack, Flutterwave
    BILL_PAYMENT = "BILL_PAYMENT" # For eBillsPay or direct biller

class TransactionTypeCategoryEnum(enum.Enum): # Broad categories for transaction_type
    FUNDS_TRANSFER = "FUNDS_TRANSFER"
    BILL_PAYMENT = "BILL_PAYMENT"
    AIRTIME_PURCHASE = "AIRTIME_PURCHASE"
    MERCHANT_PAYMENT = "MERCHANT_PAYMENT" # POS, Web payments to merchants
    LOAN_DISBURSEMENT = "LOAN_DISBURSEMENT"
    LOAN_REPAYMENT = "LOAN_REPAYMENT"
    FEE_CHARGE = "FEE_CHARGE" # Bank imposed fee/charge
    TAX_DUTY = "TAX_DUTY" # e.g. Stamp Duty, VAT
    ACCOUNT_OPENING_DEPOSIT = "ACCOUNT_OPENING_DEPOSIT"
    CASH_DEPOSIT = "CASH_DEPOSIT" # Teller/Agent cash deposit
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL" # Teller/Agent/ATM cash withdrawal
    INTEREST_APPLICATION = "INTEREST_APPLICATION" # Interest paid or charged
    SYSTEM_POSTING = "SYSTEM_POSTING" # Other internal system postings

class TransactionStatusEnum(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    FLAGGED_SUSPICION = "FLAGGED_SUSPICION" # Renamed from FLAGGED
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"
    AWAITING_RETRY = "AWAITING_RETRY" # New status for retryable failures
    PARTIALLY_SUCCESSFUL = "PARTIALLY_SUCCESSFUL" # For bulk payments where some items succeed

class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id = Column(String(40), primary_key=True, index=True) # UUID or prefixed sequence

    transaction_type = Column(SQLAlchemyEnum(TransactionTypeCategoryEnum), nullable=False, index=True)
    channel = Column(SQLAlchemyEnum(TransactionChannelEnum), nullable=False, index=True)
    status = Column(SQLAlchemyEnum(TransactionStatusEnum), default=TransactionStatusEnum.PENDING, nullable=False, index=True)

    amount = Column(Numeric(precision=18, scale=2), nullable=False) # Standard 2DP
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    # Debitor Information
    debit_account_number = Column(String(20), nullable=True, index=True) # Allow for GL codes or longer non-NUBAN
    debit_account_name = Column(String(150), nullable=True)
    debit_bank_code = Column(String(10), nullable=True)
    debit_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)

    # Creditor Information
    credit_account_number = Column(String(20), nullable=True, index=True)
    credit_account_name = Column(String(150), nullable=True)
    credit_bank_code = Column(String(10), nullable=True)
    credit_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)

    narration = Column(String(255), nullable=False)
    system_remarks = Column(Text, nullable=True)
    initiator_user_id = Column(String(50), nullable=True, index=True) # Staff, System, or Customer ID that triggered it
    approver_user_id = Column(String(50), nullable=True) # If approved

    # Fee & Charge details
    fee_amount = Column(Numeric(precision=18, scale=2), nullable=True, default=0.00)
    vat_amount = Column(Numeric(precision=18, scale=2), nullable=True, default=0.00)
    stamp_duty_amount = Column(Numeric(precision=18, scale=2), nullable=True, default=0.00)
    charge_details_json = Column(Text, nullable=True) # JSON from FeeEngine: {"fee_code": "NIP_FEE", "amount": 10.00, ...}

    # Link to a primary internal account if applicable (e.g. bill payment FROM this account)
    # related_internal_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)

    # Timestamps
    initiated_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    external_system_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # External System References
    external_transaction_id = Column(String(100), unique=True, nullable=True, index=True)
    response_code = Column(String(10), nullable=True)
    response_message = Column(String(255), nullable=True)

    # Reversals
    is_reversal = Column(Boolean, default=False)
    original_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True, index=True)

    # Linkages
    bulk_payment_batch_id = Column(String(40), ForeignKey("bulk_payment_batches.id"), nullable=True, index=True)
    standing_order_id = Column(Integer, ForeignKey("standing_orders.id"), nullable=True, index=True)

    # Relationships
    debit_customer = relationship("Customer", foreign_keys=[debit_customer_id])
    credit_customer = relationship("Customer", foreign_keys=[credit_customer_id])
    original_transaction = relationship("FinancialTransaction", remote_side=[id], back_populates="reversals_initiated")
    reversals_initiated = relationship("FinancialTransaction", back_populates="original_transaction") # For original_transaction_id

    nip_details = relationship("NIPTransaction", back_populates="financial_transaction", uselist=False, cascade="all, delete-orphan")
    rtgs_details = relationship("RTGSTransaction", back_populates="financial_transaction", uselist=False, cascade="all, delete-orphan")
    ussd_details = relationship("USSDTransaction", back_populates="financial_transaction", uselist=False, cascade="all, delete-orphan")

    bulk_payment_batch = relationship("BulkPaymentBatch", back_populates="financial_transactions")
    standing_order = relationship("StandingOrder", back_populates="executed_transactions")
    disputes = relationship("TransactionDispute", back_populates="financial_transaction")

    # ledger_entries: Mapped[List["LedgerEntry"]] = relationship( # Requires LedgerEntry model to be known, or use string ref
    #    "LedgerEntry", primaryjoin="foreign(LedgerEntry.financial_transaction_id) == FinancialTransaction.id"
    # )


    def __repr__(self):
        return f"<FinancialTransaction(id='{self.id}', type='{self.transaction_type.value}', status='{self.status.value}')>"

class NIPTransaction(Base):
    __tablename__ = "nip_transactions"
    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=False, unique=True, index=True)

    nibss_session_id = Column(String(50), unique=True, index=True, nullable=False)
    name_enquiry_ref = Column(String(50), nullable=True)
    nip_channel_code = Column(String(2), nullable=True) # NIBSS standard channel code
    fee = Column(Numeric(precision=18, scale=2), nullable=True, default=0.00)
    commission_amount = Column(Numeric(precision=18, scale=2), nullable=True, default=0.00)
    # request_payload_json = Column(Text)
    # response_payload_json = Column(Text)

    financial_transaction = relationship("FinancialTransaction", back_populates="nip_details")

class RTGSTransaction(Base):
    __tablename__ = "rtgs_transactions"
    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=False, unique=True, index=True)
    swift_message_type = Column(String(10), nullable=True) # e.g. MT103
    # bic_sender = Column(String(11), nullable=True)
    # bic_receiver = Column(String(11), nullable=True)
    priority = Column(String(10), nullable=True) # NORMAL, URGENT
    # ... other RTGS specific fields ...
    financial_transaction = relationship("FinancialTransaction", back_populates="rtgs_details")

class USSDTransaction(Base):
    __tablename__ = "ussd_transactions"
    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=False, unique=True, index=True)
    telco_provider = Column(String(20), nullable=True)
    ussd_session_id_external = Column(String(50), unique=True, nullable=True) # Telco's session ID
    ussd_menu_string_trace = Column(Text, nullable=True) # Sequence of inputs
    financial_transaction = relationship("FinancialTransaction", back_populates="ussd_details")

class BulkPaymentBatch(Base):
    __tablename__ = "bulk_payment_batches"
    id = Column(String(40), primary_key=True, index=True)
    batch_name = Column(String(100), nullable=True)
    uploaded_by_user_id = Column(String(50), nullable=False)
    debit_account_number = Column(String(20), nullable=False)
    total_amount = Column(Numeric(precision=18, scale=2), nullable=False)
    total_transactions = Column(Integer, nullable=False)
    status = Column(String(30), default="PENDING_PROCESSING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processing_start_time = Column(DateTime(timezone=True), nullable=True)
    processing_end_time = Column(DateTime(timezone=True), nullable=True)

    financial_transactions = relationship("FinancialTransaction", back_populates="bulk_payment_batch")

class StandingOrder(Base):
    __tablename__ = "standing_orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    debit_account_number = Column(String(20), nullable=False)
    credit_account_number = Column(String(20), nullable=False)
    credit_bank_code = Column(String(10), nullable=True)

    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    narration = Column(String(100), nullable=False)

    frequency = Column(String(20), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    next_execution_date = Column(DateTime(timezone=True), nullable=False, index=True)
    last_execution_date = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=True, index=True)
    failure_count = Column(Integer, default=0)
    # max_failures_allowed = Column(Integer, default=3)

    executed_transactions = relationship("FinancialTransaction", back_populates="standing_order")
    customer = relationship("Customer") # Add back_populates in Customer model

class TransactionDispute(Base):
    __tablename__ = "transaction_disputes"
    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    dispute_reason = Column(Text, nullable=False)
    status = Column(String(30), default="OPEN", index=True)
    logged_by_user_id = Column(String(50), nullable=True)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_details = Column(Text, nullable=True)

    financial_transaction = relationship("FinancialTransaction", back_populates="disputes")
    customer = relationship("Customer") # Add back_populates in Customer model
