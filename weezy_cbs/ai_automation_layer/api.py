# API Endpoints for AI & Automation Layer
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_admin_user, get_current_active_authorized_system_or_user

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_admin_user_placeholder(): return {"id": "admin_ai", "role": "admin"}
get_current_active_admin_user = get_current_active_admin_user_placeholder
def get_current_active_authorized_system_or_user_placeholder(): return {"id": "system_or_user_ai", "role": "system"} # Or specific role
get_current_active_authorized_system_or_user = get_current_active_authorized_system_or_user_placeholder


router = APIRouter(
    prefix="/ai-automation",
    tags=["AI & Automation Layer"],
    responses={404: {"description": "Not found"}},
)

# --- AI Model Configuration Endpoints (Admin/MLOps) ---
@router.post("/models/configs", response_model=schemas.AIModelConfigResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_ai_model_configuration( # Upsert logic might be in service
    config_in: schemas.AIModelConfigCreateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Configure a new AI model or a new version of an existing model. (Admin/MLOps operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        # Service might handle upsert or versioning logic
        return services.create_ai_model_config(db, config_in)
    except ValueError as e: # e.g. if model_code + version combo exists
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to configure AI model: {str(e)}")

@router.get("/models/configs/active/{model_type}", response_model=schemas.AIModelConfigResponse)
def get_active_configuration_for_model_type(
    model_type: models.AIModelTypeEnum,
    db: Session = Depends(get_db)
    # Auth: Any internal service/user needing to know which model to call
):
    """Get the currently active serving configuration for a specific AI model type."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    config = services.get_active_ai_model_config(db, model_type)
    if not config:
        raise HTTPException(status_code=404, detail=f"No active model configuration found for type {model_type.value}")
    return config

# --- AI Service Invocation Endpoints (Called by other CBS modules or authorized systems) ---
# These endpoints expose the AI capabilities.

@router.post("/predict/credit-score", response_model=schemas.CreditScoringResponse)
def predict_credit_score(
    scoring_request: schemas.CreditScoringRequest,
    db: Session = Depends(get_db)
    # auth: dict = Depends(get_current_active_authorized_system_or_user) # e.g. Loan module service principal
):
    """
    Get a credit score for a loan application or customer.
    (Typically called by Loan Management Module)
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.get_credit_score(db, scoring_request)
    except services.ConfigurationException as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except services.AIModelExecutionException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Credit scoring failed: {str(e)}")

@router.post("/predict/transaction-fraud", response_model=schemas.TransactionFraudCheckResponse)
def predict_transaction_fraud(
    fraud_check_request: schemas.TransactionFraudCheckRequest,
    db: Session = Depends(get_db)
    # auth: dict = Depends(get_current_active_authorized_system_or_user) # e.g. Transaction Mgt service
):
    """
    Check a transaction for potential fraud using ML models and/or rules.
    (Typically called by Transaction Management Module in real-time or near real-time)
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.check_transaction_for_fraud(db, fraud_check_request)
    except services.ConfigurationException as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except services.AIModelExecutionException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Fraud check failed: {str(e)}")

@router.post("/llm/execute-task", response_model=schemas.LLMTaskResponse)
def execute_llm_generic_task(
    task_request: schemas.LLMTaskRequest,
    db: Session = Depends(get_db)
    # auth: dict = Depends(get_current_active_authorized_system_or_user) # e.g. CRM, Reporting module
):
    """
    Execute a generic task using a configured Large Language Model (LLM).
    Tasks could include summarization, draft generation, data extraction, NLU for chatbots.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.execute_llm_task(db, task_request)
    except ValueError as e: # For unsupported task type
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.ConfigurationException as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except services.AIModelExecutionException as e: # If LLM API call fails
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LLM task execution failed: {str(e)}")


# --- Fraud Rule Management Endpoints (Admin/Fraud Analyst) ---
@router.post("/fraud-rules", response_model=schemas.FraudDetectionRuleResponse, status_code=status.HTTP_201_CREATED)
def create_new_fraud_detection_rule(
    rule_in: schemas.FraudDetectionRuleCreateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user) # Or fraud analyst role
):
    """Create a new rule for the fraud detection engine. (Admin/Fraud Analyst operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.create_fraud_detection_rule(db, rule_in)
    except ValueError as e: # If rule code exists
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

# TODO: Add GET, PUT, DELETE for /fraud-rules/{rule_code_or_id}

# --- Fraud Alert Management Endpoints (Fraud Analyst) ---
@router.get("/fraud-alerts", response_model=schemas.PaginatedFraudAlertLogResponse)
def list_fraud_alerts(
    status: Optional[str] = Query(None, description="Filter by status (e.g. OPEN, INVESTIGATING)"),
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
    # auth: dict = Depends(get_current_fraud_analyst_user)
):
    """List fraud alerts for review and action. (Fraud Analyst operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    query = db.query(models.FraudAlertLog)
    if status:
        query = query.filter(models.FraudAlertLog.status == status.upper())

    total = query.count() # Simplified count
    items = query.order_by(models.FraudAlertLog.alert_timestamp.desc()).offset(skip).limit(limit).all()
    return schemas.PaginatedFraudAlertLogResponse(items=items, total=total, page=(skip//limit)+1, size=len(items))

@router.patch("/fraud-alerts/{alert_id}/status", response_model=schemas.FraudAlertLogResponse)
def update_fraud_alert_status_and_notes(
    alert_id: int,
    update_request: schemas.FraudAlertStatusUpdateRequest,
    db: Session = Depends(get_db)
    # auth: dict = Depends(get_current_fraud_analyst_user)
):
    """Update status, assignment, or notes for a fraud alert. (Fraud Analyst operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # fraud_analyst_id = auth.get("id")
    # updated_alert = services.update_fraud_alert(db, alert_id, update_request, fraud_analyst_id)
    # if not updated_alert:
    #     raise HTTPException(status_code=404, detail="Fraud alert not found.")
    # return updated_alert
    # Mock update:
    alert = db.query(models.FraudAlertLog).filter(models.FraudAlertLog.id == alert_id).first()
    if not alert: raise HTTPException(status_code=404, detail="Fraud alert not found.")
    alert.status = update_request.new_status
    # alert.analyst_notes = (alert.analyst_notes or "") + f"\n{update_request.analyst_notes or ''}"
    db.commit(); db.refresh(alert)
    return alert

# --- Prediction Log Viewing Endpoint (Admin/MLOps for monitoring) ---
@router.get("/prediction-logs", response_model=schemas.PaginatedAIPredictionLogResponse)
def get_ai_prediction_logs(
    model_code: Optional[str] = Query(None),
    # entity_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """View logs of predictions made by AI models. (Admin/MLOps operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    query = db.query(models.AIPredictionLog)
    if model_code:
        query = query.filter(models.AIPredictionLog.model_code_used == model_code)
    # if entity_id:
    #     query = query.filter(models.AIPredictionLog.entity_id == entity_id)

    total = query.count() # Simplified count
    items = query.order_by(models.AIPredictionLog.prediction_timestamp.desc()).offset(skip).limit(limit).all()
    return schemas.PaginatedAIPredictionLogResponse(items=items, total=total, page=(skip//limit)+1, size=len(items))


# This AI/Automation Layer API serves two main purposes:
# 1. Admin/MLOps: Configuring models, rules, and monitoring predictions/alerts.
# 2. System-to-System: Exposing AI capabilities (scoring, fraud check, LLM tasks) to be consumed by other CBS modules.
#    These system-to-system endpoints would typically require service principal authentication, not end-user auth.

# Import func for count queries if used
from sqlalchemy import func
