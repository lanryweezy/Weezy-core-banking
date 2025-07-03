# Pydantic schemas for Loan Management Module
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List, Dict, Any # Added Dict, Any
from datetime import datetime, date
import decimal
import enum # For Pydantic enums

# Import enums from models to ensure consistency or define schema-specific versions
from .models import (
    LoanApplicationStatusEnum as ModelLoanApplicationStatusEnum,
    LoanAccountStatusEnum as ModelLoanAccountStatusEnum,
    CurrencyEnum as ModelCurrencyEnum,
    InterestTypeEnum as ModelInterestTypeEnum,
    RepaymentFrequencyEnum as ModelRepaymentFrequencyEnum,
    GuarantorTypeEnum as ModelGuarantorTypeEnum
)

# Schema Enums (ensure string values for API)
class CurrencySchema(str, enum.Enum):
    NGN = "NGN"
    USD = "USD"

class InterestTypeSchema(str, enum.Enum):
    REDUCING_BALANCE = "REDUCING_BALANCE"
    FLAT = "FLAT"
    INTEREST_ONLY = "INTEREST_ONLY"

class RepaymentFrequencySchema(str, enum.Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    BI_ANNUALLY = "BI_ANNUALLY"
    ANNUALLY = "ANNUALLY"
    BULLET = "BULLET"

class LoanApplicationStatusSchema(str, enum.Enum):
    DRAFT = "DRAFT"; SUBMITTED = "SUBMITTED"; UNDER_REVIEW = "UNDER_REVIEW"
    PENDING_DOCUMENTATION = "PENDING_DOCUMENTATION"; APPROVED = "APPROVED"
    REJECTED = "REJECTED"; PENDING_DISBURSEMENT = "PENDING_DISBURSEMENT"
    DISBURSED = "DISBURSED"; WITHDRAWN = "WITHDRAWN"; EXPIRED = "EXPIRED"

class LoanAccountStatusSchema(str, enum.Enum):
    ACTIVE = "ACTIVE"; PAID_OFF = "PAID_OFF"; OVERDUE = "OVERDUE"
    DEFAULTED = "DEFAULTED"; RESTRUCTURED = "RESTRUCTURED"; WRITTEN_OFF = "WRITTEN_OFF"

class GuarantorTypeSchema(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    CORPORATE = "CORPORATE"


# --- Loan Product Schemas ---
class LoanProductBase(BaseModel):
    product_code: str = Field(..., min_length=3, max_length=20, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    currency: CurrencySchema = CurrencySchema.NGN
    min_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    max_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    interest_rate_pa: decimal.Decimal = Field(..., ge=0, decimal_places=4) # e.g. 15.5000 for 15.5%
    interest_type: InterestTypeSchema = InterestTypeSchema.REDUCING_BALANCE
    min_tenor_months: int = Field(..., gt=0)
    max_tenor_months: int = Field(..., gt=0)
    repayment_frequency: RepaymentFrequencySchema = RepaymentFrequencySchema.MONTHLY
    linked_fee_codes_json: Optional[List[str]] = Field(None, description='List of applicable fee codes')
    eligibility_criteria_json: Optional[Dict[str, Any]] = Field(None, description='JSON defining eligibility rules')
    crms_product_code: Optional[str] = Field(None, max_length=10)
    is_active: bool = True

    @validator('max_amount')
    def max_amount_must_be_greater_than_min(cls, v, values):
        if 'min_amount' in values and v < values['min_amount']:
            raise ValueError('Max amount must be >= min amount')
        return v
    @validator('max_tenor_months')
    def max_tenor_must_be_greater_than_min(cls, v, values):
        if 'min_tenor_months' in values and v < values['min_tenor_months']:
            raise ValueError('Max tenor must be >= min tenor')
        return v

class LoanProductCreateRequest(LoanProductBase): # Renamed from LoanProductCreate
    pass

class LoanProductResponse(LoanProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- Loan Application Schemas ---
class LoanApplicationBase(BaseModel):
    customer_id: int
    loan_product_id: int # FK to loan_products.id
    requested_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    requested_currency: CurrencySchema = CurrencySchema.NGN
    requested_tenor_months: int = Field(..., gt=0)
    loan_purpose: Optional[str] = None

class LoanApplicationCreateRequest(LoanApplicationBase): # Renamed
    pass

class LoanApplicationUpdateRequest(BaseModel): # Renamed from LoanApplicationUpdate
    status: Optional[LoanApplicationStatusSchema] = None
    credit_score: Optional[int] = None
    risk_rating: Optional[str] = Field(None, max_length=50)
    decision_reason: Optional[str] = None
    approved_amount: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=2)
    approved_tenor_months: Optional[int] = Field(None, gt=0)
    approved_interest_rate_pa: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=4)
    crms_application_status: Optional[str] = Field(None, max_length=50)
    credit_bureau_report_id: Optional[str] = Field(None, max_length=50)

class LoanApplicationResponse(LoanApplicationBase):
    id: int
    application_reference: str
    status: LoanApplicationStatusSchema
    credit_score: Optional[int] = None
    risk_rating: Optional[str] = None
    decision_reason: Optional[str] = None
    approved_amount: Optional[decimal.Decimal] = None
    approved_tenor_months: Optional[int] = None
    approved_interest_rate_pa: Optional[decimal.Decimal] = None
    crms_application_status: Optional[str] = None
    credit_bureau_report_id: Optional[str] = None
    submitted_at: datetime
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    disbursed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    loan_product: Optional[LoanProductResponse] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- Loan Account Schemas ---
class LoanAccountBase(BaseModel):
    principal_disbursed: decimal.Decimal = Field(..., decimal_places=2)
    currency: CurrencySchema
    interest_rate_pa: decimal.Decimal = Field(..., decimal_places=4)
    tenor_months: int
    disbursement_date: date
    first_repayment_date: date
    maturity_date: date
    disbursement_account_number: str = Field(..., min_length=10, max_length=10)
    loan_purpose_code: Optional[str] = Field(None, max_length=10)


class LoanAccountResponse(LoanAccountBase):
    id: int
    loan_account_number: str
    application_id: int
    customer_id: int
    principal_outstanding: decimal.Decimal = Field(..., decimal_places=2)
    interest_outstanding: decimal.Decimal = Field(..., decimal_places=2)
    fees_outstanding: decimal.Decimal = Field(..., decimal_places=2)
    penalties_outstanding: decimal.Decimal = Field(..., decimal_places=2)
    total_repaid_principal: decimal.Decimal = Field(..., decimal_places=2)
    total_repaid_interest: decimal.Decimal = Field(..., decimal_places=2)
    status: LoanAccountStatusSchema
    crms_loan_status: Optional[str] = Field(None, max_length=50)
    next_repayment_date: Optional[date] = None
    days_past_due: int = 0
    last_repayment_date: Optional[datetime] = None
    last_repayment_amount: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    application: Optional[LoanApplicationResponse] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- Loan Repayment Schedule Schemas ---
class LoanRepaymentScheduleEntryResponse(BaseModel): # Renamed
    id: int
    loan_account_id: int
    due_date: date
    installment_number: int
    principal_due: decimal.Decimal = Field(..., decimal_places=2)
    interest_due: decimal.Decimal = Field(..., decimal_places=2)
    fees_due: decimal.Decimal = Field(decimal.Decimal('0.00'), decimal_places=2)
    total_due: decimal.Decimal = Field(..., decimal_places=2)
    principal_paid: decimal.Decimal = Field(decimal.Decimal('0.00'), decimal_places=2)
    interest_paid: decimal.Decimal = Field(decimal.Decimal('0.00'), decimal_places=2)
    fees_paid: decimal.Decimal = Field(decimal.Decimal('0.00'), decimal_places=2)
    is_paid: bool = False
    payment_date: Optional[date] = None
    class Config: orm_mode = True; json_encoders = {decimal.Decimal: str}

class LoanRepaymentScheduleResponse(BaseModel):
    loan_account_number: str
    schedule: List[LoanRepaymentScheduleEntryResponse]

# --- Loan Repayment Schemas ---
class LoanRepaymentCreateRequest(BaseModel): # Renamed
    loan_account_number: str
    financial_transaction_id: str # Link to master FT from TransactionManagement
    amount_paid: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    payment_date: datetime = Field(default_factory=datetime.utcnow)
    currency: CurrencySchema = CurrencySchema.NGN
    payment_method: Optional[str] = Field(None, max_length=50)
    reference: Optional[str] = Field(None, max_length=100)

class LoanRepaymentResponse(BaseModel):
    id: int
    loan_account_id: int
    financial_transaction_id: str
    payment_date: datetime
    amount_paid: decimal.Decimal = Field(..., decimal_places=2)
    currency: CurrencySchema
    allocated_to_principal: decimal.Decimal = Field(..., decimal_places=2)
    allocated_to_interest: decimal.Decimal = Field(..., decimal_places=2)
    allocated_to_fees: decimal.Decimal = Field(..., decimal_places=2)
    allocated_to_penalties: decimal.Decimal = Field(..., decimal_places=2)
    payment_method: Optional[str] = None
    reference: Optional[str] = None
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- Guarantor and Collateral Schemas ---
class GuarantorBase(BaseModel):
    guarantor_type: GuarantorTypeSchema
    name: str = Field(..., max_length=150)
    bvn: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$")
    phone: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = None
    relationship_to_applicant: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    status: str = Field("ACTIVE", max_length=20)

class GuarantorCreateRequest(GuarantorBase): # Renamed
    loan_application_id: int

class GuarantorResponse(GuarantorBase):
    id: int
    loan_application_id: int
    class Config: orm_mode = True; use_enum_values = True

class CollateralBase(BaseModel):
    type: str = Field(..., max_length=100, description="e.g., 'REAL_ESTATE', 'VEHICLE', 'STOCKS'")
    description: Optional[str] = None
    estimated_value: decimal.Decimal = Field(..., ge=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN
    valuation_date: Optional[date] = None
    location: Optional[str] = None
    lien_reference: Optional[str] = Field(None, max_length=50)
    status: str = Field("PLEDGED", max_length=20)

class CollateralCreateRequest(CollateralBase): # Renamed
    loan_application_id: int

class CollateralResponse(CollateralBase):
    id: int
    loan_application_id: int
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

# --- Other Schemas ---
class LoanDisbursementRequest(BaseModel):
    application_id: int
    disbursement_account_number: str = Field(..., min_length=10, max_length=10)
    # disbursement_amount: Optional[decimal.Decimal] = None # If different from approved amount

class LoanDisbursementResponse(BaseModel):
    loan_account_number: str
    amount_disbursed: decimal.Decimal = Field(..., decimal_places=2)
    disbursement_date: datetime # Changed to datetime to include time
    status: str
    financial_transaction_id: Optional[str] = None # Renamed from transaction_reference

class CreditRiskAssessmentRequest(BaseModel): # Request to AI/Risk module
    application_id: int
    # customer_bvn: str
    # requested_amount: decimal.Decimal
    # Other features for the model
    # features: Dict[str, Any]

class CreditRiskAssessmentResponse(BaseModel): # Response from AI/Risk module
    application_id: int
    credit_score: Optional[int] = None
    risk_rating: Optional[str] = None
    # recommended_loan_amount: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    # assessment_details: Optional[Dict[str, Any]] = None

class LoanRestructureRequest(BaseModel):
    loan_account_number: str
    new_tenor_months: Optional[int] = Field(None, gt=0)
    new_interest_rate_pa: Optional[decimal.Decimal] = Field(None, ge=0, decimal_places=4)
    reason: str
    effective_date: Optional[date] = None

class LoanWriteOffRequest(BaseModel):
    loan_account_number: str
    reason: str
    write_off_amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    effective_date: Optional[date] = None

class PaginatedLoanApplicationResponse(BaseModel):
    items: List[LoanApplicationResponse]
    total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str}

class PaginatedLoanAccountResponse(BaseModel):
    items: List[LoanAccountResponse]
    total: int; page: int; size: int
    class Config: json_encoders = {decimal.Decimal: str}
