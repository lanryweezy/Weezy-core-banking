# Pydantic schemas for Compliance Agent

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class EntityInfo(BaseModel):
    entity_id: str = Field(..., example="CUST00123")
    name: str = Field(..., example="Acme Trading Ltd.")
    entity_type: str = Field(..., example="organization") # individual, organization
    date_of_birth_or_incorporation: Optional[date] = Field(None, example="2005-10-15")
    nationality_or_jurisdiction: Optional[str] = Field(None, example="NG")
    addresses: Optional[List[str]] = Field(None, example=["123 Main St, Lagos", "456 Business Ave, Abuja"])
    related_parties: Optional[List[str]] = Field(None, example=["John Doe (Director)", "Jane Smith (UBO)"])

class TransactionInfo(BaseModel):
    transaction_id: str = Field(..., example="TXNCOMP001")
    amount: float = Field(..., example=15000000.00)
    currency: str = Field("NGN", example="NGN")
    transaction_date: datetime = Field(default_factory=datetime.now)
    description: Optional[str] = Field(None, example="Payment for services")
    source_entity_id: Optional[str] = Field(None, example="CUST00123")
    destination_entity_id: Optional[str] = Field(None, example="CUST00456")
    destination_jurisdiction: Optional[str] = Field(None, example="US")

class ComplianceCheckRequest(BaseModel):
    entity_info: Optional[EntityInfo] = None
    transaction_info: Optional[TransactionInfo] = None
    check_types: List[str] = Field(..., example=["sanctions", "aml_rules", "internal_policy"]) # "pep", "adverse_media"

class SanctionMatch(BaseModel):
    list_name: str = Field(..., example="OFAC SDN List")
    matched_name: str = Field(..., example="Acme Trading")
    match_score: Optional[float] = Field(None, example=0.92)
    details_url: Optional[HttpUrl] = Field(None)

class AMLRuleViolation(BaseModel):
    rule_id: str = Field(..., example="CTR_NGN_001")
    description: str = Field(..., example="Exceeds Currency Transaction Reporting threshold for NGN.")
    severity: str = Field("High", example="Medium") # Low, Medium, High

class ComplianceReport(BaseModel):
    report_id: str = Field(..., example="COMPREP20231027XYZ")
    entity_id_checked: Optional[str] = None
    transaction_id_checked: Optional[str] = None
    check_timestamp: datetime = Field(default_factory=datetime.now)
    overall_risk_assessment: str = Field(..., example="High Risk") # Low, Medium, High, Clear
    sanctions_matches: List[SanctionMatch] = []
    aml_violations: List[AMLRuleViolation] = []
    other_flags: Optional[List[str]] = Field(None)
    summary: Optional[str] = Field(None, example="Entity matched on sanctions list and triggered CTR.")
    recommended_actions: Optional[List[str]] = Field(None, example=["File SAR", "Freeze account pending investigation"])

class SARInput(BaseModel):
    case_id: str = Field(..., example="CASE20231027-003")
    summary_of_suspicion: str = Field(..., example="Multiple large cash deposits followed by immediate international transfers to high-risk jurisdiction.")
    subject_entity: EntityInfo
    related_transactions: List[TransactionInfo]
    additional_narrative: Optional[str] = Field(None)

class AuditLogEntry(BaseModel):
    log_id: str
    timestamp: datetime
    agent_id: str = Field("ComplianceAgent")
    action: str # e.g., "SCREEN_ENTITY", "GENERATE_SAR_DRAFT"
    target_id: str # e.g., customer_id, transaction_id, case_id
    details: Dict[str, Any]

print("Compliance Agent Pydantic schemas placeholder.")
