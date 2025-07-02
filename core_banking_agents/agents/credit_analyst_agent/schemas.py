# Pydantic schemas for Credit Analyst Agent API requests and responses

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date
import uuid

# --- Enums and Helper Models ---
LoanPurposeType = Literal[
    "PersonalUse", "BusinessStartup", "BusinessExpansion", "DebtConsolidation",
    "HomeImprovement", "VehiclePurchase", "Education", "MedicalExpenses", "Other"
]
EmploymentStatusType = Literal[
    "FullTime", "PartTime", "SelfEmployed", "Unemployed", "Student", "Retired"
]
DocumentCategory = Literal[
    "Identification", "IncomeProof", "AddressProof", "BankStatement", "BusinessDocument", "Other"
]
LoanDecisionType = Literal["Approved", "Rejected", "ConditionalApproval", "PendingReview", "InformationRequested"]


class DocumentProof(BaseModel):
    document_id: str = Field(default_factory=lambda: f"DOC-{uuid.uuid4().hex[:8].upper()}")
    document_type_name: str = Field(..., example="Payslip - March 2023") # User-friendly name
    document_category: DocumentCategory = Field(..., example="IncomeProof")
    file_url: HttpUrl = Field(..., example="https://example.com/docs/payslip_march_2023.pdf")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    # metadata: Optional[Dict[str, Any]] = None # e.g., file size, content type if needed by agent

class ApplicantInformation(BaseModel):
    applicant_id: Optional[str] = Field(None, example="APP-001-CUST123") # Can be linked to existing customer ID
    first_name: str = Field(..., example="Chiamaka")
    last_name: str = Field(..., example="Adeyemi")
    date_of_birth: date = Field(..., example="1988-07-10")
    email: EmailStr = Field(..., example="chiamaka.adeyemi@email.com")
    phone_number: str = Field(..., example="08033344455")
    bvn: Optional[str] = Field(None, min_length=11, max_length=11, example="22112233445")
    nin: Optional[str] = Field(None, min_length=11, max_length=11, example="55443322110")
    current_address: str = Field(..., example="15, Freedom Way, Lekki Phase 1, Lagos")
    employment_status: EmploymentStatusType = Field(..., example="SelfEmployed")
    monthly_income_ngn: Optional[float] = Field(None, gt=0, example=750000.00)
    # additional_financial_info: Optional[Dict[str, Any]] = None # e.g., other assets, existing debts

# --- Request Model ---
class LoanApplicationInput(BaseModel):
    application_id: str = Field(default_factory=lambda: f"LOANAPP-{uuid.uuid4().hex[:10].upper()}")
    applicant_details: ApplicantInformation
    loan_amount_requested_ngn: float = Field(..., gt=0, example=1500000.00)
    loan_purpose: LoanPurposeType = Field(..., example="BusinessExpansion")
    loan_purpose_description: Optional[str] = Field(None, example="To purchase new equipment for my catering business.")
    requested_loan_tenor_months: int = Field(..., gt=0, example=24)
    submitted_documents: List[DocumentProof] = Field(..., min_length=1) # min_items in older Pydantic
    # consent_to_credit_check: bool = Field(..., example=True) # Important for real application

    class Config:
        json_schema_extra = {
            "example": {
                "applicant_details": {
                    "first_name": "Chiamaka", "last_name": "Adeyemi", "date_of_birth": "1988-07-10",
                    "email": "chiamaka.adeyemi@email.com", "phone_number": "08033344455", "bvn": "22112233445",
                    "current_address": "15, Freedom Way, Lekki Phase 1, Lagos", "employment_status": "SelfEmployed",
                    "monthly_income_ngn": 750000.00
                },
                "loan_amount_requested_ngn": 1500000.00,
                "loan_purpose": "BusinessExpansion",
                "requested_loan_tenor_months": 24,
                "submitted_documents": [
                    {"document_type_name": "CAC Business Registration", "document_category": "BusinessDocument", "file_url": "https://example.com/docs/cac_reg.pdf"},
                    {"document_type_name": "Bank Statement (6 Months)", "document_category": "BankStatement", "file_url": "https://example.com/docs/bank_statement.pdf"},
                    {"document_type_name": "National ID", "document_category": "Identification", "file_url": "https://example.com/docs/national_id.jpg"}
                ]
            }
        }

# --- Response Models ---
class DocumentAnalysisResult(BaseModel): # Re-defined for Credit context, could be shared from Onboarding if identical
    document_id: str
    document_category: DocumentCategory
    status: Literal["Processed", "ProcessingFailed", "AwaitingProcessing"] = "AwaitingProcessing"
    key_extractions: Optional[Dict[str, Any]] = Field(None, example={"company_name": "Adeyemi Catering Services"})
    validation_summary: Optional[str] = Field(None, example="Document appears authentic.")

class CreditBureauReportSummary(BaseModel):
    bureau_name: str = Field(..., example="CRC Credit Bureau")
    credit_score: Optional[int] = Field(None, example=680)
    active_loans_count: Optional[int] = Field(None, example=1)
    total_outstanding_debt_ngn: Optional[float] = Field(None, example=250000.00)
    report_date: date = Field(default_factory=date.today)
    summary_narrative: Optional[str] = Field(None, example="Positive credit history with one active, performing loan.")

class RiskAssessmentResult(BaseModel):
    overall_risk_rating: Literal["Low", "Medium", "High", "VeryHigh"] = Field(..., example="Medium")
    key_risk_factors: Optional[List[str]] = Field(None, example=["High debt-to-income ratio", "Short business history"])
    mitigants_considered: Optional[List[str]] = Field(None)

class LoanAssessmentOutput(BaseModel):
    application_id: str
    assessment_id: str = Field(default_factory=lambda: f"ASSESS-{uuid.uuid4().hex[:10].upper()}")
    assessment_timestamp: datetime = Field(default_factory=datetime.utcnow)

    decision: LoanDecisionType = Field(..., example="Approved")
    decision_reason: Optional[str] = Field(None, example="Applicant meets affordability and credit criteria.")

    approved_loan_amount_ngn: Optional[float] = Field(None, example=1200000.00)
    approved_loan_tenor_months: Optional[int] = Field(None, example=24)
    approved_interest_rate_pa: Optional[float] = Field(None, example=21.5) # Percent per annum

    conditions_for_approval: Optional[List[str]] = Field(None, example=["Provide proof of collateral for property X."])
    required_further_documents: Optional[List[str]] = Field(None, example=["Updated 6-month bank statement."])

    document_analysis_summary: Optional[List[DocumentAnalysisResult]] = None
    credit_bureau_summary: Optional[CreditBureauReportSummary] = None
    risk_assessment_summary: Optional[RiskAssessmentResult] = None

    # For internal use or detailed feedback
    # scoring_model_output: Optional[Dict[str, Any]] = None
    # rules_engine_trace: Optional[List[Dict[str, Any]]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "application_id": "LOANAPP-ABC123XYZ", "assessment_id": "ASSESS-DEF456UVW",
                "assessment_timestamp": "2023-10-29T14:30:00Z", "decision": "ConditionalApproval",
                "decision_reason": "Applicant shows good income but existing debt is slightly high. Approval subject to collateral.",
                "approved_loan_amount_ngn": 1200000.00, "approved_loan_tenor_months": 24, "approved_interest_rate_pa": 22.0,
                "conditions_for_approval": ["Provide collateral documentation (landed property C of O)."],
                "risk_assessment_summary": {"overall_risk_rating": "Medium", "key_risk_factors": ["Debt-to-income ratio at 45%"]}
            }
        }

# For GET /loan-applications/{application_id}/status - can reuse LoanAssessmentOutput or a summary version
LoanApplicationStatusResponse = LoanAssessmentOutput


if __name__ == "__main__":
    import json
    print("--- LoanApplicationInput Schema ---")
    print(json.dumps(LoanApplicationInput.model_json_schema(), indent=2))
    print("\n--- LoanAssessmentOutput Schema ---")
    print(json.dumps(LoanAssessmentOutput.model_json_schema(), indent=2))

    # Example instantiation
    # try:
    #     app_input_data = LoanApplicationInput.Config.json_schema_extra["example"]
    #     app_input = LoanApplicationInput(**app_input_data)
    #     print("\nValid LoanApplicationInput instance:\n", app_input.model_dump_json(indent=2))

    #     assessment_output_data = LoanAssessmentOutput.Config.json_schema_extra["example"]
    #     assessment_output = LoanAssessmentOutput(**assessment_output_data)
    #     print("\nValid LoanAssessmentOutput instance:\n", assessment_output.model_dump_json(indent=2))
    # except Exception as e:
    #     print("\nError during schema instantiation example:", e)
    pass
