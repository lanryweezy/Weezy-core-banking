# Pydantic schemas for AI & Automation Layer
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
import decimal # For financial data that might be input to models

from .models import AIModelTypeEnum # Import enums

# --- AIModelConfig Schemas (Admin/MLOps) ---
class AIModelConfigBase(BaseModel):
    model_code: str = Field(..., min_length=3, pattern=r"^[A-Z0-9_.-]+$")
    model_name: str
    model_type: AIModelTypeEnum
    version: str = Field("1.0", description="Semantic version or custom version string")
    # model_source_uri: Optional[HttpUrl] = None # If model is an API endpoint
    # model_parameters_json: Optional[Dict[str, Any]] = Field({}, description="Model-specific parameters")
    # performance_metrics_json: Optional[Dict[str, Any]] = Field({}, description="e.g. accuracy, precision, recall")
    is_active_serving: bool = False
    description: Optional[str] = None

class AIModelConfigCreateRequest(AIModelConfigBase):
    # model_api_key_plain: Optional[str] = None # If model is an external API needing a key

class AIModelConfigResponse(AIModelConfigBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config:
        orm_mode = True
        use_enum_values = True

# --- AIPredictionLog Schemas (Primarily for internal logging/retrieval) ---
class AIPredictionLogResponse(BaseModel):
    id: int
    model_code_used: str
    model_version_used: str
    request_reference_id: str
    # entity_type: Optional[str] = None
    # entity_id: Optional[str] = None
    # input_features_json: Optional[Dict[str, Any]] = None # Parsed from Text by Pydantic
    prediction_raw_output_json: Optional[Dict[str, Any]] = None
    prediction_processed_value: Optional[str] = None
    prediction_score_or_confidence: Optional[float] = None
    # human_review_status: Optional[str] = None
    prediction_timestamp: datetime
    class Config:
        orm_mode = True

# --- FraudDetectionRule Schemas (Admin/Fraud Analyst) ---
class FraudDetectionRuleBase(BaseModel):
    rule_code: str = Field(..., min_length=3, pattern=r"^[A-Z0-9_]+$")
    description: str
    # parameters_json: Optional[Dict[str, Any]] = Field({})
    severity: str = "MEDIUM"
    action_to_take: str = "FLAG_FOR_REVIEW"
    is_active: bool = True

class FraudDetectionRuleCreateRequest(FraudDetectionRuleBase):
    pass

class FraudDetectionRuleResponse(FraudDetectionRuleBase):
    id: int
    class Config:
        orm_mode = True

# --- FraudAlertLog Schemas (Fraud Analyst/Ops) ---
class FraudAlertLogResponse(BaseModel):
    id: int
    source_reference_id: Optional[str] = None
    source_reference_type: Optional[str] = None
    # detection_method: Optional[str] = None
    # model_prediction_log_id: Optional[int] = None
    # fraud_rule_code_triggered: Optional[str] = None
    alert_details: Optional[str] = None
    alert_score: Optional[float] = None
    status: str
    # assigned_to_analyst_id: Optional[str] = None
    # analyst_notes: Optional[str] = None
    alert_timestamp: datetime
    resolved_timestamp: Optional[datetime] = None
    class Config:
        orm_mode = True

class FraudAlertStatusUpdateRequest(BaseModel):
    new_status: str # OPEN, INVESTIGATING, CONFIRMED_FRAUD, FALSE_POSITIVE, RESOLVED
    # analyst_notes: Optional[str] = None
    # resolution_action_taken: Optional[str] = None

# --- LLMTaskLog Schemas (Internal) ---
class LLMTaskLogResponse(BaseModel):
    id: int
    task_type: str
    # input_data_reference: Optional[str] = None
    # llm_prompt_final: Optional[str] = None
    llm_response_processed_output: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    # human_feedback_rating: Optional[int] = None
    task_timestamp: datetime
    class Config:
        orm_mode = True

# --- Schemas for invoking AI services (conceptual examples) ---

# Credit Scoring Service Invocation
class CreditScoringRequest(BaseModel):
    application_id: str # Could be internal loan application ID
    # Customer data (BVN, income, transaction history summary, etc.)
    # This data needs to be carefully curated based on the model's feature requirements.
    # customer_bvn: str
    # monthly_income: Optional[decimal.Decimal] = None
    # existing_loan_count: Optional[int] = None
    # transaction_summary_last_6m: Optional[Dict[str, Any]] = None # e.g. avg_credit, avg_debit
    features: Dict[str, Any] = Field(..., description="Key-value pairs of features for the model")


class CreditScoringResponse(BaseModel):
    application_id: str
    credit_score: int # e.g. 300-850
    risk_rating: str # e.g. "LOW", "MEDIUM", "HIGH", "A1", "C3"
    # probability_of_default: Optional[float] = None # If model provides this
    recommended_action: Optional[str] = None # e.g. "APPROVE", "REJECT", "MANUAL_REVIEW"
    # reason_codes: Optional[List[str]] = None # Codes explaining the score
    # prediction_log_id: int # Link to the AIPredictionLog entry

# Transaction Fraud Detection Service Invocation
class TransactionFraudCheckRequest(BaseModel):
    transaction_id: str # Internal financial transaction ID
    # Transaction details (amount, currency, type, channel, beneficiary, originator etc.)
    # Historical context (customer's recent activity, device info, location if available)
    # This data is highly specific to the fraud model.
    features: Dict[str, Any] = Field(..., description="Transaction and contextual features")

class TransactionFraudCheckResponse(BaseModel):
    transaction_id: str
    is_fraud_suspected: bool
    fraud_score: Optional[float] = None # e.g. 0.0 (low risk) to 1.0 (high risk)
    reason: Optional[str] = None # Explanation or rule triggered
    # recommended_action: Optional[str] = None # e.g. "ALLOW", "BLOCK", "REQUIRE_OTP", "FLAG_FOR_REVIEW"
    # alert_log_id: Optional[int] = None # Link to FraudAlertLog if alert generated

# LLM Task Service Invocation (Generic)
class LLMTaskRequest(BaseModel):
    task_type: str # e.g., "SUMMARIZE_EMAIL", "DRAFT_CUSTOMER_REPLY", "EXTRACT_LOAN_TERMS_FROM_DOC"
    input_text: Optional[str] = None
    # input_document_url: Optional[HttpUrl] = None # If processing a document
    # context_data: Optional[Dict[str, Any]] = None # Additional context for the LLM
    # output_format_preference: Optional[str] = None # e.g. "BULLET_POINTS", "FORMAL_EMAIL"

class LLMTaskResponse(BaseModel):
    task_type: str
    processed_output: str # The text generated by LLM (summary, draft, extracted info)
    # confidence_score: Optional[float] = None # If LLM provides it
    # task_log_id: int

# Paginated responses for admin views
class PaginatedAIModelConfigResponse(BaseModel):
    items: List[AIModelConfigResponse]
    total: int
    page: int
    size: int

class PaginatedAIPredictionLogResponse(BaseModel):
    items: List[AIPredictionLogResponse]
    total: int
    page: int
    size: int

class PaginatedFraudAlertLogResponse(BaseModel):
    items: List[FraudAlertLogResponse]
    total: int
    page: int
    size: int

# Import decimal for fields that might use it
import decimal
