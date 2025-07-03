import json
from typing import List, Optional, Type, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from passlib.context import CryptContext
from datetime import datetime, timedelta
import random
import string

from . import models, schemas
from weezy_cbs.core_infrastructure_config_engine.services import AuditLogService, get_password_hash, verify_password, create_access_token
# Attempt to import Customer model for type hinting and linking. This creates a circular dependency if not careful.
# from weezy_cbs.customer_identity_management.models import Customer as CIMCustomer
# For now, assume customer_id is sufficient and validation happens at higher levels or via direct DB checks.

# --- Constants & Configuration (should be in a config file) ---
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCK_DURATION_MINUTES = 30
USSD_SESSION_TIMEOUT_MINUTES = 5 # Standard USSD timeout

# Local pwd_context if not sharing directly from core_infra for digital user passwords
digital_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_digital_password(plain_password: str, hashed_password: str) -> bool:
    return digital_pwd_context.verify(plain_password, hashed_password)

def get_digital_password_hash(password: str) -> str:
    return digital_pwd_context.hash(password)

# --- OTP Management (Conceptual - In-memory or Redis backed) ---
# For a real app, use Redis or a dedicated OTP table.
# This is a simplified in-memory store for demonstration.
otp_store: Dict[str, Dict[str, Any]] = {} # Key: identifier_purpose, Value: {otp: "xxxx", expiry: datetime}

def generate_otp_value(length: int = OTP_LENGTH) -> str:
    return "".join(random.choices(string.digits, k=length))

def store_otp(identifier: str, purpose: str, otp: str, expiry_minutes: int = OTP_EXPIRY_MINUTES):
    key = f"{identifier.lower()}_{purpose.upper()}"
    otp_store[key] = {
        "otp": otp,
        "expiry": datetime.utcnow() + timedelta(minutes=expiry_minutes),
        "verified": False # Mark as unverified initially
    }

def retrieve_otp(identifier: str, purpose: str) -> Optional[Dict[str, Any]]:
    key = f"{identifier.lower()}_{purpose.upper()}"
    return otp_store.get(key)

def verify_and_consume_otp(identifier: str, purpose: str, otp_code: str) -> bool:
    stored_otp_data = retrieve_otp(identifier, purpose)
    if not stored_otp_data:
        return False
    if stored_otp_data["otp"] == otp_code and datetime.utcnow() < stored_otp_data["expiry"] and not stored_otp_data["verified"]:
        # Mark as verified to prevent reuse (important for some flows)
        # For some OTPs (like login 2FA), you might delete it immediately after verification.
        # For others (like registration verification), you might mark as verified and allow one final action.
        stored_otp_data["verified"] = True
        # Optionally, remove from store after verification:
        # key = f"{identifier.lower()}_{purpose.upper()}"
        # del otp_store[key]
        return True
    return False


# --- Base Service for Digital Channels (if common patterns emerge) ---
class BaseDigitalChannelService:
    def _get_digital_user_profile(self, db: Session, user_id: Optional[int] = None, username: Optional[str] = None) -> Optional[models.DigitalUserProfile]:
        if user_id:
            return db.query(models.DigitalUserProfile).filter(models.DigitalUserProfile.id == user_id).first()
        if username:
            return db.query(models.DigitalUserProfile).filter(func.lower(models.DigitalUserProfile.username) == func.lower(username)).first()
        return None

    def _audit_log(self, db: Session, action: str, profile: Optional[models.DigitalUserProfile] = None, summary: str = "", entity_id: Optional[str] = None, performing_username: Optional[str] = "SYSTEM"):
        AuditLogService.create_audit_log_entry(
            db,
            username_performing_action=performing_username or (profile.username if profile else "UNKNOWN_DIGITAL_USER"),
            action_type=action,
            entity_type="DigitalUserProfile",
            entity_id=str(entity_id or (profile.id if profile else "N/A")),
            summary=summary
        )

# --- DigitalUserProfile Service ---
class DigitalUserProfileService(BaseDigitalChannelService):

    def create_digital_user_profile(self, db: Session, profile_in: schemas.DigitalUserProfileCreate) -> models.DigitalUserProfile:
        # Check if customer exists (this should ideally be done by fetching Customer object)
        # For now, assume customer_id is valid. A real app would query Customer table.
        # cim_customer = db.query(CIMCustomer).filter(CIMCustomer.id == profile_in.customer_id).first()
        # if not cim_customer:
        #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer with ID {profile_in.customer_id} not found.")

        if self._get_digital_user_profile(db, username=profile_in.username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered for digital channels.")

        existing_for_customer = db.query(models.DigitalUserProfile).filter(models.DigitalUserProfile.customer_id == profile_in.customer_id).first()
        if existing_for_customer:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Customer ID {profile_in.customer_id} already has a digital profile.")

        hashed_password = get_digital_password_hash(profile_in.password)

        sec_answer_hashed = None
        if profile_in.security_answer_1:
            sec_answer_hashed = get_digital_password_hash(profile_in.security_answer_1) # Hash security answer

        db_profile_data = profile_in.dict(exclude={"password", "security_answer_1"})
        db_profile = models.DigitalUserProfile(
            **db_profile_data,
            hashed_password=hashed_password,
            security_answer_1_hashed=sec_answer_hashed
        )

        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        self._audit_log(db, "DIGITAL_PROFILE_CREATE", db_profile, f"Digital profile created for username {db_profile.username}.")
        return db_profile

    def update_digital_user_profile(self, db: Session, profile_id: int, profile_in: schemas.DigitalUserProfileUpdate, performing_username: str) -> Optional[models.DigitalUserProfile]:
        db_profile = self._get_digital_user_profile(db, user_id=profile_id)
        if not db_profile:
            return None

        update_data = profile_in.dict(exclude_unset=True)
        if "username" in update_data and update_data["username"].lower() != db_profile.username.lower():
            if self._get_digital_user_profile(db, username=update_data["username"]):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New username already taken.")

        for field, value in update_data.items():
            setattr(db_profile, field, value)

        db.commit()
        db.refresh(db_profile)
        self._audit_log(db, "DIGITAL_PROFILE_UPDATE", db_profile, "Digital profile updated.", performing_username=performing_username)
        return db_profile

    def change_password(self, db: Session, profile_id: int, pass_change: schemas.DigitalUserPasswordChangeSchema) -> bool:
        db_profile = self._get_digital_user_profile(db, user_id=profile_id)
        if not db_profile or not db_profile.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found or inactive.")

        if not verify_digital_password(pass_change.current_password, db_profile.hashed_password):
            self._audit_log(db, "DIGITAL_PASSWORD_CHANGE_FAIL", db_profile, "Password change failed: Incorrect current password.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password.")

        db_profile.hashed_password = get_digital_password_hash(pass_change.new_password)
        db.commit()
        self._audit_log(db, "DIGITAL_PASSWORD_CHANGE_SUCCESS", db_profile, "Password changed successfully.")
        return True

    def set_transaction_pin(self, db: Session, profile_id: int, pin_set: schemas.DigitalUserTransactionPinSetSchema) -> bool:
        db_profile = self._get_digital_user_profile(db, user_id=profile_id)
        if not db_profile or not db_profile.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found or inactive.")
        if not verify_digital_password(pin_set.password, db_profile.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect login password provided for PIN setup.")

        db_profile.transaction_pin_hashed = get_digital_password_hash(pin_set.new_pin) # Hash the PIN
        db_profile.is_transaction_pin_set = True
        db.commit()
        self._audit_log(db, "DIGITAL_TXN_PIN_SET", db_profile, "Transaction PIN set successfully.")
        return True

    def verify_transaction_pin(self, db: Session, profile_id: int, pin: str) -> bool:
        db_profile = self._get_digital_user_profile(db, user_id=profile_id)
        if not db_profile or not db_profile.is_active or not db_profile.is_transaction_pin_set or not db_profile.transaction_pin_hashed:
            return False # Or raise specific errors
        return verify_digital_password(pin, db_profile.transaction_pin_hashed)


    def authenticate_digital_user(self, db: Session, login_data: schemas.DigitalUserLoginSchema) -> Optional[models.DigitalUserProfile]:
        db_profile = self._get_digital_user_profile(db, username=login_data.username)
        if not db_profile:
            self._audit_log(db, "DIGITAL_LOGIN_FAIL", summary=f"Login attempt failed for username {login_data.username}: User not found.", performing_username=login_data.username)
            return None

        if not db_profile.is_active:
            self._audit_log(db, "DIGITAL_LOGIN_FAIL", db_profile, "Login attempt failed: Account inactive.")
            return None

        if db_profile.locked_until and datetime.utcnow() < db_profile.locked_until:
            self._audit_log(db, "DIGITAL_LOGIN_FAIL", db_profile, f"Login attempt failed: Account locked until {db_profile.locked_until}.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account locked. Try again after {db_profile.locked_until.strftime('%Y-%m-%d %H:%M:%S UTC')}.")

        if not verify_digital_password(login_data.password, db_profile.hashed_password):
            self.record_failed_login_attempt(db, db_profile)
            self._audit_log(db, "DIGITAL_LOGIN_FAIL", db_profile, "Login attempt failed: Incorrect password.")
            return None

        # Successful login: reset failed attempts, update last login
        db_profile.failed_login_attempts = 0
        db_profile.locked_until = None
        db_profile.last_login_at = datetime.utcnow()
        db_profile.last_login_channel = login_data.channel
        db_profile.last_login_ip = login_data.ip_address # Assuming ip_address is passed in login_data
        db.commit()
        db.refresh(db_profile)

        # Create session log
        SessionLogService().create_session_log(db, profile_id=db_profile.id, channel=login_data.channel, ip_address=login_data.ip_address, user_agent=login_data.user_agent)

        self._audit_log(db, "DIGITAL_LOGIN_SUCCESS", db_profile, f"Login successful via {login_data.channel.value}.")
        return db_profile

    def record_failed_login_attempt(self, db: Session, profile: models.DigitalUserProfile):
        profile.failed_login_attempts += 1
        if profile.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            profile.locked_until = datetime.utcnow() + timedelta(minutes=ACCOUNT_LOCK_DURATION_MINUTES)
            self._audit_log(db, "DIGITAL_ACCOUNT_LOCKED", profile, f"Account locked due to {MAX_LOGIN_ATTEMPTS} failed login attempts.")
        db.commit()
        db.refresh(profile)

    def generate_and_send_otp(self, db: Session, profile_id: int, purpose: str, delivery_channel: schemas.ChannelTypeEnum, recipient_identifier: Optional[str] = None) -> bool:
        db_profile = self._get_digital_user_profile(db, user_id=profile_id)
        if not db_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Digital user profile not found.")

        # Determine recipient identifier if not provided (e.g., from customer contact info)
        # For now, assume recipient_identifier is primary phone or email from Customer model (not directly accessed here)
        # This needs a proper way to fetch customer's verified phone/email.
        if not recipient_identifier:
            # This is a placeholder. You'd fetch customer's primary contact.
            # customer_contact = db.query(CIMCustomer.primary_phone_number).filter(CIMCustomer.id == db_profile.customer_id).scalar_one_or_none()
            # if not customer_contact:
            #     raise HTTPException(status_code=500, detail="Recipient contact not found for OTP.")
            # recipient_identifier = customer_contact
            # For demo, if not provided, we might raise error or use a default if available in DigitalUserProfile
            raise NotImplementedError("Recipient identifier must be provided or derived from customer profile.")


        otp = generate_otp_value()
        store_otp(identifier=recipient_identifier, purpose=purpose, otp=otp) # Using recipient_identifier as OTP key part

        # Use NotificationService to send OTP
        notification_service = NotificationService()
        try:
            # Construct content or use a template
            content = f"Your OTP for {purpose.replace('_', ' ')} is {otp}. It is valid for {OTP_EXPIRY_MINUTES} minutes."

            # This schema expects either direct_content OR content_params for a template
            # For OTP, direct_content is usually simpler.
            notification_service.trigger_notification(db, notification_data=schemas.NotificationCreateSchema(
                customer_id=db_profile.customer_id, # Link to customer
                digital_user_profile_id=db_profile.id,
                recipient_identifier=recipient_identifier, # e.g., phone number for SMS
                channel_type=delivery_channel, # e.g., ChannelTypeEnum.SMS_BANKING
                message_type=f"OTP_{purpose}",
                direct_content=content,
                reference_id=f"OTP_{db_profile.id}_{purpose}"
            ))
            self._audit_log(db, f"OTP_SENT_{purpose}", db_profile, f"OTP sent to {recipient_identifier} via {delivery_channel.value}.")
            return True
        except Exception as e:
            # Log actual exception e
            self._audit_log(db, f"OTP_SEND_FAIL_{purpose}", db_profile, f"Failed to send OTP to {recipient_identifier}: {str(e)}.")
            return False

    def verify_otp_for_profile(self, db: Session, profile_id: int, purpose: str, otp_code: str, recipient_identifier: str) -> bool:
        # recipient_identifier used in OTP storage key
        db_profile = self._get_digital_user_profile(db, user_id=profile_id)
        if not db_profile: return False # Should not happen if called after profile identification

        if verify_and_consume_otp(identifier=recipient_identifier, purpose=purpose, otp_code=otp_code):
            self._audit_log(db, f"OTP_VERIFY_SUCCESS_{purpose}", db_profile, f"OTP verified successfully for {recipient_identifier}.")
            return True
        else:
            self._audit_log(db, f"OTP_VERIFY_FAIL_{purpose}", db_profile, f"OTP verification failed for {recipient_identifier}.")
            return False


# --- RegisteredDevice Service ---
class RegisteredDeviceService(BaseDigitalChannelService):
    def register_device(self, db: Session, profile_id: int, device_in: schemas.RegisteredDeviceCreate) -> models.RegisteredDevice:
        db_profile = self._get_digital_user_profile(db, user_id=profile_id)
        if not db_profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Digital user profile not found.")

        existing_device = db.query(models.RegisteredDevice).filter(
            models.RegisteredDevice.digital_user_profile_id == profile_id,
            models.RegisteredDevice.device_identifier == device_in.device_identifier
        ).first()

        if existing_device:
            # If exists and PENDING_VERIFICATION, allow re-registration/update. Otherwise, might be an issue.
            if existing_device.status == "ACTIVE":
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device already registered and active.")
            # Update existing pending/blocked record
            for field, value in device_in.dict(exclude_unset=True).items():
                setattr(existing_device, field, value)
            existing_device.status = "PENDING_VERIFICATION" # Reset status if re-registering
            existing_device.registration_date = datetime.utcnow() # Update registration date
            db_device = existing_device
        else:
            db_device = models.RegisteredDevice(**device_in.dict(), digital_user_profile_id=profile_id)
            db.add(db_device)

        db.commit()
        db.refresh(db_device)
        self._audit_log(db, "DEVICE_REGISTER", db_profile, f"Device '{db_device.device_name or db_device.device_identifier}' registration initiated/updated.", entity_id=str(db_device.id))
        return db_device

    def get_devices_for_user(self, db: Session, profile_id: int) -> List[models.RegisteredDevice]:
        return db.query(models.RegisteredDevice).filter(models.RegisteredDevice.digital_user_profile_id == profile_id).all()

    def update_device_status_or_details(self, db: Session, device_id: int, device_update_in: schemas.RegisteredDeviceUpdate, profile_id: int) -> Optional[models.RegisteredDevice]:
        db_device = db.query(models.RegisteredDevice).filter(models.RegisteredDevice.id == device_id, models.RegisteredDevice.digital_user_profile_id == profile_id).first()
        if not db_device:
            return None

        update_data = device_update_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_device, field, value)

        db.commit()
        db.refresh(db_device)
        # Audit log needs to know which profile performed this
        db_profile = self._get_digital_user_profile(db, user_id=profile_id)
        self._audit_log(db, "DEVICE_UPDATE", db_profile, f"Device ID {db_device.id} details updated.", entity_id=str(db_device.id))
        return db_device

    def remove_device(self, db: Session, device_id: int, profile_id: int) -> bool:
        db_device = db.query(models.RegisteredDevice).filter(models.RegisteredDevice.id == device_id, models.RegisteredDevice.digital_user_profile_id == profile_id).first()
        if db_device:
            db_profile = self._get_digital_user_profile(db, user_id=profile_id) # For audit
            db.delete(db_device)
            db.commit()
            self._audit_log(db, "DEVICE_REMOVE", db_profile, f"Device ID {device_id} removed.", entity_id=str(device_id))
            return True
        return False

# --- SessionLog Service ---
class SessionLogService(BaseDigitalChannelService):
    def create_session_log(self, db: Session, profile_id: int, channel: schemas.ChannelTypeEnum,
                           ip_address: Optional[str], user_agent: Optional[str],
                           device_id: Optional[int] = None, session_jti: Optional[str] = None) -> models.SessionLog:
        db_log = models.SessionLog(
            digital_user_profile_id=profile_id,
            channel=channel,
            ip_address=ip_address,
            user_agent=user_agent,
            registered_device_id=device_id,
            session_token_jti=session_jti,
            is_active=True
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        # Minimal audit, as session log itself is a log.
        return db_log

    def end_session_log(self, db: Session, session_jti: Optional[str] = None, session_id_pk: Optional[int] = None) -> Optional[models.SessionLog]:
        db_log = None
        if session_jti:
            db_log = db.query(models.SessionLog).filter(models.SessionLog.session_token_jti == session_jti, models.SessionLog.is_active == True).first()
        elif session_id_pk:
            db_log = db.query(models.SessionLog).filter(models.SessionLog.id == session_id_pk, models.SessionLog.is_active == True).first()

        if db_log:
            db_log.logout_time = datetime.utcnow()
            db_log.is_active = False
            db.commit()
            db.refresh(db_log)
            # Audit this logout event for the user associated with db_log.digital_user_profile_id
            # self._audit_log(db, "DIGITAL_LOGOUT", profile_id=db_log.digital_user_profile_id, summary=f"Session {db_log.id} ended.")
            return db_log
        return None

# --- USSD Service (Conceptual - Menu logic is complex) ---
class USSDService(BaseDigitalChannelService):
    # This is highly simplified. Real USSD apps use a menu definition structure
    # (e.g., XML, JSON, or Python dicts) and a state machine.

    async def handle_ussd_request(self, db: Session, request_data: schemas.USSDRequestSchema) -> schemas.USSDResponseSchema:
        session_id = request_data.sessionId
        msisdn = request_data.msisdn # Normalize this msisdn
        user_input = request_data.ussdString

        # Try to find existing session or create new
        ussd_session = db.query(models.USSDSession).filter(models.USSDSession.id == session_id).first()

        digital_profile: Optional[models.DigitalUserProfile] = None
        # Try to link MSISDN to a digital user profile (e.g. via customer's phone number)
        # This requires querying Customer table based on phone, then getting DigitalUserProfile
        # For now, we'll assume this link can be established if user is registered.

        if not ussd_session:
            # New session
            # Check if MSISDN is registered (simplified check)
            # In real scenario: query Customer by phone, then get DigitalUserProfile
            # For now, we'll mock this. If user_input could be PIN for initial auth:
            # digital_profile = self._get_profile_by_phone_and_verify_pin(db, msisdn, initial_pin_if_any)

            ussd_session = models.USSDSession(
                id=session_id,
                phone_number=msisdn,
                # digital_user_profile_id = digital_profile.id if digital_profile else None,
                current_menu_code="MAIN_MENU_UNAUTH" if not digital_profile else "MAIN_MENU_AUTH",
                session_data_json=json.dumps({}),
                expires_at=datetime.utcnow() + timedelta(minutes=USSD_SESSION_TIMEOUT_MINUTES),
                status="ACTIVE"
            )
            db.add(ussd_session)
        else:
            # Existing session, update expiry and last interaction
            ussd_session.expires_at = datetime.utcnow() + timedelta(minutes=USSD_SESSION_TIMEOUT_MINUTES)
            ussd_session.last_interaction_at = datetime.utcnow()
            if ussd_session.digital_user_profile_id:
                digital_profile = self._get_digital_user_profile(db, user_id=ussd_session.digital_user_profile_id)


        session_data = json.loads(ussd_session.session_data_json or "{}")

        # --- Simplified Menu Logic ---
        # This should be a proper state machine or rule engine
        response_text = ""
        current_menu = ussd_session.current_menu_code

        if current_menu == "MAIN_MENU_UNAUTH":
            if not user_input: # First request
                response_text = "CON Welcome to WeezyBank!\n1. Login (Enter PIN)\n2. Register\n3. Info"
                ussd_session.current_menu_code = "MAIN_MENU_UNAUTH_CHOICE"
            # ... handle choices for UNAUTH ...
        elif current_menu == "MAIN_MENU_AUTH":
            if not digital_profile: # Should not happen if menu is AUTH
                 response_text = "END Error: Authentication lost. Please redial."
            elif not user_input:
                response_text = f"CON Welcome {digital_profile.username}!\n1. Balance\n2. Transfer\n0. Exit"
                ussd_session.current_menu_code = "MAIN_MENU_AUTH_CHOICE"
            # ... handle choices for AUTH ...
        # ... more menu states ...
        else: # Default or unknown state
            response_text = "END Invalid option. Please try again."
            ussd_session.status = "COMPLETED" # Or TIMED_OUT if error

        # Example: PIN entry state
        if current_menu == "AWAITING_PIN_FOR_LOGIN":
            if user_input and len(user_input) == 4: # Assuming 4-digit PIN
                # profile_to_auth = self._get_profile_by_phone(db, msisdn) # More complex lookup
                # if profile_to_auth and self.verify_transaction_pin(db, profile_to_auth.id, user_input):
                #    ussd_session.digital_user_profile_id = profile_to_auth.id
                #    ussd_session.current_menu_code = "MAIN_MENU_AUTH"
                #    response_text = "CON Login successful! Main Menu...\n1. Balance..." # Recursive call or next menu
                # else:
                #    response_text = "CON Invalid PIN. Try again or 0 to go back."
                #    # Handle PIN attempts
                pass # Placeholder for actual PIN verification logic
            else:
                response_text = "CON Invalid PIN format. Enter your 4-digit PIN."


        if not response_text.startswith("CON ") and not response_text.startswith("END "):
             response_text = "END An unexpected error occurred. Please redial." # Default to END if not set

        ussd_session.session_data_json = json.dumps(session_data)
        if response_text.startswith("END "):
            ussd_session.status = "COMPLETED"

        db.commit()
        # db.refresh(ussd_session) # Not strictly needed before returning schema

        return schemas.USSDResponseSchema(response_string=response_text)


# --- Notification Service ---
class NotificationService(BaseDigitalChannelService):
    # This service would integrate with actual providers (Twilio, SendGrid, FCM/APNS)

    def trigger_notification(self, db: Session, notification_data: schemas.NotificationCreateSchema) -> models.NotificationLog:
        # 1. Determine recipient identifier if not directly provided
        recipient = notification_data.recipient_identifier
        content = notification_data.direct_content # Assuming direct content for now

        if not recipient:
            # Logic to derive recipient from customer_id or digital_user_profile_id
            # This is complex and needs access to Customer contact details.
            # For demo, we'll assume recipient_identifier is usually provided for OTP etc.
            raise HTTPException(status_code=500, detail="Recipient identifier could not be determined.")

        if not content and notification_data.content_params:
            # Logic to fetch template and render with params
            # content = self._render_template(template_id, notification_data.content_params)
            raise NotImplementedError("Template-based content generation not yet implemented.")
        elif not content and not notification_data.content_params:
             raise ValueError("Notification content or params for template must be provided.")


        # 2. Simulate sending via the specified channel
        status = "PENDING" # Initial status
        external_id = None
        failure_reason = None
        sent_at = None

        try:
            if notification_data.channel_type == schemas.ChannelTypeEnum.SMS_BANKING or notification_data.channel_type == schemas.ChannelTypeEnum.USSD: # USSD might send SMS receipts
                # Simulate SMS sending
                print(f"SIMULATE SMS to {recipient}: {content}")
                status = "SENT" # Assume success for simulation
                external_id = "sms_sim_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
                sent_at = datetime.utcnow()
            elif notification_data.channel_type == schemas.ChannelTypeEnum.INTERNET_BANKING or notification_data.channel_type == schemas.ChannelTypeEnum.MOBILE_BANKING_APP and "EMAIL" in notification_data.message_type.upper() : # Assuming email for these channels
                 # Simulate Email sending
                print(f"SIMULATE EMAIL to {recipient}: Subject: {notification_data.subject}, Body: {content}")
                status = "SENT"
                external_id = "email_sim_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
                sent_at = datetime.utcnow()
            # Add PUSH_NOTIFICATION simulation if needed
            else:
                status = "FAILED"
                failure_reason = "Unsupported notification channel for simulation."
        except Exception as e:
            status = "FAILED"
            failure_reason = str(e)
            # Log actual exception e

        # 3. Log the notification attempt
        log_entry = models.NotificationLog(
            customer_id=notification_data.customer_id,
            digital_user_profile_id=notification_data.digital_user_profile_id,
            channel_type=notification_data.channel_type,
            recipient_identifier=recipient,
            message_type=notification_data.message_type,
            subject=notification_data.subject,
            content=content, # Store the actual content sent
            status=status,
            failure_reason=failure_reason,
            external_message_id=external_id,
            sent_at=sent_at,
            reference_id=notification_data.reference_id
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        # Minimal audit as NotificationLog is a log itself
        # self._audit_log(db, "NOTIFICATION_TRIGGERED", profile_id=notification_data.digital_user_profile_id, summary=f"Notification {log_entry.id} ({status}) to {recipient} via {notification_data.channel_type.value}.")
        return log_entry

# --- Chatbot Service (Conceptual) ---
class ChatbotService(BaseDigitalChannelService):
    async def handle_chatbot_message(self, db: Session, request_data: schemas.ChatbotRequestSchema) -> schemas.ChatbotResponseSchema:
        # 1. Log incoming message
        # 2. (Optional) Authenticate user if user_id is present and session is new
        # 3. Call NLU/NLP service (mocked here)
        #    - intent = nlp_service.detect_intent(request_data.message_text)
        #    - entities = nlp_service.extract_entities(request_data.message_text)
        intent = "UNKNOWN"
        bot_text_response = "I'm sorry, I didn't understand that."

        if "balance" in request_data.message_text.lower():
            intent = "CHECK_BALANCE"
            # Fetch balance (requires user authentication and account linking)
            # if authenticated_user_profile:
            #    balance = account_service.get_primary_account_balance(db, authenticated_user_profile.customer_id)
            #    bot_text_response = f"Your account balance is NGN {balance}."
            # else:
            #    bot_text_response = "Please login to check your balance."
            bot_text_response = "To check balance, please use our secure mobile app or internet banking." # Placeholder

        elif "transfer" in request_data.message_text.lower():
            intent = "INITIATE_TRANSFER"
            bot_text_response = "To make a transfer, please use our secure mobile app or internet banking for safety." # Placeholder

        # 4. Formulate response
        # 5. Log outgoing response and interaction details
        log_entry = models.ChatbotInteractionLog(
            # digital_user_profile_id = ..., customer_id = ..., (if available)
            session_id=request_data.session_id,
            channel=request_data.channel,
            user_message=request_data.message_text,
            bot_response=bot_text_response,
            intent_detected=intent
        )
        db.add(log_entry)
        db.commit()

        return schemas.ChatbotResponseSchema(
            session_id=request_data.session_id,
            bot_response_text=bot_text_response
        )

# Instantiate services
digital_user_profile_service = DigitalUserProfileService()
registered_device_service = RegisteredDeviceService()
session_log_service = SessionLogService()
ussd_service = USSDService()
notification_service = NotificationService()
chatbot_service = ChatbotService()
