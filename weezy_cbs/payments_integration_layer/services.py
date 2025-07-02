# Service layer for Payments Integration Layer
from sqlalchemy.orm import Session
import requests # Standard HTTP client
import json
import hmac # For signature verification if needed
import hashlib
from datetime import datetime
import decimal

from . import models, schemas
# from weezy_cbs.shared import exceptions, security_utils # For encryption/decryption of API keys
# from weezy_cbs.transaction_management.services import update_transaction_status_from_gateway, get_transaction_by_id
# from weezy_cbs.transaction_management.models import TransactionStatusEnum

class ExternalServiceException(Exception): pass
class ConfigurationException(Exception): pass
class PaymentValidationException(Exception): pass

# --- Helper Functions ---
def _get_gateway_config(db: Session, gateway_enum: models.PaymentGatewayEnum) -> models.PaymentGatewayConfig:
    config = db.query(models.PaymentGatewayConfig).filter(
        models.PaymentGatewayConfig.gateway == gateway_enum,
        models.PaymentGatewayConfig.is_active == True
    ).first()
    if not config:
        raise ConfigurationException(f"Active configuration for gateway {gateway_enum.value} not found.")
    return config

def _decrypt_key(encrypted_key: str) -> str:
    # return security_utils.decrypt(encrypted_key)
    return f"decrypted_{encrypted_key}" # Placeholder

def _log_api_call(
    db: Session, gateway: models.PaymentGatewayEnum, endpoint: str, method: str,
    req_payload: Optional[dict], req_headers: Optional[dict],
    resp_status_code: Optional[int], resp_payload: Optional[dict], resp_headers: Optional[dict],
    status: models.APILogStatusEnum, direction: models.APILogDirectionEnum,
    error: Optional[str] = None, duration_ms: Optional[int] = None,
    internal_ref: Optional[str] = None, external_ref: Optional[str] = None
):
    try:
        log_entry = models.PaymentAPILog(
            gateway=gateway, endpoint_url=endpoint, http_method=method,
            request_payload=json.dumps(req_payload) if req_payload else None,
            request_headers=json.dumps(req_headers) if req_headers else None,
            response_status_code=resp_status_code,
            response_payload=json.dumps(resp_payload) if resp_payload else None,
            response_headers=json.dumps(resp_headers) if resp_headers else None,
            status=status, direction=direction, error_message=error, duration_ms=duration_ms,
            internal_reference=internal_ref, external_reference=external_ref
        )
        db.add(log_entry)
        db.commit() # Commit log independently if desired
    except Exception as log_exc:
        # print(f"Error logging API call: {log_exc}") # Log to system logger
        pass # Don't let logging failure break the main flow


# --- Paystack Client (Example) ---
class PaystackService:
    def __init__(self, db: Session):
        self.db = db
        self.gateway_enum = models.PaymentGatewayEnum.PAYSTACK
        try:
            self.config = _get_gateway_config(db, self.gateway_enum)
            self.secret_key = _decrypt_key(self.config.secret_key_encrypted) if self.config.secret_key_encrypted else None
            if not self.secret_key:
                 raise ConfigurationException("Paystack secret key is not configured.")
            self.base_url = self.config.base_url
        except ConfigurationException as e:
            # Log this critical error
            # print(f"PaystackService Initialization Error: {e}")
            raise e # Re-raise to prevent service usage if misconfigured

    def _make_request(self, method: str, endpoint: str, payload: Optional[dict] = None, params: Optional[dict] = None, internal_ref: Optional[str]=None):
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

        start_time = datetime.utcnow()
        req_payload_log = payload
        resp_payload_log, resp_headers_log, resp_status_code_log, error_log = None, None, None, None
        status_log = models.APILogStatusEnum.PENDING
        external_ref_log = None

        try:
            if method.upper() == "POST":
                response = requests.post(url, json=payload, headers=headers, timeout=30)
            elif method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=30)
            else:
                raise NotImplementedError(f"HTTP method {method} not implemented for Paystack client.")

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            resp_status_code_log = response.status_code
            resp_headers_log = dict(response.headers)

            try:
                resp_payload_log = response.json()
            except json.JSONDecodeError:
                resp_payload_log = {"raw_response": response.text} # Store raw if not JSON
                # print(f"Paystack response not JSON: {response.text}")

            if response.ok and resp_payload_log.get("status") is True: # Paystack specific success check
                status_log = models.APILogStatusEnum.SUCCESS
                external_ref_log = resp_payload_log.get("data", {}).get("reference") or resp_payload_log.get("data", {}).get("access_code")
            else:
                status_log = models.APILogStatusEnum.FAILED
                error_log = resp_payload_log.get("message") or f"Request failed with status {response.status_code}"
                # print(f"Paystack API Error: {error_log} - Response: {resp_payload_log}")

            return resp_payload_log

        except requests.exceptions.RequestException as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            status_log = models.APILogStatusEnum.FAILED
            error_log = f"HTTP Request Exception: {str(e)}"
            # print(f"Paystack HTTP Error: {error_log}")
            raise ExternalServiceException(error_log)
        finally:
            _log_api_call(
                self.db, self.gateway_enum, endpoint, method.upper(),
                req_payload_log, headers, resp_status_code_log, resp_payload_log, resp_headers_log,
                status_log, models.APILogDirectionEnum.OUTGOING, error_log, duration_ms,
                internal_ref=internal_ref, external_ref=external_ref_log
            )

    def initialize_transaction(self, init_request: schemas.PaystackInitializeRequest, internal_txn_ref: str) -> schemas.PaystackInitializeWrapperResponse:
        payload = init_request.dict(exclude_none=True)
        # Paystack expects amount in kobo
        if 'amount' in payload and isinstance(payload['amount'], decimal.Decimal):
            payload['amount'] = int(payload['amount'] * 100)

        response_data = self._make_request("POST", "transaction/initialize", payload=payload, internal_ref=internal_txn_ref)

        if not response_data.get("status"): # Check Paystack's own status field
            raise ExternalServiceException(f"Paystack initialization failed: {response_data.get('message')}")

        # This will raise Pydantic validation error if structure is wrong
        return schemas.PaystackInitializeWrapperResponse(**response_data)

    def verify_transaction(self, reference: str) -> dict: # Returns raw verified data
        # `reference` here is Paystack's transaction reference
        response_data = self._make_request("GET", f"transaction/verify/{reference}", internal_ref=reference) # Use paystack ref as internal for this call type

        if not response_data.get("status") or response_data.get("data", {}).get("status") != "success":
            # Even if API call is 200 OK, data.status might not be "success"
            # print(f"Paystack verification not successful for {reference}: {response_data.get('data', {}).get('message')}")
            # This isn't necessarily an ExternalServiceException if the API call itself was fine.
            # The caller needs to handle the transaction status.
            pass # Let caller inspect the full response
        return response_data # Return the full response for caller to interpret

    def verify_webhook_signature(self, request_body_bytes: bytes, x_paystack_signature: str) -> bool:
        if not self.secret_key: return False # Should not happen if service initialized correctly

        hash_val = hmac.new(
            self.secret_key.encode('utf-8'),
            request_body_bytes,
            hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(hash_val, x_paystack_signature)

# --- Flutterwave Client (Example Structure - not fully implemented) ---
class FlutterwaveService:
    def __init__(self, db: Session):
        self.db = db
        self.gateway_enum = models.PaymentGatewayEnum.FLUTTERWAVE
        # ... load config, secret_key, base_url ...
        # self.config = _get_gateway_config(db, self.gateway_enum)
        # self.secret_key = _decrypt_key(self.config.secret_key_encrypted)
        # self.base_url = self.config.base_url
        pass # Placeholder

    def initialize_payment(self, payment_details: dict, internal_txn_ref: str) -> dict:
        # endpoint = "payments"
        # payload = {
        #     "tx_ref": internal_txn_ref, # Your unique reference
        #     "amount": str(payment_details["amount"]), # Amount as string
        #     "currency": payment_details["currency"],
        #     "redirect_url": payment_details["redirect_url"],
        #     "customer": {
        #         "email": payment_details["email"],
        #         "phonenumber": payment_details.get("phone"),
        #         "name": payment_details.get("customer_name")
        #     },
        #     "customizations": { "title": "Weezy CBS Payment", "logo": "your_logo_url"}
        # }
        # response = self._make_request("POST", endpoint, payload, internal_ref=internal_txn_ref)
        # if response.get("status") != "success":
        #     raise ExternalServiceException(f"Flutterwave init failed: {response.get('message')}")
        # return response.get("data") # e.g. {"link": "flutterwave_payment_link"}
        return {"link": "mock_flutterwave_link_for_" + internal_txn_ref} # Placeholder

    def verify_transaction(self, flutterwave_transaction_id: str) -> dict: # FW uses numeric ID
        # endpoint = f"transactions/{flutterwave_transaction_id}/verify"
        # response = self._make_request("GET", endpoint, internal_ref=str(flutterwave_transaction_id))
        # if response.get("status") != "success" or response.get("data",{}).get("status") != "successful":
        #     pass # Let caller handle
        # return response
        return {"status": "success", "data": {"status": "successful", "id": flutterwave_transaction_id, "amount": 1000, "currency": "NGN"}} # Placeholder

    def verify_webhook_signature(self, request_body_str: str, x_flutterwave_signature: str) -> bool:
        # fw_webhook_secret_hash = self.config.webhook_secret_hash # Get this from your FW dashboard
        # if not fw_webhook_secret_hash: return False
        # return x_flutterwave_signature == fw_webhook_secret_hash
        return True # Placeholder

# --- NIBSS e-BillsPay Client (Example Structure) ---
class NibssEBillsPayService:
    def __init__(self, db: Session):
        self.db = db
        self.gateway_enum = models.PaymentGatewayEnum.NIBSS_EBILLSPAY
        # ... load config (อาจจะมี client certs, specific NIBSS URLs) ...
        pass

    def get_billers(self) -> List[dict]:
        # Call NIBSS Biller List endpoint
        # response = self._make_nibss_request(...)
        # return formatted_biller_list
        return [{"id": "DSTV", "name": "DSTV Subscription", "category_id": "TV"}] # Placeholder

    def get_payment_items(self, biller_id: str) -> List[dict]:
        # Call NIBSS Payment Item List endpoint for biller_id
        return [{"id": "DSTV_BOXOFFICE", "name": "DStv BoxOffice", "biller_id": biller_id, "amount_fixed": None}] # Placeholder

    def validate_customer(self, biller_id: str, payment_item_id: str, customer_id_on_biller: str) -> dict:
        # Call NIBSS Customer Validation endpoint
        # Returns customer name, outstanding amount etc.
        return {"valid": True, "customer_name": "Mock Customer", "outstanding_amount": 5000} # Placeholder

    def make_bill_payment(self, payment_details: schemas.BillPaymentRequest, internal_txn_ref: str) -> dict:
        # Call NIBSS Bill Payment endpoint
        # This is complex, involves session IDs, MACing etc.
        # On success, returns NIBSS transaction ID, status.
        # payment_response = self._make_nibss_request(..., payload=payment_details_for_nibss)
        # if payment_response.get("responseCode") == "00":
        #     return {"status": "SUCCESSFUL", "gateway_reference": payment_response.get("transactionId")}
        # else:
        #     raise ExternalServiceException(f"eBillsPay failed: {payment_response.get('responseDescription')}")
        return {"status": "SUCCESSFUL", "gateway_reference": "NIBSS_BP_" + internal_txn_ref} # Placeholder

# --- Webhook Processing Service ---
def process_incoming_webhook(db: Session, event_data: schemas.WebhookEventData):
    # 1. Log the raw event
    log_entry = models.WebhookEventLog(
        gateway=event_data.gateway,
        event_type=event_data.event_type,
        event_id_external=event_data.event_id_external,
        payload_received=json.dumps(event_data.payload_received),
        headers_received=json.dumps(event_data.headers_received) if event_data.headers_received else None,
        processing_status="PENDING"
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    # 2. Signature Verification ( VERY IMPORTANT! )
    signature_valid = False
    if event_data.gateway == models.PaymentGatewayEnum.PAYSTACK:
        paystack_sig = event_data.headers_received.get('x-paystack-signature') if event_data.headers_received else None
        if paystack_sig:
            # Need raw body bytes for Paystack, not parsed JSON
            # This means API endpoint needs to provide raw body for webhook routes
            # For now, assume event_data.payload_received is the dict to be re-serialized if needed
            raw_body_for_sig_check = json.dumps(event_data.payload_received, separators=(',', ':')).encode('utf-8')
            paystack_service = PaystackService(db) # Initialize service to access secret key
            signature_valid = paystack_service.verify_webhook_signature(raw_body_for_sig_check, paystack_sig)
    elif event_data.gateway == models.PaymentGatewayEnum.FLUTTERWAVE:
        # fw_sig = event_data.headers_received.get('verify-hash') if event_data.headers_received else None
        # if fw_sig:
        #     flutterwave_service = FlutterwaveService(db)
        #     signature_valid = flutterwave_service.verify_webhook_signature(json.dumps(event_data.payload_received), fw_sig)
        signature_valid = True # Placeholder

    if not signature_valid:
        log_entry.processing_status = "FAILED_VALIDATION"
        log_entry.processing_notes = "Webhook signature verification failed."
        db.commit()
        # Potentially raise an alert
        # print(f"Webhook FAILED VALIDATION from {event_data.gateway.value} for event {event_data.event_type}")
        return

    # 3. Process based on gateway and event type
    try:
        # Example: Paystack charge success
        if event_data.gateway == models.PaymentGatewayEnum.PAYSTACK and event_data.event_type == "charge.success":
            paystack_data = event_data.payload_received.get("data", {})
            transaction_reference = paystack_data.get("reference") # This is OUR reference we sent to Paystack
            # status_from_paystack = paystack_data.get("status") # Should be "success"
            # amount_from_paystack = decimal.Decimal(paystack_data.get("amount")) / 100 # Convert kobo to Naira

            if transaction_reference:
                # Update our FinancialTransaction record based on this webhook
                # ft = get_transaction_by_id(db, transaction_reference) # Assuming our internal ref matches Paystack's
                # if ft and ft.status == TransactionStatusEnum.PENDING:
                #     update_transaction_status_from_gateway(
                #         db, transaction_id=ft.id, new_status=TransactionStatusEnum.SUCCESSFUL,
                #         gateway_ref=paystack_data.get("id"), # Paystack's own ID for the charge
                #         gateway_message="Payment successful via Paystack webhook."
                #     )
                #     log_entry.financial_transaction_id = ft.id
                pass # Placeholder for FT update logic

        # Add more handlers for other gateways and event types

        log_entry.processing_status = "PROCESSED"
        log_entry.processing_notes = "Webhook processed successfully."
    except Exception as processing_exc:
        log_entry.processing_status = "ERROR_PROCESSING"
        log_entry.processing_notes = f"Error during webhook processing: {str(processing_exc)}"
        # print(f"Error processing webhook {log_entry.id}: {processing_exc}")

    log_entry.processed_at = datetime.utcnow()
    db.commit()


# --- Payment Link Services ---
def create_payment_link(db: Session, link_create: schemas.PaymentLinkCreateRequest, customer_id: Optional[int]=None) -> models.PaymentLink:
    link_ref = "PLNK_" + uuid.uuid4().hex[:12].upper()
    # account_to_credit = get_bank_account(db, link_create.account_to_credit_id)
    # if not account_to_credit:
    #     raise NotFoundException("Account to credit for payment link not found.")

    db_link = models.PaymentLink(
        link_reference=link_ref,
        customer_id=customer_id,
        # account_to_credit_id=link_create.account_to_credit_id,
        amount=link_create.amount,
        currency=link_create.currency,
        description=link_create.description,
        is_reusable=link_create.is_reusable,
        max_usage_count=link_create.max_usage_count if link_create.is_reusable else 1,
        expiry_date=link_create.expiry_date,
        status="ACTIVE"
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

def get_payment_link_by_reference(db: Session, reference: str) -> Optional[models.PaymentLink]:
    return db.query(models.PaymentLink).filter(models.PaymentLink.link_reference == reference).first()

# Other services for Airtime, NQR, Remita, Monnify would follow similar patterns:
# - Client class for each.
# - Methods for specific operations (e.g., purchase_airtime, generate_nqr_code).
# - Use _make_request or specific SDKs.
# - Logging via _log_api_call.
# - Configuration via _get_gateway_config.
# - Secure handling of credentials.
