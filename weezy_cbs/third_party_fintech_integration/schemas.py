# Pydantic schemas for Third-Party & Fintech Integration Module
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import decimal

from .models import ThirdPartyServiceEnum, TPAPILogDirectionEnum, TPAPILogStatusEnum # Import enums

# --- ThirdPartyAPILog Schemas (Internal) ---
class ThirdPartyAPILogBase(BaseModel):
    service_name: ThirdPartyServiceEnum
    endpoint_url: str
    http_method: str
    direction: TPAPILogDirectionEnum
    request_payload: Optional[Any] = None # Parsed JSON/XML or raw string
    response_status_code: Optional[int] = None
    response_payload: Optional[Any] = None
    status: TPAPILogStatusEnum
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    # internal_request_reference: Optional[str] = None
    external_call_reference: Optional[str] = None

class ThirdPartyAPILogResponse(ThirdPartyAPILogBase):
    id: int
    request_headers: Optional[Dict[str, str]] = None # Assuming stored as JSON string, parsed here
    response_headers: Optional[Dict[str, str]] = None
    timestamp: datetime

    class Config:
        orm_mode = True
        use_enum_values = True

# --- ThirdPartyConfig Schemas (Admin/Setup) ---
class ThirdPartyConfigBase(BaseModel):
    service_name: ThirdPartyServiceEnum
    api_base_url: HttpUrl
    # additional_config_json: Optional[Dict[str, Any]] = None
    is_active: bool = True

class ThirdPartyConfigCreateRequest(ThirdPartyConfigBase):
    # Plain text credentials provided during creation, encrypted by service layer
    # username_plain: Optional[str] = None
    # password_plain: Optional[str] = None
    # api_key_plain: Optional[str] = None
    pass # Assume credentials managed via vault or secure env vars, not direct API for now

class ThirdPartyConfigResponse(ThirdPartyConfigBase):
    id: int
    # Indicate if credentials are set, not the credentials themselves
    # has_credentials_configured: bool
    last_updated: Optional[datetime] = None

    class Config:
        orm_mode = True
        use_enum_values = True


# --- Credit Bureau Schemas ---
class CreditReportRequestSchema(BaseModel): # Input to our service to request a report
    bvn: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    # customer_id: int # Our internal customer ID
    # loan_application_id: Optional[int] = None # If request is for a specific loan app
    bureau_to_use: ThirdPartyServiceEnum # CREDIT_BUREAU_CRC or CREDIT_BUREAU_FIRSTCENTRAL
    # reason_for_query: str = "LOAN_APPLICATION" # As required by bureaus

class CreditReportResponseSchema(BaseModel): # Output from our service after getting report
    # our_internal_report_id: int # ID from CreditBureauReport model
    bvn_queried: str
    bureau_name: ThirdPartyServiceEnum
    report_reference_external: str # Report ID from bureau
    report_date: datetime
    credit_score: Optional[int] = None
    # summary_data: Optional[Dict[str, Any]] = None # Key data points
    # full_report_link_or_data: Optional[Any] = None # Link to PDF/XML or embedded data (if small)
    status: str # e.g. "SUCCESS", "FAILED_AT_BUREAU", "NO_HIT"

    class Config:
        orm_mode = True # If mapping from CreditBureauReport model for some fields
        use_enum_values = True

# --- NIMC NIN Verification Schemas (if distinct from NIBSS) ---
class NIMCNINVerificationRequest(BaseModel):
    nin: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    # Potentially other fields like DOB for matching if required by NIMC API

class NIMCNINVerificationResponse(BaseModel):
    is_valid: bool
    message: str
    # Matched NIN details from NIMC:
    # first_name: Optional[str] = None
    # last_name: Optional[str] = None
    # date_of_birth: Optional[date] = None
    # photo_base64: Optional[str] = None # If NIMC returns photo
    # other_demographic_data: Optional[Dict[str, Any]] = None

# --- External Loan Application Schemas (for incoming loan apps from partners) ---
class ExternalLoanApplicationPayload(BaseModel): # Payload received from originator
    originator_reference_id: str
    # Customer details:
    customer_bvn: str
    customer_first_name: str
    customer_last_name: str
    customer_phone: str
    customer_email: Optional[EmailStr] = None
    # Loan details:
    requested_amount: decimal.Decimal
    requested_tenor_months: int
    loan_purpose: Optional[str] = None
    # Other data from originator...
    additional_data: Optional[Dict[str, Any]] = None

class ExternalLoanApplicationReceiveRequest(BaseModel):
    originator_name: ThirdPartyServiceEnum # e.g. EXTERNAL_LOAN_ORIGINATOR_Y
    application_payload: ExternalLoanApplicationPayload

class ExternalLoanApplicationReceiveResponse(BaseModel):
    # our_internal_tracking_id: int # ID from ExternalLoanApplication model
    originator_reference_id: str
    status: str # e.g. "RECEIVED_PENDING_REVIEW", "VALIDATION_FAILED"
    message: Optional[str] = None

# --- BaaS Partner API Call Schemas (Conceptual, if we expose APIs to partners) ---
# These would be defined by the services we expose via BaaS.
# Example: BaaS Partner wants to create a virtual account for their end-user.
class BaaSVirtualAccountCreationRequest(BaseModel):
    partner_client_id: str # Authenticated BaaS partner
    end_user_identifier: str # Partner's ID for their customer
    # Required KYC details for the virtual account (as per CBN tiering for BaaS)
    # first_name: str
    # last_name: str
    # bvn: Optional[str] = None # Depending on tier
    # ...

class BaaSVirtualAccountCreationResponse(BaseModel):
    virtual_account_number: str
    # account_tier: str
    # status: str
    # ...

# Schemas for Bill Payment Aggregators would be similar to those in PaymentsIntegrationLayer
# if this module handles specific aggregator logic beyond generic payment processing.

# This module's schemas are often wrappers around what the third-party expects or provides,
# plus our internal tracking/status fields.
# They facilitate communication between our core CBS and external systems.

# Import decimal for fields that might handle it
import decimal
