# Pydantic schemas for Compliance & Regulatory Reporting Module
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import decimal

from .models import ReportNameEnum, ReportStatusEnum # Import enums

# --- Generated Report Log Schemas ---
class GeneratedReportLogBase(BaseModel):
    report_name: ReportNameEnum
    reporting_period_start_date: date
    reporting_period_end_date: date
    notes: Optional[str] = None

class GeneratedReportLogCreateRequest(GeneratedReportLogBase):
    # Triggered by system or admin
    pass

class GeneratedReportLogResponse(GeneratedReportLogBase):
    id: int
    status: ReportStatusEnum
    generated_at: Optional[datetime] = None
    generated_by_user_id: Optional[str] = None
    file_path_or_url: Optional[str] = None
    file_format: Optional[str] = None
    checksum: Optional[str] = None
    submitted_at: Optional[datetime] = None
    submission_reference: Optional[str] = None
    validator_user_id: Optional[str] = None
    validated_at: Optional[datetime] = None
    validation_comments: Optional[str] = None

    class Config:
        orm_mode = True
        use_enum_values = True

class ReportGenerationRequest(BaseModel): # Used to manually trigger a report
    report_name: ReportNameEnum
    reporting_period_start_date: date
    reporting_period_end_date: date
    # Specific parameters for the report if any, e.g., branch_filter
    # parameters: Optional[Dict[str, Any]] = None

class ReportStatusUpdateRequest(BaseModel): # For manual status updates by admin
    new_status: ReportStatusEnum
    notes: Optional[str] = None
    file_path_or_url: Optional[str] = None # If generated file path needs update
    submission_reference: Optional[str] = None # After manual submission

# --- AML Rule Schemas (Admin) ---
class AMLRuleBase(BaseModel):
    rule_code: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Z0-9_]+$")
    description: str
    parameters_json: Optional[Dict[str, Any]] = Field({}, description="JSON object for rule parameters") # Pydantic will parse from dict
    severity: str = "MEDIUM" # LOW, MEDIUM, HIGH, CRITICAL
    action_to_take: str = "FLAG_FOR_REVIEW"
    is_active: bool = True

class AMLRuleCreateRequest(AMLRuleBase):
    pass

class AMLRuleUpdateRequest(BaseModel):
    description: Optional[str] = None
    parameters_json: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None
    action_to_take: Optional[str] = None
    is_active: Optional[bool] = None

class AMLRuleResponse(AMLRuleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# --- Suspicious Activity Log Schemas ---
class SuspiciousActivityLogBase(BaseModel):
    # customer_id: Optional[int] = None
    # account_id: Optional[int] = None
    # financial_transaction_id: Optional[str] = None
    customer_bvn: Optional[str] = None
    account_number: Optional[str] = None
    transaction_reference_primary: Optional[str] = None

    aml_rule_code_triggered: str
    activity_description: str

class SuspiciousActivityLogResponse(SuspiciousActivityLogBase):
    id: int
    flagged_at: datetime
    status: str
    assigned_to_user_id: Optional[str] = None
    investigation_notes: Optional[str] = None
    resolution_date: Optional[datetime] = None
    # str_report_log_id: Optional[int] = None # Link to NFIU STR report

    class Config:
        orm_mode = True

class SuspiciousActivityStatusUpdateRequest(BaseModel):
    new_status: str # OPEN, UNDER_INVESTIGATION, CLEARED, ESCALATED_TO_NFIU
    assigned_to_user_id: Optional[str] = None
    investigation_notes: Optional[str] = None
    # str_filed_reference: Optional[str] = None # If STR was filed manually, capture ref

# --- Sanction Screening Schemas ---
class SanctionScreeningRequest(BaseModel):
    # For on-demand screening. Batch screening is an internal process.
    name_to_screen: str
    entity_type: Optional[str] = "INDIVIDUAL" # INDIVIDUAL, CORPORATE
    bvn_to_screen: Optional[str] = None
    # Other identifiers: date_of_birth, nationality, address etc.

class SanctionScreeningResult(BaseModel):
    name_screened: str
    screening_date: datetime
    match_found: bool
    match_details: Optional[List[Dict[str, Any]]] = None # List of matches from various sanction lists
    # sanction_lists_checked: List[str]

class SanctionScreeningLogResponse(BaseModel):
    id: int
    # customer_id: Optional[int] = None
    bvn_screened: Optional[str] = None
    name_screened: str
    screening_date: datetime
    sanction_lists_checked: Optional[str] = None # Stored as JSON string in DB, parsed to list/dict here if needed
    match_found: bool
    match_details_json: Optional[Dict[str, Any]] = None # Stored as JSON string, parsed to dict

    class Config:
        orm_mode = True

# --- CTR/STR Data Schemas (for generation, not direct API input usually) ---
class CTRRecordSchema(BaseModel): # Represents one record in a CTR file
    transaction_date: date
    transaction_amount: decimal.Decimal
    transaction_currency: str
    # customer_bvn: str
    # customer_name: str
    # account_number: str
    # depositor_name: Optional[str] = None # If different from account holder
    # transaction_type: str # CASH_DEPOSIT, CASH_WITHDRAWAL
    # ... other fields required by NFIU CTR format
    class Config:
        json_encoders = { decimal.Decimal: str }


class STRRecordSchema(BaseModel): # Represents data needed to compile an STR
    # Data from SuspiciousActivityLog, Customer, Account, Transaction models
    # E.g., customer_details: Dict, transaction_details: List[Dict], grounds_for_suspicion: str
    # ... many fields as per NFIU STR template
    pass


class PaginatedReportLogResponse(BaseModel):
    items: List[GeneratedReportLogResponse]
    total: int
    page: int
    size: int

class PaginatedAMLRuleResponse(BaseModel):
    items: List[AMLRuleResponse]
    total: int
    page: int
    size: int

class PaginatedSuspiciousActivityLogResponse(BaseModel):
    items: List[SuspiciousActivityLogResponse]
    total: int
    page: int
    size: int

class PaginatedSanctionScreeningLogResponse(BaseModel):
    items: List[SanctionScreeningLogResponse]
    total: int
    page: int
    size: int
