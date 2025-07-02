# Database models for Deposit & Collection Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# from weezy_cbs.database import Base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base() # Local Base for now

import enum

# Re-use from accounts_ledger_management if possible
class CurrencyEnum(enum.Enum):
    NGN = "NGN"
    USD = "USD"
    # Add others as needed

class DepositTypeEnum(enum.Enum):
    CASH = "CASH"
    CHEQUE = "CHEQUE"
    AGENT_DEPOSIT = "AGENT_DEPOSIT" # Cash deposit via an agent
    POS_DEPOSIT = "POS_DEPOSIT" # Deposit via POS terminal (less common for direct deposit, more for payment)
    # DIRECT_DEBIT_COLLECTION = "DIRECT_DEBIT_COLLECTION"

class DepositStatusEnum(enum.Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION" # For cash > threshold, or cheque
    PENDING_CLEARANCE = "PENDING_CLEARANCE"     # For cheques
    COMPLETED = "COMPLETED"                     # Funds successfully credited
    FAILED = "FAILED"                           # Deposit failed (e.g. counterfeit, bounced cheque)
    CANCELLED = "CANCELLED"                     # Deposit cancelled by teller/system before completion

class CashDepositLog(Base):
    __tablename__ = "cash_deposit_logs"

    id = Column(Integer, primary_key=True, index=True)
    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, index=True) # Link to master FT
    # account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True) # Account being credited
    account_number = Column(String, nullable=False, index=True) # Account being credited

    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    depositor_name = Column(String, nullable=True) # Name of person making the deposit
    depositor_phone = Column(String, nullable=True)

    teller_id = Column(String, nullable=True, index=True) # ID of the bank teller or agent
    branch_code = Column(String, nullable=True, index=True) # Branch where deposit was made

    status = Column(SQLAlchemyEnum(DepositStatusEnum), default=DepositStatusEnum.COMPLETED) # Cash usually completed instantly unless large
    notes = Column(Text, nullable=True) # Any remarks by teller/system

    deposit_date = Column(DateTime(timezone=True), server_default=func.now())

    # If large cash deposit requiring AML checks
    # is_flagged_aml = Column(Boolean, default=False)
    # aml_officer_id = Column(String, nullable=True)
    # aml_cleared_at = Column(DateTime(timezone=True), nullable=True)

    # For agent banking integration (NIBSS SANEF)
    agent_id_external = Column(String, nullable=True, index=True) # SANEF Agent ID
    agent_terminal_id = Column(String, nullable=True) # Agent's POS/Terminal ID
    # agent_transaction_reference = Column(String, nullable=True, unique=True) # Agent's reference for the transaction

    def __repr__(self):
        return f"<CashDepositLog(id={self.id}, acc='{self.account_number}', amt='{self.amount}', status='{self.status.value}')>"

class ChequeDepositLog(Base):
    __tablename__ = "cheque_deposit_logs"

    id = Column(Integer, primary_key=True, index=True)
    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, index=True)
    # account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True) # Beneficiary account
    account_number = Column(String, nullable=False, index=True) # Beneficiary account number

    cheque_number = Column(String, nullable=False, index=True)
    drawee_bank_code = Column(String, nullable=False) # Bank code of the cheque being deposited
    drawee_account_number = Column(String, nullable=True) # Account number on the cheque
    drawer_name = Column(String, nullable=True) # Name of the person/entity that wrote the cheque

    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    depositor_name = Column(String, nullable=True)

    teller_id = Column(String, nullable=True, index=True)
    branch_code = Column(String, nullable=True, index=True)

    status = Column(SQLAlchemyEnum(DepositStatusEnum), default=DepositStatusEnum.PENDING_CLEARANCE)
    # reason_for_failure = Column(String, nullable=True) # e.g. "Insufficient Funds", "Signature Mismatch"

    deposit_date = Column(DateTime(timezone=True), server_default=func.now())
    clearing_date_expected = Column(DateTime(timezone=True), nullable=True) # T+1, T+2 etc.
    cleared_date_actual = Column(DateTime(timezone=True), nullable=True) # When funds actually cleared

    # Cheque image URLs (front & back) - important for modern clearing
    # cheque_image_front_url = Column(String, nullable=True)
    # cheque_image_back_url = Column(String, nullable=True)
    # micr_data = Column(String, nullable=True) # Data read from MICR line

    def __repr__(self):
        return f"<ChequeDepositLog(id={self.id}, chq_no='{self.cheque_number}', amt='{self.amount}', status='{self.status.value}')>"

# --- Collection Management ---
# For scenarios where the bank helps collect funds for third parties (schools, bills, donations)
class CollectionService(Base): # Represents a service for which bank collects payments
    __tablename__ = "collection_services"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, unique=True, nullable=False) # e.g., "ABC School Fees", "XYZ Electricity Bill"
    merchant_id_external = Column(String, unique=True, nullable=False, index=True) # The merchant's ID with the bank
    # merchant_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False) # Account where collected funds are settled

    # Configuration for validation, fees, etc.
    # validation_endpoint = Column(String, nullable=True) # URL to validate customer ID with merchant
    # fee_config_id = Column(Integer, ForeignKey("fee_configs.id"), nullable=True) # Link to fee module
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<CollectionService(name='{self.service_name}', merchant_id='{self.merchant_id_external}')>"

class CollectionPaymentLog(Base):
    __tablename__ = "collection_payment_logs"
    id = Column(Integer, primary_key=True, index=True)
    # collection_service_id = Column(Integer, ForeignKey("collection_services.id"), nullable=False, index=True)
    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, index=True) # Link to master FT

    # Payer information
    payer_name = Column(String, nullable=True)
    payer_phone = Column(String, nullable=True)
    payer_email = Column(String, nullable=True)

    # Payment details specific to the collection service
    customer_identifier_at_merchant = Column(String, nullable=False, index=True) # e.g., Student ID, Meter No, Invoice No
    amount_paid = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    payment_channel = Column(String, nullable=True) # e.g., "BRANCH_TELLER", "AGENT", "ONLINE_PORTAL", "USSD"
    payment_reference_external = Column(String, unique=True, nullable=True) # Ref from payment channel/gateway

    status = Column(String, default="SUCCESSFUL") # PENDING, SUCCESSFUL, FAILED
    payment_date = Column(DateTime(timezone=True), server_default=func.now())

    # Settlement details
    # is_settled_to_merchant = Column(Boolean, default=False)
    # settlement_batch_id = Column(String, nullable=True)
    # settlement_date = Column(DateTime(timezone=True), nullable=True)

    # collection_service = relationship("CollectionService")

    def __repr__(self):
        return f"<CollectionPaymentLog(id={self.id}, service_id='{self.collection_service_id}', cust_id='{self.customer_identifier_at_merchant}')>"


# POS Reconciliation: This is more of a process.
# It would involve:
# 1. Receiving daily transaction files from POS acquirers/switches (e.g., NIBSS, Interswitch).
# 2. Matching these transactions against internal records (e.g., FinancialTransaction, CardTransaction).
# 3. Identifying discrepancies (missing transactions, mismatched amounts).
# 4. Potentially creating adjustment entries in the ledger.
# A `POSReconciliationBatch` and `POSReconciliationDiscrepancy` model might be useful.

class POSReconciliationBatch(Base):
    __tablename__ = "pos_reconciliation_batches"
    id = Column(Integer, primary_key=True, index=True)
    batch_date = Column(DateTime(timezone=True), nullable=False, unique=True)
    source_file_name = Column(String, nullable=True) # Name of the file from acquirer
    status = Column(String, default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED
    total_transactions_in_file = Column(Integer, nullable=True)
    total_amount_in_file = Column(Numeric(precision=18, scale=2), nullable=True)
    matched_transactions_count = Column(Integer, default=0)
    unmatched_transactions_count = Column(Integer, default=0)
    discrepancy_amount = Column(Numeric(precision=18, scale=2), default=0.00)
    processed_at = Column(DateTime(timezone=True), nullable=True)

class POSReconciliationDiscrepancy(Base):
    __tablename__ = "pos_reconciliation_discrepancies"
    id = Column(Integer, primary_key=True, index=True)
    # batch_id = Column(Integer, ForeignKey("pos_reconciliation_batches.id"), nullable=False)
    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True) # Our internal FT if found
    external_transaction_reference = Column(String, nullable=True) # RRN or STAN from POS file

    discrepancy_type = Column(String) # e.g., "MISSING_INTERNAL", "MISSING_EXTERNAL", "AMOUNT_MISMATCH"
    details = Column(Text)
    status = Column(String, default="OPEN") # OPEN, INVESTIGATING, RESOLVED, CLOSED
    resolved_at = Column(DateTime(timezone=True), nullable=True)

# Agent Banking (NIBSS SANEF) integration specific logging might be part of CashDepositLog
# or a separate AgentTransaction log if more details are needed beyond what FT captures.
# The `agent_id_external`, `agent_terminal_id` in CashDepositLog are examples.
