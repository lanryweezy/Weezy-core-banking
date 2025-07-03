# Pydantic schemas for Compliance & Regulatory Reporting Module
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import decimal
import enum # For Pydantic enums

# Import enums from models to ensure consistency
from .models import (
    ReportNameEnum as ModelReportNameEnum,
    ReportStatusEnum as ModelReportStatusEnum
)

# Schema Enums
class ReportNameSchema(str, enum.Enum):
    CBN_CRMS = "CBN_CRMS"; NDIC_RETURNS = "NDIC_RETURNS"; NFIU_STR = "NFIU_STR"
    NFIU_CTR = "NFIU_CTR"; CBN_FINA = "CBN_FINA"; CBN_OVERSIGHT = "CBN_OVERSIGHT"

class ReportStatusSchema(str, enum.Enum):
    PENDING_GENERATION = "PENDING_GENERATION"; GENERATING = "GENERATING"; GENERATED = "GENERATED"
    VALIDATION_PENDING = "VALIDATION_PENDING"; VALIDATED = "VALIDATED"
    SUBMISSION_PENDING = "SUBMISSION_PENDING"; SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"; QUERIED = "QUERIED"
    FAILED_GENERATION = "FAILED_GENERATION"; FAILED_SUBMISSION = "FAILED_SUBMISSION"


# --- Generated Report Log Schemas ---
class GeneratedReportLogBase(BaseModel):
    report_name: ReportNameSchema # Use schema enum
    reporting_period_start_date: date
    reporting_period_end_date: date
    notes: Optional[str] = None

class GeneratedReportLogCreateRequest(GeneratedReportLogBase):
    pass

class GeneratedReportLogResponse(GeneratedReportLogBase):
    id: int
    status: ReportStatusSchema # Use schema enum
    generated_at: Optional[datetime] = None
    generated_by_user_id: Optional[str] = Field(None, max_length=50)
    file_path_or_url: Optional[str] = Field(None, max_length=512)
    file_format: Optional[str] = Field(None, max_length=10)
    checksum: Optional[str] = Field(None, max_length=64)
    submitted_at: Optional[datetime] = None
    submission_reference: Optional[str] = Field(None, max_length=100)
    validator_user_id: Optional[str] = Field(None, max_length=50)
    validated_at: Optional[datetime] = None
    validation_comments: Optional[str] = None
    class Config: orm_mode = True; use_enum_values = True

class ReportGenerationRequest(BaseModel):
    report_name: ReportNameSchema
    reporting_period_start_date: date
    reporting_period_end_date: date
    parameters: Optional[Dict[str, Any]] = Field(None, description="Report-specific generation parameters")

class ReportStatusUpdateRequest(BaseModel):
    new_status: ReportStatusSchema
    notes: Optional[str] = None
    file_path_or_url: Optional[str] = Field(None, max_length=512)
    submission_reference: Optional[str] = Field(None, max_length=100)

# --- AML Rule Schemas (Admin) ---
class AMLRuleBase(BaseModel):
    rule_code: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Z0-9_]+$")
    description: str
    parameters_json: Optional[Dict[str, Any]] = Field({}, description="JSON object for rule parameters")
    severity: str = Field("MEDIUM", max_length=20)
    action_to_take: str = Field("FLAG_FOR_REVIEW", max_length=50)
    is_active: bool = True

class AMLRuleCreateRequest(AMLRuleBase):
    pass

class AMLRuleUpdateRequest(BaseModel):
    description: Optional[str] = None
    parameters_json: Optional[Dict[str, Any]] = None
    severity: Optional[str] = Field(None, max_length=20)
    action_to_take: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

class AMLRuleResponse(AMLRuleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: orm_mode = True

# --- Suspicious Activity Log Schemas ---
class SuspiciousActivityLogBase(BaseModel):
    customer_id: Optional[int] = None
    account_id: Optional[int] = None
    financial_transaction_id: Optional[str] = Field(None, max_length=40)
    customer_bvn: Optional[str] = Field(None, max_length=11)
    account_number: Optional[str] = Field(None, max_length=20)
    transaction_reference_primary: Optional[str] = Field(None, max_length=40)
    aml_rule_code_triggered: str = Field(..., max_length=50)
    activity_description: str

class SuspiciousActivityLogResponse(SuspiciousActivityLogBase):
    id: int
    flagged_at: datetime
    status: str = Field(..., max_length=30)
    assigned_to_user_id: Optional[str] = Field(None, max_length=50)
    investigation_notes: Optional[str] = None
    resolution_date: Optional[datetime] = None
    str_report_log_id: Optional[int] = None
    class Config: orm_mode = True

class SuspiciousActivityStatusUpdateRequest(BaseModel):
    new_status: str = Field(..., description="e.g. OPEN, UNDER_INVESTIGATION, CLEARED, ESCALATED_TO_NFIU")
    assigned_to_user_id: Optional[str] = Field(None, max_length=50)
    investigation_notes: Optional[str] = None
    str_report_log_id: Optional[int] = Field(None, description="ID of the GeneratedReportLog if STR was filed")


# --- Sanction Screening Schemas ---
class SanctionScreeningRequest(BaseModel):
    name_to_screen: str = Field(..., max_length=255)
    entity_type: str = Field("INDIVIDUAL", max_length=20, description="INDIVIDUAL, CUSTOMER, COUNTERPARTY, BENEFICIARY")
    bvn_to_screen: Optional[str] = Field(None, max_length=11)
    customer_id: Optional[int] = None # If screening an existing customer

class SanctionScreeningResult(BaseModel): # Response from the screening service execution
    name_screened: str
    screening_date: datetime
    match_found: bool
    match_details: Optional[List[Dict[str, Any]]] = None
    sanction_lists_checked: Optional[List[str]] = None # Changed from text to list

class SanctionScreeningLogResponse(BaseModel): # For retrieving stored logs
    id: int
    customer_id: Optional[int] = None
    entity_type: str
    bvn_screened: Optional[str] = None
    name_screened: str
    screening_date: datetime
    sanction_lists_checked: Optional[List[str]] = None # Parsed from JSON Text in model
    match_found: bool
    match_details_json: Optional[List[Dict[str, Any]]] = None # Parsed from JSON Text in model
    class Config: orm_mode = True

# --- CTR/STR Data Schemas ---
class CTRRecordData(BaseModel): # Renamed from CTRRecordSchema
    transaction_reference_primary: str = Field(..., max_length=40)
    transaction_date: date
    transaction_amount: decimal.Decimal = Field(..., decimal_places=2)
    transaction_currency: str = Field(..., max_length=3)
    customer_bvn: Optional[str] = Field(None, max_length=11)
    # customer_name: str # Should be fetched based on BVN/Account
    account_number: Optional[str] = Field(None, max_length=20)
    # depositor_or_beneficiary_name: Optional[str] = None
    transaction_type: str = Field(..., max_length=50, description="e.g. CASH_DEPOSIT, CASH_WITHDRAWAL")
    # ... other NFIU CTR fields
    class Config: json_encoders = {decimal.Decimal: str}

class STRReportData(BaseModel): # Renamed from STRRecordSchema
    suspicious_activity_log_id: int
    # This would contain many fields structured according to NFIU's goAML STR template.
    # Example sections:
    # reporting_entity_info: Dict[str, Any]
    # suspicious_person_or_entity_info: List[Dict[str, Any]]
    # transaction_info: List[Dict[str, Any]]
    # grounds_for_suspicion: str
    # action_taken: str
    full_str_payload_json: Dict[str, Any] # For now, a generic dict for the payload

# --- Paginated Responses ---
class PaginatedReportLogResponse(BaseModel):
    items: List[GeneratedReportLogResponse]; total: int; page: int; size: int

class PaginatedAMLRuleResponse(BaseModel):
    items: List[AMLRuleResponse]; total: int; page: int; size: int

class PaginatedSuspiciousActivityLogResponse(BaseModel):
    items: List[SuspiciousActivityLogResponse]; total: int; page: int; size: int

class PaginatedSanctionScreeningLogResponse(BaseModel):
    items: List[SanctionScreeningLogResponse]; total: int; page: int; size: int
