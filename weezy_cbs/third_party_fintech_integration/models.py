# Database models for Third-Party & Fintech Integration Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLAlchemyEnum, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

from weezy_cbs.database import Base # Use the shared Base

class APIServiceAuthMethodEnum(enum.Enum):
    API_KEY_HEADER = "API_KEY_HEADER" # API Key in header
    BEARER_TOKEN = "BEARER_TOKEN"   # Bearer token in Authorization header
    OAUTH2_CLIENT_CREDENTIALS = "OAUTH2_CLIENT_CREDENTIALS"
    BASIC_AUTH = "BASIC_AUTH"       # Username/Password in Authorization header
    NO_AUTH = "NO_AUTH"             # For public or test endpoints
    CUSTOM_SIGNATURE = "CUSTOM_SIGNATURE" # e.g. AWS Signature V4, or custom HMAC

class WebhookProcessingStatusEnum(enum.Enum):
    PENDING = "PENDING"             # Received, not yet processed
    PROCESSING = "PROCESSING"           # Actively being processed
    PROCESSED_SUCCESS = "PROCESSED_SUCCESS" # Successfully processed, action taken
    PROCESSED_PARTIAL = "PROCESSED_PARTIAL" # Some actions taken, some failed
    FAILED_VALIDATION = "FAILED_VALIDATION" # Payload invalid or signature mismatch
    ERROR_PROCESSING = "ERROR_PROCESSING"   # Error during business logic execution
    IGNORED_DUPLICATE = "IGNORED_DUPLICATE" # Ignored as it was a duplicate event
    IGNORED_NO_ACTION = "IGNORED_NO_ACTION" # Event type recognized but no action needed by our system

class APIServiceConfig(Base):
    __tablename__ = "api_service_configs"
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    base_url = Column(String(255), nullable=False)
    # Sensitive credentials should be stored encrypted or in a vault. These fields might store references or be placeholders.
    # For API_KEY_HEADER: api_key_name (e.g. "X-API-Key"), api_key_value_encrypted
    # For BEARER_TOKEN: token_value_encrypted (if static) or mechanism to fetch/refresh
    # For OAUTH2: client_id_encrypted, client_secret_encrypted, token_url
    # For BASIC_AUTH: username_encrypted, password_encrypted
    credentials_config_json = Column(Text, nullable=True, comment="JSON storing necessary credential parts, mostly encrypted or references to vault secrets.")
    # Example for API_KEY_HEADER: {"header_name": "X-Api-Key", "api_key_secret_ref": "arn:aws:secretsmanager:..."}
    # Example for OAUTH2: {"token_url": "...", "client_id_secret_ref": "...", "client_secret_secret_ref": "...", "scopes": "read write"}


    authentication_method = Column(SQLAlchemyEnum(APIServiceAuthMethodEnum), nullable=False)
    additional_headers_json = Column(Text, nullable=True) # JSON: {"X-Custom-Header": "value"}
    timeout_seconds = Column(Integer, default=30, nullable=False)
    retry_policy_json = Column(Text, nullable=True) # JSON: {"max_retries": 3, "backoff_factor": 0.5, "status_forcelist": [500, 502, 503, 504]}

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_health_check_at = Column(DateTime(timezone=True), nullable=True)
    last_health_check_status = Column(String(20), nullable=True) # OK, ERROR, UNKNOWN

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Link to core_infra user if admin configured

class ExternalServiceLog(Base):
    __tablename__ = "external_service_logs" # For outgoing calls
    id = Column(Integer, primary_key=True, index=True)
    # Optional link to APIServiceConfig if the call was made using a predefined config
    api_service_config_id = Column(Integer, ForeignKey("api_service_configs.id", name="fk_extlog_apiservicecfg"), nullable=True)
    service_name_called = Column(String(100), nullable=False, index=True)

    request_timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    response_timestamp = Column(DateTime(timezone=True), nullable=True)

    http_method = Column(String(10), nullable=False)
    endpoint_url_called = Column(Text, nullable=False)

    request_headers_json = Column(Text, nullable=True) # Should be sanitized/masked
    request_payload_json = Column(Text, nullable=True)  # Should be sanitized/masked
    response_headers_json = Column(Text, nullable=True) # Should be sanitized/masked
    response_payload_json = Column(Text, nullable=True) # Should be sanitized/masked

    status_code_received = Column(Integer, nullable=True, index=True)
    is_success = Column(Boolean, nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    correlation_id = Column(String(100), index=True, nullable=True)
    # Example specific link: (Ensure financial_transactions table exists and is accessible)
    # financial_transaction_id = Column(Integer, ForeignKey("financial_transactions.id", name="fk_extlog_fintxn"), nullable=True, index=True)

    api_service_config = relationship("APIServiceConfig")
    # financial_transaction = relationship("FinancialTransaction") # If FinancialTransaction model is accessible

class WebhookEventLog(Base):
    __tablename__ = "webhook_event_logs" # For incoming webhooks
    id = Column(Integer, primary_key=True, index=True)
    # Optional link to APIServiceConfig if we have one for the source of the webhook (e.g. Paystack)
    # This helps in finding the secret for signature verification.
    api_service_config_id = Column(Integer, ForeignKey("api_service_configs.id", name="fk_webhook_apiservicecfg"), nullable=True)
    source_service_name = Column(String(100), nullable=False, index=True)
    event_type = Column(String(100), index=True, nullable=True)

    received_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    source_ip_address = Column(String(45), nullable=True)
    request_headers_json = Column(Text, nullable=True)
    raw_payload = Column(Text, nullable=False)

    processing_status = Column(SQLAlchemyEnum(WebhookProcessingStatusEnum), default=WebhookProcessingStatusEnum.PENDING, nullable=False, index=True)
    processing_notes_or_error = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    is_signature_verified = Column(Boolean, nullable=True) # Null if not applicable or not checked
    # Link to an internal entity that this webhook event affects or is related to
    related_internal_reference_id = Column(String(100), index=True, nullable=True)
    # Example specific link: (Ensure financial_transactions table exists and is accessible)
    # financial_transaction_id = Column(Integer, ForeignKey("financial_transactions.id", name="fk_webhook_fintxn"), nullable=True, index=True)

    api_service_config = relationship("APIServiceConfig") # For easy access to config used for verification

    Index('ix_webhook_event_logs_processing_status_received_at', processing_status, received_at)

# Notes:
# - `users.id` and `financial_transactions.id` are conceptual ForeignKeys.
#   Their actual definition depends on whether those tables are in the same database/schema
#   and how SQLAlchemy metadata is shared across modules.
# - Encryption of sensitive fields in APIServiceConfig.credentials_config_json is critical
#   and would typically involve application-level encryption using a securely managed key
#   (e.g., from a KMS or environment variable) before storing, and decryption upon use.
#   The database itself might also offer Transparent Data Encryption (TDE).
# - Masking/sanitization of request/response payloads in logs is essential for PII and security.
#   This logic would be in the service layer before logging.
# - Relationships to other modules' tables are commented out if direct import is complex,
#   but FK constraints are still defined assuming table accessibility.
#   In a microservices architecture, these links might be looser (e.g., just storing IDs).
#   In a monolith with shared Base, they can be fully defined.
# - `correlation_id` is key for tracing a request through multiple systems.
# - `related_internal_reference_id` helps link webhook events back to specific operations in the CBS.
