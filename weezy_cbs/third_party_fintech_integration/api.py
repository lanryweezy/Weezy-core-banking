# API Endpoints for Third-Party & Fintech Integration Module
# These are mostly for webhooks from third parties or admin configurations.
# Direct calls to third-party services are usually done via the *services.py* in this module,
# invoked by other core CBS modules' services.

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Query
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_admin_user, verify_third_party_webhook_signature

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_admin_user_placeholder(): return {"id": "admin01", "role": "admin"}
get_current_active_admin_user = get_current_active_admin_user_placeholder

# Placeholder for webhook signature verification dependency
async def verify_webhook_signature_placeholder(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature"), # Example header name
    # service_name: models.ThirdPartyServiceEnum # Would need to know which service this webhook is for
):
    # In a real app:
    # 1. Get raw request body: `raw_body = await request.body()`
    # 2. Fetch the configured secret for `service_name` from `ThirdPartyConfig`.
    # 3. Compute expected signature using `raw_body` and the secret.
    # 4. Compare with `x_webhook_signature`. If mismatch, raise HTTPException 401/403.
    # This placeholder does no actual verification.
    if x_webhook_signature and "invalid" in x_webhook_signature: # Simple test for failure
        # raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature.")
        pass # Allow for now
    return True # Assume valid for placeholder
verify_third_party_webhook_signature = verify_webhook_signature_placeholder


router = APIRouter(
    prefix="/third-party-integrations",
    tags=["Third-Party & Fintech Integrations"],
)

# --- Third-Party Configuration Endpoints (Admin) ---
@router.post("/admin/configs", response_model=schemas.ThirdPartyConfigResponse, status_code=status.HTTP_201_CREATED)
def configure_third_party_service(
    config_in: schemas.ThirdPartyConfigCreateRequest, # Service layer should encrypt sensitive fields
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Configure connection details for a third-party service. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # existing_config = db.query(models.ThirdPartyConfig).filter(models.ThirdPartyConfig.service_name == config_in.service_name).first()
    # if existing_config:
    #     # Update logic: services.update_third_party_config(db, existing_config.id, config_in)
    #     raise HTTPException(status_code=409, detail=f"Configuration for {config_in.service_name.value} already exists. Use PUT to update.")

    # For now, assume service handles create/update or this is simplified create
    # db_config = services.save_third_party_config(db, config_in) # This service would encrypt keys

    # Mock implementation:
    mock_db_config = models.ThirdPartyConfig(
        id=1, service_name=config_in.service_name, api_base_url=str(config_in.api_base_url),
        is_active=config_in.is_active, last_updated=datetime.utcnow()
    )
    # db.add(mock_db_config); db.commit(); db.refresh(mock_db_config)
    return schemas.ThirdPartyConfigResponse.from_orm(mock_db_config)


@router.get("/admin/configs", response_model=List[schemas.ThirdPartyConfigResponse])
def list_all_third_party_configs(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """List all configured third-party services. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # configs = db.query(models.ThirdPartyConfig).all()
    # return [schemas.ThirdPartyConfigResponse.from_orm(c) for c in configs]
    # Mock response:
    return [
        schemas.ThirdPartyConfigResponse(id=1, service_name=models.ThirdPartyServiceEnum.CREDIT_BUREAU_CRC, api_base_url="https://api.crc.com.ng", is_active=True),
        schemas.ThirdPartyConfigResponse(id=2, service_name=models.ThirdPartyServiceEnum.NIMC_NIN_VERIFICATION, api_base_url="https://api.nimc.gov.ng", is_active=False)
    ]

# --- Webhook Handler Endpoints (Example for a generic third party) ---
# Each third party might have its own dedicated webhook endpoint for clarity and specific signature verification.
@router.post("/webhooks/{service_name}", status_code=status.HTTP_200_OK)
async def handle_generic_third_party_webhook(
    service_name: models.ThirdPartyServiceEnum, # Path parameter to identify the service
    request: Request, # To get raw body for signature verification
    # signature_valid: bool = Depends(verify_third_party_webhook_signature), # Pass service_name to this dependency
    db: Session = Depends(get_db)
):
    """
    Generic webhook handler for incoming notifications from various third parties.
    Signature verification and specific processing logic depend on `service_name`.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")

    # Manually call placeholder signature verifier for this example
    # In real app, `Depends` would handle it and raise error if invalid.
    # This also means the dependency needs to know which service_name's secret to use.
    # One way is to have separate endpoint like /webhooks/credit-bureau-crc
    # For now, simulate:
    x_sig = request.headers.get("X-Webhook-Signature")
    is_sig_valid_mock = await verify_third_party_webhook_signature_placeholder(request, x_sig)
    if not is_sig_valid_mock and x_sig: # Only fail if signature was provided and was "invalid" by mock logic
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature (mock check).")


    raw_body = await request.body()
    try:
        payload_dict = json.loads(raw_body.decode('utf-8'))
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload from webhook.")

    # Log the raw event (conceptual, real logging might be in service)
    # log_entry = models.ThirdPartyAPILog(
    #     service_name=service_name, direction=models.TPAPILogDirectionEnum.INCOMING,
    #     endpoint_url=str(request.url), http_method="POST",
    #     request_payload=raw_body.decode('utf-8'), request_headers=json.dumps(dict(request.headers)),
    #     status=models.TPAPILogStatusEnum.PENDING # Initial status before processing
    # )
    # db.add(log_entry); db.commit(); db.refresh(log_entry)

    # Delegate to a specific service handler based on service_name and event type in payload
    # E.g., if service_name == CREDIT_BUREAU_CRC and payload_dict.get("event_type") == "REPORT_READY":
    #    services.handle_crc_report_ready_webhook(db, payload_dict, log_entry.id)
    # elif service_name == EXTERNAL_LOAN_ORIGINATOR_Y and payload_dict.get("event_type") == "APPLICATION_STATUS_UPDATE":
    #    services.handle_loan_originator_status_update_webhook(db, payload_dict, log_entry.id)

    # For this placeholder:
    # print(f"Webhook received for {service_name.value}: {payload_dict}")
    # Update log_entry status to PROCESSED or FAILED based on handler outcome.

    return {"message": f"Webhook for {service_name.value} received and acknowledged."}


# --- Endpoints for specific integrations (if bank initiates calls and needs an API for it) ---
# Example: Requesting a credit report (usually called by Loan Module service, but can be exposed)
@router.post("/credit-bureaus/request-report", response_model=schemas.CreditReportResponseSchema)
def request_credit_bureau_report(
    request_data: schemas.CreditReportRequestSchema,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_admin_user) # Or loan officer role
):
    """Request a credit report from a specified bureau for a BVN. (Internal/Authorized User)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    user_id_str = str(current_user.get("id"))
    try:
        return services.get_credit_report(db, request_data, user_id_str)
    except ValueError as e: # For invalid bureau name
        raise HTTPException(status_code=400, detail=str(e))
    except services.ConfigurationException as e:
        raise HTTPException(status_code=503, detail=f"Service configuration error: {str(e)}")
    except services.ExternalServiceException as e: # If bureau call fails with HTTP or known API error
        # The service.get_credit_report already returns a specific schema for this,
        # so the API can just return that. If it raises, then it's unexpected.
        raise HTTPException(status_code=502, detail=f"Credit bureau service error: {str(e)}")
    except Exception as e:
        # Log e
        raise HTTPException(status_code=500, detail=f"Unexpected error requesting credit report: {str(e)}")

# Example: Receiving a loan application from an external originator (partner uses this endpoint)
@router.post("/external-loan-applications/submit", response_model=schemas.ExternalLoanApplicationReceiveResponse)
async def submit_loan_application_from_partner(
    app_submission: schemas.ExternalLoanApplicationReceiveRequest,
    # auth: bool = Depends(verify_partner_api_key_for_originator(app_submission.originator_name)) # Specific auth per partner
    db: Session = Depends(get_db)
):
    """Endpoint for external loan originators/partners to submit loan applications."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.receive_external_loan_application(db, app_submission)
    except services.DataMappingException as e:
        raise HTTPException(status_code=400, detail=f"Invalid application payload: {str(e)}")
    except services.ConfigurationException as e: # If originator not configured
        raise HTTPException(status_code=403, detail=f"Originator not recognized or configured: {str(e)}")


# Most other interactions with third parties (NIMC, Bill Aggregators) would be:
# 1. Service functions in this module's `services.py`.
# 2. Called by other core CBS modules' services (e.g., CustomerIdentity calls NIMC service, TransactionManagement calls Bill Aggregator service).
# 3. Direct API endpoints here would be less common, mainly for admin or webhook purposes.

# Import json for webhook payload parsing if not already at top
import json
# Import datetime for model fields if not already at top
from datetime import datetime
