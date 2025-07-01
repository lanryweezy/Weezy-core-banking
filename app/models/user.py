import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import datetime

from .base import Base # Use the custom Base from base.py

class UserStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"

class AccountTier(enum.Enum):
    TIER1 = "tier1"
    TIER2 = "tier2"
    TIER3 = "tier3"

class User(Base):
    __tablename__ = "users" # Explicitly defining, though Base would default to "users"

    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False) # Store hashed passwords only
    full_name = Column(String(100))
    date_of_birth = Column(DateTime)
    phone_number = Column(String(20), unique=True, nullable=True, index=True)
    address = Column(String(255), nullable=True)

    # KYC and Identity
    bvn = Column(String(11), unique=True, nullable=True, index=True) # Bank Verification Number - typically 11 digits
    nin = Column(String(11), unique=True, nullable=True, index=True) # National Identification Number - typically 11 digits
    kyc_doc_references = Column(String, nullable=True) # Store as JSON string or use JSON type if DB supports well
    # Example kyc_doc_references: {"id_card": "path/to/id.jpg", "utility_bill": "path/to/bill.pdf"}
    kyc_status = Column(String(50), default="NOT_INITIATED", nullable=False) # E.g., NOT_INITIATED, PENDING_DOCUMENTS, PENDING_VERIFICATION, VERIFIED, REJECTED
    account_tier = Column(Enum(AccountTier), default=AccountTier.TIER1, nullable=False)

    # Customer Type
    is_sme_customer = Column(Boolean, default=False)

    # Other status and metadata
    is_staff = Column(Boolean, default=False) # For bank employees
    is_admin = Column(Boolean, default=False) # For system administrators
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    # Consider adding: registration_channel (e.g., 'mobile_app', 'web', 'agent')

    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    # transactions = relationship("Transaction", secondary="accounts", # This might be complex, consider direct link if needed
    #                             primaryjoin="User.id == Account.user_id",
    #                             secondaryjoin="Account.id == Transaction.account_id",
    #                             viewonly=True) # Avoid direct user-to-transaction link if transactions are always via accounts
    loans = relationship("Loan", back_populates="user", cascade="all, delete-orphan")
    cards = relationship("Card", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    # Placeholder for password hashing and verification methods
    def set_password(self, password):
        # In a real app, use a strong hashing library like passlib or bcrypt
        # For example: from passlib.context import CryptContext
        # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # self.hashed_password = pwd_context.hash(password)
        self.hashed_password = f"hashed_{password}" # Simple placeholder

    def check_password(self, password):
        # return pwd_context.verify(password, self.hashed_password)
        return self.hashed_password == f"hashed_{password}" # Simple placeholder
