# Pydantic schemas for Customer & Identity Management
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date # Use date for date-only fields
import enum

# Import enums from models to ensure consistency (or redefine if needed for API variations)
from .models import CBNSupportedAccountTier as ModelAccountTierEnum
from .models import CustomerTypeEnum as ModelCustomerTypeEnum
from .models import GenderEnum as ModelGenderEnum


# Schema version of Enums for API usage (explicit string values)
class AccountTierSchema(str, enum.Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"

class CustomerTypeSchema(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    SME = "SME"
    CORPORATE = "CORPORATE"

class GenderSchema(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class CustomerBase(BaseModel):
    customer_type: CustomerTypeSchema = CustomerTypeSchema.INDIVIDUAL

    bvn: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$", description="Bank Verification Number")
    nin: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$", description="National Identity Number")
    tin: Optional[str] = Field(None, description="Tax Identification Number")
    rc_number: Optional[str] = Field(None, description="CAC Registration Number for businesses")

    first_name: Optional[str] = Field(None, min_length=2)
    last_name: Optional[str] = Field(None, min_length=2)
    middle_name: Optional[str] = None
    company_name: Optional[str] = Field(None, min_length=2, description="Required if customer_type is SME or CORPORATE")

    email: Optional[EmailStr] = None
    phone_number: str = Field(..., min_length=11, max_length=15, description="Primary phone number, e.g., 08012345678 or +2348012345678")

    date_of_birth: Optional[date] = None # For individuals
    date_of_incorporation: Optional[date] = None # For SME/Corporate

    gender: Optional[GenderSchema] = None
    nationality: str = Field("NG", min_length=2, max_length=2, description="ISO 2-letter country code")
    mother_maiden_name: Optional[str] = None
    occupation: Optional[str] = None
    employer_name: Optional[str] = None

    street_address1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None # Nigerian State

    account_tier: AccountTierSchema = AccountTierSchema.TIER_1 # Default, can be determined by service layer

    # Next of Kin
    next_of_kin_name: Optional[str] = None
    next_of_kin_phone: Optional[str] = None
    next_of_kin_relationship: Optional[str] = None
    next_of_kin_address: Optional[str] = None

    referral_code_used: Optional[str] = None
    is_pep: Optional[bool] = Field(False, description="Is the customer a Politically Exposed Person?")


    @validator('company_name', always=True)
    def company_name_required_for_non_individual(cls, v, values):
        if values.get('customer_type') in [CustomerTypeSchema.SME, CustomerTypeSchema.CORPORATE] and not v:
            raise ValueError('company_name is required for SME/CORPORATE customer types')
        if values.get('customer_type') == CustomerTypeSchema.INDIVIDUAL and v:
            # Optionally clear or raise error if company_name provided for individual
            # For now, let's allow it but it might not be used.
            pass
        return v

    @validator('first_name', 'last_name', 'date_of_birth', 'gender', 'mother_maiden_name', always=True)
    def individual_fields_consistency(cls, v, values, field):
        if values.get('customer_type') == CustomerTypeSchema.INDIVIDUAL and v is None and field.name in ['first_name', 'last_name', 'date_of_birth']: # Gender MMN optional
            raise ValueError(f'{field.name} is required for INDIVIDUAL customer type')
        if values.get('customer_type') != CustomerTypeSchema.INDIVIDUAL and v is not None and field.name in ['date_of_birth', 'gender', 'mother_maiden_name']:
             # Optionally clear or raise error for individual-specific fields on corporate
            pass
        return v

    @validator('rc_number', 'date_of_incorporation', always=True)
    def corporate_fields_consistency(cls, v, values, field):
        if values.get('customer_type') in [CustomerTypeSchema.SME, CustomerTypeSchema.CORPORATE] and v is None and field.name in ['rc_number', 'date_of_incorporation']:
            raise ValueError(f'{field.name} is required for SME/CORPORATE customer types')
        return v


class CustomerCreate(CustomerBase):
    # Tier 1 might only require phone_number, first_name, last_name, (DOB or Address part for some tiers)
    # This schema allows more, service layer will determine tier based on data provided.
    # For strict Tier 1 minimal onboarding:
    # phone_number: str
    # first_name: str
    # last_name: str
    # (other fields become optional if not even in CustomerBase)
    pass

class CustomerUpdate(BaseModel): # Only allow updating specific fields
    email: Optional[EmailStr] = None
    # phone_number: Optional[str] = Field(None, min_length=11, max_length=15) # Primary phone usually not easily updatable
    middle_name: Optional[str] = None
    occupation: Optional[str] = None
    employer_name: Optional[str] = None
    street_address1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    # KYC related fields that might be updated post-verification
    bvn: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$")
    nin: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$")
    tin: Optional[str] = None

    # Next of Kin
    next_of_kin_name: Optional[str] = None
    next_of_kin_phone: Optional[str] = None
    next_of_kin_relationship: Optional[str] = None
    next_of_kin_address: Optional[str] = None

    is_pep: Optional[bool] = None
    segment: Optional[str] = None
    # is_active: Optional[bool] = None # Status changes usually via specific endpoint/service

class CustomerResponse(CustomerBase): # What is returned by API after creation or GET
    id: int
    is_active: bool
    is_verified_bvn: bool
    is_verified_nin: bool
    is_verified_identity_document: bool
    is_verified_address: bool
    # own_referral_code: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        use_enum_values = True # Serialize enums to their string values

class CustomerDocumentBase(BaseModel):
    document_type: str = Field(..., description="e.g., 'PASSPORT', 'NIN_SLIP', 'UTILITY_BILL', 'CAC_CERTIFICATE', 'SELFIE'")
    document_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    document_url: str = Field(..., description="URL to the stored document")

class CustomerDocumentCreate(CustomerDocumentBase):
    customer_id: int # Provided when creating a document for a customer

class CustomerDocumentResponse(CustomerDocumentBase):
    id: int
    customer_id: int
    uploaded_at: datetime
    verified_at: Optional[datetime] = None
    is_verified: bool
    verification_meta_json: Optional[Dict[str, Any]] = None # Parsed from Text by Pydantic

    class Config:
        orm_mode = True

# Minimal account summary for embedding in CustomerProfileResponse
class LinkedAccountSummarySchema(BaseModel):
    account_number: str
    account_type: str # e.g. "SAVINGS", "CURRENT"
    currency: str
    status: str
    class Config:
        orm_mode = True # If it ever maps from an ORM model fragment

class CustomerProfileResponse(CustomerResponse): # For 360 view
    documents: List[CustomerDocumentResponse] = []
    linked_accounts_summary: List[LinkedAccountSummarySchema] = [] # Summary of linked accounts
    # kyc_audit_logs: List[KYCAuditLogResponse] = [] # If exposing audit logs here
    # overall_kyc_level_met: Optional[str] = None # e.g. "Tier 1 Complete", "Tier 3 Pending Address Verification"


class BVNVerificationRequest(BaseModel):
    bvn: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    # NIBSS often requires more for full validation, e.g. if used for account opening
    # For simple validation, BVN alone might suffice for some NIBSS endpoints.
    # Adding phone number as it's often part of NIBSS record.
    phone_number: Optional[str] = Field(None, description="Phone number associated with BVN, for validation")
    # first_name: Optional[str] = None
    # last_name: Optional[str] = None
    # date_of_birth: Optional[date] = None

class BVNVerificationResponse(BaseModel):
    is_valid: bool # Was the BVN found and does it match provided details (if any)?
    message: str
    bvn_data: Optional[Dict[str, Any]] = None # Parsed data from NIBSS (name, DOB, phone, photo ID ref etc.)

class NINVerificationRequest(BaseModel):
    nin: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    # Similar to BVN, other fields might be needed by NIMC for full validation.
    # first_name: Optional[str] = None
    # last_name: Optional[str] = None
    # phone_number: Optional[str] = None # Often linked to NIN

class NINVerificationResponse(BaseModel):
    is_valid: bool
    message: str
    nin_data: Optional[Dict[str, Any]] = None # Parsed data from NIMC (name, DOB, photo etc.)

class KYCStatusUpdateRequest(BaseModel): # For admin/system to update verification flags
    is_verified_bvn: Optional[bool] = None
    is_verified_nin: Optional[bool] = None
    is_verified_identity_document: Optional[bool] = None # Specify which doc in notes or separate endpoint
    is_verified_address: Optional[bool] = None
    account_tier_override: Optional[AccountTierSchema] = None # If admin manually sets tier
    is_pep_status_override: Optional[bool] = None # Admin overriding PEP status after review
    notes: str = Field(..., description="Reason or audit note for this KYC status update")

class PaginatedCustomerResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
    page: int
    size: int
