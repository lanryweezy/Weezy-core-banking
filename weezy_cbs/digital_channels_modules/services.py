# Service layer for Digital Channels Modules (Shared or Common Utilities)
from sqlalchemy.orm import Session
from . import models, schemas
# from weezy_cbs.customer_identity_management.services import get_customer_by_id
# from weezy_cbs.core_infrastructure_config_engine.services import get_user_by_username # For system user/digital user login
# from weezy_cbs.shared import exceptions, security_utils # For OTP, session tokens
# from weezy_cbs.integrations import notification_gateway_service # (Twilio, Mandrill etc.)
import jwt # Example for session tokens
from datetime import datetime, timedelta
import random
import string

# Placeholder for shared exceptions
class AuthenticationException(Exception): pass
class SessionExpiredException(Exception): pass
class InvalidOTPException(Exception): pass
class DeviceNotRegisteredException(Exception): pass

# --- Digital User Authentication & Session Management (Conceptual) ---
# This assumes a DigitalUser model or links Customer to a User model for login.
# For simplicity, let's assume Customer can log in directly or via a linked User.

JWT_SECRET = "your-super-secret-jwt-key-for-digital-channels" # Load from config
JWT_ALGORITHM = "HS256"
SESSION_EXPIRY_MINUTES = 30
OTP_EXPIRY_MINUTES = 5

# Mock OTP store (in a real app, use Redis or DB with expiry)
_otp_store = {} # { (identifier, purpose): {"otp": "1234", "expires_at": datetime_obj} }

def create_digital_session_token(user_id: int, customer_id: int, channel: str) -> str:
    payload = {
        "user_id": user_id, # Could be same as customer_id or a linked system user ID
        "customer_id": customer_id,
        "channel": channel,
        "exp": datetime.utcnow() + timedelta(minutes=SESSION_EXPIRY_MINUTES)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # Persist session to DB (models.DigitalChannelSession) - for tracking active sessions, server-side logout
    # db_session = models.DigitalChannelSession(id=payload.get('jti') or token, user_id=user_id, ...)
    # db.add(db_session); db.commit()
    return token

def verify_digital_session_token(token: str) -> Optional[dict]: # Returns payload if valid
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # Check if session is still active in DB (e.g. not logged out server-side)
        # session_valid_in_db = db.query(models.DigitalChannelSession).filter(models.DigitalChannelSession.id == payload.get('jti'), models.DigitalChannelSession.is_active == True).first()
        # if not session_valid_in_db: raise SessionExpiredException("Session invalidated")
        return payload
    except jwt.ExpiredSignatureError:
        raise SessionExpiredException("Session token has expired.")
    except jwt.InvalidTokenError:
        raise AuthenticationException("Invalid session token.")


def digital_user_login(db: Session, login_req: schemas.DigitalUserLoginRequest) -> schemas.DigitalUserLoginResponse:
    # user = get_user_by_username(db, login_req.username) # From core_infra User model
    # if not user or not security_utils.verify_password(login_req.password, user.hashed_password):
    #     raise AuthenticationException("Invalid username or password.")
    # if not user.is_active:
    #     raise AuthenticationException("User account is inactive.")

    # customer = get_customer_by_id(db, user.customer_id) # Assuming User is linked to Customer
    # if not customer:
    #     raise AuthenticationException("Associated customer profile not found.")

    # Mock successful login:
    mock_user_id = random.randint(1000,2000)
    mock_customer_id = random.randint(1,100)

    # Device check for mobile
    if login_req.channel == "MOBILE_APP" and login_req.device_id:
        # registered_device = db.query(models.RegisteredDevice).filter(models.RegisteredDevice.customer_id == mock_customer_id, models.RegisteredDevice.device_id_unique == login_req.device_id).first()
        # if not registered_device:
        #     # Depending on policy, either fail login or proceed to device registration flow
        #     raise DeviceNotRegisteredException("Device not registered for this user.")
        # registered_device.last_login_from_device = datetime.utcnow()
        # db.commit()
        pass # Placeholder for device check

    # TODO: Implement 2FA check if required for user/channel
    # requires_2fa = check_if_2fa_required(user, login_req.channel)
    # if requires_2fa:
    #    otp_ref = generate_and_send_otp(db, mock_customer_id, "LOGIN_2FA")
    #    return schemas.DigitalUserLoginResponse(..., requires_2fa=True, otp_reference_id=otp_ref)

    session_token = create_digital_session_token(mock_user_id, mock_customer_id, login_req.channel)

    return schemas.DigitalUserLoginResponse(
        session_id=session_token,
        user_id=mock_user_id,
        customer_id=mock_customer_id,
        username=login_req.username,
        full_name="Mock User FullName", # Fetch from user/customer model
        expires_at=datetime.utcnow() + timedelta(minutes=SESSION_EXPIRY_MINUTES)
        # requires_2fa=False # For this simple path
    )

# --- Device Registration ---
def register_device_for_customer(db: Session, reg_req: schemas.DeviceRegistrationRequest, customer_id: int) -> models.RegisteredDevice:
    existing_device = db.query(models.RegisteredDevice).filter(
        models.RegisteredDevice.customer_id == customer_id,
        models.RegisteredDevice.device_id_unique == reg_req.device_id_unique
    ).first()

    if existing_device:
        # Update existing registration (e.g. FCM token, app version)
        existing_device.fcm_token_or_push_id = reg_req.fcm_token_or_push_id or existing_device.fcm_token_or_push_id
        existing_device.app_version = reg_req.app_version or existing_device.app_version
        existing_device.device_name = reg_req.device_name or existing_device.device_name
        db_device = existing_device
    else:
        db_device = models.RegisteredDevice(
            customer_id=customer_id,
            **reg_req.dict()
        )
        db.add(db_device)

    db.commit()
    db.refresh(db_device)
    return db_device

# --- OTP Management ---
def generate_and_send_otp(db: Session, customer_id: int, purpose: str, channel_pref: Optional[str] = "SMS") -> str:
    # customer = get_customer_by_id(db, customer_id)
    # if not customer: raise NotFoundException("Customer not found for OTP generation.")

    otp_code = "".join(random.choices(string.digits, k=6))
    otp_expiry = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    identifier = f"cust_{customer_id}" # Could be phone number or email from customer profile

    _otp_store[(identifier, purpose)] = {"otp": otp_code, "expires_at": otp_expiry}

    # recipient = customer.phone_number if channel_pref == "SMS" else customer.email
    # message_content = f"Your Weezy Bank OTP for {purpose.replace('_',' ')} is {otp_code}. Valid for {OTP_EXPIRY_MINUTES} minutes."

    # try:
    #     notification_gateway_service.send_notification(channel_pref.lower(), recipient, message_content)
    #     _log_notification(db, customer_id, channel_pref, recipient, "OTP", status="SENT")
    # except Exception as e:
    #     _log_notification(db, customer_id, channel_pref, recipient, "OTP", status="FAILED", error=str(e))
    #     raise ExternalServiceException(f"Failed to send OTP: {str(e)}")

    # print(f"DEBUG OTP for {identifier}, purpose {purpose}: {otp_code}") # For testing
    return "OTP_REF_" + uuid.uuid4().hex[:8] # Mock reference

def verify_otp_code(db: Session, customer_id: int, purpose: str, otp_code: str) -> bool:
    identifier = f"cust_{customer_id}"
    stored_otp_data = _otp_store.get((identifier, purpose))

    if not stored_otp_data:
        raise InvalidOTPException("No OTP found or already used for this purpose. Please request a new one.")

    if datetime.utcnow() > stored_otp_data["expires_at"]:
        del _otp_store[(identifier, purpose)] # Clean up expired OTP
        raise InvalidOTPException("OTP has expired. Please request a new one.")

    if stored_otp_data["otp"] == otp_code:
        del _otp_store[(identifier, purpose)] # OTP is single-use
        return True
    else:
        # Implement attempt counter if needed
        raise InvalidOTPException("Invalid OTP code.")

# --- Notification Service (Wrapper around external gateways) ---
def _log_notification(db: Session, customer_id: int, channel: str, recipient: str, msg_type: str, status: str, error: Optional[str]=None):
    log = models.NotificationLog(
        customer_id=customer_id,
        channel_sent_via=channel.upper(),
        recipient_identifier=recipient,
        message_type=msg_type,
        status=status.upper(),
        error_message=error
    )
    db.add(log)
    db.commit() # Commit log

def send_transaction_alert(db: Session, customer_id: int, transaction_details: dict):
    # customer = get_customer_by_id(db, customer_id)
    # if not customer: return

    # Determine preferred channel from customer.preferences or default to SMS
    # preferred_channel = customer.preferences.get("notification_channel", "SMS")
    # recipient = customer.phone_number if preferred_channel == "SMS" else customer.email
    # message = f"Dear Customer, a transaction of {transaction_details['currency']} {transaction_details['amount']:.2f} (Ref: {transaction_details['ref']}) occurred on your account {transaction_details['account_no'][-4:]}."

    # try:
    #     notification_gateway_service.send_notification(preferred_channel.lower(), recipient, message)
    #     _log_notification(db, customer_id, preferred_channel, recipient, "TRANSACTION_ALERT", "SENT")
    # except Exception as e:
    #     _log_notification(db, customer_id, preferred_channel, recipient, "TRANSACTION_ALERT", "FAILED", error=str(e))
    pass # Placeholder for actual notification sending

# --- USSD Service Logic (Conceptual - to be called by USSD API handler) ---
# This would involve a state machine to manage USSD menu navigation.
# For example:
# _ussd_sessions_state = {} # session_id: {"current_menu": "MAIN", "data": {}}

def handle_ussd_request(db: Session, ussd_req: schemas.USSDRequest) -> schemas.USSDResponse:
    # session_id = ussd_req.session_id
    # phone_number = ussd_req.phone_number # Authenticate/Identify user by phone number
    # user_input = ussd_req.ussd_string.split('*')[-1].rstrip('#') # Get last input part

    # state = _ussd_sessions_state.get(session_id, {"current_menu": "MAIN", "data": {}})

    # response_message = ""
    # is_final = False

    # if state["current_menu"] == "MAIN":
    #     if user_input == "" or user_input == "0": # Initial input or back to main
    #         response_message = "Welcome to Weezy Bank USSD!\n1. Check Balance\n2. Transfer Funds\n3. Buy Airtime"
    #     elif user_input == "1":
    #         state["current_menu"] = "BALANCE_ACC_SELECT"
    #         # Fetch user's accounts, present for selection
    #         response_message = "Select Account for Balance:\n1. SAV...1234\n2. CUR...5678" # Mock
    #     # ... other main menu options ...
    #     else:
    #         response_message = "Invalid option. Try again."
    # elif state["current_menu"] == "BALANCE_ACC_SELECT":
    #     # selected_account_idx = int(user_input) -1
    #     # account_to_check = user_accounts[selected_account_idx]
    #     # balance = accounts_service.get_balance(db, account_to_check.number)
    #     response_message = f"Your balance for ACC...1234 is NGN 50,000.00.\n0. Main Menu" # Mock
    #     state["current_menu"] = "MAIN" # Or provide option to end
    #     is_final = True # Or false if offering more options from here
    # # ... other menu states ...

    # _ussd_sessions_state[session_id] = state
    # return schemas.USSDResponse(session_id=session_id, message=response_message, is_final_response=is_final)

    # Mocked USSD handler
    return schemas.USSDResponse(
        session_id=ussd_req.session_id,
        message="USSD Service Mock: You entered: " + ussd_req.ussd_string + "\n1. Option A\n2. Option B",
        # is_final_response=False
    )

# --- Chatbot Service Logic (Conceptual - called by Chatbot API handler) ---
def handle_chatbot_message(db: Session, chat_req: schemas.ChatbotMessageRequest) -> schemas.ChatbotMessageResponse:
    # user_id_on_platform = chat_req.user_id_on_chat_platform
    # message = chat_req.message_text.lower()

    # Authenticate/Identify user based on user_id_on_platform (e.g. link WhatsApp number to customer profile)
    # Use NLU/NLP to understand intent from message

    # reply = "I'm sorry, I didn't understand that."
    # if "balance" in message:
    #     # Assuming user is authenticated and has one primary account for simplicity
    #     # balance_info = accounts_service.get_primary_account_balance(db, customer_id_linked_to_chat_user)
    #     reply = "Your account balance is NGN 75,000.00 (mock)." # Mock
    # elif "transfer" in message:
    #     reply = "To transfer funds, please provide: Beneficiary Account, Bank, Amount, and Narration."
    # # ... other intents ...

    return schemas.ChatbotMessageResponse(reply_text="Chatbot Mock: You said: " + chat_req.message_text)


# The services in this module are often facades or orchestrators that:
# 1. Handle channel-specific authentication and session management.
# 2. Adapt requests from channel-specific formats to core CBS service calls.
# 3. Format responses from core CBS services into channel-specific presentation.
# 4. Manage channel-specific user preferences and notifications.
# Each sub-channel (web, mobile, USSD, chatbot) would have its own set of more detailed services.
# This file contains common/shared utilities or high-level orchestration if a unified approach is taken.

# Import decimal for balance fields if any are handled here directly
import decimal
