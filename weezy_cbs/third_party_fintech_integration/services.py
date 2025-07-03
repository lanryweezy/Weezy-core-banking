import json
import httpx # For making HTTP requests to third parties
import hmac # For webhook signature verification (example)
import hashlib # For webhook signature verification (example)
from typing import List, Optional, Type, Dict, Any, Tuple, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import datetime

from . import models, schemas
from weezy_cbs.core_infrastructure_config_engine.services import AuditLogService
# Conceptual: For encryption/decryption of credentials
# from weezy_cbs.core.security import encrypt_value, decrypt_value # Assume this exists

# --- Placeholder for Encryption (Actual implementation would use Fernet, KMS, etc.) ---
def encrypt_value(value: str) -> str:
    # In a real app, this would be strong encryption. This is a placeholder.
    if not value: return value
    return f"encrypted_{value[::-1]}"

def decrypt_value(encrypted_value: str) -> str:
    if not encrypted_value or not encrypted_value.startswith("encrypted_"):
        return encrypted_value # Or raise error if expected to be encrypted
    return encrypted_value[len("encrypted_"):][::-1]

# --- Base Service ---
class BaseThirdPartyIntegrationService:
    def _audit_log(self, db: Session, action: str, entity_type: str, entity_id: Any, summary: str = "", performing_user: str = "SYSTEM"):
        AuditLogService.create_audit_log_entry(
            db, username_performing_action=performing_user, action_type=action,
            entity_type=entity_type, entity_id=str(entity_id), summary=summary
        )

    def _parse_json_field(self, data: Optional[str]) -> Optional[Any]:
        if data is None: return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON content in field", "original_data": data}


# --- APIServiceConfig Service ---
class APIServiceConfigService(BaseThirdPartyIntegrationService):
    def create_config(self, db: Session, config_in: schemas.APIServiceConfigCreate, user_id: Optional[int], username: str) -> models.APIServiceConfig:
        if db.query(models.APIServiceConfig).filter(models.APIServiceConfig.service_name == config_in.service_name).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Configuration for service '{config_in.service_name}' already exists.")

        # Encrypt credentials before storing (conceptual)
        encrypted_creds = None
        if config_in.credentials_config_json:
            # This logic would be more complex, iterating through known sensitive keys based on auth_method
            # For example, if 'api_key' is a field, encrypt it.
            # This is a simplified representation.
            temp_creds = config_in.credentials_config_json.copy()
            for k, v in temp_creds.items():
                if isinstance(v, str) and ("key" in k.lower() or "secret" in k.lower() or "password" in k.lower() or "token" in k.lower()):
                    temp_creds[k] = encrypt_value(v) # Conceptual encryption
            encrypted_creds = json.dumps(temp_creds)

        db_config = models.APIServiceConfig(
            service_name=config_in.service_name,
            description=config_in.description,
            base_url=str(config_in.base_url), # Ensure HttpUrl is converted to string
            authentication_method=config_in.authentication_method,
            credentials_config_json=encrypted_creds,
            additional_headers_json=json.dumps(config_in.additional_headers_json) if config_in.additional_headers_json else None,
            timeout_seconds=config_in.timeout_seconds,
            retry_policy_json=json.dumps(config_in.retry_policy_json) if config_in.retry_policy_json else None,
            is_active=config_in.is_active,
            # created_by_user_id=user_id # If tracking creator
        )
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        self._audit_log(db, "API_SERVICE_CONFIG_CREATE", "APIServiceConfig", db_config.id, f"Config for '{db_config.service_name}' created.", username)
        return db_config

    def get_config_by_id(self, db: Session, config_id: int) -> Optional[models.APIServiceConfig]:
        return db.query(models.APIServiceConfig).filter(models.APIServiceConfig.id == config_id).first()

    def get_config_by_service_name(self, db: Session, service_name: str, active_only: bool = True) -> Optional[models.APIServiceConfig]:
        query = db.query(models.APIServiceConfig).filter(models.APIServiceConfig.service_name == service_name)
        if active_only:
            query = query.filter(models.APIServiceConfig.is_active == True)
        return query.first()

    def get_all_configs(self, db: Session, skip: int = 0, limit: int = 100) -> Tuple[List[models.APIServiceConfig], int]:
        query = db.query(models.APIServiceConfig)
        total = query.count()
        configs = query.order_by(models.APIServiceConfig.service_name).offset(skip).limit(limit).all()
        return configs, total

    def update_config(self, db: Session, config_id: int, config_upd: schemas.APIServiceConfigUpdate, username: str) -> Optional[models.APIServiceConfig]:
        db_config = self.get_config_by_id(db, config_id)
        if not db_config: return None

        update_data = config_upd.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field == "credentials_config_json" and isinstance(value, dict):
                     # Similar encryption logic as in create_config
                    temp_creds = value.copy()
                    for k, v_item in temp_creds.items():
                        if isinstance(v_item, str) and ("key" in k.lower() or "secret" in k.lower() or "password" in k.lower() or "token" in k.lower()):
                             temp_creds[k] = encrypt_value(v_item)
                    setattr(db_config, field, json.dumps(temp_creds))
                elif field.endswith("_json") and isinstance(value, (dict, list)):
                    setattr(db_config, field, json.dumps(value))
                elif field == "base_url" and isinstance(value, Any): # Pydantic HttpUrl
                     setattr(db_config, field, str(value))
                else:
                    setattr(db_config, field, value)

        db_config.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_config)
        self._audit_log(db, "API_SERVICE_CONFIG_UPDATE", "APIServiceConfig", db_config.id, f"Config for '{db_config.service_name}' updated.", username)
        return db_config

    def delete_config(self, db: Session, config_id: int, username: str) -> bool:
        db_config = self.get_config_by_id(db, config_id)
        if not db_config: return False
        # Consider if there are active logs or dependent items before deleting
        self._audit_log(db, "API_SERVICE_CONFIG_DELETE", "APIServiceConfig", db_config.id, f"Config for '{db_config.service_name}' deleted.", username)
        db.delete(db_config)
        db.commit()
        return True

    def get_decrypted_credentials(self, db_config: models.APIServiceConfig) -> Optional[Dict[str, Any]]:
        if not db_config.credentials_config_json:
            return None

        encrypted_creds = self._parse_json_field(db_config.credentials_config_json)
        if not isinstance(encrypted_creds, dict): return None

        decrypted_creds = {}
        for k, v in encrypted_creds.items():
            if isinstance(v, str) and ("key" in k.lower() or "secret" in k.lower() or "password" in k.lower() or "token" in k.lower()): # Heuristic
                decrypted_creds[k] = decrypt_value(v) # Conceptual decryption
            else:
                decrypted_creds[k] = v
        return decrypted_creds

# --- ExternalServiceLog Service ---
class ExternalServiceLogService(BaseThirdPartyIntegrationService):
    def log_outgoing_call(
        self, db: Session, service_name: str, http_method: str, endpoint_url: str,
        request_headers: Optional[Dict] = None, request_payload: Optional[Any] = None, # Payload can be dict or str
        response_status_code: Optional[int] = None, response_headers: Optional[Dict] = None, response_payload: Optional[Any] = None,
        is_success: Optional[bool] = None, error_message: Optional[str] = None, duration_ms: Optional[int] = None,
        correlation_id: Optional[str] = None, api_config_id: Optional[int] = None
        # financial_transaction_id: Optional[int] = None
    ) -> models.ExternalServiceLog:

        # Conceptual: Mask sensitive data in headers/payloads before logging
        # masked_req_headers = self._mask_sensitive_data(request_headers)
        # masked_req_payload = self._mask_sensitive_data(request_payload)
        # ... same for response ...

        db_log = models.ExternalServiceLog(
            api_service_config_id=api_config_id,
            service_name_called=service_name,
            http_method=http_method.upper(),
            endpoint_url_called=endpoint_url,
            request_headers_json=json.dumps(request_headers) if request_headers else None,
            request_payload_json=json.dumps(request_payload) if isinstance(request_payload, (dict, list)) else str(request_payload) if request_payload is not None else None,
            response_timestamp=datetime.utcnow() if response_status_code is not None else None, # Log response time when available
            response_status_code=response_status_code,
            response_headers_json=json.dumps(response_headers) if response_headers else None,
            response_payload_json=json.dumps(response_payload) if isinstance(response_payload, (dict, list)) else str(response_payload) if response_payload is not None else None,
            is_success=is_success,
            error_message=error_message,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            # financial_transaction_id=financial_transaction_id
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log

    def get_log_by_id(self, db: Session, log_id: int) -> Optional[models.ExternalServiceLog]:
        return db.query(models.ExternalServiceLog).filter(models.ExternalServiceLog.id == log_id).first()

    def get_logs(self, db: Session, service_name: Optional[str] = None, correlation_id: Optional[str] = None,
                 is_success: Optional[bool] = None, skip: int = 0, limit: int = 100) -> Tuple[List[models.ExternalServiceLog], int]:
        query = db.query(models.ExternalServiceLog)
        if service_name: query = query.filter(models.ExternalServiceLog.service_name_called.ilike(f"%{service_name}%"))
        if correlation_id: query = query.filter(models.ExternalServiceLog.correlation_id == correlation_id)
        if is_success is not None: query = query.filter(models.ExternalServiceLog.is_success == is_success)

        total = query.count()
        logs = query.order_by(models.ExternalServiceLog.request_timestamp.desc()).offset(skip).limit(limit).all()
        return logs, total

# --- WebhookEventLog Service ---
class WebhookEventLogService(BaseThirdPartyIntegrationService):
    def log_incoming_webhook(
        self, db: Session, source_service_name: str, raw_payload: Union[str, bytes],
        request_headers: Optional[Dict] = None, source_ip: Optional[str] = None,
        event_type: Optional[str] = None, api_config_id: Optional[int] = None
    ) -> models.WebhookEventLog:

        if isinstance(raw_payload, bytes):
            try:
                raw_payload_str = raw_payload.decode('utf-8')
            except UnicodeDecodeError:
                raw_payload_str = raw_payload.hex() # Or base64, if it's binary non-text

        db_log = models.WebhookEventLog(
            api_service_config_id=api_config_id,
            source_service_name=source_service_name,
            event_type=event_type,
            source_ip_address=source_ip,
            request_headers_json=json.dumps(request_headers) if request_headers else None,
            raw_payload=raw_payload_str,
            processing_status=models.WebhookProcessingStatusEnum.PENDING,
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        # Minimal audit, as this is a log itself.
        return db_log

    def update_webhook_log_processing(
        self, db: Session, log_id: int, status: models.WebhookProcessingStatusEnum,
        notes: Optional[str] = None, related_ref_id: Optional[str] = None,
        is_signature_verified: Optional[bool] = None
    ) -> Optional[models.WebhookEventLog]:
        db_log = db.query(models.WebhookEventLog).filter(models.WebhookEventLog.id == log_id).first()
        if not db_log: return None

        db_log.processing_status = status
        db_log.processing_notes_or_error = notes
        db_log.processed_at = datetime.utcnow()
        if related_ref_id is not None: # Allow clearing it
            db_log.related_internal_reference_id = related_ref_id
        if is_signature_verified is not None:
            db_log.is_signature_verified = is_signature_verified

        db.commit()
        db.refresh(db_log)
        return db_log

    def get_webhook_log_by_id(self, db: Session, log_id: int) -> Optional[models.WebhookEventLog]:
        return db.query(models.WebhookEventLog).filter(models.WebhookEventLog.id == log_id).first()

    def get_webhook_logs(
        self, db: Session, source_service_name: Optional[str] = None, event_type: Optional[str] = None,
        processing_status: Optional[models.WebhookProcessingStatusEnum] = None,
        skip: int = 0, limit: int = 100
    ) -> Tuple[List[models.WebhookEventLog], int]:
        query = db.query(models.WebhookEventLog)
        if source_service_name: query = query.filter(models.WebhookEventLog.source_service_name.ilike(f"%{source_service_name}%"))
        if event_type: query = query.filter(models.WebhookEventLog.event_type.ilike(f"%{event_type}%"))
        if processing_status: query = query.filter(models.WebhookEventLog.processing_status == processing_status)

        total = query.count()
        logs = query.order_by(models.WebhookEventLog.received_at.desc()).offset(skip).limit(limit).all()
        return logs, total

    def verify_webhook_signature(
        self, db_config: Optional[models.APIServiceConfig], # Config for the service sending webhook (e.g. Paystack)
        raw_payload_bytes: bytes, # Raw request body bytes
        signature_header_value: Optional[str], # e.g. content of "X-Paystack-Signature"
        service_name_for_verification: str # To know which verification method to use
    ) -> bool:
        if not db_config or not signature_header_value:
            return False # Cannot verify without config or signature

        # --- Example: Paystack HMAC-SHA512 Verification ---
        if service_name_for_verification.upper() == "PAYSTACK_PAYMENTS": # Match service_name
            creds = APIServiceConfigService().get_decrypted_credentials(db_config)
            if not creds or "secret_key" not in creds: # Assuming secret_key is stored in credentials_config_json
                # Log missing secret key for verification
                return False

            secret_key_bytes = creds["secret_key"].encode('utf-8')
            expected_signature = hmac.new(secret_key_bytes, raw_payload_bytes, hashlib.sha512).hexdigest()
            return hmac.compare_digest(expected_signature, signature_header_value)

        # --- Add other verification methods for other services ---
        # e.g., NIBSS might have a different mechanism.
        # if service_name_for_verification.upper() == "NIBSS_NIP":
        #     ... NIBSS specific verification ...

        # Default if no specific method matches
        # Log that verification method is not implemented for this service
        print(f"WARN: Webhook signature verification not implemented for service: {service_name_for_verification}")
        return False # Or True if signature optional/not configured


# --- Generic External API Client Service (Conceptual) ---
# This would be used by other modules' services to make calls.
class GenericExternalAPICaller:
    def __init__(self, db: Session,
                 api_config_service: APIServiceConfigService,
                 ext_log_service: ExternalServiceLogService):
        self.db = db
        self.api_config_service = api_config_service
        self.ext_log_service = ext_log_service

    async def make_request(
        self, service_name: str, method: str, endpoint_path: str,
        params: Optional[Dict] = None, # URL query params
        json_payload: Optional[Dict] = None, # JSON body for POST/PUT
        data_payload: Optional[Dict] = None, # Form data for POST/PUT
        headers: Optional[Dict] = None,
        correlation_id: Optional[str] = None
    ) -> httpx.Response: # Returns the raw httpx.Response for flexibility

        config = self.api_config_service.get_config_by_service_name(self.db, service_name)
        if not config:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"API configuration for service '{service_name}' not found or inactive.")

        base_url = config.base_url.rstrip('/')
        full_url = f"{base_url}/{endpoint_path.lstrip('/')}"

        request_headers = json.loads(config.additional_headers_json or "{}")
        if headers: request_headers.update(headers)

        # Authentication (Conceptual - this is complex)
        creds = self.api_config_service.get_decrypted_credentials(config)
        if config.authentication_method == models.APIServiceAuthMethodEnum.API_KEY_HEADER:
            if creds and "header_name" in creds and "api_key" in creds:
                request_headers[creds["header_name"]] = creds["api_key"]
            else: # Log missing credential parts
                pass
        elif config.authentication_method == models.APIServiceAuthMethodEnum.BEARER_TOKEN:
            if creds and "token" in creds: # Assuming static token for simplicity
                request_headers["Authorization"] = f"Bearer {creds['token']}"
            # Real OAuth2 would involve fetching token from token_url if expired
        # ... Add other auth methods ...

        start_time = datetime.utcnow()
        log_entry_id = None # Will be set after initial log

        # Log attempt (minimal info first, update later)
        try:
            # Can't log full request yet as it's not made.
            # Could log an "ATTEMPTING_CALL" state if needed.
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.request(
                    method.upper(), full_url,
                    params=params, json=json_payload, data=data_payload, headers=request_headers
                )

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Log full call details
            self.ext_log_service.log_outgoing_call(
                self.db, service_name=service_name, http_method=method, endpoint_url=full_url,
                request_headers=request_headers, request_payload=json_payload or data_payload,
                response_status_code=response.status_code, response_headers=dict(response.headers),
                response_payload=response.text, # Log raw text, parse to JSON if needed later
                is_success=(200 <= response.status_code < 300), duration_ms=duration_ms,
                correlation_id=correlation_id, api_config_id=config.id
            )
            return response

        except httpx.RequestError as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            error_msg = f"HTTP Request failed: {type(e).__name__} - {str(e)}"
            self.ext_log_service.log_outgoing_call(
                self.db, service_name=service_name, http_method=method, endpoint_url=full_url,
                request_headers=request_headers, request_payload=json_payload or data_payload,
                is_success=False, error_message=error_msg, duration_ms=duration_ms,
                correlation_id=correlation_id, api_config_id=config.id
            )
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Error calling external service '{service_name}': {error_msg}")
        except Exception as e: # Catch any other errors during prep or logging
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self.ext_log_service.log_outgoing_call(
                self.db, service_name=service_name, http_method=method, endpoint_url=full_url,
                is_success=False, error_message=f"Generic error: {str(e)}", duration_ms=duration_ms,
                correlation_id=correlation_id, api_config_id=config.id
            )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error during external call to '{service_name}'.")


# Instantiate services
api_service_config_service = APIServiceConfigService()
external_service_log_service = ExternalServiceLogService()
webhook_event_log_service = WebhookEventLogService()
# GenericExternalAPICaller would be instantiated by services that need to make calls, e.g.:
# caller = GenericExternalAPICaller(db_session, api_service_config_service, external_service_log_service)
# await caller.make_request(...)
