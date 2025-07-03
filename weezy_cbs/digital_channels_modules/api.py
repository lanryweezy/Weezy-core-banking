from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status, Body, Header, Request
from fastapi.security import OAuth2PasswordBearer # For API token auth
from sqlalchemy.orm import Session
from jose import JWTError, jwt # For decoding JWT

from weezy_cbs.database import get_db
from . import schemas, services, models
from .services import (
    digital_user_profile_service, registered_device_service, session_log_service,
    ussd_service, notification_service, chatbot_service,
    create_access_token # Re-using from core_infra for token creation structure (adapt if needed)
)
# Assuming JWT_SECRET_KEY and ALGORITHM are defined, possibly in services or a config module
# For now, let's use what's in services, but ideally, this comes from a central config.
from .services import JWT_SECRET_KEY, ALGORITHM


# --- Authentication & Authorization Dependencies for Digital Channels ---
oauth2_scheme_digital = OAuth2PasswordBearer(tokenUrl="/digital-channels/profiles/login") # Adjusted tokenUrl

async def get_current_digital_user_profile(
    token: str = Depends(oauth2_scheme_digital),
    db: Session = Depends(get_db)
) -> models.DigitalUserProfile:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        user_id: Optional[int] = payload.get("user_profile_id") # Ensure this is in the token
        if username is None or user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user_profile = digital_user_profile_service._get_digital_user_profile(db, user_id=user_id) # Use service method
    if user_profile is None:
        raise credentials_exception
    if not user_profile.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user profile")

    # Optional: Check session validity based on JTI if stored in token and SessionLog
    # session_jti = payload.get("jti")
    # if session_jti:
    #     active_session = db.query(models.SessionLog).filter(models.SessionLog.session_token_jti == session_jti, models.SessionLog.is_active == True).first()
    #     if not active_session:
    #         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")

    return user_profile

# Router for digital user profiles and related actions
profiles_router = APIRouter(
    prefix="/profiles",
    tags=["Digital User Profiles & Authentication"],
)

@profiles_router.post("/", response_model=schemas.DigitalUserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_digital_user_profile_endpoint(
    profile_in: schemas.DigitalUserProfileCreate,
    db: Session = Depends(get_db)
):
    # In a real scenario, self-registration might involve OTP verification of email/phone
    # before profile creation or marking as verified.
    # This endpoint assumes pre-validation or that verification happens post-creation.
    return digital_user_profile_service.create_digital_user_profile(db=db, profile_in=profile_in)

@profiles_router.post("/login", response_model=schemas.DigitalUserTokenSchema)
async def login_digital_user(
    request: Request, # To get IP and User-Agent
    login_data: schemas.DigitalUserLoginSchema, # No longer OAuth2PasswordRequestForm for more fields
    db: Session = Depends(get_db)
):
    login_data.ip_address = request.client.host if request.client else "Unknown IP"
    login_data.user_agent = request.headers.get("user-agent", "Unknown User-Agent")

    user_profile = digital_user_profile_service.authenticate_digital_user(db, login_data=login_data)
    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password, or account locked/inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create session log entry (already done inside authenticate_digital_user, get JTI if created)
    active_session = db.query(models.SessionLog)\
        .filter(models.SessionLog.digital_user_profile_id == user_profile.id, models.SessionLog.is_active == True)\
        .order_by(models.SessionLog.login_time.desc())\
        .first()

    # Standard JWT claims: sub, exp. Add user_profile_id and jti (JWT ID for session tracking)
    token_data = {
        "sub": user_profile.username,
        "user_profile_id": user_profile.id,
        "jti": active_session.session_token_jti if active_session and active_session.session_token_jti else None
    }
    access_token = create_access_token(data=token_data) # Uses core_infra token creation

    return schemas.DigitalUserTokenSchema(
        access_token=access_token,
        user_profile=schemas.DigitalUserProfileResponse.from_orm(user_profile),
        # session_jti=active_session.session_token_jti if active_session else None
    )

@profiles_router.post("/logout")
async def logout_digital_user(
    db: Session = Depends(get_db),
    current_profile: models.DigitalUserProfile = Depends(get_current_digital_user_profile),
    token: str = Depends(oauth2_scheme_digital) # To get JTI from token
):
    # Invalidate session by JTI if used
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False}) # Allow expired for logout
        session_jti = payload.get("jti")
        if session_jti:
            session_log_service.end_session_log(db, session_jti=session_jti)
            digital_user_profile_service._audit_log(db, "DIGITAL_LOGOUT", current_profile, f"User logged out, session JTI {session_jti} invalidated.")
            return {"message": "Logout successful, session invalidated."}
    except JWTError:
        pass # Token might be invalid, proceed to generic logout for current profile sessions

    # Fallback: End latest active session for the user if JTI not found or invalid
    active_sessions = db.query(models.SessionLog)\
        .filter(models.SessionLog.digital_user_profile_id == current_profile.id, models.SessionLog.is_active == True)\
        .all()
    for sess in active_sessions: # End all active sessions for this user on logout
        session_log_service.end_session_log(db, session_id_pk=sess.id)

    digital_user_profile_service._audit_log(db, "DIGITAL_LOGOUT_ALL_SESSIONS", current_profile, "User logged out, all active sessions ended.")
    return {"message": "Logout successful."}


@profiles_router.get("/me", response_model=schemas.DigitalUserProfileWithDevicesResponse)
async def read_current_user_profile(
    current_profile: models.DigitalUserProfile = Depends(get_current_digital_user_profile),
    db: Session = Depends(get_db) # Required for joinedload
):
    # Eager load devices for the response model
    profile_with_devices = db.query(models.DigitalUserProfile)\
        .options(joinedload(models.DigitalUserProfile.registered_devices))\
        .filter(models.DigitalUserProfile.id == current_profile.id).first()
    if not profile_with_devices: # Should not happen if Depends worked
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current user profile not found.")
    return profile_with_devices


@profiles_router.put("/me", response_model=schemas.DigitalUserProfileResponse)
async def update_current_user_profile(
    profile_in: schemas.DigitalUserProfileUpdate,
    db: Session = Depends(get_db),
    current_profile: models.DigitalUserProfile = Depends(get_current_digital_user_profile)
):
    return digital_user_profile_service.update_digital_user_profile(
        db, profile_id=current_profile.id, profile_in=profile_in, performing_username=current_profile.username
    )

@profiles_router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_current_user_password(
    pass_change: schemas.DigitalUserPasswordChangeSchema,
    db: Session = Depends(get_db),
    current_profile: models.DigitalUserProfile = Depends(get_current_digital_user_profile)
):
    if not digital_user_profile_service.change_password(db, profile_id=current_profile.id, pass_change=pass_change):
        # This case should be handled by exceptions within the service for specific errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password change failed.")
    return None

@profiles_router.post("/me/set-pin", status_code=status.HTTP_204_NO_CONTENT)
async def set_current_user_transaction_pin(
    pin_set: schemas.DigitalUserTransactionPinSetSchema,
    db: Session = Depends(get_db),
    current_profile: models.DigitalUserProfile = Depends(get_current_digital_user_profile)
):
    digital_user_profile_service.set_transaction_pin(db, profile_id=current_profile.id, pin_set=pin_set)
    return None

# OTP Endpoints (could be part of profiles or separate)
@profiles_router.post("/otp/request", summary="Request OTP for a specific purpose")
async def request_otp(
    otp_request: schemas.OTPRequestSchema,
    db: Session = Depends(get_db),
    # This might be authenticated or not, depending on purpose.
    # If for logged-in user, use current_profile. If for password reset, identifier is key.
    # For now, let's assume it can be called by an identified (but not necessarily token-authed) user.
    # current_profile: Optional[models.DigitalUserProfile] = Depends(get_optional_current_digital_user_profile) # Needs a new dependency
):
    # Simplified: Assume profile_id is known or derived from otp_request.identifier (e.g. username for password reset)
    # This needs robust logic to map identifier to profile_id securely.
    # For now, let's assume otp_request.identifier IS the username for a profile.
    target_profile = digital_user_profile_service._get_digital_user_profile(db, username=otp_request.identifier)
    if not target_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found for OTP request.")

    # Determine delivery channel and actual recipient identifier (e.g., customer's verified phone)
    # This is placeholder logic.
    delivery_channel = schemas.ChannelTypeEnum.SMS_BANKING # Default
    # recipient_contact = customer_service.get_verified_phone(db, target_profile.customer_id) # Example
    recipient_contact = "customer_phone_placeholder" # Placeholder

    if not digital_user_profile_service.generate_and_send_otp(
        db, profile_id=target_profile.id, purpose=otp_request.otp_purpose,
        delivery_channel=delivery_channel, recipient_identifier=recipient_contact
    ):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send OTP.")
    return {"message": f"OTP sent successfully for {otp_request.otp_purpose}."}


@profiles_router.post("/otp/verify", summary="Verify OTP for a specific purpose")
async def verify_otp(
    otp_verify: schemas.OTPVerifySchema,
    db: Session = Depends(get_db)
):
    # Again, map identifier to profile_id securely.
    target_profile = digital_user_profile_service._get_digital_user_profile(db, username=otp_verify.identifier)
    if not target_profile: # Should generally not happen if request_otp was called for same identifier
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found for OTP verification.")

    # recipient_identifier used in OTP storage key must match the one used in generate_and_send_otp
    # This might be the same as otp_verify.identifier or derived.
    recipient_contact_for_otp_key = "customer_phone_placeholder" # Must match what was used for sending

    if not digital_user_profile_service.verify_otp_for_profile(
        db, profile_id=target_profile.id, purpose=otp_verify.otp_purpose,
        otp_code=otp_verify.otp_code, recipient_identifier=recipient_contact_for_otp_key
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP.")

    # If OTP is verified, specific actions can be taken based on purpose
    # e.g., mark email as verified, allow password reset, complete device registration
    if otp_verify.otp_purpose == "EMAIL_VERIFICATION":
        target_profile.is_verified_email = True # Example action
        db.commit()
        digital_user_profile_service._audit_log(db, "EMAIL_VERIFIED_VIA_OTP", target_profile, "Email verified via OTP.")

    return {"message": f"OTP verified successfully for {otp_verify.otp_purpose}."}


# --- RegisteredDevice Endpoints (nested under /me for context) ---
devices_router = APIRouter(
    prefix="/me/devices",
    tags=["Digital User Devices"],
    dependencies=[Depends(get_current_digital_user_profile)]
)

@devices_router.post("/", response_model=schemas.RegisteredDeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_new_device(
    device_in: schemas.RegisteredDeviceCreate,
    db: Session = Depends(get_db),
    current_profile: models.DigitalUserProfile = Depends(get_current_digital_user_profile)
):
    # Device registration might require OTP verification in some flows.
    # For simplicity, this endpoint directly registers it.
    # OTP step could be added here or as a separate verification endpoint.
    return registered_device_service.register_device(db, profile_id=current_profile.id, device_in=device_in)

@devices_router.get("/", response_model=List[schemas.RegisteredDeviceResponse])
async def list_user_devices(
    db: Session = Depends(get_db),
    current_profile: models.DigitalUserProfile = Depends(get_current_digital_user_profile)
):
    return registered_device_service.get_devices_for_user(db, profile_id=current_profile.id)

@devices_router.put("/{device_id}", response_model=schemas.RegisteredDeviceResponse)
async def update_user_device(
    device_id: int,
    device_update_in: schemas.RegisteredDeviceUpdate,
    db: Session = Depends(get_db),
    current_profile: models.DigitalUserProfile = Depends(get_current_digital_user_profile)
):
    updated_device = registered_device_service.update_device_status_or_details(
        db, device_id=device_id, device_update_in=device_update_in, profile_id=current_profile.id
    )
    if not updated_device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found or does not belong to user.")
    return updated_device

@devices_router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_profile: models.DigitalUserProfile = Depends(get_current_digital_user_profile)
):
    if not registered_device_service.remove_device(db, device_id=device_id, profile_id=current_profile.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found or does not belong to user.")
    return None


# --- USSD Endpoint ---
ussd_callbacks_router = APIRouter(
    prefix="/ussd",
    tags=["USSD Channel"],
)

@ussd_callbacks_router.post("/callback", response_model=schemas.USSDResponseSchema)
async def ussd_request_handler(
    # USSD gateways send data differently, often form-encoded or query params.
    # FastAPI can handle form data with `Body(...)` or individual `Form(...)` fields.
    # This example uses a Pydantic model, assuming gateway sends JSON or FastAPI parses it.
    # Adjust based on actual gateway integration.
    request_data: schemas.USSDRequestSchema, # = Body(...) if form data
    db: Session = Depends(get_db)
):
    # Add security here: IP whitelisting for USSD gateway, signature verification if provided.
    # X-Forwarded-For might be needed if behind a reverse proxy.
    return await ussd_service.handle_ussd_request(db, request_data=request_data)


# --- Chatbot Endpoint ---
chatbot_router = APIRouter(
    prefix="/chatbot",
    tags=["Chatbot Channel"],
)

@chatbot_router.post("/message", response_model=schemas.ChatbotResponseSchema)
async def chatbot_message_handler(
    request_data: schemas.ChatbotRequestSchema,
    db: Session = Depends(get_db)
    # Optional: X-Chatbot-Signature for verifying requests from chatbot platform
    # chatbot_signature: Optional[str] = Header(None, alias="X-Chatbot-Signature")
):
    # Add security: Signature verification, IP whitelisting for chatbot platform.
    return await chatbot_service.handle_chatbot_message(db, request_data=request_data)


# --- Notification Logs Endpoint (Admin/Internal) ---
notifications_admin_router = APIRouter(
    prefix="/notifications",
    tags=["Notification Logs (Admin)"],
    # dependencies=[Depends(get_current_active_superuser)] # Protect with admin auth from core_infra
)

@notifications_admin_router.get("/logs", response_model=schemas.PaginatedNotificationLogResponse)
async def get_notification_logs(
    customer_id: Optional[int] = None,
    digital_user_profile_id: Optional[int] = None,
    channel_type: Optional[schemas.ChannelTypeEnum] = None,
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db)
):
    # This is a simplified query. A service method would be better.
    query = db.query(models.NotificationLog)
    if customer_id: query = query.filter(models.NotificationLog.customer_id == customer_id)
    if digital_user_profile_id: query = query.filter(models.NotificationLog.digital_user_profile_id == digital_user_profile_id)
    if channel_type: query = query.filter(models.NotificationLog.channel_type == channel_type)
    if status: query = query.filter(models.NotificationLog.status == status)

    total = query.count()
    logs = query.order_by(models.NotificationLog.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": logs, "total": total, "page": (skip // limit) + 1, "size": limit}


# Main router for this module to be included in the FastAPI app
digital_channels_api_router = APIRouter(prefix="/digital-channels")
digital_channels_api_router.include_router(profiles_router)
digital_channels_api_router.include_router(devices_router) # Already prefixed with /me/devices
digital_channels_api_router.include_router(ussd_callbacks_router)
digital_channels_api_router.include_router(chatbot_router)
digital_channels_api_router.include_router(notifications_admin_router)

# The main app would then do:
# app.include_router(digital_channels_api_router)
