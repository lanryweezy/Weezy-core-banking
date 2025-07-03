from pydantic import BaseModel, Field, validator, Json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import json

from .models import (
    AIModelTypeEnum, AIModelStatusEnum, AITaskStatusEnum
)

# --- Helper Schemas for JSON fields ---
class LLMConfigSchema(BaseModel): # For llm_config_json in AIAgentConfig
    provider: Optional[str] = Field("OPENAI", description="e.g., OPENAI, AZURE_OPENAI, ANTHROPIC, LOCAL_HF")
    model_name: str = Field(..., description="e.g., gpt-4-turbo, claude-2, local_model_path_or_id")
    api_key_secret_ref: Optional[str] = Field(None, description="Reference to secret storing API key (e.g., vault path)")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    # Add other common LLM parameters like top_p, presence_penalty etc.

class ToolConfigSchema(BaseModel): # For individual tools in tools_config_json
    tool_name: str = Field(..., description="Unique name/identifier for the tool")
    description: Optional[str] = None
    # Configuration for the tool, e.g., API endpoint, model_id for an AIModelMetadata tool
    config: Optional[Dict[str, Any]] = None

class RuleConditionSchema(BaseModel): # Example for conditions_json in AutomatedRule
    field: str
    operator: str # e.g., "eq", "gt", "lt", "contains", "matches_regex"
    value: Any

class RuleActionSchema(BaseModel): # Example for actions_json in AutomatedRule
    action_type: str # e.g., "FLAG_FOR_REVIEW", "AUTO_APPROVE_LOAN", "SEND_ALERT_SMS"
    parameters: Optional[Dict[str, Any]] = None


# --- AIModelMetadata Schemas ---
class AIModelMetadataBase(BaseModel):
    model_name: str = Field(..., max_length=150)
    model_type: AIModelTypeEnum
    version: str = Field("1.0.0", max_length=20)
    description: Optional[str] = None
    source_type: str = Field(..., max_length=50, description="e.g., INTERNAL_PATH, EXTERNAL_API_ENDPOINT, HUGGINGFACE_HUB_ID")
    source_identifier: str = Field(..., description="Path, URL, Hub ID, or Python class path")
    input_schema_json: Optional[Dict[str, Any]] = Field(None, description="JSON schema of expected input")
    output_schema_json: Optional[Dict[str, Any]] = Field(None, description="JSON schema of model's output")
    status: AIModelStatusEnum = AIModelStatusEnum.ACTIVE
    performance_metrics_json: Optional[Dict[str, Any]] = Field(None, description='e.g., {"accuracy": 0.95}')

    @validator('input_schema_json', 'output_schema_json', 'performance_metrics_json', pre=True)
    def parse_json_fields(cls, value):
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: raise ValueError("Invalid JSON string")
        return value

class AIModelMetadataCreate(AIModelMetadataBase):
    # created_by_user_id from authenticated user
    pass

class AIModelMetadataUpdate(BaseModel): # Partial updates
    model_name: Optional[str] = Field(None, max_length=150)
    model_type: Optional[AIModelTypeEnum] = None
    version: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    source_type: Optional[str] = Field(None, max_length=50)
    source_identifier: Optional[str] = None
    input_schema_json: Optional[Dict[str, Any]] = None
    output_schema_json: Optional[Dict[str, Any]] = None
    status: Optional[AIModelStatusEnum] = None
    deployed_at: Optional[datetime] = None # Allow manual update of deployment timestamp
    performance_metrics_json: Optional[Dict[str, Any]] = None

    @validator('input_schema_json', 'output_schema_json', 'performance_metrics_json', pre=True)
    def parse_update_json_fields(cls, value): # Duplicate for update
        if value is None: return None
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: raise ValueError("Invalid JSON string")
        return value

class AIModelMetadataResponse(AIModelMetadataBase):
    id: int
    deployed_at: Optional[datetime] = None
    created_by_user_id: Optional[int] = None
    # created_by_username: Optional[str] = None # Added by service
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True


# --- AITaskLog Schemas ---
class AITaskLogCreate(BaseModel): # For internal service use
    model_metadata_id: Optional[int] = None
    task_name: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    input_data_summary_json: Optional[Dict[str, Any]] = None
    user_triggering_task_id: Optional[int] = None
    correlation_id: Optional[str] = None
    status: AITaskStatusEnum = AITaskStatusEnum.PENDING # Default for new tasks

class AITaskLogResponse(BaseModel):
    id: int
    model_metadata_id: Optional[int] = None
    model_name_used: Optional[str] = None # Denormalized from model_metadata for convenience
    model_version_used: Optional[str] = None # Denormalized

    task_name: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    input_data_summary_json: Optional[Dict[str, Any]] = None
    output_data_summary_json: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    status: AITaskStatusEnum
    error_message: Optional[str] = None
    processing_duration_ms: Optional[int] = None
    user_triggering_task_id: Optional[int] = None
    # user_triggering_username: Optional[str] = None # Added by service
    correlation_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @validator('input_data_summary_json', 'output_data_summary_json', pre=True)
    def parse_log_json_fields(cls, value):
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: return {"error": "Invalid JSON in log data"}
        return value

    class Config:
        orm_mode = True
        use_enum_values = True


# --- AIAgentConfig Schemas ---
class AIAgentConfigBase(BaseModel):
    agent_name: str = Field(..., max_length=100)
    role_description: str
    goal_description: str
    backstory: Optional[str] = None
    llm_config_json: Optional[LLMConfigSchema] = None # Use helper schema
    tools_config_json: Optional[List[ToolConfigSchema]] = None # Use helper schema
    is_active: bool = True
    version: str = Field("1.0", max_length=20)

    @validator('llm_config_json', 'tools_config_json', pre=True)
    def parse_agent_json_fields(cls, value, field):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if field.name == 'llm_config_json' and parsed is not None:
                    return LLMConfigSchema.parse_obj(parsed)
                if field.name == 'tools_config_json' and isinstance(parsed, list) and parsed is not None:
                    return [ToolConfigSchema.parse_obj(item) for item in parsed]
                return parsed # Should not happen if types match
            except json.JSONDecodeError: raise ValueError(f"Invalid JSON for {field.name}")
        # If already parsed Pydantic model or list of them
        if field.name == 'llm_config_json' and isinstance(value, dict) and value is not None:
            return LLMConfigSchema.parse_obj(value)
        if field.name == 'tools_config_json' and isinstance(value, list) and value is not None:
            return [ToolConfigSchema.parse_obj(v) if isinstance(v, dict) else v for v in value]
        return value


class AIAgentConfigCreate(AIAgentConfigBase):
    pass

class AIAgentConfigUpdate(BaseModel): # Partial updates
    role_description: Optional[str] = None
    goal_description: Optional[str] = None
    backstory: Optional[str] = None
    llm_config_json: Optional[LLMConfigSchema] = None
    tools_config_json: Optional[List[ToolConfigSchema]] = None
    is_active: Optional[bool] = None
    version: Optional[str] = Field(None, max_length=20)

    @validator('llm_config_json', 'tools_config_json', pre=True)
    def parse_update_agent_json_fields(cls, value, field): # Duplicate for update
        if value is None: return None
        # Similar parsing logic as in AIAgentConfigBase
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if field.name == 'llm_config_json' and parsed is not None:
                    return LLMConfigSchema.parse_obj(parsed)
                if field.name == 'tools_config_json' and isinstance(parsed, list) and parsed is not None:
                    return [ToolConfigSchema.parse_obj(item) for item in parsed]
                return parsed
            except json.JSONDecodeError: raise ValueError(f"Invalid JSON for {field.name}")
        if field.name == 'llm_config_json' and isinstance(value, dict) and value is not None:
            return LLMConfigSchema.parse_obj(value)
        if field.name == 'tools_config_json' and isinstance(value, list) and value is not None:
            return [ToolConfigSchema.parse_obj(v) if isinstance(v, dict) else v for v in value]
        return value


class AIAgentConfigResponse(AIAgentConfigBase):
    id: int
    created_by_user_id: Optional[int] = None
    # created_by_username: Optional[str] = None # Added by service
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- AutomatedRule Schemas ---
class AutomatedRuleBase(BaseModel):
    rule_name: str = Field(..., max_length=150)
    description: Optional[str] = None
    module_area: str = Field(..., max_length=100, description="e.g., LOAN_APPROVAL, FRAUD_DETECTION")
    conditions_json: List[RuleConditionSchema] # Use helper schema
    actions_json: List[RuleActionSchema]    # Use helper schema
    priority: int = Field(100, ge=0)
    status: str = Field("ACTIVE", max_length=20) # Could be an enum
    version: str = Field("1.0", max_length=20)

    @validator('conditions_json', 'actions_json', pre=True)
    def parse_rule_json_fields(cls, value, field):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if not isinstance(parsed, list): raise ValueError(f"{field.name} must be a list")
                helper_schema = RuleConditionSchema if field.name == 'conditions_json' else RuleActionSchema
                return [helper_schema.parse_obj(item) for item in parsed]
            except json.JSONDecodeError: raise ValueError(f"Invalid JSON for {field.name}")
        if isinstance(value, list): # Already a list, validate items
            helper_schema = RuleConditionSchema if field.name == 'conditions_json' else RuleActionSchema
            return [helper_schema.parse_obj(v) if isinstance(v, dict) else v for v in value]
        return value


class AutomatedRuleCreate(AutomatedRuleBase):
    ai_model_suggestion_id: Optional[int] = None
    ai_confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)

class AutomatedRuleUpdate(BaseModel): # Partial updates
    description: Optional[str] = None
    module_area: Optional[str] = Field(None, max_length=100)
    conditions_json: Optional[List[RuleConditionSchema]] = None
    actions_json: Optional[List[RuleActionSchema]] = None
    priority: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=20)
    version: Optional[str] = Field(None, max_length=20)
    ai_model_suggestion_id: Optional[int] = None
    ai_confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    @validator('conditions_json', 'actions_json', pre=True)
    def parse_update_rule_json_fields(cls, value, field): # Duplicate for update
        # Similar parsing logic as in AutomatedRuleBase
        if value is None: return None
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if not isinstance(parsed, list): raise ValueError(f"{field.name} must be a list")
                helper_schema = RuleConditionSchema if field.name == 'conditions_json' else RuleActionSchema
                return [helper_schema.parse_obj(item) for item in parsed]
            except json.JSONDecodeError: raise ValueError(f"Invalid JSON for {field.name}")
        if isinstance(value, list):
            helper_schema = RuleConditionSchema if field.name == 'conditions_json' else RuleActionSchema
            return [helper_schema.parse_obj(v) if isinstance(v, dict) else v for v in value]
        return value


class AutomatedRuleResponse(AutomatedRuleBase):
    id: int
    ai_model_suggestion_id: Optional[int] = None
    ai_confidence_score: Optional[float] = None
    # created_by_user_id: Optional[int] = None
    # created_by_username: Optional[str] = None # Added by service
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- AI Service Request/Response Schemas (Conceptual Examples) ---
class CreditScoreRequestData(BaseModel): # Example input for credit scoring
    # Fields from loan application, customer data, transaction history etc.
    customer_id: int
    loan_application_id: Optional[int] = None
    bvn: Optional[str] = Field(None, min_length=11, max_length=11)
    age: Optional[int] = Field(None, ge=18)
    income_monthly: Optional[float] = Field(None, ge=0)
    existing_loan_count: Optional[int] = Field(None, ge=0)
    # ... many more features

class CreditScoreResponseData(BaseModel): # Example output
    request_reference_id: str # Link back to the request or AITaskLog ID
    score: int = Field(..., ge=300, le=850)
    risk_level: str # e.g., LOW, MEDIUM, HIGH, VERY_HIGH
    reason_codes: Optional[List[str]] = None # Codes explaining the score
    model_name_used: str
    model_version_used: str
    confidence: Optional[float] = None

class FraudDetectionRequestData(BaseModel):
    transaction_id: str # The ID of the transaction to check
    # Relevant transaction details: amount, currency, merchant, location, customer_id, card_details (tokenized)
    # customer_behavioral_features_json: Optional[Dict[str, Any]] = None
    # device_info_json: Optional[Dict[str, Any]] = None

class FraudDetectionResponseData(BaseModel):
    request_reference_id: str
    is_fraud_suspected: bool
    fraud_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    rules_triggered_json: Optional[List[str]] = None # If rule-based component involved
    model_name_used: str
    model_version_used: str

class TextProcessingRequest(BaseModel):
    text_content: str
    task_type: str = Field("SUMMARIZE", description="e.g., SUMMARIZE, GENERATE_DRAFT_EMAIL, EXTRACT_ENTITIES")
    # Additional params based on task_type
    max_summary_length: Optional[int] = Field(None, description="For summarization")
    email_prompt_details: Optional[Dict[str, Any]] = Field(None, description="For email drafting")

class TextProcessingResponse(BaseModel):
    request_reference_id: str
    processed_text: str
    # Optional: entities_extracted, sentiment, etc.
    model_name_used: str


# --- Paginated Responses ---
class PaginatedAIModelMetadataResponse(BaseModel):
    items: List[AIModelMetadataResponse]
    total: int
    page: int
    size: int

class PaginatedAITaskLogResponse(BaseModel):
    items: List[AITaskLogResponse]
    total: int
    page: int
    size: int

class PaginatedAIAgentConfigResponse(BaseModel):
    items: List[AIAgentConfigResponse]
    total: int
    page: int
    size: int

class PaginatedAutomatedRuleResponse(BaseModel):
    items: List[AutomatedRuleResponse]
    total: int
    page: int
    size: int
