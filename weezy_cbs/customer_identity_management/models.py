# Database models for Customer & Identity Management
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# Assuming a shared declarative base is defined in weezy_cbs.database
# from weezy_cbs.database import Base
# For now, let's define a local Base for standalone capability,
# but this should be centralized.
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

import enum

class AccountTier(enum.Enum):
    TIER1 = "Tier 1"
    TIER2 = "Tier 2"
    TIER3 = "Tier 3"

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    bvn = Column(String(11), unique=True, index=True, nullable=True) # Bank Verification Number
    nin = Column(String(11), unique=True, index=True, nullable=True) # National Identity Number

    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    middle_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone_number = Column(String, unique=True, index=True)

    date_of_birth = Column(DateTime, nullable=True)
    address = Column(String, nullable=True)
    # Consider a separate Address table for more structured address data

    is_active = Column(Boolean, default=True)
    is_verified_bvn = Column(Boolean, default=False)
    is_verified_nin = Column(Boolean, default=False)
    is_verified_identity_document = Column(Boolean, default=False) # e.g., passport, driver's license
    is_verified_address = Column(Boolean, default=False) # e.g., utility bill

    account_tier = Column(SQLAlchemyEnum(AccountTier), default=AccountTier.TIER1)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (examples)
    # accounts = relationship("Account", back_populates="customer") # Link to Account model in accounts_ledger_management
    # documents = relationship("CustomerDocument", back_populates="customer")

    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.first_name} {self.last_name}', bvn='{self.bvn}')>"

class CustomerDocument(Base):
    __tablename__ = "customer_documents"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, index=True) # ForeignKey("customers.id") - uncomment when Customer is defined

    document_type = Column(String) # e.g., 'PASSPORT', 'NIN_SLIP', 'UTILITY_BILL', 'SELFIE'
    document_url = Column(String) # URL to stored document (e.g., S3 link)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, default=False)
    # customer = relationship("Customer", back_populates="documents")


# Example: AML/KYC related flags or status
class KYCAuditLog(Base):
    __tablename__ = "kyc_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, index=True) # ForeignKey("customers.id")
    changed_by_user_id = Column(Integer, nullable=True) # ID of admin/agent who made change
    event_type = Column(String) # e.g., 'BVN_VERIFIED', 'TIER_UPGRADED', 'DOC_UPLOADED'
    details = Column(String, nullable=True) # JSON string or text for more details
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

# Note: To make this runnable, you'd need to set up SQLAlchemy engine and create tables.
# E.g.,
# from sqlalchemy import create_engine
# from weezy_cbs.database import DATABASE_URL # Assuming you have this
# engine = create_engine(DATABASE_URL)
# Base.metadata.create_all(bind=engine)
