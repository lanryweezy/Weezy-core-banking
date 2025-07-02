# Database models for Compliance & Regulatory Reporting Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum as SQLAlchemyEnum, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# from weezy_cbs.database import Base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base() # Local Base for now

import enum

class ReportNameEnum(enum.Enum):
    CBN_CRMS = "CBN_CRMS" # Credit Risk Management System
    NDIC_RETURNS = "NDIC_RETURNS" # Nigeria Deposit Insurance Corporation
    NFIU_STR = "NFIU_STR" # Nigerian Financial Intelligence Unit - Suspicious Transaction Report
    NFIU_CTR = "NFIU_CTR" # Nigerian Financial Intelligence Unit - Currency Transaction Report
    CBN_FINA = "CBN_FINA" # Financial Analysis System
    CBN_OVERSIGHT = "CBN_OVERSIGHT" # CBN Oversight reports
    # Add more specific report names as needed

class ReportStatusEnum(enum.Enum):
    PENDING_GENERATION = "PENDING_GENERATION"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED" # File produced
    VALIDATION_PENDING = "VALIDATION_PENDING" # Awaiting internal review/validation
    VALIDATED = "VALIDATED"
    SUBMISSION_PENDING = "SUBMISSION_PENDING" # Ready to be sent to regulator
    SUBMITTED = "SUBMITTED" # Sent to regulator
    ACKNOWLEDGED = "ACKNOWLEDGED" # Regulator confirmed receipt
    QUERIED = "QUERIED" # Regulator has questions/issues
    FAILED_GENERATION = "FAILED_GENERATION"
    FAILED_SUBMISSION = "FAILED_SUBMISSION"

class GeneratedReportLog(Base):
    __tablename__ = "generated_report_logs"

    id = Column(Integer, primary_key=True, index=True)
    report_name = Column(SQLAlchemyEnum(ReportNameEnum), nullable=False, index=True)
    reporting_period_start_date = Column(Date, nullable=False)
    reporting_period_end_date = Column(Date, nullable=False)

    status = Column(SQLAlchemyEnum(ReportStatusEnum), default=ReportStatusEnum.PENDING_GENERATION, nullable=False)

    generated_at = Column(DateTime(timezone=True), nullable=True)
    generated_by_user_id = Column(String, nullable=True) # User who triggered generation

    file_path_or_url = Column(String, nullable=True) # Path to the generated report file (e.g. XML, CSV, Excel)
    file_format = Column(String, nullable=True) # e.g., 'XML', 'CSV', 'XLSX', 'PDF'
    checksum = Column(String, nullable=True) # MD5 or SHA256 hash of the file for integrity

    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submission_reference = Column(String, nullable=True) # Reference from regulator's portal

    validator_user_id = Column(String, nullable=True) # User who validated the report
    validated_at = Column(DateTime(timezone=True), nullable=True)
    validation_comments = Column(Text, nullable=True)

    notes = Column(Text, nullable=True) # General remarks or error messages

    __table_args__ = (
        Index("idx_report_period_name", "report_name", "reporting_period_end_date"),
    )

    def __repr__(self):
        return f"<GeneratedReportLog(id={self.id}, name='{self.report_name.value}', period_end='{self.reporting_period_end_date}', status='{self.status.value}')>"

class AMLRule(Base): # Anti-Money Laundering Rules Configuration
    __tablename__ = "aml_rules"
    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String, unique=True, nullable=False, index=True) # e.g., "LARGE_CASH_DEPOSIT", "HIGH_VELOCITY_TXNS"
    description = Column(Text, nullable=False)
    parameters_json = Column(Text) # JSON string for rule parameters, e.g., {"threshold_amount": 1000000, "currency": "NGN", "period_days": 1}

    severity = Column(String, default="MEDIUM") # LOW, MEDIUM, HIGH, CRITICAL
    action_to_take = Column(String, default="FLAG_FOR_REVIEW") # e.g., "FLAG_FOR_REVIEW", "BLOCK_TRANSACTION", "ALERT_COMPLIANCE_OFFICER"

    is_active = Column(Boolean, default=True)
    # Versioning for rules might be needed
    # version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<AMLRule(code='{self.rule_code}', active={self.is_active})>"

class SuspiciousActivityLog(Base): # Log of activities flagged by AML rules
    __tablename__ = "suspicious_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    # account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, index=True) # The transaction that triggered the flag

    # Denormalized fields for easier querying for AML even if source records change/archived
    customer_bvn = Column(String, nullable=True)
    account_number = Column(String, nullable=True)
    transaction_reference_primary = Column(String, nullable=True, index=True) # Could be FT.id or other ref

    aml_rule_code_triggered = Column(String, ForeignKey("aml_rules.rule_code"), nullable=False, index=True)

    flagged_at = Column(DateTime(timezone=True), server_default=func.now())
    activity_description = Column(Text) # Description of why it was flagged (can be auto-generated)

    status = Column(String, default="OPEN") # OPEN, UNDER_INVESTIGATION, CLEARED, ESCALATED_TO_NFIU (STR filed)
    assigned_to_user_id = Column(String, nullable=True) # Compliance officer investigating
    investigation_notes = Column(Text, nullable=True)
    resolution_date = Column(DateTime(timezone=True), nullable=True)

    # str_report_log_id = Column(Integer, ForeignKey("generated_report_logs.id"), nullable=True) # Link to the NFIU STR if one was filed

    # rule_triggered = relationship("AMLRule")
    # str_report = relationship("GeneratedReportLog")

    def __repr__(self):
        return f"<SuspiciousActivityLog(id={self.id}, rule='{self.aml_rule_code_triggered}', status='{self.status}')>"


class SanctionScreeningLog(Base): # Log of sanction list screening results
    __tablename__ = "sanction_screening_logs"
    id = Column(Integer, primary_key=True, index=True)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    # entity_name_screened = Column(String, nullable=False) # Name of individual or entity
    # entity_type = Column(String, default="CUSTOMER") # CUSTOMER, COUNTERPARTY, BENEFICIARY, EMPLOYEE

    # Denormalized for audit
    bvn_screened = Column(String, nullable=True, index=True)
    name_screened = Column(String, nullable=False, index=True)

    screening_date = Column(DateTime(timezone=True), server_default=func.now())
    sanction_lists_checked = Column(Text) # JSON array of lists checked, e.g. ["OFAC_SDN", "UN_CONSOLIDATED", "UK_HMT"]

    match_found = Column(Boolean, default=False, index=True)
    match_details_json = Column(Text, nullable=True) # JSON with details of the match(es) from sanction list

    # decision = Column(String, nullable=True) # e.g. "NO_MATCH", "POTENTIAL_MATCH_REVIEW", "CONFIRMED_MATCH_BLOCK"
    # decision_by_user_id = Column(String, nullable=True)
    # decision_notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<SanctionScreeningLog(id={self.id}, name='{self.name_screened}', match={self.match_found})>"

# CTR (Currency Transaction Report) specific log, if needed beyond FinancialTransaction flags
# NFIU mandates reporting cash transactions above a certain threshold (e.g. NGN 5M for individuals, NGN 10M for corporates)
class CTRLog(Base): # Could also be flags on FinancialTransaction or CashDepositLog
    __tablename__ = "ctr_logs" # Potentially redundant if FinancialTransaction/CashDepositLog has enough detail + AML flags
    id = Column(Integer, primary_key=True, index=True)
    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), unique=True, nullable=False)
    # cash_deposit_log_id = Column(Integer, ForeignKey("cash_deposit_logs.id"), unique=True, nullable=True)

    # Denormalized for direct CTR generation
    transaction_reference_primary = Column(String, nullable=False, unique=True, index=True)
    transaction_date = Column(Date, nullable=False)
    transaction_amount = Column(Numeric(precision=18, scale=2), nullable=False)
    transaction_currency = Column(String(3), nullable=False) # Using string to be flexible
    # customer_bvn = Column(String)
    # account_number = Column(String)
    # transaction_type = Column(String) # e.g. "CASH_DEPOSIT", "CASH_WITHDRAWAL"

    # ctr_report_log_id = Column(Integer, ForeignKey("generated_report_logs.id"), nullable=True) # Link to the NFIU CTR if one was filed

    # transaction = relationship("FinancialTransaction")
    # ctr_report = relationship("GeneratedReportLog")

# This module would also have services to:
# - Query various other modules (Customer, Accounts, Transactions, Loans) to gather data for reports.
# - Format data into required XML/CSV/Excel for each regulatory body.
# - Integrate with regulator portals for submission (if APIs exist) or guide manual upload.
# - Schedule report generation.
# - Implement AML transaction monitoring rules against FinancialTransaction data.
# - Perform periodic and on-demand sanction screening.
