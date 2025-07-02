# Pydantic schemas for Credit Analyst Agent API requests and responses

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any

class DocumentInput(BaseModel):
    document_url: HttpUrl = Field(..., example="https://example.com/docs/payslip.pdf")
    document_type: str = Field(..., example="income_proof") # e.g., loan_form, income_proof, transaction_history

class LoanApplicationInput(BaseModel):
    application_id: str = Field(..., example="LOANAPP20231027XYZ")
    applicant_id: str = Field(..., example="CUST12345")
    loan_amount: float = Field(..., gt=0, example=500000.00)
    loan_purpose: str = Field(..., example="Home renovation")
    currency: str = Field("NGN", example="NGN")
    documents: List[DocumentInput] = Field(..., description="List of documents submitted by the applicant")
    additional_data: Optional[Dict[str, Any]] = Field(None, example={"employment_status": "employed", "years_at_job": 5})

class DocumentAnalysisResult(BaseModel):
    document_url: HttpUrl
    document_type: str
    status: str = Field(..., example="Processed") # Processed, Error
    extracted_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class CreditScoreResult(BaseModel):
    score: Optional[int] = Field(None, example=720)
    risk_level: Optional[str] = Field(None, example="Medium") # Low, Medium, High
    factors: Optional[List[str]] = Field(None, example=["Length of credit history", "Payment history"])
    model_version: Optional[str] = Field(None, example="CS_Model_v2.1")

class RiskRuleCheck(BaseModel):
    rule_name: str = Field(..., example="Debt-to-Income Ratio Check")
    passed: bool = Field(..., example=True)
    details: Optional[str] = Field(None, example="DTI is 35%")

class LoanDecisionOutput(BaseModel):
    application_id: str
    decision: str = Field(..., example="Approved") # Approved, Rejected, ConditionalApproval, PendingReview
    reason: Optional[str] = Field(None, example="Applicant meets all credit criteria.")
    conditions: Optional[List[str]] = Field(None, example=["Provide proof of collateral."])
    risk_score_result: Optional[CreditScoreResult] = None
    document_analysis_summary: Optional[List[DocumentAnalysisResult]] = None
    risk_rule_checks: Optional[List[RiskRuleCheck]] = None
    recommended_loan_amount: Optional[float] = Field(None, example=450000.00)
    interest_rate: Optional[float] = Field(None, example=18.5)

print("Credit Analyst Agent Pydantic schemas placeholder.")
