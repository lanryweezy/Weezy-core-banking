# Service layer for Third-Party & Fintech Integration Module
from sqlalchemy.orm import Session
import requests # Standard HTTP client
import json
from datetime import datetime
import uuid

from . import models, schemas
# from weezy_cbs.shared import exceptions, security_utils, http_client_wrapper
# from weezy_cbs.customer_identity_management.services import link_bureau_report_to_customer
# from weezy_cbs.loan_management_module.services import create_loan_application_from_external # (if applicable)

class ExternalServiceException(Exception): pass
class ConfigurationException(Exception): pass
class DataMappingException(Exception): pass

# --- Helper: Generic API Client (can be refactored into shared utility) ---
def _make_third_party_api_call(
    db: Session,
    service_enum: models.ThirdPartyServiceEnum,
    method: str,
    endpoint: str,
    payload: Optional[dict] = None,
    params: Optional[dict] = None,
    headers_override: Optional[dict] = None,
    internal_ref: Optional[str] = None # Our internal reference for this call
) -> dict: # Returns parsed JSON response

    config = db.query(models.ThirdPartyConfig).filter(
        models.ThirdPartyConfig.service_name == service_enum,
        models.ThirdPartyConfig.is_active == True
    ).first()
    if not config:
        raise ConfigurationException(f"Active configuration for service {service_enum.value} not found.")

    # Decrypt credentials if needed (using placeholder decryption)
    # api_key = security_utils.decrypt(config.api_key_encrypted) if config.api_key_encrypted else None
    # This is where you'd fetch actual API keys, tokens, certs based on config.
    # For mock, assume headers are constructed by specific service methods.

    base_url = config.api_base_url.rstrip('/')
    full_url = f"{base_url}/{endpoint.lstrip('/')}"

    default_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    final_headers = {**default_headers, **(headers_override or {})}

    start_time = datetime.utcnow()
    log_status = models.TPAPILogStatusEnum.PENDING
    log_error, log_resp_status_code, log_resp_payload, log_resp_headers, log_ext_ref = None, None, None, None, None

    try:
        response = requests.request(method.upper(), full_url, json=payload, params=params, headers=final_headers, timeout=60)
        log_resp_status_code = response.status_code
        log_resp_headers = dict(response.headers)

        try:
            log_resp_payload = response.json()
        except json.JSONDecodeError:
            log_resp_payload = {"raw_response": response.text}
            # print(f"{service_enum.value} response not JSON: {response.text}")

        if response.ok: # Basic check, specific services might have other success criteria
            log_status = models.TPAPILogStatusEnum.SUCCESS
            # Extract external reference if possible from response (e.g., report ID, transaction ID from 3rd party)
            # log_ext_ref = log_resp_payload.get("data", {}).get("id") or log_resp_payload.get("reference") # Example
        else:
            log_status = models.TPAPILogStatusEnum.FAILED
            log_error = log_resp_payload.get("message") or log_resp_payload.get("error") or f"Request failed with status {response.status_code}"
            # print(f"{service_enum.value} API Error: {log_error} - Response: {log_resp_payload}")

        # Return parsed JSON from response
        return log_resp_payload

    except requests.exceptions.RequestException as e:
        log_status = models.TPAPILogStatusEnum.FAILED
        log_error = f"HTTP Request Exception: {str(e)}"
        # print(f"{service_enum.value} HTTP Error: {log_error}")
        raise ExternalServiceException(log_error)
    finally:
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        # Log the API call (simplified logging call)
        log_entry = models.ThirdPartyAPILog(
            service_name=service_enum, endpoint_url=full_url, http_method=method.upper(), direction=models.TPAPILogDirectionEnum.OUTGOING,
            request_payload=json.dumps(payload) if payload else None, request_headers=json.dumps(final_headers),
            response_status_code=log_resp_status_code, response_payload=json.dumps(log_resp_payload) if log_resp_payload else None, response_headers=json.dumps(log_resp_headers),
            status=log_status, error_message=log_error, duration_ms=duration_ms,
            internal_request_reference=internal_ref, external_call_reference=log_ext_ref
        )
        db.add(log_entry)
        db.commit() # Commit log

# --- Credit Bureau Services ---
def get_credit_report(db: Session, request_data: schemas.CreditReportRequestSchema, requested_by_user_id: str) -> schemas.CreditReportResponseSchema:
    bureau_service_enum = request_data.bureau_to_use
    if bureau_service_enum not in [models.ThirdPartyServiceEnum.CREDIT_BUREAU_CRC, models.ThirdPartyServiceEnum.CREDIT_BUREAU_FIRSTCENTRAL]:
        raise ValueError("Invalid credit bureau specified.")

    # Construct payload specific to the bureau's API
    # This is highly dependent on the bureau's API specs.
    bureau_payload = {
        "bvn": request_data.bvn,
        "reasonCode": "01", # Example reason code for loan application
        "consumerInformation": { "enquiryType": "CONSUMER_CREDIT_REPORT" }
        # ... other required fields
    }

    internal_call_ref = f"CR_{request_data.bvn}_{uuid.uuid4().hex[:6]}"

    try:
        # Headers might include specific auth tokens for the bureau
        # bureau_headers = {"Authorization": f"Bearer {decrypted_bureau_api_key}"}
        bureau_response_json = _make_third_party_api_call(
            db, bureau_service_enum, "POST", "creditreport", # Example endpoint
            payload=bureau_payload, internal_ref=internal_call_ref #, headers_override=bureau_headers
        )

        # Map bureau's response to our internal CreditReport model and schema
        # This is critical and complex. Each bureau has a different response format.
        # Example mapping (highly simplified):
        report_ref_ext = bureau_response_json.get("reportId") or bureau_response_json.get("data",{}).get("enquiryReference")
        credit_score_val = bureau_response_json.get("summary",{}).get("creditScore") or bureau_response_json.get("data",{}).get("scoreValue")

        if not report_ref_ext: # Or if bureau indicates an error in its response payload
            # Even if HTTP call was 200, bureau might return error in body
            raise ExternalServiceException(f"Credit bureau ({bureau_service_enum.value}) returned error: {bureau_response_json.get('message', 'Unknown error')}")

        db_report = models.CreditBureauReport(
            bvn_queried=request_data.bvn,
            # customer_id=request_data.customer_id, # Link to customer
            # loan_application_id=request_data.loan_application_id, # Link to loan app
            bureau_name=bureau_service_enum,
            report_reference_external=report_ref_ext,
            report_date=datetime.utcnow(), # Or date from bureau report
            credit_score=int(credit_score_val) if credit_score_val else None,
            # summary_data_json=json.dumps(bureau_response_json.get("summary")),
            # full_report_path_or_lob=json.dumps(bureau_response_json), # Store full response for now
            requested_by_user_id=requested_by_user_id
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)

        return schemas.CreditReportResponseSchema(
            # our_internal_report_id=db_report.id,
            bvn_queried=db_report.bvn_queried,
            bureau_name=db_report.bureau_name,
            report_reference_external=db_report.report_reference_external,
            report_date=db_report.report_date,
            credit_score=db_report.credit_score,
            # summary_data=json.loads(db_report.summary_data_json) if db_report.summary_data_json else None,
            status="SUCCESS"
        )

    except ExternalServiceException as e:
        # Log detailed error from _make_third_party_api_call already happens
        return schemas.CreditReportResponseSchema(
            bvn_queried=request_data.bvn, bureau_name=bureau_service_enum,
            report_reference_external=None, report_date=datetime.utcnow(), status="FAILED_AT_BUREAU",
            message=str(e) # Pass along the error message
        )
    except Exception as e: # Catch other unexpected errors
        # Log e
        raise ExternalServiceException(f"Unexpected error getting credit report: {str(e)}")


# --- NIMC NIN Verification Service (Conceptual) ---
def verify_nin_with_nimc(db: Session, request_data: schemas.NIMCNINVerificationRequest) -> schemas.NIMCNINVerificationResponse:
    service_enum = models.ThirdPartyServiceEnum.NIMC_NIN_VERIFICATION
    # Payload for NIMC (this is fictional, actual API will differ)
    nimc_payload = {"nin": request_data.nin} # Add other fields like DOB if needed for matching
    internal_call_ref = f"NIN_{request_data.nin}_{uuid.uuid4().hex[:6]}"

    try:
        nimc_response_json = _make_third_party_api_call(
            db, service_enum, "POST", "verifyIdentity", # Fictional endpoint
            payload=nimc_payload, internal_ref=internal_call_ref
        )

        # Map NIMC response
        is_valid_nimc = nimc_response_json.get("status") == "VALID" # Fictional success indicator
        message = nimc_response_json.get("remarks") or ("NIN Valid" if is_valid_nimc else "NIN Invalid or Not Found")

        # demographic_data = nimc_response_json.get("demographics")
        return schemas.NIMCNINVerificationResponse(
            is_valid=is_valid_nimc,
            message=message,
            # first_name=demographic_data.get("firstName"),
            # ... map other fields ...
        )
    except ExternalServiceException as e:
        return schemas.NIMCNINVerificationResponse(is_valid=False, message=f"NIMC service error: {str(e)}")


# --- External Loan Application Ingestion Service ---
def receive_external_loan_application(db: Session, request_data: schemas.ExternalLoanApplicationReceiveRequest) -> schemas.ExternalLoanApplicationReceiveResponse:
    originator_service_enum = request_data.originator_name
    payload = request_data.application_payload

    # Validate originator is configured and active
    # _get_gateway_config(db, originator_service_enum) # Reuses helper to check config exists

    # Basic validation of payload
    if not payload.customer_bvn or not payload.requested_amount:
        raise DataMappingException("Missing required fields (BVN, amount) in external loan application payload.")

    # Log the incoming application
    db_ext_app = models.ExternalLoanApplication(
        originator_name=originator_service_enum,
        originator_reference_id=payload.originator_reference_id,
        # customer_bvn=payload.customer_bvn,
        # requested_amount=payload.requested_amount,
        # raw_payload_received_json=json.dumps(payload.dict()),
        status_at_originator=payload.additional_data.get("originator_status", "SUBMITTED"), # Example
        internal_status="PENDING_REVIEW" # Our initial status
    )
    # Populate more fields on db_ext_app from payload
    db.add(db_ext_app)
    db.commit()
    db.refresh(db_ext_app)

    # Optional: Automatically create an internal LoanApplication record
    # Or this can be a manual step by a loan officer after reviewing the external app log.
    # try:
    #     internal_app = create_loan_application_from_external(db, db_ext_app)
    #     db_ext_app.internal_loan_application_id = internal_app.id
    #     db.commit()
    # except Exception as e:
    #     # Log error, may need manual intervention
    #     db_ext_app.internal_status = "MAPPING_FAILED"
    #     db_ext_app.processing_notes = f"Failed to create internal loan app: {str(e)}"
    #     db.commit()

    return schemas.ExternalLoanApplicationReceiveResponse(
        # our_internal_tracking_id=db_ext_app.id,
        originator_reference_id=db_ext_app.originator_reference_id,
        status=db_ext_app.internal_status,
        message="External loan application received and logged."
    )

# --- BaaS Partner Services (Conceptual - if we provide APIs to partners) ---
# These services would be called by our API endpoints that BaaS partners consume.
# Example:
# def baas_create_virtual_account_for_partner(db: Session, partner_id: str, request_data: schemas.BaaSVirtualAccountCreationRequest) -> schemas.BaaSVirtualAccountCreationResponse:
    # 1. Authenticate BaaS partner (e.g. using partner_id and API key/secret)
    # 2. Validate request (e.g. KYC data provided by partner for their end-user)
    # 3. Call internal CustomerIdentityManagement and AccountsLedgerManagement services to create customer & account.
    #    - The customer created might be a "light KYC" or "sub-account" type under the BaaS partner's master relationship.
    # 4. Return virtual account details to the BaaS partner.
    #    return schemas.BaaSVirtualAccountCreationResponse(virtual_account_number="VACC123...", ...)
    # This is highly dependent on the BaaS product offering.

# Services for other integrations (Bill Aggregators if not in Payments, etc.) would follow a similar pattern:
# - Configuration model and loading.
# - API client logic (_make_third_party_api_call or custom).
# - Data mapping schemas and functions.
# - Logging of interactions.
# - Business logic that uses the integration.

# Note: Many of these services will be called by other core CBS modules.
# For example, LoanManagementModule's `perform_credit_assessment` would call `get_credit_report` here.
# CustomerIdentityManagement's KYC process would call `verify_nin_with_nimc`.
# This module centralizes the actual communication and data adaptation with these external third parties.
