import enum
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class LoanType(enum.Enum):
    PERSONAL = "personal"
    MORTGAGE = "mortgage"
    AUTO = "auto"
    STUDENT = "student"
    BUSINESS = "business"
    PAYDAY = "payday"

class LoanStatus(enum.Enum):
    REQUESTED = "requested" # User applied for a loan
    PENDING_APPROVAL = "pending_approval" # Application under review
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active" # Loan disbursed and ongoing
    PAID_OFF = "paid_off"
    DEFAULTED = "defaulted" # Borrower failed to meet obligations
    CANCELLED = "cancelled" # Application cancelled before approval/disbursement

class RepaymentFrequency(enum.Enum):
    WEEKLY = "weekly"
    BI_WEEKLY = "bi_weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"

class Loan(Base):
    __tablename__ = "loans"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    loan_type = Column(Enum(LoanType), nullable=False)
    principal_amount = Column(Numeric(precision=15, scale=2), nullable=False) # Original loan amount
    current_balance = Column(Numeric(precision=15, scale=2), nullable=False) # Remaining amount to be paid
    interest_rate = Column(Numeric(precision=5, scale=4), nullable=False) # Annual interest rate, e.g., 0.05 for 5%
    term_months = Column(Integer, nullable=False) # Duration of the loan in months
    status = Column(Enum(LoanStatus), default=LoanStatus.REQUESTED, nullable=False)
    application_date = Column(DateTime, default=datetime.datetime.utcnow)
    approval_date = Column(DateTime, nullable=True)
    disbursement_date = Column(DateTime, nullable=True) # Date when funds were given to user
    next_payment_date = Column(DateTime, nullable=True)
    final_payment_date = Column(DateTime, nullable=True) # Expected or actual final payment date
    collateral_description = Column(Text, nullable=True) # Description of any collateral
    purpose = Column(Text, nullable=True) # Purpose of the loan

    # For AI/Automation
    credit_score_at_application = Column(Integer, nullable=True)
    automated_approval_status = Column(String(50), nullable=True) # e.g., 'auto-approved', 'requires_manual_review', 'auto-rejected'
    risk_rating = Column(String(50), nullable=True) # e.g., 'low', 'medium', 'high' (could be AI-determined)
    repayment_frequency = Column(Enum(RepaymentFrequency), default=RepaymentFrequency.MONTHLY)
    installment_amount = Column(Numeric(precision=15, scale=2), nullable=True) # Calculated periodic payment

    # Relationships
    user = relationship("User", back_populates="loans")
    # If a loan is disbursed to a specific account or repayments are made from a specific account
    # This might be better handled via transactions linking to the loan
    # disbursement_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    # repayment_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    # Transactions related to this loan (e.g., disbursement, repayments, fees)
    # This requires transactions to have a loan_id ForeignKey
    # transactions = relationship("Transaction", back_populates="loan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Loan(id={self.id}, user_id={self.user_id}, type='{self.loan_type.value}', amount={self.principal_amount}, status='{self.status.value}')>"

    def calculate_installment_amount(self):
        """
        Placeholder for calculating the periodic installment amount.
        A real implementation would use the appropriate financial formula (e.g., for an amortizing loan).
        This is a simplified example.
        PMT = P * [r(1+r)^n] / [(1+r)^n-1]
        where P = Principal, r = periodic interest rate, n = number of periods
        """
        if not self.principal_amount or not self.interest_rate or not self.term_months or self.term_months == 0:
            return 0.00

        if self.interest_rate == 0: # Interest-free loan
            return self.principal_amount / self.term_months

        monthly_rate = self.interest_rate / 12
        n_payments = self.term_months

        if monthly_rate > 0:
            try:
                payment = float(self.principal_amount) * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
                return round(payment, 2)
            except OverflowError: # Handle potential math errors with large numbers
                return float('inf') # Or some other error indicator
        return round(float(self.principal_amount) / n_payments, 2) # Fallback for zero rate if not caught above


    def disburse(self, disbursement_account, effective_date=None):
        """
        Logic to disburse the loan.
        This would typically involve creating a transaction.
        """
        if self.status != LoanStatus.APPROVED:
            raise ValueError("Loan must be approved to be disbursed.")

        self.status = LoanStatus.ACTIVE
        self.disbursement_date = effective_date or datetime.datetime.utcnow()
        self.current_balance = self.principal_amount # Initially, current balance is full principal

        # TODO: Create a disbursement transaction
        # This method would ideally be part of a service layer that handles db session
        print(f"Loan {self.id} disbursed. Amount: {self.principal_amount}. Current Balance: {self.current_balance}")
        # Update next_payment_date and final_payment_date based on disbursement_date and term_months
        # self.installment_amount = self.calculate_installment_amount()

    def make_repayment(self, amount, repayment_account, effective_date=None):
        """
        Logic to make a repayment.
        This would typically involve creating a transaction.
        """
        if self.status != LoanStatus.ACTIVE:
            raise ValueError("Loan must be active to make repayments.")
        if amount <= 0:
            raise ValueError("Repayment amount must be positive.")

        # Basic repayment logic, doesn't handle interest vs principal split here
        self.current_balance -= amount
        if self.current_balance <= 0:
            self.current_balance = 0
            self.status = LoanStatus.PAID_OFF
            self.final_payment_date = effective_date or datetime.datetime.utcnow()

        # TODO: Create a repayment transaction
        print(f"Repayment of {amount} made for loan {self.id}. Remaining balance: {self.current_balance}")
        # Update next_payment_date
        if self.status == LoanStatus.PAID_OFF:
            print(f"Loan {self.id} is now PAID_OFF.")
