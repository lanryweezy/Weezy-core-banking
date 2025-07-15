# SQLAlchemy models for core data structures
# These models define the database table schemas.

from sqlalchemy import Column, String, DateTime, Float, JSON, Enum as SQLAlchemyEnum, ForeignKey, Boolean, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from datetime import datetime, date # date is needed for date columns
import enum

from .database import Base # Import Base from database.py

# --- Enum Definitions for SQLAlchemy ---
class ApplicationStatusEnum(str, enum.Enum): # Renamed from OnboardingStatusEnum
    INITIATED = "Initiated"
    PENDING_VERIFICATION = "PendingVerification"
    VERIFICATION_FAILED = "VerificationFailed"
    PENDING_DECISION = "PendingDecision" # e.g. for loan/credit
    APPROVED = "Approved" # Generic approval
    REJECTED = "Rejected" # Generic rejection
    COMPLETED = "Completed" # e.g. Onboarding complete, account opened
    REQUIRES_MANUAL_INTERVENTION = "RequiresManualIntervention"
    CANCELLED = "Cancelled"
    INFORMATION_REQUESTED = "InformationRequested" # For credit/compliance needing more info

class ApplicationTypeEnum(str, enum.Enum):
    CUSTOMER_ONBOARDING = "CustomerOnboarding"
    LOAN_APPLICATION = "LoanApplication"
    # Other application types can be added

class AccountTypeEnum(str, enum.Enum):
    SAVINGS = "Savings"
    CURRENT = "Current"
    FIXED_DEPOSIT = "FixedDeposit"

class AccountStatusEnum(str, enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    DORMANT = "Dormant"
    CLOSED = "Closed"
    BLOCKED = "Blocked"

class TransactionTypeEnum(str, enum.Enum):
    DEPOSIT = "Deposit"
    WITHDRAWAL = "Withdrawal"
    TRANSFER_INTRA_BANK = "TransferIntraBank"
    TRANSFER_INTER_BANK_NIP = "TransferInterBankNIP"
    BILL_PAYMENT = "BillPayment"
    FEE_CHARGE = "FeeCharge"
    INTEREST_ACCRUAL = "InterestAccrual"
    LOAN_DISBURSEMENT = "LoanDisbursement"
    LOAN_REPAYMENT = "LoanRepayment"

class TransactionStatusEnum(str, enum.Enum):
    PENDING = "Pending"
    SUCCESSFUL = "Successful"
    FAILED = "Failed"
    PROCESSING = "Processing"
    REVERSED = "Reversed"

class SupportTicketStatusEnum(str, enum.Enum):
    OPEN = "Open"
    PENDING_CUSTOMER_REPLY = "PendingCustomerReply"
    PENDING_AGENT_REPLY = "PendingAgentReply"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    ESCALATED = "Escalated"

class ComplianceScreeningStatusEnum(str, enum.Enum):
    PENDING = "Pending"
    CLEAR = "Clear"
    POTENTIAL_HIT = "PotentialHit"
    CONFIRMED_HIT = "ConfirmedHit"
    ERROR = "Error"

# --- Core Models ---

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=lambda: f"CUST-{uuid.uuid4().hex[:10].upper()}")
    first_name = Column(String, nullable=False, index=True)
    last_name = Column(String, nullable=False, index=True)
    middle_name = Column(String, nullable=True)
    date_of_birth = Column(DateTime, nullable=True) # Changed to DateTime to store date for consistency, can be Date type too
    email_address = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    bvn = Column(String(11), unique=True, index=True, nullable=True)
    nin = Column(String(11), unique=True, index=True, nullable=True)

    primary_address_street = Column(String)
    primary_address_city = Column(String)
    primary_address_state = Column(String)
    primary_address_country = Column(String(2), default="NG") # ISO Alpha-2

    customer_segment = Column(String, nullable=True) # e.g., Retail, SME, Corporate
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    accounts = relationship("Account", back_populates="customer")
    applications = relationship("ApplicationCase", back_populates="customer") # If applications are tied to customers
    support_tickets = relationship("SupportTicket", back_populates="customer")

    def __repr__(self):
        return f"<Customer(id='{self.id}', name='{self.first_name} {self.last_name}')>"


class Account(Base):
    __tablename__ = "accounts"

    account_number = Column(String(10), primary_key=True, unique=True, index=True) # NUBAN
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False, index=True)

    account_type = Column(SQLAlchemyEnum(AccountTypeEnum), nullable=False)
    account_status = Column(SQLAlchemyEnum(AccountStatusEnum), default=AccountStatusEnum.ACTIVE, nullable=False)

    currency = Column(String(3), default="NGN", nullable=False) # ISO 4217
    ledger_balance = Column(Float, default=0.0, nullable=False)
    available_balance = Column(Float, default=0.0, nullable=False) # Can differ due to liens, uncleared funds

    lien_amount = Column(Float, default=0.0)
    minimum_balance = Column(Float, default=0.0)

    date_opened = Column(DateTime, default=datetime.utcnow)
    last_transaction_date = Column(DateTime, nullable=True)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    customer = relationship("Customer", back_populates="accounts")
    # transactions_source = relationship("TransactionRecord", foreign_keys="[TransactionRecord.source_account_number]", back_populates="source_account_obj")
    # transactions_destination = relationship("TransactionRecord", foreign_keys="[TransactionRecord.destination_account_number]", back_populates="destination_account_obj")


    def __repr__(self):
        return f"<Account(account_number='{self.account_number}', customer_id='{self.customer_id}', balance='{self.available_balance} {self.currency}')>"


class ApplicationCase(Base): # Renamed from OnboardingAttempt, made more generic
    __tablename__ = "application_cases"

    id = Column(String, primary_key=True, default=lambda: f"APPCASE-{uuid.uuid4().hex[:10].upper()}")
    application_type = Column(SQLAlchemyEnum(ApplicationTypeEnum), nullable=False, index=True)

    customer_id = Column(String, ForeignKey("customers.id"), nullable=True, index=True) # Nullable if app before customer exists
    # Store key applicant details even if customer_id is also present, for snapshot at time of application
    applicant_first_name = Column(String, index=True)
    applicant_last_name = Column(String, index=True)
    applicant_email = Column(String, index=True)
    applicant_phone = Column(String, index=True)

    status = Column(SQLAlchemyEnum(ApplicationStatusEnum), default=ApplicationStatusEnum.INITIATED, nullable=False, index=True)
    status_message = Column(Text, nullable=True)

    # JSON fields for flexibility with different application types
    request_payload_json = Column(JSON, nullable=False) # Stores OnboardingRequest, LoanApplicationInput etc.
    assessment_details_json = Column(JSON, nullable=True) # Stores OnboardingProcess, LoanAssessmentOutput etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    customer = relationship("Customer", back_populates="applications")

    def __repr__(self):
        return f"<ApplicationCase(id='{self.id}', type='{self.application_type}', status='{self.status}')>"


class TransactionRecord(Base):
    __tablename__ = "transaction_records"

    id = Column(String, primary_key=True, default=lambda: f"TRN-{uuid.uuid4().hex[:12].upper()}")
    external_reference_id = Column(String, index=True, nullable=True) # e.g., NIP Session ID, Paystack Ref

    transaction_type = Column(SQLAlchemyEnum(TransactionTypeEnum), nullable=False, index=True)
    status = Column(SQLAlchemyEnum(TransactionStatusEnum), default=TransactionStatusEnum.PENDING, nullable=False, index=True)

    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="NGN", nullable=False)
    fee_amount = Column(Float, default=0.0)

    source_account_number = Column(String(10), ForeignKey("accounts.account_number"), nullable=True, index=True)
    destination_account_number = Column(String(10), ForeignKey("accounts.account_number"), nullable=True, index=True) # Internal if local NUBAN
    destination_bank_code = Column(String, nullable=True) # For inter-bank
    destination_account_name_external = Column(String, nullable=True) # For external transfers where we don't have local account

    narration = Column(Text, nullable=True)
    channel = Column(String, nullable=True) # e.g., MobileApp, USSD, API

    transaction_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    value_timestamp = Column(DateTime, default=datetime.utcnow) # When value is applied
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (optional, can make queries complex if overused)
    # source_account_obj = relationship("Account", foreign_keys=[source_account_number])
    # destination_account_obj = relationship("Account", foreign_keys=[destination_account_number])

    def __repr__(self):
        return f"<TransactionRecord(id='{self.id}', type='{self.transaction_type}', amount='{self.amount} {self.currency}', status='{self.status}')>"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(String, primary_key=True, default=lambda: f"TCKT-{uuid.uuid4().hex[:10].upper()}")
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False, index=True)
    related_query_id = Column(String, index=True, nullable=True) # From CustomerSupportAgent schemas

    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SQLAlchemyEnum(SupportTicketStatusEnum), default=SupportTicketStatusEnum.OPEN, nullable=False, index=True)
    priority = Column(String, default="Medium") # Low, Medium, High, Urgent
    category = Column(String, nullable=True) # e.g., TransactionDispute, AccountInquiry
    channel_of_complaint = Column(String, nullable=True) # e.g., Chat, Email

    assigned_to_agent_id = Column(String, nullable=True) # Human agent ID
    resolution_details = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationship
    customer = relationship("Customer", back_populates="support_tickets")

    def __repr__(self):
        return f"<SupportTicket(id='{self.id}', subject='{self.subject[:30]}...', status='{self.status}')>"


class ComplianceScreeningLog(Base):
    __tablename__ = "compliance_screening_logs"

    id = Column(String, primary_key=True, default=lambda: f"CSL-{uuid.uuid4().hex[:10].upper()}")
    request_id = Column(String, index=True, nullable=False) # From ComplianceAgent schemas
    entity_id_screened = Column(String, index=True, nullable=False) # The internal ID of the entity in the request
    entity_name_screened = Column(String, nullable=False)
    entity_type = Column(SQLAlchemyEnum(EntityType), nullable=False) # Individual, Organization

    screening_status = Column(SQLAlchemyEnum(ComplianceScreeningStatusEnum), nullable=False)
    overall_risk_rating = Column(SQLAlchemyEnum(RiskRating), nullable=True) # Low, Medium, High, Critical

    checks_performed_json = Column(JSON) # List of ScreeningCheckType
    hits_details_json = Column(JSON, nullable=True) # List of ScreeningHitDetails
    errors_json = Column(JSON, nullable=True) # List of error strings
    summary_message = Column(Text, nullable=True)

    screened_by_agent_id = Column(String, default="ComplianceAgent")
    screening_timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ComplianceScreeningLog(id='{self.id}', entity='{self.entity_name_screened}', status='{self.screening_status}')>"


if __name__ == "__main__":
    print("Core SQLAlchemy models defined (Customer, Account, ApplicationCase, TransactionRecord, SupportTicket, ComplianceScreeningLog).")
    # Table creation logic is in database.py's init_db().
    # To create these tables, run: python -m core_banking_agents.core.database
    pass
