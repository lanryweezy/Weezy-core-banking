# Pydantic schemas for Digital Channels Modules (Shared or Common)
from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Digital User/Session Schemas ---
class DigitalUserLoginRequest(BaseModel):
    username: str
    password: str
    channel: str # "WEB_BANKING", "MOBILE_APP"
    device_id: Optional[str] = None # For mobile app login
    # recaptcha_token: Optional[str] = None # For web

class DigitalUserLoginResponse(BaseModel):
    session_id: str # JWT or opaque session token
    # user_id: int
    customer_id: int
    username: str
    full_name: Optional[str] = None
    # roles: List[str] # Roles relevant to digital channel access
    expires_at: datetime
    # requires_2fa: bool = False
    # two_fa_channel_options: Optional[List[str]] = None # e.g. ["SMS_OTP", "APP_OTP"]

class DeviceRegistrationRequest(BaseModel):
    device_id_unique: str
    device_name: Optional[str] = None
    device_os: Optional[str] = None
    app_version: Optional[str] = None
    fcm_token_or_push_id: Optional[str] = None

class DeviceRegistrationResponse(BaseModel):
    id: int
    device_id_unique: str
    device_name: Optional[str] = None
    is_trusted: bool
    registered_at: datetime
    class Config:
        orm_mode = True

class OTPRequest(BaseModel):
    # For generating and sending OTP
    # customer_id: int # Or username
    purpose: str # e.g., "LOGIN_2FA", "TRANSACTION_AUTHORIZATION", "PASSWORD_RESET"
    channel_preference: Optional[str] = "SMS" # SMS, EMAIL

class OTPResponse(BaseModel):
    message: str # e.g., "OTP sent successfully to your registered phone/email."
    # otp_reference_id: Optional[str] = None # If system needs to track OTP attempts

class OTPVerifyRequest(BaseModel):
    # customer_id: int # Or username
    purpose: str
    otp_code: str = Field(..., min_length=4, max_length=8)
    # otp_reference_id: Optional[str] = None

class OTPVerifyResponse(BaseModel):
    is_valid: bool
    message: str
    # auth_token_for_action: Optional[str] = None # If OTP grants a short-lived token for the intended action

# --- Notification Schemas ---
class NotificationPreferenceUpdate(BaseModel):
    # customer_id: int (usually from path or auth context)
    # preferred_notification_channel: Optional[str] = None # SMS, EMAIL, PUSH_APP
    # receive_promotional_emails: Optional[bool] = None
    # transaction_alert_thresholds: Optional[Dict[str, float]] = None # {"NIP_OUT": 1000, "CARD_TXN": 500}
    pass # Define specific preferences

class NotificationLogResponse(BaseModel):
    id: int
    # customer_id: int
    channel_sent_via: str
    recipient_identifier: str
    message_type: Optional[str] = None
    status: str
    sent_at: datetime
    error_message: Optional[str] = None

    class Config:
        orm_mode = True

# --- Schemas for specific channel functionalities (examples) ---
# These would often be wrappers around core CBS module schemas,
# tailored for the presentation and interaction model of each channel.

# Example: Account Summary for Web/Mobile
class DigitalChannelAccountSummary(BaseModel):
    account_number: str
    account_type: str # e.g. "Savings Account", "Current Account"
    available_balance: decimal.Decimal
    currency: str
    # account_nickname: Optional[str] = None # User-defined nickname

# Example: Transaction History Item for Web/Mobile
class DigitalChannelTransactionItem(BaseModel):
    date: datetime
    description: str # Narration or custom description
    amount: decimal.Decimal
    currency: str
    transaction_type: str # "DEBIT" or "CREDIT" (simplified)
    # running_balance: Optional[decimal.Decimal] = None

# Example: Beneficiary Management for Web/Mobile
class BeneficiaryBase(BaseModel):
    beneficiary_name: str
    account_number: str
    bank_code: str # CBN bank code
    # bank_name: Optional[str] = None # Can be fetched from bank_code
    # nickname: Optional[str] = None

class BeneficiaryCreateRequest(BeneficiaryBase):
    pass

class BeneficiaryResponse(BeneficiaryBase):
    id: int # Internal ID for the saved beneficiary record
    # customer_id: int
    added_at: datetime
    class Config:
        orm_mode = True

# --- USSD Specific Schemas (Conceptual) ---
class USSDRequest(BaseModel):
    session_id: str # Telco provided session ID
    phone_number: str # MSISDN
    ussd_string: str # The full USSD string entered by user, e.g. *123*1*1*Amount#
    # network_code: Optional[str] = None # e.g. MTN, GLO

class USSDResponse(BaseModel):
    session_id: str
    message: str # Message to display to user on USSD screen
    # is_final_response: bool = False # True if session should terminate, False if expecting further input
    # next_menu_level: Optional[str] = None # If navigating menus

# --- Chatbot Specific Schemas (Conceptual) ---
class ChatbotMessageRequest(BaseModel):
    user_id_on_chat_platform: str # e.g. WhatsApp number, Telegram chat ID
    chat_platform: str # WHATSAPP, TELEGRAM, FACEBOOK_MESSENGER
    message_text: str
    # session_id: Optional[str] = None # Ongoing conversation session

class ChatbotMessageResponse(BaseModel):
    reply_text: str
    # suggested_actions: Optional[List[Dict[str,str]]] = None # e.g. [{"title": "Check Balance", "payload": "CHECK_BAL"}]
    # is_session_ended: bool = False

# The APIs for each digital channel (InternetBankingAPI, MobileBankingAPI, USSDHandlerAPI)
# would use these schemas and interact with the service layers of other core modules
# (Accounts, Transactions, CustomerIdentity, etc.) to fulfill user requests.
# This schema file is for shared/common elements or high-level concepts.
# Each sub-module (e.g., `internet_banking`, `mobile_banking`) would have its own more specific schemas.

# Import decimal for balance fields
import decimal
