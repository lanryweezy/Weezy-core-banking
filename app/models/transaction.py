import enum
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class TransactionType(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PAYMENT = "payment" # e.g., bill payment, card payment
    FEE = "fee"
    INTEREST = "interest"
    LOAN_DISBURSEMENT = "loan_disbursement"
    LOAN_REPAYMENT = "loan_repayment"
    REFUND = "refund"
    AI_ADJUSTMENT = "ai_adjustment" # For automated adjustments by AI systems

class TransactionStatus(enum.Enum):
    PENDING = "pending"       # Transaction initiated, awaiting processing/confirmation
    PROCESSING = "processing" # Transaction is actively being processed
    COMPLETED = "completed"     # Transaction successfully processed
    FAILED = "failed"         # Transaction failed (e.g., insufficient funds, technical error)
    CANCELLED = "cancelled"   # Transaction cancelled by user or system before completion
    REVERSED = "reversed"       # Transaction was completed but then reversed

class Transaction(Base):
    __tablename__ = "transactions"

    # Using account_id directly instead of from_account_id and to_account_id for simplicity if only one account involved
    # For transfers, both from_account_id and to_account_id will be used.
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True) # Source account for transfers/payments
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)   # Destination account for deposits/transfers

    transaction_type = Column(Enum(TransactionType), nullable=False, index=True)
    amount = Column(Numeric(precision=15, scale=2), nullable=False) # Always positive, type determines debit/credit
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False, index=True)
    description = Column(Text, nullable=True) # User-provided or system-generated description
    reference_id = Column(String(100), unique=True, index=True, nullable=True) # External or unique internal reference
    transaction_date = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=True) # Timestamp when transaction reached a final state (completed/failed)

    # For AI/Automation
    fraud_score = Column(Numeric(precision=5, scale=4), nullable=True) # e.g., 0.0 to 1.0
    is_flagged_for_review = Column(Boolean, default=False)
    automated_by = Column(String(50), nullable=True) # e.g., 'fraud_detection_system', 'recurring_payment_scheduler'

    # Relationships
    # Define relationships to from_account and to_account if needed for easier querying
    from_account = relationship("Account", foreign_keys=[from_account_id], backref="outgoing_transactions")
    to_account = relationship("Account", foreign_keys=[to_account_id], backref="incoming_transactions")

    # If a transaction is directly linked to a loan (e.g. a specific repayment)
    # loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True)
    # loan = relationship("Loan", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, type='{self.transaction_type.value}', amount={self.amount}, status='{self.status.value}')>"

    @staticmethod
    def generate_reference_id():
        import uuid
        return str(uuid.uuid4())
