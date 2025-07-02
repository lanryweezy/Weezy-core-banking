# API Endpoints for Payments Integration Layer (mostly for webhooks and admin)
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Query
from sqlalchemy.orm import Session
from typing import Any, Dict, List

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_admin_user, api_key_auth (for webhooks)

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_admin_user_placeholder(): return {"id": 1, "role": "admin"}
get_current_active_admin_user = get_current_active_admin_user_placeholder
async def api_key_auth_placeholder(x_api_key: str = Header(None)):
    if x_api_key != "fake-webhook-api-key": # Example key
        # raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key for webhook")
        pass # For now, allow through for testing if key not provided
    return True
api_key_auth = api_key_auth_placeholder


router = APIRouter(
    prefix="/payment-integrations",
    tags=["Payments Integration Layer"],
)

# --- Webhook Endpoints (Example for Paystack) ---
@router.post("/webhooks/paystack", status_code=status.HTTP_200_OK)
async def handle_paystack_webhook(
    request: Request, # FastAPI request object to get raw body
    x_paystack_signature: Optional[str] = Header(None), # Paystack signature header
    db: Session = Depends(get_db)
    # No direct user auth; webhook auth is via signature or IP whitelist
):
    """
    Handle incoming webhooks from Paystack.
    Signature verification is crucial here.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")

    raw_body = await request.body()
    try:
        payload_dict = json.loads(raw_body.decode('utf-8'))
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload from webhook.")

    event_data = schemas.WebhookEventData(
        gateway=models.PaymentGatewayEnum.PAYSTACK,
        event_type=payload_dict.get("event"),
        event_id_external=payload_dict.get("data", {}).get("id"), # Or other unique ID from payload
        payload_received=payload_dict,
        headers_received={"x-paystack-signature": x_paystack_signature} if x_paystack_signature else None
    )

    try:
        # The service will log, validate signature, and process
        services.process_incoming_webhook(db, event_data)
        return {"message": "Webhook received and processing initiated."}
    except services.ConfigurationException as e: # E.g. if PaystackService can't init due to no secret key
        # Log this critical error server-side
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Webhook processing configuration error: {str(e)}")
    except Exception as e:
        # Log unexpected error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error handling webhook: {str(e)}")


# --- Payment Link Endpoints (Example) ---
@router.post("/payment-links", response_model=schemas.PaymentLinkResponse, status_code=status.HTTP_201_CREATED)
def create_new_payment_link(
    link_create_req: schemas.PaymentLinkCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_admin_user) # Or a merchant user
):
    """
    Create a new shareable payment link. (Admin/Merchant operation)
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = current_user.get("customer_id") # Or None if admin creates non-customer specific link

    try:
        link_model = services.create_payment_link(db, link_create_req, customer_id=customer_id)
        # Construct the full URL (replace with actual base URL from config)
        base_payment_url = "https://pay.weezybank.com/link/" # Example
        full_url = f"{base_payment_url}{link_model.link_reference}"

        response_data = schemas.PaymentLinkResponse.from_orm(link_model).dict()
        response_data["full_payment_url"] = full_url
        return schemas.PaymentLinkResponse(**response_data)

    except services.NotFoundException as e: # e.g. if account_to_credit_id is invalid
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create payment link: {str(e)}")

@router.get("/payment-links/{link_reference}", response_model=schemas.PaymentLinkResponse)
def get_payment_link_details(link_reference: str, db: Session = Depends(get_db)):
    """
    Get details of a payment link. This might be public if the link itself is public.
    No specific auth here, but consider if sensitive info is in response.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    link_model = services.get_payment_link_by_reference(db, link_reference)
    if not link_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment link not found.")

    base_payment_url = "https://pay.weezybank.com/link/" # Example
    full_url = f"{base_payment_url}{link_model.link_reference}"
    response_data = schemas.PaymentLinkResponse.from_orm(link_model).dict()
    response_data["full_payment_url"] = full_url
    return schemas.PaymentLinkResponse(**response_data)

# --- Gateway Configuration Endpoints (Admin only) ---
@router.post("/admin/gateway-configs", response_model=schemas.PaymentGatewayConfigResponse, status_code=status.HTTP_201_CREATED)
def configure_payment_gateway(
    config_in: schemas.PaymentGatewayConfigCreate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user) # Ensures only admin can call
):
    """
    Add or update configuration for a payment gateway. (Admin operation)
    Plain text API keys are provided here and should be encrypted by the service layer before storage.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # Service layer should handle encryption of keys
    # existing_config = db.query(models.PaymentGatewayConfig).filter(models.PaymentGatewayConfig.gateway == config_in.gateway).first()
    # if existing_config:
    #     # Update logic
    #     for key, value in config_in.dict(exclude_unset=True).items():
    #         if key.endswith("_plain"): # Handle encryption for key fields
    #             # service logic to encrypt and set corresponding _encrypted field
    #             pass
    #         else:
    #             setattr(existing_config, key, value)
    #     db_config = existing_config
    # else:
    #     # Create logic
    #     encrypted_data = {} # Populate with encrypted keys
    #     db_config = models.PaymentGatewayConfig(**config_in.dict(exclude={"api_key_plain", "secret_key_plain", "public_key_plain"}), **encrypted_data)
    #     db.add(db_config)

    # This is a simplified placeholder for create/update config logic
    # Assume a service function `save_gateway_config` handles encryption and DB operations
    # db_config = services.save_gateway_config(db, config_in)

    # Mock implementation for now:
    mock_db_config = models.PaymentGatewayConfig(
        id=random.randint(1,100), gateway=config_in.gateway, base_url=str(config_in.base_url),
        is_active=config_in.is_active, merchant_id=config_in.merchant_id,
        api_key_encrypted="enc_api_"+(config_in.api_key_plain or ""), # Simulate encryption
        secret_key_encrypted="enc_secret_"+(config_in.secret_key_plain or ""),
        public_key_encrypted="enc_public_"+(config_in.public_key_plain or "")
    )
    # db.add(mock_db_config); db.commit(); db.refresh(mock_db_config)
    return schemas.PaymentGatewayConfigResponse.from_orm(mock_db_config)


@router.get("/admin/gateway-configs", response_model=List[schemas.PaymentGatewayConfigResponse])
def list_all_gateway_configs(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """List all payment gateway configurations. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # configs = db.query(models.PaymentGatewayConfig).all()
    # return [schemas.PaymentGatewayConfigResponse.from_orm(c) for c in configs]
    # Mock response
    return [
        schemas.PaymentGatewayConfigResponse(id=1, gateway=models.PaymentGatewayEnum.PAYSTACK, base_url="https://api.paystack.co", is_active=True, merchant_id="MOCK_PAYSTACK_ID"),
        schemas.PaymentGatewayConfigResponse(id=2, gateway=models.PaymentGatewayEnum.FLUTTERWAVE, base_url="https://api.flutterwave.com/v3", is_active=False)
    ]

# This API layer is minimal because most interactions are outbound calls from other services (e.g., TransactionManagement)
# or inbound webhooks. Direct API calls to this layer might be for:
# - Admin configuring gateways.
# - System generating payment links.
# - Potentially a unified payment initiation endpoint if the bank wants to abstract gateways from client apps.
# - Fetching lists of billers or payment items if this layer caches/proxies them.

# Example: Unified Bill Payment Endpoints (if this layer provides them)
@router.get("/billers", response_model=List[schemas.BillerResponse])
def get_all_billers(
    category_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
    # auth: bool = Depends(api_key_auth_placeholder) # Or user auth
):
    """Get a list of available billers, optionally filtered by category."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # This would call a service that fetches from NIBSS e-BillsPay or other aggregators
    # billers = services.get_billers_from_aggregator(category_id=category_id)
    # Mock response:
    mock_billers = [
        schemas.BillerResponse(id="DSTV", name="DStv", category_id="TV_SUBSCRIPTION"),
        schemas.BillerResponse(id="IKEDC", name="Ikeja Electric", category_id="ELECTRICITY"),
        schemas.BillerResponse(id="MTN_VTU", name="MTN Airtime", category_id="AIRTIME"),
    ]
    if category_id:
        return [b for b in mock_billers if b.category_id.lower() == category_id.lower()]
    return mock_billers

@router.get("/billers/{biller_id}/payment-items", response_model=List[schemas.PaymentItemResponse])
def get_biller_payment_items(biller_id: str, db: Session = Depends(get_db)):
    """Get payment items for a specific biller."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # items = services.get_payment_items_for_biller(biller_id)
    # Mock response:
    if biller_id.upper() == "DSTV":
        return [schemas.PaymentItemResponse(id="DSTV_COMPACT", name="DStv Compact Bouquet", biller_id="DSTV", amount_fixed=decimal.Decimal("10500.00"))]
    elif biller_id.upper() == "IKEDC":
        return [schemas.PaymentItemResponse(id="IKEDC_POSTPAID", name="Ikeja Electric Postpaid", biller_id="IKEDC")]
    raise HTTPException(status_code=404, detail="Biller not found or no payment items.")

# The actual "pay bill" or "buy airtime" would likely be part of TransactionManagement API,
# which then calls the specific service methods in this payment_integration_layer.services.

# Example: An endpoint to test a Paystack initialize call (for dev/admin)
@router.post("/test/paystack/initialize", response_model=schemas.PaystackInitializeWrapperResponse, include_in_schema=False)
def test_paystack_initialize(
    test_request: schemas.PaystackInitializeRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        paystack_service = services.PaystackService(db)
        # Use a unique internal reference for testing
        internal_ref = "TEST_INIT_" + datetime.now().strftime("%Y%m%d%H%M%S")
        return paystack_service.initialize_transaction(test_request, internal_ref)
    except services.ConfigurationException as e:
        raise HTTPException(status_code=500, detail=f"Paystack not configured: {str(e)}")
    except services.ExternalServiceException as e:
        raise HTTPException(status_code=502, detail=f"Paystack API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Import necessary modules if not already imported at the top
import json
import random
from sqlalchemy import func # For count queries if needed
import decimal # For Paginated responses if they contain Decimals. Not directly needed here for this structure.
