# Pydantic schemas for Payments Integration Layer
from pydantic import BaseModel, Field, HttpUrl, validator, EmailStr # Added EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, date # Added date
import decimal
import enum # For Pydantic enums

# Import enums from models to ensure consistency
from .models import (
    PaymentGatewayEnum as ModelPaymentGatewayEnum,
    APILogDirectionEnum as ModelAPILogDirectionEnum,
    APILogStatusEnum as ModelAPILogStatusEnum,
    CurrencyEnum as ModelCurrencyEnum
)

# Schema Enums
class CurrencySchema(str, enum.Enum): # Replicated for independence if needed
    NGN = "NGN"; USD = "USD"; EUR = "EUR"; GBP = "GBP"

class PaymentGatewaySchema(str, enum.Enum):
    PAYSTACK = "PAYSTACK"; FLUTTERWAVE = "FLUTTERWAVE"; MONNIFY = "MONNIFY"; REMITA = "REMITA"
    INTERSWITCH_WEB = "INTERSWITCH_WEB"; NIBSS_EBILLSPAY = "NIBSS_EBILLSPAY"; NQR = "NQR"

class APILogDirectionSchema(str, enum.Enum):
    OUTGOING = "OUTGOING"; INCOMING = "INCOMING"

class APILogStatusSchema(str, enum.Enum):
    SUCCESS = "SUCCESS"; FAILED = "FAILED"; PENDING = "PENDING"


# --- API Log Schemas (Primarily for internal use/auditing) ---
class PaymentAPILogBase(BaseModel):
    gateway: PaymentGatewaySchema
    endpoint_url: str = Field(..., max_length=512)
    http_method: str = Field(..., max_length=10)
    direction: APILogDirectionSchema
    request_headers: Optional[Dict[str, str]] = None
    request_payload: Optional[Any] = None
    response_status_code: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_payload: Optional[Any] = None
    status: APILogStatusSchema
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    financial_transaction_id: Optional[str] = Field(None, max_length=40)
    external_reference: Optional[str] = Field(None, max_length=100)
    internal_reference: Optional[str] = Field(None, max_length=100)

class PaymentAPILogCreateRequest(PaymentAPILogBase): # Renamed
    pass

class PaymentAPILogResponse(PaymentAPILogBase):
    id: int
    timestamp: datetime
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}


# --- Payment Gateway Config Schemas (For admin/setup) ---
class PaymentGatewayConfigBase(BaseModel):
    gateway: PaymentGatewaySchema
    base_url: HttpUrl
    merchant_id: Optional[str] = Field(None, max_length=100)
    additional_headers_json: Optional[Dict[str, str]] = Field(None, description='JSON fixed headers for gateway')
    is_active: bool = True

class PaymentGatewayConfigCreateRequest(PaymentGatewayConfigBase): # Renamed
    api_key_plain: Optional[str] = None
    secret_key_plain: Optional[str] = None
    public_key_plain: Optional[str] = None
    webhook_secret_key_plain: Optional[str] = None

class PaymentGatewayConfigResponse(PaymentGatewayConfigBase):
    id: int
    # To indicate if keys are set, not the keys themselves
    # has_api_key: bool = False
    # has_secret_key: bool = False
    # has_public_key: bool = False
    # has_webhook_secret: bool = False
    last_updated: Optional[datetime] = None
    class Config: orm_mode = True; use_enum_values = True

# --- Webhook Event Schemas (For internal processing) ---
class WebhookEventData(BaseModel):
    gateway: PaymentGatewaySchema
    event_type: str = Field(..., max_length=100)
    event_id_external: Optional[str] = Field(None, max_length=100)
    payload_received: Dict[str, Any]
    headers_received: Optional[Dict[str, str]] = None

class WebhookProcessResponse(BaseModel):
    status: str
    message: Optional[str] = None
    financial_transaction_id: Optional[str] = Field(None, max_length=40)

# --- Payment Initiation Schemas (Generic) ---
class UnifiedPaymentInitiationRequest(BaseModel): # Renamed
    financial_transaction_id: str = Field(..., max_length=40) # Master FT ID
    gateway_preference: Optional[PaymentGatewaySchema] = None
    amount: decimal.Decimal = Field(..., decimal_places=2)
    currency: CurrencySchema
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    redirect_url: Optional[HttpUrl] = None
    callback_url: Optional[HttpUrl] = None # Our webhook endpoint for this transaction
    metadata: Optional[Dict[str, Any]] = None
    # payment_method_details: Optional[Dict[str, Any]] = None # e.g. card_token for card payment

class UnifiedPaymentInitiationResponse(BaseModel): # Renamed
    financial_transaction_id: str
    status: str # PENDING_USER_ACTION, PENDING_GATEWAY_CONFIRMATION, SUCCESSFUL, FAILED
    gateway_used: PaymentGatewaySchema
    gateway_reference: Optional[str] = None
    authorization_url: Optional[HttpUrl] = None # If user needs to be redirected
    message: Optional[str] = None

# --- Bill Payment Schemas ---
class BillerCategoryResponse(BaseModel):
    id: str; name: str
    class Config: orm_mode = True

class BillerResponse(BaseModel):
    id: str; name: str; category_id: str
    # payment_items: List[PaymentItemResponse] = [] # Embed payment items
    class Config: orm_mode = True

class PaymentItemResponse(BaseModel):
    id: str; name: str; biller_id: str
    amount_fixed: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    amount_min: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    amount_max: Optional[decimal.Decimal] = Field(None, decimal_places=2)
    # custom_fields_schema: Optional[List[Dict[str, Any]]] = None # Schema for required custom fields
    class Config: orm_mode = True; json_encoders = {decimal.Decimal: str}

class BillPaymentDetailsRequest(BaseModel): # Renamed
    financial_transaction_id: str = Field(..., max_length=40)
    biller_id: str
    payment_item_id: str
    amount: decimal.Decimal = Field(..., decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN
    customer_identifier_on_biller: str # e.g., SmartCard number
    # additional_fields_values: Optional[Dict[str, Any]] = None # Values for custom fields

class BillPaymentDetailsResponse(BaseModel): # Renamed
    financial_transaction_id: str
    status: str
    gateway_reference: Optional[str] = None
    biller_reference: Optional[str] = None
    message: Optional[str] = None
    # receipt_data: Optional[Dict[str, Any]] = None
    class Config: json_encoders = {decimal.Decimal: str}

# --- Airtime/Data Purchase Schemas ---
class AirtimePurchaseRequest(BaseModel): # Renamed
    financial_transaction_id: str = Field(..., max_length=40)
    telco: str
    phone_number: str = Field(..., pattern=r"^\d{11}$")
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    is_data_bundle: bool = False
    bundle_code: Optional[str] = None

class AirtimePurchaseResponse(BaseModel): # Renamed
    financial_transaction_id: str
    status: str
    telco_reference: Optional[str] = None
    message: Optional[str] = None

# --- Payment Link Schemas ---
class PaymentLinkCreateRequest(BaseModel):
    customer_id: Optional[int] = None
    account_to_credit_id: int
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN
    description: Optional[str] = Field(None, max_length=255)
    is_reusable: bool = False
    max_usage_count: Optional[int] = Field(None, gt=0)
    expiry_date: Optional[datetime] = None
    # custom_callback_url_override: Optional[HttpUrl] = None

    @validator('max_usage_count', always=True)
    def _validate_max_usage(cls, v, values): # Renamed validator
        if values.get('is_reusable') is False and v is not None:
            raise ValueError("max_usage_count not allowed if not reusable.")
        if values.get('is_reusable') is True and v is None: # Or some default like 1 if reusable
            raise ValueError("max_usage_count required if reusable.")
        return v

class PaymentLinkResponse(BaseModel):
    id: int
    link_reference: str = Field(..., max_length=50)
    full_payment_url: HttpUrl
    customer_id: Optional[int] = None
    account_to_credit_id: int
    amount: decimal.Decimal = Field(..., decimal_places=2)
    currency: CurrencySchema
    description: Optional[str] = None
    is_reusable: bool
    max_usage_count: Optional[int] = None
    current_usage_count: int
    status: str = Field(..., max_length=20)
    expiry_date: Optional[datetime] = None
    created_at: datetime
    class Config: orm_mode = True; use_enum_values = True; json_encoders = {decimal.Decimal: str}

class PaymentLinkUpdateRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=20) # e.g., "INACTIVE"
    expiry_date: Optional[datetime] = None

# --- NQR Schemas ---
class NQRGenerationDetailsRequest(BaseModel): # Renamed
    # financial_transaction_id: Optional[str] = Field(None, max_length=40)
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencySchema = CurrencySchema.NGN
    # merchant_id_nqr: str
    # account_to_credit_nqr: str
    # description_for_nqr: Optional[str] = None
    # is_one_time_nqr: bool = True

class NQRGenerationDetailsResponse(BaseModel): # Renamed
    qr_code_payload_string: str # Renamed
    # nibss_nqr_reference: Optional[str] = None # Renamed
    # qr_image_base64: Optional[str] = None # If generating image
    class Config: json_encoders = {decimal.Decimal: str}

# --- Gateway Specific Schemas (Example: Paystack) ---
class PaystackInitializeRequest(BaseModel):
    email: EmailStr
    amount: int # Kobo
    currency: str = "NGN"
    reference: Optional[str] = None
    callback_url: Optional[HttpUrl] = None
    metadata: Optional[Dict[str, Any]] = None

class PaystackInitializeResponseData(BaseModel):
    authorization_url: HttpUrl; access_code: str; reference: str

class PaystackInitializeWrapperResponse(BaseModel):
    status: bool; message: str; data: PaystackInitializeResponseData
