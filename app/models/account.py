import enum
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class AccountType(enum.Enum):
    SAVINGS = "savings"
    CHECKING = "checking"
    FIXED_DEPOSIT = "fixed_deposit"
    CREDIT = "credit" # For credit card accounts, if managed differently
    LOAN = "loan_account" # For loan disbursement and repayment tracking

class AccountStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DORMANT = "dormant"
    SUSPENDED = "suspended"
    CLOSED = "closed"

class Account(Base):
    __tablename__ = "accounts"

    account_number = Column(String(20), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    balance = Column(Numeric(precision=15, scale=2), default=0.00, nullable=False) # Use Numeric for currency
    currency = Column(String(3), default="USD", nullable=False) # ISO currency code
    status = Column(Enum(AccountStatus), default=AccountStatus.PENDING, nullable=False)
    opened_date = Column(DateTime, default=datetime.datetime.utcnow)
    closed_date = Column(DateTime, nullable=True)
    # For AI features like anomaly detection or personalized offers
    interest_rate = Column(Numeric(precision=5, scale=4), nullable=True) # e.g., 0.0150 for 1.5%
    overdraft_limit = Column(Numeric(precision=15, scale=2), default=0.00)
    is_primary = Column(Boolean, default=False) # If a user can have a primary account

    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction",
                                primaryjoin="or_(Account.id==Transaction.from_account_id, Account.id==Transaction.to_account_id)",
                                # cascade="all, delete-orphan" # Be careful with cascading deletes on transactions
                                viewonly=True, # Transactions are usually immutable once created
                                )
    # If one account is directly tied to one loan (e.g. loan account)
    # loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True)
    # loan = relationship("Loan", back_populates="related_account") # if a loan has a specific account

    def __repr__(self):
        return f"<Account(id={self.id}, account_number='{self.account_number}', user_id={self.user_id}, balance={self.balance} {self.currency})>"

    # Placeholder for generating unique account numbers
    @staticmethod
    def generate_account_number():
        # In a real system, this would be a sophisticated, collision-resistant generator
        import random
        import string
        return ''.join(random.choices(string.digits, k=10))

    def can_transact(self) -> bool:
        """Check if the account is in a state that allows transactions."""
        return self.status == AccountStatus.ACTIVE

    def has_sufficient_funds(self, amount: float) -> bool:
        """Check if account has enough balance for a debit operation, considering overdraft."""
        if amount <= 0:
            return True # Or raise error for invalid amount
        return (self.balance + self.overdraft_limit) >= amount
