from pydantic import BaseModel, Field, validator, HttpUrl, Json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import json

from .models import APIServiceAuthMethodEnum, WebhookProcessingStatusEnum

# --- APIServiceConfig Schemas ---
class APIServiceConfigBase(BaseModel):
    service_name: str = Field(..., max_length=100, description="Unique identifier for the service, e.g., CRC_CREDIT_BUREAU")
    description: Optional[str] = None
    base_url: HttpUrl
    authentication_method: APIServiceAuthMethodEnum
    # credentials_config_json: This will be handled carefully.
    # For create/update, accept a dict. For response, it should be masked or omitted.
    additional_headers_json: Optional[Dict[str, str]] = Field(None, description='e.g., {"X-Custom-Header": "value"}')
    timeout_seconds: int = Field(30, ge=5, le=300) # 5 to 300 seconds
    retry_policy_json: Optional[Dict[str, Any]] = Field(None, description='e.g., {"max_retries": 3, "backoff_factor": 0.5}')
    is_active: bool = True

    @validator('additional_headers_json', 'retry_policy_json', pre=True)
    def parse_json_string_if_needed(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for JSON field")
        return value

class APIServiceConfigCreate(APIServiceConfigBase):
    # For create, accept credentials as a dictionary. Service layer will handle encryption/storage.
    credentials_config_json: Optional[Dict[str, Any]] = Field(None, description="Credentials specific to auth_method, e.g. API keys, client_id/secret. Will be encrypted by service.")
    # Example for API_KEY_HEADER: {"header_name": "X-Api-Key", "api_key": "actual_key_value"}
    # Example for OAUTH2: {"token_url": "...", "client_id": "...", "client_secret": "...", "scopes": "read write"}

class APIServiceConfigUpdate(BaseModel): # Partial updates
    description: Optional[str] = None
    base_url: Optional[HttpUrl] = None
    authentication_method: Optional[APIServiceAuthMethodEnum] = None
    credentials_config_json: Optional[Dict[str, Any]] = Field(None, description="Provide new credentials to update. Service handles encryption.")
    additional_headers_json: Optional[Dict[str, str]] = None
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300)
    retry_policy_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    @validator('additional_headers_json', 'retry_policy_json', 'credentials_config_json', pre=True)
    def parse_update_json_string_if_needed(cls, value): # Duplicate for update
        if value is None: return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for JSON field")
        return value

class APIServiceConfigResponse(APIServiceConfigBase):
    id: int
    # IMPORTANT: credentials_config_json should NOT be returned directly if it contains secrets.
    # Instead, return masked version or status indicators.
    # For simplicity in this phase, we might return it, but flag for masking.
    credentials_config_json: Optional[Dict[str, Any]] = Field(None, description="MASKED/OMITTED in real production responses for security")
    last_health_check_at: Optional[datetime] = None
    last_health_check_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # created_by_user_id: Optional[int] = None

    class Config:
        orm_mode = True
        use_enum_values = True


# --- ExternalServiceLog Schemas ---
class ExternalServiceLogResponse(BaseModel):
    id: int
    api_service_config_id: Optional[int] = None
    service_name_called: str
    request_timestamp: datetime
    response_timestamp: Optional[datetime] = None
    http_method: str
    endpoint_url_called: str
    # Payloads should be masked/summarized if sensitive, or only available to specific roles
    request_headers_json: Optional[Dict[str, Any]] = Field(None, description="Potentially MASKED/SUMMARIZED")
    request_payload_json: Optional[Any] = Field(None, description="Potentially MASKED/SUMMARIZED") # Could be dict or string
    response_headers_json: Optional[Dict[str, Any]] = Field(None, description="Potentially MASKED/SUMMARIZED")
    response_payload_json: Optional[Any] = Field(None, description="Potentially MASKED/SUMMARIZED")
    status_code_received: Optional[int] = None
    is_success: Optional[bool] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    correlation_id: Optional[str] = None
    # financial_transaction_id: Optional[int] = None

    @validator('request_headers_json', 'request_payload_json', 'response_headers_json', 'response_payload_json', pre=True)
    def parse_log_json_fields(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError: # If not valid JSON, return as string (might be non-JSON payload)
                return value
        return value

    class Config:
        orm_mode = True

# --- WebhookEventLog Schemas ---
class WebhookEventLogResponse(BaseModel):
    id: int
    api_service_config_id: Optional[int] = None # If webhook source is a configured service
    source_service_name: str
    event_type: Optional[str] = None
    received_at: datetime
    source_ip_address: Optional[str] = None
    request_headers_json: Optional[Dict[str, Any]] = None # Parsed from Text
    # raw_payload: str # Keep as string to show exactly what was received
    raw_payload_parsed: Optional[Any] = Field(None, description="Attempted JSON parsing of raw_payload")

    processing_status: WebhookProcessingStatusEnum
    processing_notes_or_error: Optional[str] = None
    processed_at: Optional[datetime] = None
    is_signature_verified: Optional[bool] = None
    related_internal_reference_id: Optional[str] = None
    # financial_transaction_id: Optional[int] = None

    @validator('request_headers_json', pre=True)
    def parse_webhook_headers_json(cls, value):
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: return {"error": "Invalid JSON in headers"}
        return value

    # A separate field for parsed payload, original `raw_payload` remains string
    # This can be populated by a @root_validator or in the service layer.
    # For simplicity, we assume service might add it if payload is JSON.

    class Config:
        orm_mode = True
        use_enum_values = True

class WebhookProcessingUpdateRequest(BaseModel): # For admin to manually update status
    processing_status: WebhookProcessingStatusEnum
    processing_notes_or_error: Optional[str] = None


# --- Generic Webhook Schemas (Conceptual) ---
class GenericWebhookPayload(BaseModel): # Can be used with Request.body() and manual parsing
    # Actual structure is unknown and varies by provider
    # This is a placeholder if you want to type hint a very generic incoming dict
    event: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    # Add other common top-level fields if any pattern exists across webhooks

# --- Paginated Responses ---
class PaginatedAPIServiceConfigResponse(BaseModel):
    items: List[APIServiceConfigResponse]
    total: int
    page: int
    size: int

class PaginatedExternalServiceLogResponse(BaseModel):
    items: List[ExternalServiceLogResponse]
    total: int
    page: int
    size: int

class PaginatedWebhookEventLogResponse(BaseModel):
    items: List[WebhookEventLogResponse]
    total: int
    page: int
    size: int
