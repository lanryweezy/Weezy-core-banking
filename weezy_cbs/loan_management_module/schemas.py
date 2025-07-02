# Pydantic schemas for Loan Management Module
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
import decimal

from .models import LoanApplicationStatusEnum, LoanAccountStatusEnum, CurrencyEnum # Import enums

# --- Loan Product Schemas ---
class LoanProductBase(BaseModel):
    name: str = Field(..., min_length=3)
    description: Optional[str] = None
    min_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    max_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    interest_rate_pa: decimal.Decimal = Field(..., ge=0, decimal_places=2, description="Annual interest rate in percentage, e.g., 15.5 for 15.5%")
    min_tenor_months: int = Field(..., gt=0)
    max_tenor_months: int = Field(..., gt=0)
    is_active: bool = True

    @validator('max_amount')
    def max_amount_must_be_greater_than_min(cls, v, values):
        if 'min_amount' in values and v < values['min_amount']:
            raise ValueError('Max amount must be greater than or equal to min amount')
        return v

    @validator('max_tenor_months')
    def max_tenor_must_be_greater_than_min(cls, v, values):
        if 'min_tenor_months' in values and v < values['min_tenor_months']:
            raise ValueError('Max tenor must be greater than or equal to min tenor')
        return v

class LoanProductCreate(LoanProductBase):
    pass

class LoanProductResponse(LoanProductBase):
    id: int

    class Config:
        orm_mode = True
        json_encoders = { decimal.Decimal: lambda v: str(v) }

# --- Loan Application Schemas ---
class LoanApplicationBase(BaseModel):
    customer_id: int
    loan_product_id: int
    requested_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    requested_tenor_months: int = Field(..., gt=0)
    loan_purpose: Optional[str] = None

class LoanApplicationCreate(LoanApplicationBase):
    pass # Submitted by customer or agent

class LoanApplicationUpdate(BaseModel): # For internal updates by loan officers/system
    status: Optional[LoanApplicationStatusEnum] = None
    credit_score: Optional[int] = None
    risk_rating: Optional[str] = None
    decision_reason: Optional[str] = None
    # Potentially add fields for adjusting requested_amount/tenor by bank during review

class LoanApplicationResponse(LoanApplicationBase):
    id: int
    application_reference: str
    status: LoanApplicationStatusEnum
    credit_score: Optional[int] = None
    risk_rating: Optional[str] = None
    decision_reason: Optional[str] = None
    submitted_at: datetime
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    disbursed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    loan_product: Optional[LoanProductResponse] = None # Nested response for product details

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: lambda v: str(v) }

# --- Loan Account Schemas (Active Loans) ---
class LoanAccountBase(BaseModel):
    # application_id: int # Usually derived, not directly set
    # customer_id: int # Usually derived
    # disbursement_account_id: int # Customer's savings/current account NUBAN where loan is paid
    principal_disbursed: decimal.Decimal
    interest_rate_pa: decimal.Decimal
    tenor_months: int
    disbursement_date: date # Or datetime
    first_repayment_date: date
    maturity_date: date

class LoanAccountResponse(LoanAccountBase):
    id: int
    loan_account_number: str
    application_id: int
    customer_id: int

    principal_outstanding: decimal.Decimal
    interest_outstanding: decimal.Decimal
    fees_outstanding: decimal.Decimal
    penalties_outstanding: decimal.Decimal

    total_repaid_principal: decimal.Decimal
    total_repaid_interest: decimal.Decimal

    status: LoanAccountStatusEnum
    next_repayment_date: Optional[date] = None
    days_past_due: int = 0
    last_repayment_date: Optional[datetime] = None
    last_repayment_amount: Optional[decimal.Decimal] = None

    application: Optional[LoanApplicationResponse] = None # Nested app details

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str(v) for v in [decimal.Decimal] }


# --- Loan Repayment Schedule Schemas ---
class LoanRepaymentScheduleEntry(BaseModel):
    due_date: date
    installment_number: int
    principal_due: decimal.Decimal
    interest_due: decimal.Decimal
    fees_due: decimal.Decimal = decimal.Decimal('0.00')
    total_due: decimal.Decimal
    principal_paid: decimal.Decimal = decimal.Decimal('0.00')
    interest_paid: decimal.Decimal = decimal.Decimal('0.00')
    fees_paid: decimal.Decimal = decimal.Decimal('0.00')
    is_paid: bool = False
    payment_date: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_encoders = { decimal.Decimal: str }

class LoanRepaymentScheduleResponse(BaseModel):
    loan_account_number: str
    schedule: List[LoanRepaymentScheduleEntry]

# --- Loan Repayment Schemas (Actual Payments) ---
class LoanRepaymentCreate(BaseModel):
    loan_account_number: str
    amount_paid: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    payment_date: datetime = Field(default_factory=datetime.utcnow)
    currency: CurrencyEnum = CurrencyEnum.NGN
    payment_method: Optional[str] = None # e.g., 'DIRECT_DEBIT', 'NIP_TRANSFER'
    reference: Optional[str] = None # Payment reference from gateway or teller

class LoanRepaymentResponse(BaseModel):
    id: int
    loan_account_id: int
    # transaction_id: str # Link to financial_transactions
    payment_date: datetime
    amount_paid: decimal.Decimal
    currency: CurrencyEnum

    allocated_to_principal: decimal.Decimal
    allocated_to_interest: decimal.Decimal
    allocated_to_fees: decimal.Decimal
    allocated_to_penalties: decimal.Decimal

    payment_method: Optional[str] = None
    reference: Optional[str] = None

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }


# --- Guarantor and Collateral Schemas ---
class GuarantorBase(BaseModel):
    name: str
    bvn: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$")
    phone: Optional[str] = None
    email: Optional[str] = None # pydantic.EmailStr if strict validation needed
    relationship_to_applicant: Optional[str] = None

class GuarantorCreate(GuarantorBase):
    loan_application_id: int # Or loan_account_id

class GuarantorResponse(GuarantorBase):
    id: int
    loan_application_id: int

    class Config:
        orm_mode = True

class CollateralBase(BaseModel):
    type: str = Field(..., description="e.g., 'REAL_ESTATE', 'VEHICLE', 'STOCKS'")
    description: Optional[str] = None
    estimated_value: decimal.Decimal = Field(..., ge=0, decimal_places=2)
    # document_urls: Optional[List[str]] = None # List of URLs to documents

class CollateralCreate(CollateralBase):
    loan_application_id: int # Or loan_account_id

class CollateralResponse(CollateralBase):
    id: int
    loan_application_id: int

    class Config:
        orm_mode = True
        json_encoders = { decimal.Decimal: str }

# --- Other Schemas ---
class LoanDisbursementRequest(BaseModel):
    application_id: int
    disbursement_account_number: str # Customer's NUBAN to credit
    # Potentially allow override of disbursed amount if less than approved

class LoanDisbursementResponse(BaseModel):
    loan_account_number: str
    amount_disbursed: decimal.Decimal
    disbursement_date: datetime
    status: str # e.g. "SUCCESSFUL"
    transaction_reference: Optional[str] = None # Ref for the actual fund transfer

class CreditRiskAssessmentRequest(BaseModel):
    application_id: int
    # Include any data needed for the risk model not already in the application
    # e.g., bureau_report_id, additional_financial_statement_data

class CreditRiskAssessmentResponse(BaseModel):
    application_id: int
    credit_score: int
    risk_rating: str # e.g. 'A1', 'B2', 'LOW', 'HIGH'
    recommended_loan_amount: Optional[decimal.Decimal] = None
    assessment_details: Optional[dict] = None # For more granular risk factors

class LoanRestructureRequest(BaseModel):
    loan_account_number: str
    new_tenor_months: Optional[int] = None
    new_interest_rate_pa: Optional[decimal.Decimal] = None
    reason: str
    # effective_date: date

class LoanWriteOffRequest(BaseModel):
    loan_account_number: str
    reason: str
    write_off_amount: decimal.Decimal # Amount of principal being written off
    # effective_date: date

class PaginatedLoanApplicationResponse(BaseModel):
    items: List[LoanApplicationResponse]
    total: int
    page: int
    size: int
    class Config:
        json_encoders = { decimal.Decimal: str }

class PaginatedLoanAccountResponse(BaseModel):
    items: List[LoanAccountResponse]
    total: int
    page: int
    size: int
    class Config:
        json_encoders = { decimal.Decimal: str }
