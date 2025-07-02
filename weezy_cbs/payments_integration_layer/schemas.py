# Pydantic schemas for Payments Integration Layer
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import decimal

from .models import PaymentGatewayEnum, APILogDirectionEnum, APILogStatusEnum, CurrencyEnum # Enums

# --- API Log Schemas (Primarily for internal use/auditing) ---
class PaymentAPILogBase(BaseModel):
    gateway: PaymentGatewayEnum
    endpoint_url: str
    http_method: str
    direction: APILogDirectionEnum
    request_headers: Optional[Dict[str, str]] = None
    request_payload: Optional[Any] = None # Can be dict, list, str
    response_status_code: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_payload: Optional[Any] = None
    status: APILogStatusEnum
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    # financial_transaction_id: Optional[str] = None
    external_reference: Optional[str] = None
    internal_reference: Optional[str] = None

class PaymentAPILogCreate(PaymentAPILogBase):
    pass # All fields from base needed for creation

class PaymentAPILogResponse(PaymentAPILogBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }


# --- Payment Gateway Config Schemas (For admin/setup) ---
class PaymentGatewayConfigBase(BaseModel):
    gateway: PaymentGatewayEnum
    # api_key: Optional[str] = None # Sensitive, handle carefully
    # secret_key: Optional[str] = None # Sensitive
    # public_key: Optional[str] = None # Sensitive
    base_url: HttpUrl
    merchant_id: Optional[str] = None
    is_active: bool = True

class PaymentGatewayConfigCreate(PaymentGatewayConfigBase):
    # When creating, expect plain text keys, service layer will encrypt
    api_key_plain: Optional[str] = None
    secret_key_plain: Optional[str] = None
    public_key_plain: Optional[str] = None

class PaymentGatewayConfigResponse(PaymentGatewayConfigBase):
    id: int
    # Encrypted keys are not exposed in response. Maybe indicate if they are set.
    # has_api_key: bool
    # has_secret_key: bool
    last_updated: Optional[datetime] = None

    class Config:
        orm_mode = True
        use_enum_values = True

# --- Webhook Event Schemas (For internal processing) ---
class WebhookEventData(BaseModel): # Generic structure for incoming webhook data
    gateway: PaymentGatewayEnum
    event_type: str
    event_id_external: Optional[str] = None
    payload_received: Dict[str, Any] # The actual event data from gateway
    headers_received: Optional[Dict[str, str]] = None # For signature validation etc.

class WebhookProcessResponse(BaseModel):
    status: str # e.g. "RECEIVED", "PROCESSED", "IGNORED", "VALIDATION_FAILED"
    message: Optional[str] = None
    # financial_transaction_id: Optional[str] = None # If webhook led to FT update/creation

# --- Payment Initiation Schemas (Generic, can be adapted by specific gateway clients) ---
# These are conceptual, as actual payment initiation often happens via TransactionManagement
# which then calls specific services here. This layer might expose a unified API if desired.

class UnifiedPaymentRequest(BaseModel):
    # This would be a very generic request that this layer then routes to the appropriate gateway
    # financial_transaction_id: str # Master FT ID from TransactionManagement
    gateway_preference: Optional[PaymentGatewayEnum] = None # User/system preference
    amount: decimal.Decimal
    currency: CurrencyEnum
    email: Optional[str] = None # Customer email for notifications
    phone: Optional[str] = None
    # redirect_url: HttpUrl # Where to redirect user after payment attempt (for gateway pages)
    # callback_url: HttpUrl # Where gateway sends async notification
    metadata: Optional[Dict[str, Any]] = None # Custom data
    # payment_method_details: Optional[Dict[str, Any]] = None # e.g. card token, bank for pay-by-bank

class UnifiedPaymentResponse(BaseModel):
    # This would be a generic response, abstracting gateway specifics
    # financial_transaction_id: str
    status: str # PENDING, SUCCESSFUL, FAILED (maps from gateway status)
    gateway_used: PaymentGatewayEnum
    gateway_reference: Optional[str] = None
    # authorization_url: Optional[HttpUrl] = None # If user needs to be redirected (e.g. Paystack)
    message: Optional[str] = None

# --- Bill Payment Schemas (e.g. for NIBSS e-BillsPay or direct biller integration) ---
class BillerCategoryResponse(BaseModel):
    id: str # Biller category ID
    name: str

class BillerResponse(BaseModel):
    id: str # Biller ID (e.g. from NIBSS e-BillsPay)
    name: str
    category_id: str
    # payment_item_ids: List[str] # If biller has multiple payment items

class PaymentItemResponse(BaseModel):
    id: str # Payment item ID (e.g. "DSTV_SUBSCRIPTION_BOXOFFICE")
    name: str
    biller_id: str
    amount_fixed: Optional[decimal.Decimal] = None # If fixed amount
    amount_min: Optional[decimal.Decimal] = None
    amount_max: Optional[decimal.Decimal] = None
    # custom_fields: List[Dict] # Definition of fields required for this payment item (e.g., SmartCard Number)

class BillPaymentRequest(BaseModel):
    # financial_transaction_id: str # Master FT ID
    biller_id: str
    payment_item_id: str
    amount: decimal.Decimal # User entered amount (must be validated against item config)
    currency: CurrencyEnum = CurrencyEnum.NGN
    customer_identifier: str # e.g., SmartCard number, Meter number, Phone number for airtime
    # additional_fields: Optional[Dict[str, Any]] = None # For other custom fields required by biller

class BillPaymentResponse(BaseModel):
    # financial_transaction_id: str
    status: str # PENDING, SUCCESSFUL, FAILED
    gateway_reference: Optional[str] = None
    biller_reference: Optional[str] = None # Reference from the biller if any
    message: Optional[str] = None
    # receipt_details: Optional[Dict[str, Any]] = None # e.g. token for electricity, new expiry for subscription

# --- Airtime/Data Purchase Schemas ---
class AirtimeRequest(BaseModel):
    # financial_transaction_id: str
    telco: str # e.g., "MTN", "GLO", "AIRTEL", "9MOBILE"
    phone_number: str = Field(..., pattern=r"^\d{11}$") # Validate Nigerian phone number
    amount: decimal.Decimal = Field(..., gt=0) # Validate against Telco allowed amounts
    is_data_bundle: bool = False # True if it's a data bundle, false for airtime top-up
    bundle_code: Optional[str] = None # If is_data_bundle is true

class AirtimeResponse(BaseModel):
    # financial_transaction_id: str
    status: str
    telco_reference: Optional[str] = None
    message: Optional[str] = None

# --- Payment Link Schemas ---
class PaymentLinkCreateRequest(BaseModel):
    # customer_id: Optional[int] = None # Who is creating this link
    # account_to_credit_id: int # Which internal account gets the funds
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencyEnum = CurrencyEnum.NGN
    description: Optional[str] = Field(None, max_length=200)
    is_reusable: bool = False
    max_usage_count: Optional[int] = Field(None, gt=0)
    expiry_date: Optional[datetime] = None
    # custom_callback_url: Optional[HttpUrl] = None

    @validator('max_usage_count', always=True)
    def validate_max_usage(cls, v, values):
        if values.get('is_reusable') is False and v is not None:
            raise ValueError("max_usage_count should not be set if link is not reusable.")
        if values.get('is_reusable') is True and v is None:
            raise ValueError("max_usage_count must be set if link is reusable.")
        return v

class PaymentLinkResponse(BaseModel):
    id: int
    link_reference: str # The unique part of the URL
    full_payment_url: HttpUrl # The complete URL to share
    amount: decimal.Decimal
    currency: CurrencyEnum
    description: Optional[str] = None
    is_reusable: bool
    max_usage_count: Optional[int] = None
    current_usage_count: int
    status: str
    expiry_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = { decimal.Decimal: str }

class PaymentLinkUpdateRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = None # e.g., "INACTIVE" to disable a link
    expiry_date: Optional[datetime] = None
    # Cannot update amount or reusability typically after creation for integrity

# --- QR Code Payment Schemas (NQR) ---
class NQRGenerationRequest(BaseModel):
    # financial_transaction_id: Optional[str] = None # If QR is for a specific pre-initiated transaction
    amount: decimal.Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencyEnum = CurrencyEnum.NGN
    # merchant_id: str # Merchant's NQR ID
    # account_to_credit: str # Merchant's account to receive funds
    # description: Optional[str] = None
    # is_one_time: bool = True # If QR is for single use

class NQRGenerationResponse(BaseModel):
    qr_code_string: str # The raw string to be encoded into QR image
    # qr_code_image_url: Optional[HttpUrl] = None # If system generates and hosts the image
    # nqr_reference: str # NIBSS reference for this QR
    # expiry_timestamp: Optional[datetime] = None

# Schemas for each payment gateway (Paystack, Flutterwave, etc.) would also exist here
# defining the specific request/response structures for their APIs if not using their SDKs directly.
# Example for Paystack Initialize Transaction:
class PaystackInitializeRequest(BaseModel):
    email: str
    amount: int # Paystack expects amount in kobo (integer)
    currency: str = "NGN" # Or other supported currencies
    reference: Optional[str] = None # Your unique transaction reference
    callback_url: Optional[HttpUrl] = None
    metadata: Optional[Dict[str, Any]] = None
    # channels: Optional[List[str]] = ['card', 'bank', 'ussd', 'qr', 'mobile_money', 'bank_transfer']

class PaystackInitializeResponseData(BaseModel):
    authorization_url: HttpUrl
    access_code: str
    reference: str

class PaystackInitializeWrapperResponse(BaseModel): # Paystack wraps data in a structure
    status: bool
    message: str
    data: PaystackInitializeResponseData

# This highlights that each gateway will have its own specific schema needs.
# The service layer would handle mapping between our internal/unified schemas and these gateway-specific ones.
