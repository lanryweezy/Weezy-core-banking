# Database models for AI & Automation Layer
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLAlchemyEnum, ForeignKey, Boolean, Index, Float
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB # If using PostgreSQL, JSONB is good for unstructured data
from sqlalchemy.sql import func

# from weezy_cbs.database import Base
Base = declarative_base() # Local Base for now

import enum

class AIModelTypeEnum(enum.Enum):
    CREDIT_SCORING_ML = "CREDIT_SCORING_ML"
    FRAUD_DETECTION_ML = "FRAUD_DETECTION_ML"
    TRANSACTION_ANOMALY_ML = "TRANSACTION_ANOMALY_ML"
    LLM_EMAIL_AUTOMATION = "LLM_EMAIL_AUTOMATION"
    LLM_CHATBOT_NLU = "LLM_CHATBOT_NLU"
    LLM_REPORT_SUMMARY = "LLM_REPORT_SUMMARY"
    OCR_DOCUMENT_PARSING = "OCR_DOCUMENT_PARSING" # Though OCR might be a more traditional CV model
    FACE_RECOGNITION = "FACE_RECOGNITION"

class AIModelConfig(Base): # Configuration for different AI models used in the system
    __tablename__ = "ai_model_configs"
    id = Column(Integer, primary_key=True, index=True)
    model_code = Column(String, unique=True, nullable=False, index=True) # e.g., "CS_V1_LOGISTICREG", "FD_V2_RANDOMFOREST"
    model_name = Column(String, nullable=False)
    model_type = Column(SQLAlchemyEnum(AIModelTypeEnum), nullable=False)
    version = Column(String, nullable=False, default="1.0")

    # Location of the model (e.g. path to a serialized file, API endpoint of a deployed model)
    # model_source_uri = Column(String, nullable=True)
    # If deployed as a microservice:
    # model_api_endpoint = Column(String, nullable=True)
    # model_api_key_encrypted = Column(String, nullable=True)

    # Parameters used for this model version (e.g. feature list, hyperparameters if relevant to store)
    # model_parameters_json = Column(Text, nullable=True) # Store as JSONB if using PostgreSQL

    # Performance metrics (e.g. from last validation/retraining)
    # performance_metrics_json = Column(Text, nullable=True) # {"accuracy": 0.95, "precision": 0.92, "recall": 0.90, "auc": 0.97}

    is_active_serving = Column(Boolean, default=False, index=True) # Is this model version currently active for predictions?
    # deployment_environment = Column(String, nullable=True) # e.g. "PRODUCTION", "STAGING"

    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (UniqueConstraint('model_code', 'version', name='uq_model_code_version'),)

class AIPredictionLog(Base): # Log of predictions made by AI models
    __tablename__ = "ai_prediction_logs"
    id = Column(Integer, primary_key=True, index=True)
    # model_config_id = Column(Integer, ForeignKey("ai_model_configs.id"), nullable=False, index=True)
    model_code_used = Column(String, nullable=False, index=True)
    model_version_used = Column(String, nullable=False, index=True)

    # Reference to the entity for which prediction was made
    # e.g., loan_application_id, financial_transaction_id, customer_id
    # entity_type = Column(String, index=True)
    # entity_id = Column(String, index=True)
    request_reference_id = Column(String, unique=True, nullable=False, index=True) # Unique ID for this prediction request

    # Input features/data sent to the model (can be large, store sample or hash if needed for privacy/size)
    # input_features_json = Column(Text, nullable=True) # Store as JSONB

    # Prediction output
    prediction_raw_output_json = Column(Text, nullable=True) # Raw output from model (e.g. probabilities)
    prediction_processed_value = Column(String, nullable=True) # e.g. "APPROVED", "REJECTED", "FRAUD", "NOT_FRAUD", "RISK_SCORE_750"
    prediction_score_or_confidence = Column(Float, nullable=True)

    # Was human override/review involved?
    # human_review_status = Column(String, nullable=True) # e.g. "PENDING_REVIEW", "REVIEWED_AGREED", "REVIEWED_OVERRIDDEN"
    # human_reviewer_id = Column(String, nullable=True)
    # human_review_decision = Column(String, nullable=True)
    # human_review_comments = Column(Text, nullable=True)

    prediction_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # model_config = relationship("AIModelConfig")
    __table_args__ = (
        Index("idx_prediction_entity", "entity_type", "entity_id"),
        Index("idx_prediction_model_ts", "model_code_used", "prediction_timestamp"),
    )

class FraudDetectionRule(Base): # For rule-based components complementing ML fraud detection
    __tablename__ = "fraud_detection_rules" # Similar to AMLRule but specific to fraud
    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    # parameters_json = Column(Text) # e.g. {"max_failed_logins_per_hour": 5, "unusual_location_threshold_km": 500}
    severity = Column(String, default="MEDIUM")
    action_to_take = Column(String, default="FLAG_FOR_REVIEW") # BLOCK_TRANSACTION, REQUIRE_STEP_UP_AUTH
    is_active = Column(Boolean, default=True)

class FraudAlertLog(Base): # Log of alerts generated by fraud detection (ML or rule-based)
    __tablename__ = "fraud_alert_logs" # Similar to SuspiciousActivityLog but for fraud
    id = Column(Integer, primary_key=True, index=True)
    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, index=True)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    # session_id = Column(String, ForeignKey("digital_channel_sessions.id"), nullable=True, index=True)

    # Denormalized references
    source_reference_id = Column(String, index=True) # e.g. transaction ID, session ID, customer ID
    source_reference_type = Column(String, index=True) # TRANSACTION, SESSION, CUSTOMER_LOGIN

    # detection_method = Column(String) # "ML_MODEL_X", "RULE_Y"
    # model_prediction_log_id = Column(Integer, ForeignKey("ai_prediction_logs.id"), nullable=True) # If ML triggered
    # fraud_rule_code_triggered = Column(String, ForeignKey("fraud_detection_rules.rule_code"), nullable=True) # If rule triggered

    alert_details = Column(Text) # Why this was flagged
    alert_score = Column(Float, nullable=True) # If applicable

    status = Column(String, default="OPEN") # OPEN, INVESTIGATING, CONFIRMED_FRAUD, FALSE_POSITIVE, RESOLVED
    # assigned_to_analyst_id = Column(String, nullable=True)
    # analyst_notes = Column(Text, nullable=True)
    # resolution_action_taken = Column(Text, nullable=True) # e.g. "Blocked card", "Contacted customer"

    alert_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    resolved_timestamp = Column(DateTime(timezone=True), nullable=True)

# LLM Task Automation Log (e.g. for email summarization, draft replies)
class LLMTaskLog(Base):
    __tablename__ = "llm_task_logs"
    id = Column(Integer, primary_key=True, index=True)
    # model_config_id = Column(Integer, ForeignKey("ai_model_configs.id"), nullable=False, index=True) # Which LLM model/config
    task_type = Column(String, nullable=False, index=True) # e.g. "EMAIL_SUMMARIZATION", "DRAFT_REPLY_GENERATION", "REPORT_NARRATIVE"

    # input_data_reference = Column(String, nullable=True) # e.g. email_id from an email system, report_id
    # input_text_preview = Column(Text, nullable=True) # Snippet of input

    # llm_prompt_used_template_id = Column(String, nullable=True)
    # llm_prompt_final = Column(Text, nullable=True) # Actual prompt sent to LLM

    llm_response_raw_json = Column(Text, nullable=True) # Full response from LLM
    llm_response_processed_output = Column(Text, nullable=True) # Extracted summary, draft, etc.

    status = Column(String, default="COMPLETED") # PENDING, PROCESSING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)

    # human_feedback_rating = Column(Integer, nullable=True) # e.g. 1-5 stars on usefulness
    # human_feedback_comments = Column(Text, nullable=True)

    task_timestamp = Column(DateTime(timezone=True), server_default=func.now())

# This module is highly service-oriented. The models here are primarily for:
# 1. Configuring AI models and their parameters.
# 2. Logging predictions and actions taken by AI systems for audit, monitoring, and retraining.
# 3. Storing rules that complement ML models (e.g., for fraud or AML).
#
# The actual AI/ML models (Python code, serialized model files like .pkl, .h5, ONNX)
# would typically be managed outside the main CBS database, possibly in:
# - A dedicated model registry (e.g., MLflow, SageMaker Model Registry).
# - Deployed as microservices with their own runtimes.
# This module's `AIModelConfig` would then point to these external resources.
#
# Interactions:
# - LoanManagementModule calls CreditScoring service here.
# - TransactionManagement calls FraudDetection service here.
# - CRMSupport might use LLM services for summarizing tickets or drafting replies.
# - ComplianceReporting might use LLM services for summarizing regulatory text or drafting parts of reports.
# - DigitalChannels (Chatbot) uses NLU services here.
# - CustomerIdentity (Onboarding) might use OCR/FaceRecognition services here.
