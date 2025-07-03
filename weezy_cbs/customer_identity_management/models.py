# Database models for Customer & Identity Management
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLAlchemyEnum, Date, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from weezy_cbs.database import Base # Use the shared Base

import enum

class CBNSupportedAccountTier(enum.Enum): # Aligned with CBN tiers
    TIER_1 = "TIER_1" # Min KYC, limited functionality
    TIER_2 = "TIER_2" # Mid-level KYC
    TIER_3 = "TIER_3" # Full KYC, full functionality

class CustomerTypeEnum(enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    SME = "SME" # Small and Medium Enterprise
    CORPORATE = "CORPORATE"

class GenderEnum(enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_type = Column(SQLAlchemyEnum(CustomerTypeEnum), default=CustomerTypeEnum.INDIVIDUAL, nullable=False)

    # Identifiers
    bvn = Column(String(11), unique=True, index=True, nullable=True)
    nin = Column(String(11), unique=True, index=True, nullable=True)
    tin = Column(String(20), unique=True, index=True, nullable=True) # Tax Identification Number
    rc_number = Column(String(20), unique=True, index=True, nullable=True) # CAC Registration Number for SME/Corporate

    # Personal/Corporate Details
    first_name = Column(String, index=True, nullable=True) # Nullable for corporates
    last_name = Column(String, index=True, nullable=True)  # Nullable for corporates
    middle_name = Column(String, nullable=True)
    company_name = Column(String, index=True, nullable=True) # For SME/Corporate

    email = Column(String, unique=True, index=True, nullable=True) # Email optional for some tiers/customer types
    phone_number = Column(String(15), unique=True, index=True, nullable=False) # Primary phone
    # secondary_phone_number = Column(String(15), nullable=True)

    date_of_birth = Column(Date, nullable=True) # For individuals
    date_of_incorporation = Column(Date, nullable=True) # For SME/Corporate

    gender = Column(SQLAlchemyEnum(GenderEnum), nullable=True) # For individuals
    nationality = Column(String(2), default="NG", nullable=False) # ISO 2-letter country code
    mother_maiden_name = Column(String, nullable=True) # For individuals, KYC
    occupation = Column(String, nullable=True) # For individuals
    employer_name = Column(String, nullable=True) # For individuals

    # Address (consider a separate Address model for multiple addresses or more structure)
    street_address1 = Column(String, nullable=True)
    # street_address2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True) # Nigerian State
    # lga = Column(String, nullable=True) # Local Government Area
    # postal_code = Column(String, nullable=True)
    # country = Column(String(2), default="NG", nullable=True)

    # KYC Status
    is_active = Column(Boolean, default=True)
    is_verified_bvn = Column(Boolean, default=False)
    is_verified_nin = Column(Boolean, default=False)
    is_verified_identity_document = Column(Boolean, default=False)
    is_verified_address = Column(Boolean, default=False)
    is_pep = Column(Boolean, default=False, comment="Politically Exposed Person") # Politically Exposed Person

    account_tier = Column(SQLAlchemyEnum(CBNSupportedAccountTier), default=CBNSupportedAccountTier.TIER_1, nullable=False)

    # Other attributes
    segment = Column(String, nullable=True) # e.g., RETAIL, MASS_AFFLUENT, HNI, STUDENT
    referral_code_used = Column(String, nullable=True, index=True) # If customer was referred
    # own_referral_code = Column(String, unique=True, nullable=True, index=True) # Customer's own code for referring others

    # Next of Kin (for individuals)
    next_of_kin_name = Column(String, nullable=True)
    next_of_kin_phone = Column(String(15), nullable=True)
    next_of_kin_relationship = Column(String, nullable=True)
    next_of_kin_address = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    documents = relationship("CustomerDocument", back_populates="customer")
    kyc_audit_logs = relationship("KYCAuditLog", back_populates="customer")
    # accounts = relationship("Account", back_populates="customer") # Defined in accounts_ledger_management

    __table_args__ = (
        Index('idx_customer_name_individual', 'last_name', 'first_name', postgresql_where=(customer_type == CustomerTypeEnum.INDIVIDUAL)),
        Index('idx_customer_name_corporate', 'company_name', postgresql_where=(customer_type != CustomerTypeEnum.INDIVIDUAL)),
    )

    def __repr__(self):
        name = f"{self.first_name} {self.last_name}" if self.customer_type == CustomerTypeEnum.INDIVIDUAL else self.company_name
        return f"<Customer(id={self.id}, name='{name}', type='{self.customer_type.value}', bvn='{self.bvn}')>"

class CustomerDocument(Base):
    __tablename__ = "customer_documents"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)

    document_type = Column(String, nullable=False) # e.g., 'PASSPORT', 'NIN_SLIP', 'UTILITY_BILL', 'CAC_CERTIFICATE', 'SELFIE'
    document_number = Column(String, nullable=True, index=True) # e.g. Passport No, Driver's License No
    issuing_authority = Column(String, nullable=True)
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True, index=True)

    document_url = Column(String, nullable=False) # URL to stored document (e.g., S3 link)
    verification_meta_json = Column(Text, nullable=True) # JSON from verification provider (e.g. Verifyme, SmileID)

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, default=False)

    customer = relationship("Customer", back_populates="documents")

class KYCAuditLog(Base):
    __tablename__ = "kyc_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    changed_by_user_id = Column(String, nullable=True) # Staff/System ID of who made change
    event_type = Column(String, nullable=False) # e.g., 'BVN_VERIFIED', 'TIER_UPGRADED', 'ADDRESS_VERIFIED', 'PEP_STATUS_CHANGED'
    details_before_json = Column(Text, nullable=True) # JSON state before
    details_after_json = Column(Text, nullable=True) # JSON state after
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="kyc_audit_logs")

# Note: To make this runnable with relationships across modules, a shared Base and
# careful import order or use of string type for ForeignKey targets is needed.
# For now, ForeignKey("customers.id") assumes "customers" table will be known to this Base.
# When using a central Base from weezy_cbs.database, these relationships will resolve correctly.
