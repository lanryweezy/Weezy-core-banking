# Database models for AI & Automation Layer Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLAlchemyEnum, Float, Index
from sqlalchemy.orm import relationship, declarative_base # Correct import
from sqlalchemy.sql import func
import enum

from weezy_cbs.database import Base # Use the shared Base

class AIModelTypeEnum(enum.Enum):
    CREDIT_SCORING_ML = "CREDIT_SCORING_ML"
    FRAUD_DETECTION_ML = "FRAUD_DETECTION_ML"
    TRANSACTION_CLASSIFICATION_ML = "TRANSACTION_CLASSIFICATION_ML"
    CUSTOMER_SEGMENTATION_ML = "CUSTOMER_SEGMENTATION_ML"
    LLM_TEXT_GENERATION = "LLM_TEXT_GENERATION" # For summarization, drafting emails
    LLM_EMBEDDING = "LLM_EMBEDDING" # For RAG or semantic search
    LLM_TASK_AUTOMATION = "LLM_TASK_AUTOMATION" # For email-based task understanding, agent actions
    RECOMMENDATION_ENGINE_ML = "RECOMMENDATION_ENGINE_ML" # Product recommendations
    OCR_DOCUMENT_PARSING = "OCR_DOCUMENT_PARSING"
    FACE_MATCH_BIOMETRIC = "FACE_MATCH_BIOMETRIC"
    OTHER_AI_SERVICE = "OTHER_AI_SERVICE" # For generic external AI services

class AIModelStatusEnum(enum.Enum):
    ACTIVE = "ACTIVE"; INACTIVE = "INACTIVE"; EXPERIMENTAL = "EXPERIMENTAL"
    TRAINING = "TRAINING"; DEPLOYING = "DEPLOYING"; ERROR = "ERROR"; ARCHIVED = "ARCHIVED"

class AITaskStatusEnum(enum.Enum):
    PENDING = "PENDING"; PROCESSING = "PROCESSING"; SUCCESS = "SUCCESS"
    FAILED = "FAILED"; REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"; CANCELLED = "CANCELLED"


class AIModelMetadata(Base):
    __tablename__ = "ai_model_metadata"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(150), unique=True, nullable=False, index=True)
    model_type = Column(SQLAlchemyEnum(AIModelTypeEnum), nullable=False, index=True)
    version = Column(String(20), nullable=False, default="1.0.0")
    description = Column(Text, nullable=True)

    source_type = Column(String(50), nullable=False, comment="e.g., INTERNAL_PATH, EXTERNAL_API_ENDPOINT, HUGGINGFACE_HUB_ID, SERVICE_CLASS_NAME")
    source_identifier = Column(Text, nullable=False, comment="Path, URL, Hub ID, or Python class path")

    input_schema_json = Column(Text, nullable=True, comment="JSON schema of expected input features/structure")
    output_schema_json = Column(Text, nullable=True, comment="JSON schema of model's output structure")

    status = Column(SQLAlchemyEnum(AIModelStatusEnum), default=AIModelStatusEnum.ACTIVE, nullable=False, index=True)
    deployed_at = Column(DateTime(timezone=True), nullable=True) # When this version was made active/deployed
    performance_metrics_json = Column(Text, nullable=True, comment='e.g., {"accuracy": 0.95, "precision": {"class_A": 0.9}}')

    # Ensure User model (core_infra) has: ai_models_created = relationship("AIModelMetadata", foreign_keys="[AIModelMetadata.created_by_user_id]", back_populates="created_by_user")
    created_by_user_id = Column(Integer, ForeignKey("users.id", name="fk_aimodel_createdby"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    task_logs = relationship("AITaskLog", back_populates="model_metadata")
    # created_by_user = relationship("User", foreign_keys=[created_by_user_id]) # If User model is importable


class AITaskLog(Base):
    __tablename__ = "ai_task_logs"
    id = Column(Integer, primary_key=True, index=True)
    model_metadata_id = Column(Integer, ForeignKey("ai_model_metadata.id", name="fk_aitask_aimodel"), nullable=True)

    task_name = Column(String(150), index=True, nullable=False)
    related_entity_type = Column(String(50), nullable=True, index=True)
    related_entity_id = Column(String(50), nullable=True, index=True)

    input_data_summary_json = Column(Text, nullable=True, comment="Summary or reference, not full PII if possible")
    output_data_summary_json = Column(Text, nullable=True, comment="Summary of result or reference")
    confidence_score = Column(Float, nullable=True)

    status = Column(SQLAlchemyEnum(AITaskStatusEnum), default=AITaskStatusEnum.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)

    # Ensure User model (core_infra) has: ai_tasks_triggered = relationship("AITaskLog", foreign_keys="[AITaskLog.user_triggering_task_id]", back_populates="user_triggering_task")
    user_triggering_task_id = Column(Integer, ForeignKey("users.id", name="fk_aitask_triggeredby"), nullable=True)
    correlation_id = Column(String(100), index=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    model_metadata = relationship("AIModelMetadata", back_populates="task_logs")
    # user_triggering_task = relationship("User", foreign_keys=[user_triggering_task_id]) # If User model is importable

    Index('ix_ai_task_logs_related_entity', related_entity_type, related_entity_id)
    Index('ix_ai_task_logs_status_created_at', status, created_at)


class AIAgentConfig(Base):
    __tablename__ = "ai_agent_configs"
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100), unique=True, nullable=False, index=True)
    role_description = Column(Text, nullable=False)
    goal_description = Column(Text, nullable=False)
    backstory = Column(Text, nullable=True)

    llm_config_json = Column(Text, nullable=True, comment='e.g., {"provider": "OPENAI", "model_name": "gpt-4-turbo", "api_key_secret_ref": "..."}')
    tools_config_json = Column(Text, nullable=True, comment='e.g., [{"tool_name": "credit_score_tool", "config": {"model_id": 1}}, ...]')

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    version = Column(String(20), default="1.0", nullable=False)

    # Ensure User model (core_infra) has appropriate relationships if tracking creator
    created_by_user_id = Column(Integer, ForeignKey("users.id", name="fk_aiagent_createdby"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AutomatedRule(Base):
    __tablename__ = "automated_rules"
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(150), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    module_area = Column(String(100), nullable=False, index=True, comment="e.g., LOAN_APPROVAL, FRAUD_DETECTION")

    conditions_json = Column(Text, nullable=False, comment="Rule logic, e.g., JSON Rules Engine format")
    actions_json = Column(Text, nullable=False, comment="Actions if conditions met, e.g., trigger alert, auto-approve")

    ai_model_suggestion_id = Column(Integer, ForeignKey("ai_model_metadata.id", name="fk_rule_aimodel_suggestion"), nullable=True)
    ai_confidence_score = Column(Float, nullable=True)

    priority = Column(Integer, default=100, nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False, index=True) # ACTIVE, INACTIVE, TESTING
    version = Column(String(20), default="1.0", nullable=False)

    # created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    # trigger_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ai_model_suggestion = relationship("AIModelMetadata") # If AIModelMetadata is importable

# Notes on Foreign Keys and Relationships:
# - `users.id` FKs assume a User model in `core_infrastructure_config_engine`.
# - Corresponding `back_populates` would need to be defined in those external models
#   if bi-directional relationships are desired and models are part of a shared SQLAlchemy Base.
# - JSON fields are used for flexible configuration storage. Their internal structure
#   should be validated by Pydantic schemas at the application/service layer.
# - This module's primary role is metadata management and logging for AI operations.
#   The actual AI models/code reside elsewhere or are external services.
# - `AITaskLog.related_entity_id` is a string to accommodate various ID types (int, UUID, etc.)
#   from different modules.
# - `AITaskLog.model_metadata_id` is nullable to allow logging of tasks not tied to a predefined model
#   (e.g., a generic LLM call via a configured agent, or a rule-based automation).
# - `AutomatedRule.ai_model_suggestion_id` links a rule to an AI model that might have suggested or tuned it.
