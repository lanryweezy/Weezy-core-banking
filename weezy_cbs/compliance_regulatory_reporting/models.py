# Database models for Compliance & Regulatory Reporting Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum as SQLAlchemyEnum, ForeignKey, Date, Index, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from weezy_cbs.database import Base # Use the shared Base

import enum

class ReportNameEnum(enum.Enum):
    CBN_CRMS = "CBN_CRMS"; NDIC_RETURNS = "NDIC_RETURNS"; NFIU_STR = "NFIU_STR"
    NFIU_CTR = "NFIU_CTR"; CBN_FINA = "CBN_FINA"; CBN_OVERSIGHT = "CBN_OVERSIGHT"
    # Add more

class ReportStatusEnum(enum.Enum):
    PENDING_GENERATION = "PENDING_GENERATION"; GENERATING = "GENERATING"; GENERATED = "GENERATED"
    VALIDATION_PENDING = "VALIDATION_PENDING"; VALIDATED = "VALIDATED"
    SUBMISSION_PENDING = "SUBMISSION_PENDING"; SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"; QUERIED = "QUERIED"
    FAILED_GENERATION = "FAILED_GENERATION"; FAILED_SUBMISSION = "FAILED_SUBMISSION"

class GeneratedReportLog(Base):
    __tablename__ = "generated_report_logs"
    id = Column(Integer, primary_key=True, index=True)
    report_name = Column(SQLAlchemyEnum(ReportNameEnum), nullable=False, index=True)
    reporting_period_start_date = Column(Date, nullable=False)
    reporting_period_end_date = Column(Date, nullable=False)
    status = Column(SQLAlchemyEnum(ReportStatusEnum), default=ReportStatusEnum.PENDING_GENERATION, nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    generated_by_user_id = Column(String(50), nullable=True)
    file_path_or_url = Column(String(512), nullable=True)
    file_format = Column(String(10), nullable=True)
    checksum = Column(String(64), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submission_reference = Column(String(100), nullable=True)
    validator_user_id = Column(String(50), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    validation_comments = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    __table_args__ = (Index("idx_report_period_name_v2", "report_name", "reporting_period_end_date"),) # Renamed index due to potential conflict
    def __repr__(self): return f"<GeneratedReportLog(id={self.id}, name='{self.report_name.value}', status='{self.status.value}')>"

class AMLRule(Base):
    __tablename__ = "aml_rules"
    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    parameters_json = Column(Text)
    severity = Column(String(20), default="MEDIUM")
    action_to_take = Column(String(50), default="FLAG_FOR_REVIEW")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()) # Added server_default
    def __repr__(self): return f"<AMLRule(code='{self.rule_code}', active={self.is_active})>"

class SuspiciousActivityLog(Base):
    __tablename__ = "suspicious_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True, index=True)

    customer_bvn = Column(String(11), nullable=True, index=True) # Denormalized BVN
    account_number = Column(String(20), nullable=True, index=True) # Denormalized Acc No
    transaction_reference_primary = Column(String(40), nullable=True, index=True) # Denormalized FT ID

    aml_rule_code_triggered = Column(String(50), ForeignKey("aml_rules.rule_code"), nullable=False, index=True)
    flagged_at = Column(DateTime(timezone=True), server_default=func.now())
    activity_description = Column(Text, nullable=False)
    status = Column(String(30), default="OPEN", index=True)
    assigned_to_user_id = Column(String(50), nullable=True)
    investigation_notes = Column(Text, nullable=True)
    resolution_date = Column(DateTime(timezone=True), nullable=True)
    str_report_log_id = Column(Integer, ForeignKey("generated_report_logs.id"), nullable=True)

    rule_triggered = relationship("AMLRule") # Add back_populates if needed
    str_report = relationship("GeneratedReportLog") # Add back_populates if needed
    customer = relationship("Customer") # Add back_populates if needed
    account = relationship("Account") # Add back_populates if needed
    financial_transaction = relationship("FinancialTransaction") # Add back_populates if needed

    def __repr__(self): return f"<SuspiciousActivityLog(id={self.id}, rule='{self.aml_rule_code_triggered}', status='{self.status}')>"

class SanctionScreeningLog(Base):
    __tablename__ = "sanction_screening_logs"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True) # Link to customer if screening a customer
    entity_type = Column(String(20), default="CUSTOMER", nullable=False) # CUSTOMER, COUNTERPARTY, BENEFICIARY

    bvn_screened = Column(String(11), nullable=True, index=True)
    name_screened = Column(String(255), nullable=False, index=True) # Increased length

    screening_date = Column(DateTime(timezone=True), server_default=func.now())
    sanction_lists_checked = Column(Text, nullable=True) # JSON array of lists checked
    match_found = Column(Boolean, default=False, index=True)
    match_details_json = Column(Text, nullable=True)

    # decision = Column(String(50), nullable=True)
    # decision_by_user_id = Column(String(50), nullable=True)
    # decision_notes = Column(Text, nullable=True)

    customer = relationship("Customer") # Add back_populates if needed

    def __repr__(self): return f"<SanctionScreeningLog(id={self.id}, name='{self.name_screened}', match={self.match_found})>"

class CTRLog(Base):
    __tablename__ = "ctr_logs"
    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), unique=True, nullable=True) # Made nullable, as CTR might be logged based on aggregated daily cash, not single FT
    cash_deposit_log_id = Column(Integer, ForeignKey("cash_deposit_logs.id"), unique=True, nullable=True) # Or linked to a specific cash deposit event

    transaction_reference_primary = Column(String(40), nullable=False, unique=True, index=True) # Primary reference for this CTR event
    transaction_date = Column(Date, nullable=False)
    transaction_amount = Column(Numeric(precision=18, scale=2), nullable=False)
    transaction_currency = Column(String(3), nullable=False)
    customer_bvn = Column(String(11), nullable=True, index=True)
    account_number = Column(String(20), nullable=True, index=True)
    transaction_type = Column(String(50), nullable=False) # e.g. "CASH_DEPOSIT", "CASH_WITHDRAWAL", "AGGREGATED_CASH"

    ctr_report_log_id = Column(Integer, ForeignKey("generated_report_logs.id"), nullable=True)

    # Relationships for clarity if needed, though denormalized fields are primary for CTR
    # financial_transaction = relationship("FinancialTransaction")
    # cash_deposit_log = relationship("CashDepositLog")
    # ctr_report = relationship("GeneratedReportLog")
