from typing import List, Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Header, BackgroundTasks
from sqlalchemy.orm import Session
import json # For parsing raw request body if not auto-parsed by FastAPI for certain content types

from weezy_cbs.database import get_db
from . import schemas, services, models
from .services import (
    api_service_config_service, external_service_log_service, webhook_event_log_service
)
# Assuming an authentication dependency from core_infrastructure_config_engine
from weezy_cbs.core_infrastructure_config_engine.api import get_current_active_superuser
from weezy_cbs.core_infrastructure_config_engine.models import User as CoreUser # For type hint

# Main router for Third-Party Integration Admin & Webhooks
integrations_api_router = APIRouter(
    prefix="/integrations",
    tags=["Third-Party Integrations"],
)

# --- APIServiceConfig Admin Endpoints ---
admin_configs_router = APIRouter(
    prefix="/admin/service-configs",
    tags=["Admin: API Service Configurations"],
    dependencies=[Depends(get_current_active_superuser)]
)

@admin_configs_router.post("/", response_model=schemas.APIServiceConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_api_service_config_endpoint(
    config_in: schemas.APIServiceConfigCreate,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    return api_service_config_service.create_config(
        db, config_in=config_in, user_id=current_user.id, username=current_user.username
    )

@admin_configs_router.get("/", response_model=schemas.PaginatedAPIServiceConfigResponse)
async def list_api_service_configs_endpoint(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    configs, total = api_service_config_service.get_all_configs(db, skip=skip, limit=limit)
    # Note: APIServiceConfigResponse schema has credentials_config_json flagged for masking.
    # Actual masking logic would apply here if not done by Pydantic model itself based on user role.
    return {"items": configs, "total": total, "page": (skip // limit) + 1, "size": limit}

@admin_configs_router.get("/{config_id}", response_model=schemas.APIServiceConfigResponse)
async def read_api_service_config_endpoint(config_id: int, db: Session = Depends(get_db)):
    db_config = api_service_config_service.get_config_by_id(db, config_id)
    if not db_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Service Configuration not found")
    # Masking note applies here too.
    return db_config

@admin_configs_router.put("/{config_id}", response_model=schemas.APIServiceConfigResponse)
async def update_api_service_config_endpoint(
    config_id: int,
    config_upd: schemas.APIServiceConfigUpdate,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    updated_config = api_service_config_service.update_config(
        db, config_id=config_id, config_upd=config_upd, username=current_user.username
    )
    if not updated_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Service Configuration not found")
    return updated_config

@admin_configs_router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_service_config_endpoint(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    if not api_service_config_service.delete_config(db, config_id=config_id, username=current_user.username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Service Configuration not found")
    return None

# --- ExternalServiceLog Admin Endpoints ---
admin_ext_logs_router = APIRouter(
    prefix="/admin/external-service-logs",
    tags=["Admin: External Service Logs (Outgoing)"],
    dependencies=[Depends(get_current_active_superuser)]
)

@admin_ext_logs_router.get("/", response_model=schemas.PaginatedExternalServiceLogResponse)
async def list_external_service_logs_endpoint(
    service_name: Optional[str] = None,
    correlation_id: Optional[str] = None,
    is_success: Optional[bool] = None,
    skip: int = 0, limit: int = 20,
    db: Session = Depends(get_db)
):
    logs, total = external_service_log_service.get_logs(
        db, service_name=service_name, correlation_id=correlation_id, is_success=is_success, skip=skip, limit=limit
    )
    # Note: ExternalServiceLogResponse schema has payloads flagged for masking.
    # Actual masking logic would apply here before returning.
    return {"items": logs, "total": total, "page": (skip // limit) + 1, "size": limit}

@admin_ext_logs_router.get("/{log_id}", response_model=schemas.ExternalServiceLogResponse)
async def read_external_service_log_endpoint(log_id: int, db: Session = Depends(get_db)):
    db_log = external_service_log_service.get_log_by_id(db, log_id)
    if not db_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="External Service Log not found")
    # Masking note applies here too.
    return db_log


# --- Webhook Receiver Endpoint ---
webhooks_receiver_router = APIRouter(prefix="/webhooks", tags=["Webhook Receivers"])

async def process_webhook_event_background(log_id: int, db_session_creator: Any):
    """
    Conceptual background task to process a webhook event.
    It needs its own DB session.
    """
    db: Session = next(db_session_creator()) # Create a new session for this task
    try:
        webhook_log = webhook_event_log_service.get_webhook_log_by_id(db, log_id)
        if not webhook_log or webhook_log.processing_status != models.WebhookProcessingStatusEnum.PENDING:
            print(f"Webhook log {log_id} not found or not pending, skipping background processing.")
            return

        webhook_event_log_service.update_webhook_log_processing(db, log_id, models.WebhookProcessingStatusEnum.PROCESSING)

        # Simulate processing based on source_service_name and event_type
        print(f"BACKGROUND PROCESSING Webhook ID: {log_id}, Service: {webhook_log.source_service_name}, Event: {webhook_log.event_type}")
        # Example:
        # if webhook_log.source_service_name == "PAYSTACK_PAYMENTS":
        #     if webhook_log.event_type == "charge.success":
        #         # Call payment_service.handle_paystack_charge_success(json.loads(webhook_log.raw_payload))
        #         pass
        #     # ... other Paystack events
        # elif webhook_log.source_service_name == "NIBSS_NIP":
        #     # Call transaction_service.handle_nip_notification(json.loads(webhook_log.raw_payload))
        #     pass

        # Simulate some work
        await asyncio.sleep(2) # Requires `import asyncio`

        # Update status after processing
        webhook_event_log_service.update_webhook_log_processing(
            db, log_id, models.WebhookProcessingStatusEnum.PROCESSED_SUCCESS,
            notes="Processed successfully in background.",
            related_ref_id=webhook_log.related_internal_reference_id # Preserve or update
        )
        print(f"BACKGROUND PROCESSING COMPLETED for Webhook ID: {log_id}")

    except Exception as e:
        print(f"ERROR in background processing webhook {log_id}: {str(e)}")
        webhook_event_log_service.update_webhook_log_processing(
            db, log_id, models.WebhookProcessingStatusEnum.ERROR_PROCESSING,
            notes=f"Error during background processing: {str(e)}"
        )
    finally:
        db.close()


@webhooks_receiver_router.post("/{source_service_name}", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook_endpoint(
    source_service_name: str,
    request: Request, # To get raw body, headers, IP
    background_tasks: BackgroundTasks, # For async processing
    db: Session = Depends(get_db),
    # Signature headers vary by provider, e.g., X-Paystack-Signature, X-Flutterwave-Signature
    # These need to be explicitly declared or accessed from request.headers
    # x_paystack_signature: Optional[str] = Header(None, alias="X-Paystack-Signature"),
    # x_flutterwave_signature: Optional[str] = Header(None, alias="X-Flutterwave-Signature"),
    # ... add others as needed
):
    raw_body_bytes = await request.body()
    headers = dict(request.headers)
    source_ip = request.client.host if request.client else "Unknown IP"

    # Try to parse event_type from payload (common patterns)
    event_type: Optional[str] = None
    try:
        payload_json = json.loads(raw_body_bytes.decode('utf-8'))
        event_type = payload_json.get("event") or payload_json.get("event_type") or payload_json.get("type")
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload_json = None # Not JSON or decode error

    # Log the incoming webhook first
    log_entry = webhook_event_log_service.log_incoming_webhook(
        db, source_service_name=source_service_name, raw_payload=raw_body_bytes,
        request_headers=headers, source_ip=source_ip, event_type=event_type
    )

    # Signature Verification (Conceptual)
    is_verified = None # Null if not applicable or check fails before attempting
    api_config = api_service_config_service.get_config_by_service_name(db, source_service_name, active_only=True)

    # Example for Paystack, assuming header is X-Paystack-Signature
    paystack_sig = headers.get("x-paystack-signature") # Case-insensitive get from dict
    if api_config and source_service_name.upper() == "PAYSTACK_PAYMENTS" and paystack_sig:
        is_verified = webhook_event_log_service.verify_webhook_signature(
            api_config, raw_body_bytes, paystack_sig, source_service_name
        )
        if not is_verified:
            webhook_event_log_service.update_webhook_log_processing(
                db, log_entry.id, models.WebhookProcessingStatusEnum.FAILED_VALIDATION,
                notes="Signature verification failed.", is_signature_verified=False
            )
            # Depending on policy, might raise 400 or just log and not process further
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook signature verification failed.")

    # Update log with verification status if checked
    if is_verified is not None:
         webhook_event_log_service.update_webhook_log_processing(db, log_entry.id, is_signature_verified=is_verified, status=log_entry.processing_status) # Keep PENDING if verified

    # Add to background tasks for actual processing
    # Pass get_db to the background task so it can create its own session
    # background_tasks.add_task(process_webhook_event_background, log_entry.id, get_db)

    # For now, synchronous conceptual processing:
    print(f"Webhook from {source_service_name} (Log ID: {log_entry.id}) received. Payload: {raw_body_bytes[:200]}...")
    # In a real app, this is where you'd dispatch to a handler based on source_service_name and event_type
    # e.g., if source_service_name == "PAYSTACK": payments_module.handle_paystack_webhook(log_entry, payload_json)
    # For now, just mark as PROCESSED_SUCCESS conceptually if signature was okay or not required.
    if is_verified or not api_config or not paystack_sig : # If verified, or no means to verify
        webhook_event_log_service.update_webhook_log_processing(
            db, log_entry.id, models.WebhookProcessingStatusEnum.PROCESSED_SUCCESS,
            notes="Conceptually processed (actual business logic would run async).",
            is_signature_verified=is_verified
        )

    return {"message": "Webhook received and logged.", "log_id": log_entry.id}


# --- WebhookEventLog Admin Endpoints ---
admin_webhook_logs_router = APIRouter(
    prefix="/admin/webhook-event-logs",
    tags=["Admin: Webhook Event Logs (Incoming)"],
    dependencies=[Depends(get_current_active_superuser)]
)

@admin_webhook_logs_router.get("/", response_model=schemas.PaginatedWebhookEventLogResponse)
async def list_webhook_event_logs_endpoint(
    source_service_name: Optional[str] = None,
    event_type: Optional[str] = None,
    processing_status: Optional[models.WebhookProcessingStatusEnum] = None,
    skip: int = 0, limit: int = 20,
    db: Session = Depends(get_db)
):
    logs, total = webhook_event_log_service.get_webhook_logs(
        db, source_service_name=source_service_name, event_type=event_type,
        processing_status=processing_status, skip=skip, limit=limit
    )
    # Attempt to parse raw_payload as JSON for response if it's likely JSON
    augmented_logs = []
    for log_orm in logs:
        log_schema = schemas.WebhookEventLogResponse.from_orm(log_orm).dict()
        try:
            log_schema["raw_payload_parsed"] = json.loads(log_orm.raw_payload)
        except (json.JSONDecodeError, TypeError):
            log_schema["raw_payload_parsed"] = log_orm.raw_payload # Keep as string if not valid JSON
        augmented_logs.append(log_schema)

    return {"items": augmented_logs, "total": total, "page": (skip // limit) + 1, "size": limit}


@admin_webhook_logs_router.get("/{log_id}", response_model=schemas.WebhookEventLogResponse)
async def read_webhook_event_log_endpoint(log_id: int, db: Session = Depends(get_db)):
    db_log = webhook_event_log_service.get_webhook_log_by_id(db, log_id)
    if not db_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook Event Log not found")

    log_schema = schemas.WebhookEventLogResponse.from_orm(db_log).dict()
    try:
        log_schema["raw_payload_parsed"] = json.loads(db_log.raw_payload)
    except (json.JSONDecodeError, TypeError):
        log_schema["raw_payload_parsed"] = db_log.raw_payload
    return log_schema


@admin_webhook_logs_router.put("/{log_id}/status", response_model=schemas.WebhookEventLogResponse)
async def update_webhook_log_status_endpoint(
    log_id: int,
    update_request: schemas.WebhookProcessingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser) # Ensure admin action
):
    # Admin manually updating status or notes.
    updated_log = webhook_event_log_service.update_webhook_log_processing(
        db, log_id=log_id, status=update_request.processing_status,
        notes=f"Admin update by {current_user.username}: {update_request.processing_notes_or_error or ''}"
    )
    if not updated_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook Event Log not found")

    log_schema = schemas.WebhookEventLogResponse.from_orm(updated_log).dict()
    try:
        log_schema["raw_payload_parsed"] = json.loads(updated_log.raw_payload)
    except (json.JSONDecodeError, TypeError):
        log_schema["raw_payload_parsed"] = updated_log.raw_payload
    return log_schema


# Add sub-routers to the main integrations_api_router
integrations_api_router.include_router(admin_configs_router)
integrations_api_router.include_router(admin_ext_logs_router)
integrations_api_router.include_router(webhooks_receiver_router) # This is the public-facing webhook receiver
integrations_api_router.include_router(admin_webhook_logs_router)


# The main app would then do:
# from weezy_cbs.third_party_fintech_integration.api import integrations_api_router
# app.include_router(integrations_api_router)
