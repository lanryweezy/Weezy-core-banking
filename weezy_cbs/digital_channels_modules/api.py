# API Endpoints for Digital Channels Modules (Shared or Entry Points)
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Any

from . import services, schemas # Assuming shared services and schemas
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_digital_user_session_payload # For authenticated endpoints

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder

# Placeholder for session payload from a token (e.g. JWT)
def get_current_digital_user_session_payload_placeholder(request: Request) -> Optional[dict]:
    # In a real app, this would parse Authorization header, validate token, return payload
    # For mock, simulate a valid session or None if no/invalid token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer mock_session_"):
        # Extract mock user/customer ID from token
        try:
            parts = auth_header.split("_")
            return {"user_id": int(parts[2]), "customer_id": int(parts[3]), "channel": parts[4]}
        except (IndexError, ValueError):
            return None # Invalid mock token format
    return None
get_current_digital_user_session_payload = get_current_digital_user_session_payload_placeholder


router = APIRouter(
    prefix="/digital-channels",
    tags=["Digital Channels"],
)

# --- Authentication & Session Endpoints ---
@router.post("/auth/login", response_model=schemas.DigitalUserLoginResponse)
async def login_to_digital_channel(
    login_request: schemas.DigitalUserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate a user for a digital channel (Web Banking, Mobile App).
    Returns a session token upon successful authentication.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.digital_user_login(db, login_request)
    except services.AuthenticationException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except services.DeviceNotRegisteredException as e:
        # Client might use this to trigger device registration flow
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e), headers={"X-Weezy-Error-Code": "DEVICE_NOT_REGISTERED"})
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed due to an unexpected error.")

@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_from_digital_channel(
    session_payload: Optional[dict] = Depends(get_current_digital_user_session_payload),
    db: Session = Depends(get_db)
):
    """Invalidate the current user's session token."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    if not session_payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated or invalid session.")
    # In services.py:
    # services.invalidate_session(db, session_payload.get("jti") or session_id_from_token)
    return # No content response

# --- Device Registration Endpoint (Mobile) ---
@router.post("/devices/register", response_model=schemas.DeviceRegistrationResponse)
async def register_mobile_device(
    reg_request: schemas.DeviceRegistrationRequest,
    db: Session = Depends(get_db),
    session_payload: Optional[dict] = Depends(get_current_digital_user_session_payload) # Requires authenticated user
):
    """Register a new device for mobile banking for the authenticated customer."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    if not session_payload or not session_payload.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required to register device.")
    customer_id = session_payload.get("customer_id")
    try:
        device = services.register_device_for_customer(db, reg_request, customer_id)
        return device
    except Exception as e:
        # Log e
        raise HTTPException(status_code=500, detail=f"Device registration failed: {str(e)}")

# --- OTP Endpoints ---
@router.post("/otp/request", response_model=schemas.OTPResponse)
async def request_otp_for_action(
    otp_req: schemas.OTPRequest,
    db: Session = Depends(get_db),
    session_payload: Optional[dict] = Depends(get_current_digital_user_session_payload) # Usually for authenticated actions
):
    """Request an OTP for a specific purpose (e.g., 2FA, transaction confirmation)."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = otp_req.customer_id if hasattr(otp_req, 'customer_id') else (session_payload.get("customer_id") if session_payload else None)
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer context required for OTP request.")
    try:
        otp_ref = services.generate_and_send_otp(db, customer_id, otp_req.purpose, otp_req.channel_preference)
        return schemas.OTPResponse(message="OTP sent successfully.", otp_reference_id=otp_ref)
    except services.NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except services.ExternalServiceException as e: # If SMS/Email gateway fails
        raise HTTPException(status_code=502, detail=str(e))

@router.post("/otp/verify", response_model=schemas.OTPVerifyResponse)
async def verify_otp(
    otp_verify_req: schemas.OTPVerifyRequest,
    db: Session = Depends(get_db),
    session_payload: Optional[dict] = Depends(get_current_digital_user_session_payload)
):
    """Verify an OTP provided by the user."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = otp_verify_req.customer_id if hasattr(otp_verify_req, 'customer_id') else (session_payload.get("customer_id") if session_payload else None)
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer context required for OTP verification.")
    try:
        is_valid = services.verify_otp_code(db, customer_id, otp_verify_req.purpose, otp_verify_req.otp_code)
        if is_valid:
            return schemas.OTPVerifyResponse(is_valid=True, message="OTP verified successfully.")
        else: # Should be caught by InvalidOTPException typically
            return schemas.OTPVerifyResponse(is_valid=False, message="OTP verification failed.")
    except services.InvalidOTPException as e:
        return schemas.OTPVerifyResponse(is_valid=False, message=str(e)) # Return 200 with error message in body
        # Or raise HTTPException(status_code=400, detail=str(e))


# --- USSD Handler Endpoint (Called by Telco Gateway) ---
@router.post("/ussd/handler", response_model=schemas.USSDResponse) # Telcos usually expect specific XML/text format
async def handle_ussd_session_request(
    # USSD requests often come as form data or simple query params, not JSON
    # For FastAPI, this might be:
    # session_id: str = Form(...), phone_number: str = Form(...), ussd_string: str = Form(...)
    # Or a generic model if the gateway sends JSON
    ussd_input: schemas.USSDRequest, # Assuming gateway sends JSON for this example
    db: Session = Depends(get_db)
    # No user session here; authentication is by phone number mapping or PIN within USSD flow
):
    """
    Handle incoming USSD requests from Telco Aggregator.
    Manages USSD menu navigation and interaction logic.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.handle_ussd_request(db, ussd_input)
    except Exception as e:
        # Log e
        # Return a generic error message suitable for USSD display
        return schemas.USSDResponse(session_id=ussd_input.session_id, message="An error occurred. Please try again later.", is_final_response=True)

# --- Chatbot Handler Endpoint (Called by Chat Platform Webhook) ---
@router.post("/chatbot/webhook/{chat_platform}", response_model=schemas.ChatbotMessageResponse)
async def handle_chatbot_platform_message(
    chat_platform: str, # e.g., "whatsapp", "telegram"
    message_payload: Dict[Any, Any], # Raw payload from chat platform (e.g. WhatsApp Business API, Telegram Bot API)
    db: Session = Depends(get_db)
    # Signature/Token verification for webhook authenticity needed here
):
    """
    Handle incoming messages from Chat Platforms (WhatsApp, Telegram, etc.).
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")

    # 1. Authenticate webhook source (e.g. verify signature, IP whitelist)
    # ...

    # 2. Adapt platform-specific payload to our internal ChatbotMessageRequest schema
    # This is highly dependent on the chat platform's API.
    # Example conceptual adaptation:
    user_id_on_platform = message_payload.get("sender_id") or message_payload.get("message",{}).get("chat",{}).get("id") # Example
    text_received = message_payload.get("text") or message_payload.get("message",{}).get("text") # Example

    if not user_id_on_platform or not text_received:
        raise HTTPException(status_code=400, detail="Malformed chatbot message payload.")

    chat_request = schemas.ChatbotMessageRequest(
        user_id_on_chat_platform=str(user_id_on_platform),
        chat_platform=chat_platform.upper(),
        message_text=text_received
    )

    try:
        return services.handle_chatbot_message(db, chat_request)
    except Exception as e:
        # Log e
        return schemas.ChatbotMessageResponse(reply_text="Sorry, I encountered an issue. Please try again.")

# Each specific digital channel (Internet Banking, Mobile Banking App) would have its own
# set of routers and API endpoints, likely in sub-directories:
# e.g., /digital-channels/web/accounts, /digital-channels/mobile/transfers
# These would then call the appropriate services from this module or core CBS modules.
# The endpoints here are for shared functionalities or entry points like USSD/Chatbot handlers.

# Import date for query param typing if not already at top
from datetime import date
# Import func for count queries if not already at top
from sqlalchemy import func
