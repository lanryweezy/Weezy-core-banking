# Database models for Loan Management Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from weezy_cbs.database import Base # Use the shared Base

import enum

# Assuming CurrencyEnum will be shared, for now define locally or import if available
# from weezy_cbs.accounts_ledger_management.models import CurrencyEnum as SharedCurrencyEnum
class CurrencyEnum(enum.Enum):
    NGN = "NGN"
    USD = "USD"
    # Add others as needed

class InterestTypeEnum(enum.Enum):
    REDUCING_BALANCE = "REDUCING_BALANCE"
    FLAT = "FLAT"
    INTEREST_ONLY = "INTEREST_ONLY"

class RepaymentFrequencyEnum(enum.Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    BI_ANNUALLY = "BI_ANNUALLY"
    ANNUALLY = "ANNUALLY"
    BULLET = "BULLET" # Single repayment at end

class LoanProduct(Base):
    __tablename__ = "loan_products"

    id = Column(Integer, primary_key=True, index=True) # Internal DB ID
    product_code = Column(String(20), unique=True, nullable=False, index=True) # Business key, e.g. "PERSLN001"
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False, default=CurrencyEnum.NGN)

    min_amount = Column(Numeric(precision=18, scale=2), nullable=False)
    max_amount = Column(Numeric(precision=18, scale=2), nullable=False)
    interest_rate_pa = Column(Numeric(precision=7, scale=4), nullable=False) # Annual interest rate, e.g. 15.5000 for 15.5%
    interest_type = Column(SQLAlchemyEnum(InterestTypeEnum), default=InterestTypeEnum.REDUCING_BALANCE, nullable=False)

    min_tenor_months = Column(Integer, nullable=False)
    max_tenor_months = Column(Integer, nullable=False)
    repayment_frequency = Column(SQLAlchemyEnum(RepaymentFrequencyEnum), default=RepaymentFrequencyEnum.MONTHLY, nullable=False)

    linked_fee_codes_json = Column(Text, nullable=True) # JSON: ["APP_FEE_01", "PROC_FEE_LOAN"]
    eligibility_criteria_json = Column(Text, nullable=True) # JSON: {"min_income": 100000, "required_docs": ["NIN", "PAYSLIP"]}
    crms_product_code = Column(String(10), nullable=True) # CBN CRMS classification

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    applications = relationship("LoanApplication", back_populates="loan_product")

class LoanApplicationStatusEnum(enum.Enum): # Keep existing is fine
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    PENDING_DOCUMENTATION = "PENDING_DOCUMENTATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING_DISBURSEMENT = "PENDING_DISBURSEMENT"
    DISBURSED = "DISBURSED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"

class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(Integer, primary_key=True, index=True)
    application_reference = Column(String(30), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    loan_product_id = Column(Integer, ForeignKey("loan_products.id"), nullable=False, index=True) # FK to loan_products.id

    requested_amount = Column(Numeric(precision=18, scale=2), nullable=False)
    requested_currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False, default=CurrencyEnum.NGN)
    requested_tenor_months = Column(Integer, nullable=False)
    loan_purpose = Column(Text, nullable=True)

    status = Column(SQLAlchemyEnum(LoanApplicationStatusEnum), default=LoanApplicationStatusEnum.SUBMITTED, nullable=False, index=True)

    # Credit Score & Risk
    credit_score = Column(Integer, nullable=True)
    risk_rating = Column(String(50), nullable=True)
    decision_reason = Column(Text, nullable=True)
    credit_bureau_report_id = Column(String(50), nullable=True, index=True) # Ref to external report

    # Approved terms (can differ from requested)
    approved_amount = Column(Numeric(precision=18, scale=2), nullable=True)
    approved_tenor_months = Column(Integer, nullable=True)
    approved_interest_rate_pa = Column(Numeric(precision=7, scale=4), nullable=True)

    crms_application_status = Column(String(50), nullable=True) # For CRMS

    # Timestamps
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    disbursed_at = Column(DateTime(timezone=True), nullable=True) # When loan_account created and funded
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    customer = relationship("Customer") # Define in Customer: applications = relationship("LoanApplication", back_populates="customer")
    loan_product = relationship("LoanProduct", back_populates="applications")
    loan_account = relationship("LoanAccount", back_populates="application", uselist=False)
    guarantors = relationship("Guarantor", back_populates="loan_application")
    collaterals = relationship("Collateral", back_populates="loan_application")

class LoanAccountStatusEnum(enum.Enum): # Keep existing is fine
    ACTIVE = "ACTIVE"
    PAID_OFF = "PAID_OFF"
    OVERDUE = "OVERDUE"
    DEFAULTED = "DEFAULTED"
    RESTRUCTURED = "RESTRUCTURED"
    WRITTEN_OFF = "WRITTEN_OFF"

class LoanAccount(Base):
    __tablename__ = "loan_accounts"

    id = Column(Integer, primary_key=True, index=True)
    loan_account_number = Column(String(20), unique=True, index=True, nullable=False)
    application_id = Column(Integer, ForeignKey("loan_applications.id"), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    disbursement_account_number = Column(String(10), nullable=False) # Customer's NUBAN credited
    # disbursement_account_bank_code = Column(String(10), nullable=True) # If external disbursement (rare for this model)

    principal_disbursed = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False) # From application/product
    interest_rate_pa = Column(Numeric(precision=7, scale=4), nullable=False)
    tenor_months = Column(Integer, nullable=False)

    principal_outstanding = Column(Numeric(precision=18, scale=2), default=0.00)
    interest_outstanding = Column(Numeric(precision=18, scale=2), default=0.00) # Accrued interest not yet due or paid
    fees_outstanding = Column(Numeric(precision=18, scale=2), default=0.00)
    penalties_outstanding = Column(Numeric(precision=18, scale=2), default=0.00)

    total_repaid_principal = Column(Numeric(precision=18, scale=2), default=0.00)
    total_repaid_interest = Column(Numeric(precision=18, scale=2), default=0.00)

    status = Column(SQLAlchemyEnum(LoanAccountStatusEnum), default=LoanAccountStatusEnum.ACTIVE, index=True)
    crms_loan_status = Column(String(50), nullable=True) # For CRMS
    loan_purpose_code = Column(String(10), nullable=True) # Standardized purpose code

    disbursement_date = Column(Date, nullable=False)
    first_repayment_date = Column(Date, nullable=False)
    next_repayment_date = Column(Date, nullable=True, index=True)
    maturity_date = Column(Date, nullable=False)

    days_past_due = Column(Integer, default=0, index=True)
    last_repayment_date = Column(DateTime(timezone=True), nullable=True)
    last_repayment_amount = Column(Numeric(precision=18, scale=2), nullable=True)

    application = relationship("LoanApplication", back_populates="loan_account")
    repayment_schedules = relationship("LoanRepaymentSchedule", back_populates="loan_account", order_by="LoanRepaymentSchedule.installment_number")
    repayments_received = relationship("LoanRepayment", back_populates="loan_account", order_by="LoanRepayment.payment_date")

class LoanRepaymentSchedule(Base):
    __tablename__ = "loan_repayment_schedules"

    id = Column(Integer, primary_key=True, index=True)
    loan_account_id = Column(Integer, ForeignKey("loan_accounts.id"), nullable=False, index=True)

    due_date = Column(Date, nullable=False)
    installment_number = Column(Integer, nullable=False)

    principal_due = Column(Numeric(precision=18, scale=2), nullable=False)
    interest_due = Column(Numeric(precision=18, scale=2), nullable=False)
    fees_due = Column(Numeric(precision=18, scale=2), default=0.00)
    total_due = Column(Numeric(precision=18, scale=2), nullable=False)

    principal_paid = Column(Numeric(precision=18, scale=2), default=0.00)
    interest_paid = Column(Numeric(precision=18, scale=2), default=0.00)
    fees_paid = Column(Numeric(precision=18, scale=2), default=0.00)

    is_paid = Column(Boolean, default=False)
    payment_date = Column(Date, nullable=True)

    loan_account = relationship("LoanAccount", back_populates="repayment_schedules")

class LoanRepayment(Base):
    __tablename__ = "loan_repayments"

    id = Column(Integer, primary_key=True, index=True)
    loan_account_id = Column(Integer, ForeignKey("loan_accounts.id"), nullable=False, index=True)
    financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=False, index=True)

    payment_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    amount_paid = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    allocated_to_principal = Column(Numeric(precision=18, scale=2), default=0.00)
    allocated_to_interest = Column(Numeric(precision=18, scale=2), default=0.00)
    allocated_to_fees = Column(Numeric(precision=18, scale=2), default=0.00)
    allocated_to_penalties = Column(Numeric(precision=18, scale=2), default=0.00)

    payment_method = Column(String(50), nullable=True)
    reference = Column(String(100), nullable=True)

    loan_account = relationship("LoanAccount", back_populates="repayments_received")

class GuarantorTypeEnum(enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    CORPORATE = "CORPORATE"

class Guarantor(Base):
    __tablename__ = "guarantors"
    id = Column(Integer, primary_key=True, index=True)
    loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=False, index=True)

    guarantor_type = Column(SQLAlchemyEnum(GuarantorTypeEnum), nullable=False)
    name = Column(String(150), nullable=False)
    bvn = Column(String(11), nullable=True, index=True)
    # For corporate guarantor, this could be RC number
    # corporate_rc_number = Column(String(20), nullable=True)
    phone = Column(String(15), nullable=True)
    email = Column(String(100), nullable=True)
    relationship_to_applicant = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    status = Column(String(20), default="ACTIVE") # ACTIVE, INACTIVE, RELEASED

    loan_application = relationship("LoanApplication", back_populates="guarantors")

class Collateral(Base):
    __tablename__ = "collaterals"
    id = Column(Integer, primary_key=True, index=True)
    loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=False, index=True)

    type = Column(String(100), nullable=False)
    description = Column(Text)
    estimated_value = Column(Numeric(precision=18, scale=2))
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False, default=CurrencyEnum.NGN)
    valuation_date = Column(Date, nullable=True)
    location = Column(Text, nullable=True)
    # document_reference_json = Column(Text) # JSON array of document IDs/URLs from CustomerDocument or other doc system
    lien_reference = Column(String(50), nullable=True) # If lien placed on collateral
    status = Column(String(20), default="PLEDGED") # PLEDGED, ACTIVE_SECURITY, RELEASED, SOLD

    loan_application = relationship("LoanApplication", back_populates="collaterals")

# Ensure ForeignKeys point to the correct table names if they are in different schemas or defined by other modules.
# For now, assuming "customers.id", "loan_products.id", etc. are resolvable by SQLAlchemy.
# FinancialTransaction link in LoanRepayment implies transaction_management module.
# Consider adding `created_at` and `updated_at` to most tables for audit.
