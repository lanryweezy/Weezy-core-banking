# Service layer for AI & Automation Layer
from sqlalchemy.orm import Session
import requests # For calling external AI model APIs
import json
from datetime import datetime
import uuid
import random # For mock responses

from . import models, schemas
# from weezy_cbs.shared import exceptions, security_utils
# from weezy_cbs.loan_management_module.services import get_loan_application_data_for_scoring
# from weezy_cbs.transaction_management.services import get_transaction_details_for_fraud_check

class AIModelExecutionException(Exception): pass
class ConfigurationException(Exception): pass

# --- AI Model Config Management (Admin/MLOps) ---
def create_ai_model_config(db: Session, config_in: schemas.AIModelConfigCreateRequest) -> models.AIModelConfig:
    existing = db.query(models.AIModelConfig).filter(
        models.AIModelConfig.model_code == config_in.model_code,
        models.AIModelConfig.version == config_in.version
    ).first()
    if existing:
        raise ValueError(f"AI Model config for {config_in.model_code} version {config_in.version} already exists.")

    # Encrypt model_api_key if provided (conceptual)
    # encrypted_api_key = None
    # if config_in.model_api_key_plain:
    #     encrypted_api_key = security_utils.encrypt(config_in.model_api_key_plain)

    db_config = models.AIModelConfig(
        **config_in.dict(exclude={"model_api_key_plain"}), # Exclude plain key
        # model_api_key_encrypted=encrypted_api_key
    )
    # if config_in.model_parameters_json:
    #     db_config.model_parameters_json = json.dumps(config_in.model_parameters_json)
    # if config_in.performance_metrics_json:
    #     db_config.performance_metrics_json = json.dumps(config_in.performance_metrics_json)

    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

def get_active_ai_model_config(db: Session, model_type: models.AIModelTypeEnum) -> Optional[models.AIModelConfig]:
    # Gets the latest active version for a given model type (simplified: assumes one active per type)
    return db.query(models.AIModelConfig).filter(
        models.AIModelConfig.model_type == model_type,
        models.AIModelConfig.is_active_serving == True
    ).order_by(models.AIModelConfig.version.desc()).first() # Or by created_at/updated_at

# --- Generic Prediction Logging ---
def _log_ai_prediction(
    db: Session, model_code: str, model_version: str, request_ref: str,
    # entity_type: Optional[str], entity_id: Optional[str],
    # input_features: Optional[dict],
    raw_output: Optional[dict], processed_value: Optional[str], score: Optional[float]
) -> models.AIPredictionLog:

    log_entry = models.AIPredictionLog(
        model_code_used=model_code,
        model_version_used=model_version,
        request_reference_id=request_ref,
        # entity_type=entity_type,
        # entity_id=entity_id,
        # input_features_json=json.dumps(input_features) if input_features else None,
        prediction_raw_output_json=json.dumps(raw_output) if raw_output else None,
        prediction_processed_value=processed_value,
        prediction_score_or_confidence=score
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

# --- Credit Scoring Service ---
def get_credit_score(db: Session, scoring_request: schemas.CreditScoringRequest) -> schemas.CreditScoringResponse:
    model_config = get_active_ai_model_config(db, models.AIModelTypeEnum.CREDIT_SCORING_ML)
    if not model_config:
        raise ConfigurationException("No active Credit Scoring model configured.")

    # In a real scenario, fetch/prepare features based on scoring_request.application_id
    # features_for_model = get_loan_application_data_for_scoring(db, scoring_request.application_id)
    # if not features_for_model:
    #     raise AIModelExecutionException("Could not retrieve necessary features for credit scoring.")

    # This would then call the actual model (e.g. deployed API endpoint or local model)
    # if model_config.model_api_endpoint:
    #     response = requests.post(model_config.model_api_endpoint, json={"features": features_for_model})
    #     response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
    #     prediction_data = response.json()
    # else: # Placeholder for local model call
    #     # prediction_data = local_credit_model.predict(features_for_model)
    #     pass

    # Mocked prediction:
    prediction_ref = f"CSPRED_{scoring_request.application_id}_{uuid.uuid4().hex[:6]}"
    mock_score = random.randint(300, 850)
    mock_risk_rating = "MEDIUM"
    if mock_score > 700: mock_risk_rating = "LOW"
    elif mock_score < 500: mock_risk_rating = "HIGH"

    mock_raw_output = {"score": mock_score, "probabilities": {"default": 1 - (mock_score-300)/550, "no_default": (mock_score-300)/550}}

    log_entry = _log_ai_prediction(
        db, model_config.model_code, model_config.version, prediction_ref,
        # entity_type="LOAN_APPLICATION", entity_id=scoring_request.application_id,
        # input_features=features_for_model, # Be careful with PII
        raw_output=mock_raw_output,
        processed_value=f"SCORE_{mock_score}",
        score=float(mock_score)
    )

    return schemas.CreditScoringResponse(
        application_id=scoring_request.application_id,
        credit_score=mock_score,
        risk_rating=mock_risk_rating,
        # prediction_log_id=log_entry.id
    )

# --- Transaction Fraud Detection Service ---
def check_transaction_for_fraud(db: Session, fraud_check_request: schemas.TransactionFraudCheckRequest) -> schemas.TransactionFraudCheckResponse:
    model_config = get_active_ai_model_config(db, models.AIModelTypeEnum.FRAUD_DETECTION_ML)
    # Fallback to anomaly detection if specific fraud model not active/found
    if not model_config:
        model_config = get_active_ai_model_config(db, models.AIModelTypeEnum.TRANSACTION_ANOMALY_ML)
    if not model_config:
        raise ConfigurationException("No active Fraud Detection or Anomaly Detection model configured.")

    # features_for_model = get_transaction_details_for_fraud_check(db, fraud_check_request.transaction_id)
    # ... call model API or local model ...

    prediction_ref = f"FDCHK_{fraud_check_request.transaction_id}_{uuid.uuid4().hex[:6]}"
    mock_fraud_score = random.random() # Score between 0 and 1
    is_suspected = mock_fraud_score > 0.8 # Example threshold

    mock_raw_output = {"fraud_probability": mock_fraud_score, "contributing_factors": ["unusual_amount", "new_beneficiary"]}

    log_entry = _log_ai_prediction(
        db, model_config.model_code, model_config.version, prediction_ref,
        raw_output=mock_raw_output,
        processed_value="SUSPECTED_FRAUD" if is_suspected else "NOT_SUSPECTED",
        score=mock_fraud_score
    )

    if is_suspected:
        # Log to FraudAlertLog
        alert = models.FraudAlertLog(
            source_reference_id=fraud_check_request.transaction_id,
            source_reference_type="TRANSACTION",
            # detection_method=f"ML_{model_config.model_code}",
            # model_prediction_log_id=log_entry.id,
            alert_details=f"Transaction flagged by model {model_config.model_code} with score {mock_fraud_score:.2f}",
            alert_score=mock_fraud_score,
            status="OPEN"
        )
        db.add(alert)
        db.commit()
        # db.refresh(alert) # To get alert.id if needed for response

    return schemas.TransactionFraudCheckResponse(
        transaction_id=fraud_check_request.transaction_id,
        is_fraud_suspected=is_suspected,
        fraud_score=mock_fraud_score,
        reason="High fraud score based on transaction patterns." if is_suspected else "Transaction appears normal.",
        # alert_log_id=alert.id if is_suspected and alert else None
    )

# --- LLM Task Execution Service (Generic) ---
def execute_llm_task(db: Session, task_request: schemas.LLMTaskRequest) -> schemas.LLMTaskResponse:
    model_type_map = {
        "SUMMARIZE_EMAIL": models.AIModelTypeEnum.LLM_EMAIL_AUTOMATION,
        "DRAFT_CUSTOMER_REPLY": models.AIModelTypeEnum.LLM_EMAIL_AUTOMATION, # Or specific CHATBOT_NLU
        "EXTRACT_LOAN_TERMS_FROM_DOC": models.AIModelTypeEnum.LLM_EMAIL_AUTOMATION, # Or specific document processing LLM
        "NLU_CHATBOT_INTENT": models.AIModelTypeEnum.LLM_CHATBOT_NLU,
        "GENERATE_REPORT_SUMMARY": models.AIModelTypeEnum.LLM_REPORT_SUMMARY,
    }
    model_type_to_use = model_type_map.get(task_request.task_type.upper())
    if not model_type_to_use:
        raise ValueError(f"Unsupported LLM task type: {task_request.task_type}")

    model_config = get_active_ai_model_config(db, model_type_to_use)
    if not model_config:
        raise ConfigurationException(f"No active LLM model configured for task type {task_request.task_type}.")

    # Construct prompt based on task_type and input_text/context_data
    # This is where prompt engineering happens.
    # final_prompt = f"Task: {task_request.task_type}\nInput: {task_request.input_text}\nContext: {task_request.context_data}\nOutput Format: {task_request.output_format_preference}\n\nPlease provide the response:"

    # Call LLM (e.g. OpenAI API, local HuggingFace model via API)
    # if model_config.model_api_endpoint:
    #     llm_response = requests.post(model_config.model_api_endpoint, json={"prompt": final_prompt, "max_tokens": 500})
    #     llm_response.raise_for_status()
    #     llm_output_data = llm_response.json() # e.g. {"choices": [{"text": "..."}]}
    #     processed_output = llm_output_data.get("choices")[0].get("text")
    # else:
    #     # Mock local LLM call
    #     processed_output = f"Mock LLM Output for task {task_request.task_type}: Processed '{task_request.input_text[:50]}...'"

    prediction_ref = f"LLMTASK_{task_request.task_type}_{uuid.uuid4().hex[:6]}"
    mock_processed_output = f"Mock LLM Output for task {task_request.task_type}: Processed '{task_request.input_text[:50] if task_request.input_text else 'N/A'}...'"
    mock_raw_output = {"generated_text": mock_processed_output, "model_used": model_config.model_code}

    # Log LLM task
    llm_log = models.LLMTaskLog(
        # model_config_id=model_config.id,
        task_type=task_request.task_type,
        # input_text_preview=task_request.input_text[:200] if task_request.input_text else None,
        # llm_prompt_final=final_prompt,
        llm_response_raw_json=json.dumps(mock_raw_output),
        llm_response_processed_output=mock_processed_output,
        status="COMPLETED"
    )
    db.add(llm_log)
    db.commit()
    # db.refresh(llm_log) # To get llm_log.id

    return schemas.LLMTaskResponse(
        task_type=task_request.task_type,
        processed_output=mock_processed_output,
        # task_log_id=llm_log.id
    )

# --- Fraud Rule Management (Admin) ---
def create_fraud_detection_rule(db: Session, rule_in: schemas.FraudDetectionRuleCreateRequest) -> models.FraudDetectionRule:
    # Similar to AML rule creation
    existing = db.query(models.FraudDetectionRule).filter(models.FraudDetectionRule.rule_code == rule_in.rule_code).first()
    if existing:
        raise ValueError(f"Fraud detection rule code {rule_in.rule_code} already exists.")

    db_rule = models.FraudDetectionRule(
        **rule_in.dict()
        # parameters_json=json.dumps(rule_in.parameters_json) if rule_in.parameters_json else None
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

# Other services:
# - Updating AI model configs (e.g. new version, toggle active status).
# - Managing FraudAlertLog status updates by analysts.
# - Services for OCR, Face Recognition would follow a similar pattern:
#   - Get model config.
#   - Prepare input (e.g. image data).
#   - Call model (API or local).
#   - Log prediction.
#   - Return processed result.

# This AI/Automation Layer acts as an orchestrator for various AI capabilities.
# It needs to be highly configurable and resilient to external model API failures.
# Logging is crucial for audit, debugging, and model retraining/monitoring.
# It will be called by many other modules to embed AI into their workflows.
