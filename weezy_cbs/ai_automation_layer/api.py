from typing import List, Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from sqlalchemy.orm import Session

from weezy_cbs.database import get_db
from . import schemas, services, models
from .services import (
    ai_model_metadata_service, ai_task_log_service, ai_agent_config_service,
    automated_rule_service, credit_scoring_ai_service, fraud_detection_ai_service
    # Conceptual: llm_service, document_parsing_service, etc.
)
# Assuming an authentication dependency from core_infrastructure_config_engine
from weezy_cbs.core_infrastructure_config_engine.api import get_current_active_superuser
from weezy_cbs.core_infrastructure_config_engine.models import User as CoreUser # For type hint

# Main router for AI & Automation Layer
ai_api_router = APIRouter(
    prefix="/ai-automation",
    tags=["AI & Automation Layer"],
)

# --- AIModelMetadata Admin Endpoints ---
admin_models_router = APIRouter(
    prefix="/admin/models",
    tags=["Admin: AI Model Metadata"],
    dependencies=[Depends(get_current_active_superuser)]
)

@admin_models_router.post("/", response_model=schemas.AIModelMetadataResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_model_metadata_endpoint(
    metadata_in: schemas.AIModelMetadataCreate,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    return ai_model_metadata_service.create_model_metadata(
        db, metadata_in=metadata_in, user_id=current_user.id, username=current_user.username
    )

@admin_models_router.get("/", response_model=schemas.PaginatedAIModelMetadataResponse)
async def list_ai_model_metadata_endpoint(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    metadata_list, total = ai_model_metadata_service.get_all_model_metadata(db, skip=skip, limit=limit)
    return {"items": metadata_list, "total": total, "page": (skip // limit) + 1, "size": limit}

@admin_models_router.get("/{model_id}", response_model=schemas.AIModelMetadataResponse)
async def read_ai_model_metadata_endpoint(model_id: int, db: Session = Depends(get_db)):
    db_metadata = ai_model_metadata_service.get_model_metadata_by_id(db, model_id)
    if not db_metadata:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI Model Metadata not found")
    return db_metadata

@admin_models_router.get("/name/{model_name}", response_model=schemas.AIModelMetadataResponse, summary="Get latest active version by name, or specific version")
async def read_ai_model_metadata_by_name_endpoint(model_name: str, version: Optional[str] = None, db: Session = Depends(get_db)):
    db_metadata = ai_model_metadata_service.get_model_metadata_by_name_version(db, model_name=model_name, version=version)
    if not db_metadata:
        v_info = f"version {version}" if version else "latest active version"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"AI Model Metadata for '{model_name}' ({v_info}) not found.")
    return db_metadata


@admin_models_router.put("/{model_id}", response_model=schemas.AIModelMetadataResponse)
async def update_ai_model_metadata_endpoint(
    model_id: int,
    metadata_upd: schemas.AIModelMetadataUpdate,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    updated_metadata = ai_model_metadata_service.update_model_metadata(
        db, model_id=model_id, metadata_upd=metadata_upd, username=current_user.username
    )
    if not updated_metadata:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI Model Metadata not found")
    return updated_metadata

@admin_models_router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_model_metadata_endpoint(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    if not ai_model_metadata_service.delete_model_metadata(db, model_id=model_id, username=current_user.username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI Model Metadata not found")
    return None

# --- AITaskLog Admin/Monitoring Endpoints ---
admin_tasks_router = APIRouter(
    prefix="/admin/tasks",
    tags=["Admin: AI Task Logs"],
    dependencies=[Depends(get_current_active_superuser)]
)

@admin_tasks_router.get("/", response_model=schemas.PaginatedAITaskLogResponse)
async def list_ai_task_logs_endpoint(
    model_id: Optional[int] = None,
    task_name: Optional[str] = None,
    status: Optional[models.AITaskStatusEnum] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    skip: int = 0, limit: int = 20,
    db: Session = Depends(get_db)
):
    logs, total = ai_task_log_service.get_task_logs(
        db, model_id=model_id, task_name=task_name, status=status,
        related_entity_type=related_entity_type, related_entity_id=related_entity_id,
        skip=skip, limit=limit
    )
    # Augment with model name/version if not directly in response schema via ORM
    augmented_logs = []
    for log_orm in logs:
        log_data = schemas.AITaskLogResponse.from_orm(log_orm).dict()
        if log_orm.model_metadata:
            log_data["model_name_used"] = log_orm.model_metadata.model_name
            log_data["model_version_used"] = log_orm.model_metadata.version
        augmented_logs.append(log_data)

    return {"items": augmented_logs, "total": total, "page": (skip // limit) + 1, "size": limit}


@admin_tasks_router.get("/{task_log_id}", response_model=schemas.AITaskLogResponse)
async def read_ai_task_log_endpoint(task_log_id: int, db: Session = Depends(get_db)):
    db_log = ai_task_log_service.get_task_log_by_id(db, task_log_id)
    if not db_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI Task Log not found")

    log_data = schemas.AITaskLogResponse.from_orm(db_log).dict()
    if db_log.model_metadata:
        log_data["model_name_used"] = db_log.model_metadata.model_name
        log_data["model_version_used"] = db_log.model_metadata.version
    return log_data


# --- AI Service Endpoints (Internal / Service-to-Service) ---
# These endpoints expose AI capabilities to other internal modules.
# They are protected by staff auth for now; in microservices, could be service-to-service auth.
service_ai_router = APIRouter(
    prefix="/service",
    tags=["AI Services (Internal)"],
    dependencies=[Depends(get_current_active_superuser)] # Or a different auth for service calls
)

@service_ai_router.post("/credit-score", response_model=schemas.CreditScoreResponseData)
async def invoke_credit_scoring_endpoint(
    request_data: schemas.CreditScoreRequestData,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser) # User initiating the process that needs scoring
):
    # In a real app, background_tasks might be used if scoring is slow.
    # For now, direct call.
    return await credit_scoring_ai_service.calculate_credit_score(
        db, request_data=request_data, user_id_triggering=current_user.id
    )

@service_ai_router.post("/detect-fraud", response_model=schemas.FraudDetectionResponseData)
async def invoke_fraud_detection_endpoint(
    request_data: schemas.FraudDetectionRequestData,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser) # System user if automated check
):
    return await fraud_detection_ai_service.check_transaction_for_fraud(
        db, request_data=request_data, user_id_triggering=current_user.id
    )

@service_ai_router.post("/process-text", response_model=schemas.TextProcessingResponse)
async def invoke_text_processing_endpoint(
    request_data: schemas.TextProcessingRequest,
    # db: Session = Depends(get_db), # LLMService might not need DB directly for mock
    # current_user: CoreUser = Depends(get_current_active_superuser)
):
    # Conceptual: Instantiate LLMService if it's structured like others
    # For now, direct mock call:
    # Placeholder for LLMService call
    # result = await llm_service.process_text_task(db, request_data, user_id_triggering=current_user.id)
    # return result

    # Mock response:
    if request_data.task_type.upper() == "SUMMARIZE":
        processed_text = f"Summary of '{request_data.text_content[:30]}...': This is a mock summary."
    elif request_data.task_type.upper() == "GENERATE_DRAFT_EMAIL":
        processed_text = f"Subject: Regarding your inquiry\n\nDear Customer,\n\nThis is a mock draft email based on '{request_data.text_content[:30]}...'.\n\nSincerely,\nWeezy CBS"
    else:
        processed_text = f"Mock processed text for task '{request_data.task_type}' on input '{request_data.text_content[:30]}...'"

    return schemas.TextProcessingResponse(
        request_reference_id="mock_ref_" + request_data.text_content[:10].replace(" ", "_"),
        processed_text=processed_text,
        model_name_used="MOCK_LLM_V1"
    )

# --- AIAgentConfig & AutomatedRule Admin Endpoints (Conceptual Stubs) ---
# These would follow the same pattern as AIModelMetadata if fully implemented.
admin_agents_router = APIRouter(prefix="/admin/agents", tags=["Admin: AI Agent Configurations"], dependencies=[Depends(get_current_active_superuser)])
admin_rules_router = APIRouter(prefix="/admin/rules", tags=["Admin: Automated Rules"], dependencies=[Depends(get_current_active_superuser)])

# @admin_agents_router.post("/", response_model=schemas.AIAgentConfigResponse)
# async def create_ai_agent_config(...): pass
# ... other CRUD for AIAgentConfig ...

# @admin_rules_router.post("/", response_model=schemas.AutomatedRuleResponse)
# async def create_automated_rule(...): pass
# ... other CRUD for AutomatedRule ...


# Include all sub-routers into the main AI API router
ai_api_router.include_router(admin_models_router)
ai_api_router.include_router(admin_tasks_router)
ai_api_router.include_router(service_ai_router)
ai_api_router.include_router(admin_agents_router) # Add if implemented
ai_api_router.include_router(admin_rules_router)   # Add if implemented


# The main app would then do:
# from weezy_cbs.ai_automation_layer.api import ai_api_router
# app.include_router(ai_api_router)
