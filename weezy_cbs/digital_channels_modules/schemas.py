from pydantic import BaseModel, EmailStr, Field, validator, HttpUrl
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date # Added date
import json

from .models import ChannelTypeEnum # Import the enum from models

# --- DigitalUserProfile Schemas ---
class DigitalUserProfileBase(BaseModel):
    username: str = Field(..., max_length=100, description="Username for digital channels, could be email or custom ID")
    is_active: bool = True
    preferences_json: Optional[Dict[str, Any]] = Field(None, description="User preferences like language, theme")
    notification_settings_json: Optional[Dict[str, Any]] = Field(None, description="Notification preferences per type/channel")

    @validator('preferences_json', 'notification_settings_json', pre=True)
    def parse_json_string_if_needed(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for JSON fields")
        return value

class DigitalUserProfileCreate(DigitalUserProfileBase):
    password: str = Field(..., min_length=8)
    customer_id: int
    security_question_1: Optional[str] = Field(None, max_length=255)
    security_answer_1: Optional[str] = Field(None, min_length=3)

class DigitalUserProfileUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    preferences_json: Optional[Dict[str, Any]] = None
    notification_settings_json: Optional[Dict[str, Any]] = None
    is_verified_email: Optional[bool] = None
    is_verified_phone: Optional[bool] = None
    locked_until: Optional[datetime] = None

    @validator('preferences_json', 'notification_settings_json', pre=True)
    def parse_update_json_string(cls, value):
        if value is None: return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for JSON fields")
        return value

class DigitalUserProfileResponse(DigitalUserProfileBase):
    id: int
    customer_id: int
    is_verified_email: bool
    is_verified_phone: bool
    last_login_channel: Optional[ChannelTypeEnum] = None
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    failed_login_attempts: int
    locked_until: Optional[datetime] = None
    is_transaction_pin_set: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True


class DigitalUserPasswordChangeSchema(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class DigitalUserTransactionPinSetSchema(BaseModel):
    password: str
    new_pin: str = Field(..., min_length=4, max_length=6, regex=r"^\d{4,6}$")

class DigitalUserTransactionPinChangeSchema(BaseModel):
    current_pin: str = Field(..., min_length=4, max_length=6, regex=r"^\d{4,6}$")
    new_pin: str = Field(..., min_length=4, max_length=6, regex=r"^\d{4,6}$")
    password: Optional[str] = None

class DigitalUserLoginSchema(BaseModel):
    username: str
    password: str
    channel: ChannelTypeEnum
    device_identifier: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class DigitalUserTokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_profile: DigitalUserProfileResponse

class OTPRequestSchema(BaseModel):
    identifier: str
    otp_purpose: str

class OTPVerifySchema(BaseModel):
    identifier: str
    otp_purpose: str
    otp_code: str = Field(..., min_length=6, max_length=6)


# --- RegisteredDevice Schemas ---
class RegisteredDeviceBase(BaseModel):
    device_identifier: str = Field(..., max_length=255)
    device_name: Optional[str] = Field(None, max_length=100)
    device_os: Optional[str] = Field(None, max_length=50)
    app_version: Optional[str] = Field(None, max_length=20)
    push_notification_token: Optional[str] = Field(None, max_length=512)

class RegisteredDeviceCreate(RegisteredDeviceBase):
    pass

class RegisteredDeviceUpdate(BaseModel):
    device_name: Optional[str] = Field(None, max_length=100)
    is_trusted: Optional[bool] = None
    status: Optional[str] = Field(None, max_length=20)
    push_notification_token: Optional[str] = Field(None, max_length=512)


class RegisteredDeviceResponse(RegisteredDeviceBase):
    id: int
    digital_user_profile_id: int
    is_trusted: bool
    status: str
    last_login_from_device_at: Optional[datetime] = None
    registration_date: datetime

    class Config:
        orm_mode = True

class DigitalUserProfileWithDevicesResponse(DigitalUserProfileResponse):
    registered_devices: List[RegisteredDeviceResponse] = []

# --- SessionLog Schemas ---
class SessionLogResponse(BaseModel):
    id: int
    digital_user_profile_id: int
    channel: ChannelTypeEnum
    registered_device_id: Optional[int] = None
    login_time: datetime
    logout_time: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_token_jti: Optional[str] = None
    is_active: bool

    class Config:
        orm_mode = True
        use_enum_values = True

# --- USSD Schemas ---
class USSDRequestSchema(BaseModel):
    sessionId: str
    msisdn: str
    serviceCode: str
    ussdString: Optional[str] = Field(None, description="User's input, empty for initial request")

class USSDResponseSchema(BaseModel):
    response_string: str = Field(..., description="The text to display to the user. Prefix with CON or END.")

class USSDSessionData(BaseModel):
    current_menu_code: Optional[str] = None
    language_code: str = "en"
    amount: Optional[float] = None
    beneficiary_account: Optional[str] = None
    pin_attempts: int = 0

class USSDPinVerificationRequest(BaseModel):
    session_id: str
    pin: str = Field(..., min_length=4, max_length=4, regex=r"^\d{4}$")


# --- NotificationLog Schemas ---
class NotificationCreateSchema(BaseModel):
    customer_id: Optional[int] = None
    digital_user_profile_id: Optional[int] = None
    recipient_identifier: Optional[str] = Field(None, max_length=255, description="Explicit phone/email if not deriving from profile")
    channel_type: ChannelTypeEnum
    message_type: str = Field(..., max_length=50, description="e.g., OTP, TRANSACTION_ALERT, WELCOME_EMAIL")
    subject: Optional[str] = Field(None, max_length=255)
    content_params: Optional[Dict[str, Any]] = Field(None, description="Parameters for template-based content generation")
    direct_content: Optional[str] = Field(None, description="Use if content is not template-based")
    reference_id: Optional[str] = Field(None, max_length=50)

    @validator('direct_content', always=True)
    def check_content_or_params_exist(cls, v, values):
        if not v and not values.get('content_params'):
            raise ValueError('Either direct_content or content_params must be provided')
        if v and values.get('content_params'):
            raise ValueError('Provide either direct_content or content_params, not both')
        return v

class NotificationLogResponse(BaseModel):
    id: int
    customer_id: Optional[int] = None
    digital_user_profile_id: Optional[int] = None
    channel_type: ChannelTypeEnum
    recipient_identifier: str
    message_type: Optional[str] = None
    subject: Optional[str] = None
    content: str
    status: str
    failure_reason: Optional[str] = None
    external_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    reference_id: Optional[str] = None

    class Config:
        orm_mode = True
        use_enum_values = True

# --- Chatbot Schemas ---
class ChatbotRequestSchema(BaseModel):
    session_id: str = Field(..., description="Unique ID for the chat session")
    user_id: Optional[str] = Field(None, description="Authenticated user ID if available, else anonymous")
    customer_id: Optional[int] = None
    message_text: str = Field(..., description="User's message to the chatbot")
    channel: ChannelTypeEnum = Field(..., description="e.g., WHATSAPP_BOT, WEB_CHAT")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata like language, location if available")

class ChatbotResponseSchema(BaseModel):
    session_id: str
    bot_response_text: str
    suggested_actions: Optional[List[str]] = None
    is_escalated: bool = False

class ChatbotInteractionLogResponse(BaseModel):
    id: int
    digital_user_profile_id: Optional[int] = None
    customer_id: Optional[int] = None
    session_id: str
    channel: ChannelTypeEnum
    user_message: Optional[str] = None
    bot_response: Optional[str] = None
    intent_detected: Optional[str] = None
    entities_extracted_json: Optional[Dict[str, Any]] = None
    confidence_score: Optional[str] = None
    timestamp: datetime
    feedback_rating: Optional[int] = None
    is_escalated: bool

    @validator('entities_extracted_json', pre=True)
    def parse_json_string_if_needed(cls, value): # Renamed validator
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {"error": "Invalid JSON string in entities_extracted_json"}
        return value

    class Config:
        orm_mode = True
        use_enum_values = True

# --- Schemas for Customer Dashboard ---
class DashboardAccountSummarySchema(BaseModel):
    account_id: int
    account_number_masked: str
    account_type: str
    available_balance: float
    currency: str
    account_nickname: Optional[str] = None

class DashboardTransactionSummarySchema(BaseModel):
    id: str
    date: datetime
    description: str
    amount: float
    currency: str
    transaction_type: str
    status: str

class DashboardLoanSummarySchema(BaseModel):
    loan_account_id: int
    loan_product_name: str
    outstanding_principal: float
    outstanding_interest: float
    total_outstanding: float
    currency: str
    next_repayment_date: Optional[date] = None
    next_repayment_amount: Optional[float] = None

class CustomerDashboardSummaryResponse(BaseModel):
    welcome_name: str
    last_login_at: Optional[datetime] = None
    accounts: List[DashboardAccountSummarySchema] = []
    recent_transactions: List[DashboardTransactionSummarySchema] = []
    active_loans: List[DashboardLoanSummarySchema] = []
    unread_notification_count: int = 0

    class Config:
        orm_mode = True

# --- Paginated Responses for Digital Channels ---
class PaginatedDigitalUserProfileResponse(BaseModel):
    items: List[DigitalUserProfileResponse]
    total: int
    page: int
    size: int

class PaginatedRegisteredDeviceResponse(BaseModel):
    items: List[RegisteredDeviceResponse]
    total: int
    page: int
    size: int

class PaginatedSessionLogResponse(BaseModel):
    items: List[SessionLogResponse]
    total: int
    page: int
    size: int

class PaginatedNotificationLogResponse(BaseModel):
    items: List[NotificationLogResponse]
    total: int
    page: int
    size: int

class PaginatedChatbotInteractionLogResponse(BaseModel):
    items: List[ChatbotInteractionLogResponse]
    total: int
    page: int
    size: int
