# Database models for Loan Management Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# from weezy_cbs.database import Base # Assuming a shared declarative base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base() # Local Base for now

# from weezy_cbs.accounts_ledger_management.models import CurrencyEnum # Re-use if possible
# For now, defining locally to avoid circular dependency if modules are separate apps
import enum

class CurrencyEnum(enum.Enum):
    NGN = "NGN"
    USD = "USD"
    # Add others as needed

class LoanProduct(Base):
    __tablename__ = "loan_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    min_amount = Column(Numeric(precision=18, scale=4), nullable=False)
    max_amount = Column(Numeric(precision=18, scale=4), nullable=False)
    interest_rate_pa = Column(Numeric(precision=5, scale=2), nullable=False) # Annual interest rate
    # interest_type (e.g., FLAT, REDUCING_BALANCE) - could be an Enum
    min_tenor_months = Column(Integer, nullable=False)
    max_tenor_months = Column(Integer, nullable=False)
    # fees (e.g., application_fee, processing_fee) - could link to a FeeConfig table
    is_active = Column(Boolean, default=True)
    # eligibility_criteria (e.g., min_credit_score, required_documents) - could be JSON or link to rules

    # loans = relationship("LoanApplication", back_populates="loan_product")

class LoanApplicationStatusEnum(enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED" # Application received, pending review
    UNDER_REVIEW = "UNDER_REVIEW" # Credit assessment in progress
    PENDING_DOCUMENTATION = "PENDING_DOCUMENTATION"
    APPROVED = "APPROVED" # Loan sanctioned
    REJECTED = "REJECTED" # Loan application denied
    PENDING_DISBURSEMENT = "PENDING_DISBURSEMENT" # Approved, awaiting funds release
    DISBURSED = "DISBURSED" # Loan amount released to customer
    WITHDRAWN = "WITHDRAWN" # Application withdrawn by customer
    EXPIRED = "EXPIRED" # Application expired

class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(Integer, primary_key=True, index=True)
    application_reference = Column(String, unique=True, index=True, nullable=False) # Auto-generated
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True) # From customer_identity
    loan_product_id = Column(Integer, ForeignKey("loan_products.id"), nullable=False, index=True)

    requested_amount = Column(Numeric(precision=18, scale=4), nullable=False)
    requested_tenor_months = Column(Integer, nullable=False)
    loan_purpose = Column(Text, nullable=True)

    status = Column(SQLAlchemyEnum(LoanApplicationStatusEnum), default=LoanApplicationStatusEnum.SUBMITTED, nullable=False)

    # Credit Score & Risk
    credit_score = Column(Integer, nullable=True) # From internal or external bureau
    risk_rating = Column(String, nullable=True) # e.g., A, B, C or Low, Medium, High
    decision_reason = Column(Text, nullable=True) # Reason for approval/rejection

    # Timestamps
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    disbursed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    # customer = relationship("Customer") # From customer_identity_management.models.Customer
    # loan_product = relationship("LoanProduct", back_populates="loans")
    # loan_account = relationship("LoanAccount", back_populates="application", uselist=False) # One-to-one after approval
    # guarantors = relationship("Guarantor", back_populates="loan_application")
    # collaterals = relationship("Collateral", back_populates="loan_application")

class LoanAccountStatusEnum(enum.Enum):
    ACTIVE = "ACTIVE"       # Loan is ongoing, payments expected
    PAID_OFF = "PAID_OFF"   # Loan fully repaid
    OVERDUE = "OVERDUE"     # Missed one or more payments
    DEFAULTED = "DEFAULTED" # Seriously delinquent, recovery actions may start
    RESTRUCTURED = "RESTRUCTURED"
    WRITTEN_OFF = "WRITTEN_OFF"

class LoanAccount(Base): # This is the active loan after disbursement
    __tablename__ = "loan_accounts"

    id = Column(Integer, primary_key=True, index=True)
    loan_account_number = Column(String, unique=True, index=True, nullable=False) # Similar to NUBAN or internal format
    application_id = Column(Integer, ForeignKey("loan_applications.id"), unique=True, nullable=False) # Link to the approved application
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    # disbursement_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False) # Customer's account where loan was disbursed

    principal_disbursed = Column(Numeric(precision=18, scale=4), nullable=False)
    interest_rate_pa = Column(Numeric(precision=5, scale=2), nullable=False) # Can be from product or adjusted
    tenor_months = Column(Integer, nullable=False)

    # Balances
    principal_outstanding = Column(Numeric(precision=18, scale=4), default=0.0000)
    interest_outstanding = Column(Numeric(precision=18, scale=4), default=0.0000)
    fees_outstanding = Column(Numeric(precision=18, scale=4), default=0.0000)
    penalties_outstanding = Column(Numeric(precision=18, scale=4), default=0.0000)

    total_repaid_principal = Column(Numeric(precision=18, scale=4), default=0.0000)
    total_repaid_interest = Column(Numeric(precision=18, scale=4), default=0.0000)

    status = Column(SQLAlchemyEnum(LoanAccountStatusEnum), default=LoanAccountStatusEnum.ACTIVE)

    disbursement_date = Column(DateTime(timezone=True), nullable=False)
    first_repayment_date = Column(DateTime(timezone=True), nullable=False)
    next_repayment_date = Column(DateTime(timezone=True), nullable=True)
    maturity_date = Column(DateTime(timezone=True), nullable=False) # Calculated from tenor

    # Delinquency info
    days_past_due = Column(Integer, default=0)
    last_repayment_date = Column(DateTime(timezone=True), nullable=True)
    last_repayment_amount = Column(Numeric(precision=18, scale=4), nullable=True)

    # Relationships
    # application = relationship("LoanApplication", back_populates="loan_account")
    # repayment_schedules = relationship("LoanRepaymentSchedule", back_populates="loan_account")
    # repayments_received = relationship("LoanRepayment", back_populates="loan_account")

class LoanRepaymentSchedule(Base): # Expected repayment plan
    __tablename__ = "loan_repayment_schedules"

    id = Column(Integer, primary_key=True, index=True)
    loan_account_id = Column(Integer, ForeignKey("loan_accounts.id"), nullable=False, index=True)

    due_date = Column(DateTime(timezone=True), nullable=False)
    installment_number = Column(Integer, nullable=False)

    principal_due = Column(Numeric(precision=18, scale=4), nullable=False)
    interest_due = Column(Numeric(precision=18, scale=4), nullable=False)
    fees_due = Column(Numeric(precision=18, scale=4), default=0.0000)
    total_due = Column(Numeric(precision=18, scale=4), nullable=False) # principal + interest + fees

    principal_paid = Column(Numeric(precision=18, scale=4), default=0.0000)
    interest_paid = Column(Numeric(precision=18, scale=4), default=0.0000)
    fees_paid = Column(Numeric(precision=18, scale=4), default=0.0000)

    is_paid = Column(Boolean, default=False)
    payment_date = Column(DateTime(timezone=True), nullable=True) # Date when this installment was fully settled

    # loan_account = relationship("LoanAccount", back_populates="repayment_schedules")

class LoanRepayment(Base): # Actual payments received
    __tablename__ = "loan_repayments"

    id = Column(Integer, primary_key=True, index=True)
    loan_account_id = Column(Integer, ForeignKey("loan_accounts.id"), nullable=False, index=True)
    # transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=False) # From master transaction table

    payment_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    amount_paid = Column(Numeric(precision=18, scale=4), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    # How the payment was allocated
    allocated_to_principal = Column(Numeric(precision=18, scale=4), default=0.0000)
    allocated_to_interest = Column(Numeric(precision=18, scale=4), default=0.0000)
    allocated_to_fees = Column(Numeric(precision=18, scale=4), default=0.0000)
    allocated_to_penalties = Column(Numeric(precision=18, scale=4), default=0.0000)

    payment_method = Column(String, nullable=True) # e.g., 'DIRECT_DEBIT', 'NIP_TRANSFER', 'CASH'
    reference = Column(String, nullable=True) # Payment reference

    # loan_account = relationship("LoanAccount", back_populates="repayments_received")

class Guarantor(Base):
    __tablename__ = "guarantors"
    id = Column(Integer, primary_key=True, index=True)
    loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=False, index=True)
    # Or loan_account_id if guarantor added after disbursement

    # Guarantor details (could be a link to another Customer record or external entity)
    name = Column(String, nullable=False)
    bvn = Column(String(11), nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    relationship_to_applicant = Column(String, nullable=True)
    # documents (e.g. guarantee form URL)

    # loan_application = relationship("LoanApplication", back_populates="guarantors")

class Collateral(Base):
    __tablename__ = "collaterals"
    id = Column(Integer, primary_key=True, index=True)
    loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=False, index=True)
    # Or loan_account_id

    type = Column(String, nullable=False) # e.g., 'REAL_ESTATE', 'VEHICLE', 'STOCKS'
    description = Column(Text)
    estimated_value = Column(Numeric(precision=18, scale=4))
    # document_urls (e.g. title deed, valuation report) - could be JSON array or separate table

    # loan_application = relationship("LoanApplication", back_populates="collaterals")

# CBN CRMS Reporting would likely be a separate process that queries these tables.
# Credit Bureau Integration: Store bureau report IDs or summary data linked to applications.
# Loan Restructuring, Top-up, Write-off: These would involve creating new loan records or updating existing ones with audit trails.
# For example, a LoanModificationLog table could track changes.
# Write-off would update LoanAccount status and potentially move balances to specific GLs.
# Top-up might be a new loan application linked to an existing one, or modification of the existing loan.
