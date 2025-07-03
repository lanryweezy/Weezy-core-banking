# Database models for Treasury & Liquidity Management Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Date, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from weezy_cbs.database import Base # Use the shared Base

import enum

# Assuming CurrencyEnum will be shared
# from weezy_cbs.accounts_ledger_management.models import CurrencyEnum as SharedCurrencyEnum
class CurrencyEnum(enum.Enum):
    NGN = "NGN"; USD = "USD"; EUR = "EUR"; GBP = "GBP"
    # Add other relevant currencies

class BankCashPosition(Base):
    __tablename__ = "bank_cash_positions"
    id = Column(Integer, primary_key=True, index=True)
    position_date = Column(Date, nullable=False, index=True)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False, index=True)
    total_cash_at_vault = Column(Numeric(precision=20, scale=2), nullable=False)
    total_cash_at_cbn = Column(Numeric(precision=20, scale=2), nullable=False)
    total_cash_at_correspondent_banks = Column(Numeric(precision=20, scale=2), nullable=False)
    # total_customer_deposits = Column(Numeric(precision=20, scale=2))
    # liquidity_ratio = Column(Numeric(precision=10, scale=4), nullable=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('position_date', 'currency', name='uq_bankpos_date_currency'),)
    def __repr__(self): return f"<BankCashPosition(date='{self.position_date}', currency='{self.currency.value}')>"

class FXTransactionTypeEnum(enum.Enum):
    SPOT = "SPOT"; FORWARD = "FORWARD"; SWAP = "SWAP"

class FXTransaction(Base):
    __tablename__ = "fx_transactions"
    id = Column(Integer, primary_key=True, index=True)
    deal_reference = Column(String(30), unique=True, nullable=False, index=True)
    transaction_type = Column(SQLAlchemyEnum(FXTransactionTypeEnum), nullable=False)
    trade_date = Column(Date, nullable=False)
    value_date = Column(Date, nullable=False)
    currency_pair = Column(String(7), nullable=False)
    rate = Column(Numeric(precision=18, scale=8), nullable=False)
    buy_currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    buy_amount = Column(Numeric(precision=20, scale=2), nullable=False)
    sell_currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    sell_amount = Column(Numeric(precision=20, scale=2), nullable=False)
    counterparty_name = Column(String(100), nullable=False)
    settlement_type = Column(String(20), nullable=True) # e.g. "CLSS", "NOSTRO"
    status = Column(String(30), default="PENDING_SETTLEMENT", index=True)
    settled_at = Column(DateTime(timezone=True), nullable=True)
    created_by_user_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    def __repr__(self): return f"<FXTransaction(ref='{self.deal_reference}', pair='{self.currency_pair}')>"

class TreasuryBillInvestment(Base):
    __tablename__ = "treasury_bill_investments"
    id = Column(Integer, primary_key=True, index=True)
    investment_reference = Column(String(30), unique=True, nullable=False, index=True)
    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    tenor_days = Column(Integer, nullable=False)
    face_value = Column(Numeric(precision=20, scale=2), nullable=False)
    discount_rate_pa = Column(Numeric(precision=10, scale=4), nullable=False)
    purchase_price = Column(Numeric(precision=20, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), default=CurrencyEnum.NGN, nullable=False)
    status = Column(String(30), default="ACTIVE", index=True)
    matured_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    def __repr__(self): return f"<TreasuryBillInvestment(ref='{self.investment_reference}', fv='{self.face_value}')>"

class InterbankPlacement(Base):
    __tablename__ = "interbank_placements"
    id = Column(Integer, primary_key=True, index=True)
    deal_reference = Column(String(30), unique=True, nullable=False, index=True)
    placement_type = Column(String(20), nullable=False)
    counterparty_bank_code = Column(String(10), nullable=False)
    counterparty_bank_name = Column(String(100), nullable=False)
    principal_amount = Column(Numeric(precision=20, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    interest_rate_pa = Column(Numeric(precision=10, scale=4), nullable=False)
    placement_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    tenor_days = Column(Integer, nullable=False)
    status = Column(String(30), default="ACTIVE", index=True)
    matured_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    def __repr__(self): return f"<InterbankPlacement(ref='{self.deal_reference}', type='{self.placement_type}')>"

class CBNRepoOperation(Base):
    __tablename__ = "cbn_repo_operations"
    id = Column(Integer, primary_key=True, index=True)
    operation_reference = Column(String(30), unique=True, nullable=False, index=True)
    operation_type = Column(String(20), nullable=False)
    loan_amount = Column(Numeric(precision=20, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), default=CurrencyEnum.NGN, nullable=False)
    interest_rate_pa = Column(Numeric(precision=10, scale=4), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    tenor_days = Column(Integer, nullable=False)
    status = Column(String(20), default="ACTIVE", index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# --- Conceptual Models for CBN Reconciliation ---
class CBNSettlementStatementEntry(Base):
    __tablename__ = "cbn_settlement_statement_entries"
    id = Column(Integer, primary_key=True, index=True)
    statement_date = Column(Date, nullable=False, index=True)
    cbn_reference = Column(String(50), unique=True, nullable=False, index=True)
    narration = Column(Text, nullable=True)
    debit_amount = Column(Numeric(precision=20, scale=2), nullable=True)
    credit_amount = Column(Numeric(precision=20, scale=2), nullable=True)
    balance = Column(Numeric(precision=20, scale=2), nullable=True)
    value_date = Column(Date, nullable=True)
    # internal_financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True, index=True)
    # reconciliation_status = Column(String(20), default="UNRECONCILED", index=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())

class CBNReconciliationDiscrepancy(Base):
    __tablename__ = "cbn_reconciliation_discrepancies"
    id = Column(Integer, primary_key=True, index=True)
    # settlement_entry_id = Column(Integer, ForeignKey("cbn_settlement_statement_entries.id"), nullable=True)
    # internal_financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True)
    discrepancy_type = Column(String(50), nullable=False)
    details = Column(Text)
    status = Column(String(20), default="OPEN", index=True)
    reported_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    # resolved_by_user_id = Column(String(50), nullable=True)
