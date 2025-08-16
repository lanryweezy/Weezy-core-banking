# Database models for Deposit & Collection Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from weezy_cbs.database import Base # Use the shared Base

import enum

# Assuming CurrencyEnum will be shared
# from weezy_cbs.accounts_ledger_management.models import CurrencyEnum as SharedCurrencyEnum
class CurrencyEnum(enum.Enum):
    NGN = "NGN"; USD = "USD" # Add others as needed

class DepositTypeEnum(enum.Enum):
    CASH = "CASH"
    CHEQUE = "CHEQUE"
    AGENT_DEPOSIT = "AGENT_DEPOSIT"
    POS_DEPOSIT = "POS_DEPOSIT"
    DIRECT_DEBIT_COLLECTION = "DIRECT_DEBIT_COLLECTION"

class DepositStatusEnum(enum.Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    PENDING_CLEARANCE = "PENDING_CLEARANCE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class CashDepositLog(Base):
    __tablename__ = "cash_deposit_logs"

    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    account_number = Column(String(20), nullable=False, index=True)

    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    depositor_name = Column(String(150), nullable=True)
    depositor_phone = Column(String(15), nullable=True)

    teller_id = Column(String(50), nullable=True, index=True)
    branch_code = Column(String(10), nullable=True, index=True)

    status = Column(SQLAlchemyEnum(DepositStatusEnum), default=DepositStatusEnum.COMPLETED, index=True)
    notes = Column(Text, nullable=True)

    deposit_date = Column(DateTime(timezone=True), server_default=func.now())

    agent_id_external = Column(String(50), nullable=True, index=True)
    agent_terminal_id = Column(String(30), nullable=True)
    # agent_transaction_reference = Column(String(50), nullable=True, unique=True)

    financial_transaction = relationship("FinancialTransaction") # Add back_populates in FT model if needed
    account = relationship("Account") # Add back_populates in Account model

    def __repr__(self):
        return f"<CashDepositLog(id={self.id}, ft_id='{self.financial_transaction_id}', status='{self.status.value}')>"

class ChequeDepositLog(Base):
    __tablename__ = "cheque_deposit_logs"

    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True, index=True, comment="Populated upon successful clearing or if FT created upfront")
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    account_number = Column(String(20), nullable=False, index=True)

    cheque_number = Column(String(20), nullable=False, index=True)
    drawee_bank_code = Column(String(10), nullable=False)
    drawee_account_number = Column(String(20), nullable=True)
    drawer_name = Column(String(150), nullable=True)

    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    depositor_name = Column(String(150), nullable=True)

    teller_id = Column(String(50), nullable=True, index=True)
    branch_code = Column(String(10), nullable=True, index=True)

    status = Column(SQLAlchemyEnum(DepositStatusEnum), default=DepositStatusEnum.PENDING_CLEARANCE, index=True)
    reason_for_failure = Column(String(255), nullable=True)

    deposit_date = Column(Date, server_default=func.current_date()) # Date of deposit
    clearing_date_expected = Column(Date, nullable=True)
    cleared_date_actual = Column(Date, nullable=True)

    # cheque_image_front_url = Column(String(512), nullable=True)
    # cheque_image_back_url = Column(String(512), nullable=True)
    # micr_data = Column(String(100), nullable=True)

    financial_transaction = relationship("FinancialTransaction")
    account = relationship("Account")

    def __repr__(self):
        return f"<ChequeDepositLog(id={self.id}, chq_no='{self.cheque_number}', status='{self.status.value}')>"

class CollectionService(Base):
    __tablename__ = "collection_services"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), unique=True, nullable=False)
    merchant_id_external = Column(String(50), unique=True, nullable=False, index=True)
    merchant_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    fee_config_code = Column(String, ForeignKey("fee_configs.fee_code"), nullable=True) # Link by code

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    merchant_account = relationship("Account") # Add back_populates if needed
    # fee_config = relationship("FeeConfig") # Add back_populates if needed

    def __repr__(self):
        return f"<CollectionService(name='{self.service_name}', merchant_id='{self.merchant_id_external}')>"

class CollectionPaymentLog(Base):
    __tablename__ = "collection_payment_logs"
    id = Column(Integer, primary_key=True, index=True)
    collection_service_id = Column(Integer, ForeignKey("collection_services.id"), nullable=False, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=False, index=True)

    payer_name = Column(String(150), nullable=True)
    payer_phone = Column(String(15), nullable=True)
    payer_email = Column(String(100), nullable=True)

    customer_identifier_at_merchant = Column(String(100), nullable=False, index=True)
    amount_paid = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    payment_channel = Column(String(30), nullable=True)
    payment_reference_external = Column(String(100), unique=True, nullable=True, index=True)

    status = Column(String(20), default="SUCCESSFUL", index=True)
    payment_date = Column(DateTime(timezone=True), server_default=func.now())

    is_settled_to_merchant = Column(Boolean, default=False, index=True)
    settlement_batch_id = Column(String(50), nullable=True, index=True)
    settlement_date = Column(DateTime(timezone=True), nullable=True)

    collection_service = relationship("CollectionService") # Add back_populates if needed
    financial_transaction = relationship("FinancialTransaction") # Add back_populates if needed

    def __repr__(self):
        return f"<CollectionPaymentLog(id={self.id}, service_id='{self.collection_service_id}', cust_id='{self.customer_identifier_at_merchant}')>"

class POSReconciliationBatch(Base):
    __tablename__ = "pos_reconciliation_batches"
    id = Column(Integer, primary_key=True, index=True)
    batch_date = Column(Date, nullable=False, unique=True) # Changed to Date
    source_file_name = Column(String(255), nullable=True)
    status = Column(String(30), default="PENDING", index=True)
    total_transactions_in_file = Column(Integer, nullable=True)
    total_amount_in_file = Column(Numeric(precision=18, scale=2), nullable=True)
    matched_transactions_count = Column(Integer, default=0)
    unmatched_transactions_count = Column(Integer, default=0)
    discrepancy_amount = Column(Numeric(precision=18, scale=2), default=0.00)
    processed_at = Column(DateTime(timezone=True), nullable=True)

class POSReconciliationDiscrepancy(Base):
    __tablename__ = "pos_reconciliation_discrepancies"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("pos_reconciliation_batches.id"), nullable=False, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True, index=True)
    external_transaction_reference = Column(String(50), nullable=True, index=True)

    discrepancy_type = Column(String(30), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(20), default="OPEN", index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    batch = relationship("POSReconciliationBatch") # Add back_populates if needed
    financial_transaction = relationship("FinancialTransaction") # Add back_populates if needed
