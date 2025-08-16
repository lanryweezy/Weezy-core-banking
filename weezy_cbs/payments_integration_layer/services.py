# Service layer for Payments Integration Layer
from sqlalchemy.orm import Session
import requests # Standard HTTP client
import json
import hmac # For signature verification if needed
import hashlib
from datetime import datetime, timedelta
import decimal
import uuid # For generating unique references for payment links etc.
from typing import Optional, List, Dict, Any # For type hinting

from . import models, schemas
# from weezy_cbs.shared import exceptions, security_utils # For encryption/decryption of API keys
# from weezy_cbs.transaction_management.services import update_financial_transaction_from_gateway_response, get_financial_transaction_by_id
# from weezy_cbs.transaction_management.models import TransactionStatusEnum as FinancialTransactionStatusEnum


class ExternalServiceException(Exception): pass
class ConfigurationException(Exception): pass
class PaymentValidationException(Exception): pass

# --- Helper Functions ---
def _get_gateway_config(db: Session, gateway_enum: models.PaymentGatewayEnum) -> models.PaymentGatewayConfig:
    # Ensure db session is passed and used if this function is called outside a service class instance
    config = db.query(models.PaymentGatewayConfig).filter(
        models.PaymentGatewayConfig.gateway == gateway_enum,
        models.PaymentGatewayConfig.is_active == True
    ).first()
    if not config:
        raise ConfigurationException(f"Active configuration for gateway {gateway_enum.value} not found.")
    return config

def _decrypt_key_placeholder(encrypted_key: Optional[str]) -> Optional[str]:
    if not encrypted_key: return None
    # In a real system: return security_utils.decrypt(encrypted_key)
    if encrypted_key.startswith("enc_"): # Simple check for mock
        return encrypted_key[4:] # "decrypted_value"
    return encrypted_key # Assume already plain if not prefixed (for testing)


def _log_payment_api_call(
    db: Session, financial_transaction_id: Optional[str], gateway: models.PaymentGatewayEnum,
    endpoint: str, method: str,
    req_payload: Optional[Any], req_headers: Optional[Dict[str, str]],
    resp_status_code: Optional[int], resp_payload: Optional[Any], resp_headers: Optional[Dict[str, str]],
    status: models.APILogStatusEnum, direction: models.APILogDirectionEnum,
    error: Optional[str] = None, duration_ms: Optional[int] = None,
    internal_ref: Optional[str] = None, external_ref: Optional[str] = None
):
    # Ensure payloads/headers are serialized to JSON strings if they are dicts/lists
    req_payload_str = json.dumps(req_payload, default=str) if isinstance(req_payload, (dict, list)) else str(req_payload) if req_payload is not None else None
    req_headers_str = json.dumps(req_headers) if req_headers else None
    resp_payload_str = json.dumps(resp_payload, default=str) if isinstance(resp_payload, (dict, list)) else str(resp_payload) if resp_payload is not None else None
    resp_headers_str = json.dumps(resp_headers) if resp_headers else None

    try:
        log_entry = models.PaymentAPILog(
            financial_transaction_id=financial_transaction_id,
            gateway=gateway, endpoint_url=endpoint, http_method=method,
            request_payload=req_payload_str, request_headers=req_headers_str,
            response_status_code=resp_status_code, response_payload=resp_payload_str, response_headers=resp_headers_str,
            status=status, direction=direction, error_message=error, duration_ms=duration_ms,
            internal_reference=internal_ref, external_reference=external_ref
        )
        db.add(log_entry)
        db.commit()
    except Exception as log_exc:
        # print(f"CRITICAL: Error logging API call to PaymentAPILog: {log_exc}")
        # This should go to a more resilient logging system (e.g. system logger, Sentry)
        db.rollback() # Rollback attempt to add log if it fails
        pass


# --- Base Gateway Service (Conceptual) ---
class BasePaymentGatewayService:
    def __init__(self, db: Session, gateway_enum: models.PaymentGatewayEnum):
        self.db = db
        self.gateway_enum = gateway_enum
        self.config = _get_gateway_config(self.db, self.gateway_enum)
        self.base_url = self.config.base_url.rstrip('/')
        self.secret_key = _decrypt_key_placeholder(self.config.secret_key_encrypted)
        self.api_key = _decrypt_key_placeholder(self.config.api_key_encrypted)
        self.public_key = _decrypt_key_placeholder(self.config.public_key_encrypted)
        self.webhook_secret = _decrypt_key_placeholder(self.config.webhook_secret_key_encrypted)
        self.default_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.config.additional_headers_json:
            self.default_headers.update(json.loads(self.config.additional_headers_json))

    def _make_request(self, method: str, endpoint: str,
                      payload: Optional[Dict[str, Any]] = None,
                      params: Optional[Dict[str, Any]] = None,
                      custom_headers: Optional[Dict[str, str]] = None,
                      internal_ref: Optional[str] = None,
                      financial_transaction_id: Optional[str] = None) -> Dict[str, Any]:
        # ... (Implementation similar to PaystackService._make_request but more generic, using self.default_headers) ...
        # This method should use self.db for _log_payment_api_call
        # For brevity, reusing the one in PaystackService logic conceptually for now.
        # This would be the place for common retry logic, timeout handling if not using a wrapper.
        # For mock:
        # print(f"BaseGatewayService: Mock request {method} to {self.base_url}/{endpoint} for {self.gateway_enum.value}")
        if method.upper() == "POST" and "initialize" in endpoint: # Generic initialize mock
            return {"status": True, "message": "Mock Initialization Successful", "data": {"authorization_url": "http://mockurl.com/pay", "access_code": "MOCK_ACC_CODE", "reference": internal_ref or payload.get("reference")}}
        elif method.upper() == "GET" and "verify" in endpoint: # Generic verify mock
            return {"status": True, "message": "Mock Verification Successful", "data": {"status": "success", "reference": endpoint.split('/')[-1]}}
        return {"status": False, "message": "Mock request method/endpoint not handled by base mock"}


# --- Paystack Client (Example using BasePaymentGatewayService) ---
class PaystackService(BasePaymentGatewayService):
    def __init__(self, db: Session):
        super().__init__(db, models.PaymentGatewayEnum.PAYSTACK)
        if not self.secret_key:
            raise ConfigurationException("Paystack secret key is not configured or decrypted.")
        self.default_headers["Authorization"] = f"Bearer {self.secret_key}"

    # _make_request inherited or specialized if needed. For now, assume generic one is called by methods below.
    # The generic _log_api_call needs to be available or part of BasePaymentGatewayService._make_request.

    def initialize_transaction(self, init_request: schemas.PaystackInitializeRequest, internal_txn_ref: str, financial_transaction_id: str) -> schemas.PaystackInitializeWrapperResponse:
        payload = init_request.dict(exclude_none=True)
        if 'amount' in payload and isinstance(payload['amount'], decimal.Decimal): # Schema uses int for kobo for Paystack
             payload['amount'] = int(init_request.amount) # Already int in schema, but good check if it were Decimal

        # Reusing the more detailed _make_request from previous implementation for logging example
        url = f"{self.base_url.rstrip('/')}/transaction/initialize"
        start_time = datetime.utcnow()
        # ... (full _make_request logic including _log_payment_api_call as in original PaystackService) ...
        # For mock, simplifying:
        response_data = self._make_request("POST", "transaction/initialize", payload=payload, internal_ref=internal_txn_ref, financial_transaction_id=financial_transaction_id) # Call inherited/base _make_request
        if not response_data.get("status"):
            raise ExternalServiceException(f"Paystack initialization failed: {response_data.get('message')}")
        return schemas.PaystackInitializeWrapperResponse(**response_data)


    def verify_transaction(self, paystack_reference: str, financial_transaction_id: Optional[str]=None) -> Dict[str, Any]:
        # ... (full _make_request logic including _log_payment_api_call) ...
        # For mock:
        response_data = self._make_request("GET", f"transaction/verify/{paystack_reference}", internal_ref=paystack_reference, financial_transaction_id=financial_transaction_id)
        return response_data

    def verify_webhook_signature(self, request_body_bytes: bytes, x_paystack_signature: str) -> bool:
        if not self.secret_key:
            # print("Paystack webhook secret key not available for signature verification.")
            return False
        hash_val = hmac.new(self.secret_key.encode('utf-8'), request_body_bytes, hashlib.sha512).hexdigest()
        return hmac.compare_digest(hash_val, x_paystack_signature)

# --- Flutterwave, Interswitch, NIBSS eBillsPay, NQR, Remita, Monnify services would follow a similar structure ---
# Each would inherit from BasePaymentGatewayService or have its own _make_request logic
# and specific methods for their API operations (initialize, verify, get_billers, etc.)

# --- Webhook Processing Service (Refined) ---
def process_incoming_webhook(db: Session, event_data: schemas.WebhookEventData, raw_request_body: bytes):
    # 1. Log the raw event (as before)
    log_entry = models.WebhookEventLog(
        gateway=event_data.gateway, event_type=event_data.event_type,
        event_id_external=event_data.event_id_external,
        payload_received=raw_request_body.decode('utf-8'), # Store raw body
        headers_received=json.dumps(event_data.headers_received) if event_data.headers_received else None,
        processing_status="PENDING"
    )
    db.add(log_entry); db.commit(); db.refresh(log_entry)

    # 2. Signature Verification
    signature_valid = False
    try:
        if event_data.gateway == models.PaymentGatewayEnum.PAYSTACK:
            paystack_sig = event_data.headers_received.get('x-paystack-signature') if event_data.headers_received else None
            if paystack_sig:
                paystack_service = PaystackService(db)
                signature_valid = paystack_service.verify_webhook_signature(raw_request_body, paystack_sig)
        # elif event_data.gateway == models.PaymentGatewayEnum.FLUTTERWAVE:
            # flutterwave_service = FlutterwaveService(db) # Assuming FlutterwaveService is defined
            # verify_hash = event_data.headers_received.get('verify-hash')
            # signature_valid = flutterwave_service.verify_webhook_signature(raw_request_body.decode('utf-8'), verify_hash)
        else: # Default to valid for other gateways in mock, or implement their verification
            signature_valid = True # Placeholder for other gateways

        if not signature_valid:
            log_entry.processing_status = "FAILED_VALIDATION"; log_entry.processing_notes = "Webhook signature verification failed."
            db.commit(); return
    except ConfigurationException as e: # E.g. webhook secret not found for gateway
        log_entry.processing_status = "FAILED_VALIDATION"; log_entry.processing_notes = f"Signature validation config error: {str(e)}"
        db.commit(); return
    except Exception as sig_exc: # Catch any other error during signature verification
        log_entry.processing_status = "FAILED_VALIDATION"; log_entry.processing_notes = f"Signature verification error: {str(sig_exc)}"
        db.commit(); return

    # 3. Process validated webhook (payload_received is now a dict from schema)
    payload_dict = event_data.payload_received
    try:
        linked_ft_id = None
        if event_data.gateway == models.PaymentGatewayEnum.PAYSTACK and event_data.event_type == "charge.success":
            paystack_data = payload_dict.get("data", {})
            our_reference = paystack_data.get("reference") # This is our FinancialTransaction.id
            gateway_status = paystack_data.get("status") # "success"
            gateway_reference_id = paystack_data.get("id") # Paystack's own ID for the charge

            if our_reference:
                # update_financial_transaction_from_gateway_response(
                #     db, financial_transaction_id=our_reference,
                #     new_status=FinancialTransactionStatusEnum.SUCCESSFUL, # Map gateway_status
                #     gateway_name=event_data.gateway.value,
                #     gateway_ref=gateway_reference_id,
                #     gateway_message=f"Payment successful via {event_data.gateway.value} webhook."
                # )
                linked_ft_id = our_reference # For logging

        # ... Add handlers for Flutterwave, Interswitch, NIBSS events ...
        # Each handler would parse `payload_dict` according to its gateway's structure
        # and call `update_financial_transaction_from_gateway_response` or similar.

        log_entry.processing_status = "PROCESSED"
        log_entry.processing_notes = "Webhook processed successfully."
        if linked_ft_id: log_entry.financial_transaction_id = linked_ft_id
    except Exception as processing_exc:
        log_entry.processing_status = "ERROR_PROCESSING"
        log_entry.processing_notes = f"Error during webhook payload processing: {str(processing_exc)}"

    log_entry.processed_at = datetime.utcnow()
    db.commit()

# --- Payment Link Services (Refined) ---
def create_payment_link(db: Session, link_create_req: schemas.PaymentLinkCreateRequest) -> models.PaymentLink:
    # Validate account_to_credit_id exists
    # account = get_account_by_id_internal(db, link_create_req.account_to_credit_id) # From accounts_ledger
    # if not account:
    #     raise NotFoundException(f"Account to credit (ID: {link_create_req.account_to_credit_id}) not found.")

    link_ref = "PLNK_" + uuid.uuid4().hex[:12].upper()
    db_link = models.PaymentLink(
        link_reference=link_ref,
        customer_id=link_create_req.customer_id, # Can be None if system-generated link
        account_to_credit_id=link_create_req.account_to_credit_id,
        amount=link_create_req.amount,
        currency=link_create_req.currency, # Uses schema enum, maps to model enum
        description=link_create_req.description,
        is_reusable=link_create_req.is_reusable,
        max_usage_count=link_create_req.max_usage_count if link_create_req.is_reusable else (1 if not link_create_req.is_reusable else None),
        expiry_date=link_create_req.expiry_date,
        status="ACTIVE"
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

# ... (get_payment_link_by_reference, and other gateway client services for NIBSS eBillsPay, NQR, Airtime etc. would be added here) ...
# These would largely follow the pattern of PaystackService:
# - Initialize with DB session and gateway enum.
# - Load config and credentials.
# - Implement methods for specific API operations (get_billers, make_payment, purchase_airtime, generate_nqr).
# - Use a shared or specific _make_request method that includes robust logging via _log_payment_api_call.
# - Map data between internal schemas and gateway-specific formats.
# - Handle gateway-specific error conditions.
