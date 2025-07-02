# Pydantic schemas for Compliance Agent

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date
import uuid

# --- Enums and Helper Models ---
EntityType = Literal["Individual", "Organization"]
ScreeningCheckType = Literal["Sanctions", "PEP", "AdverseMedia", "InternalWatchlist"]
ScreeningStatus = Literal["Pending", "Clear", "PotentialHit", "ConfirmedHit", "Error"]
RiskRating = Literal["Low", "Medium", "High", "Critical"]

class EntityToScreen(BaseModel):
    entity_id: str = Field(default_factory=lambda: f"ENT-{uuid.uuid4().hex[:10].upper()}", description="A unique ID for this entity within the request or system.")
    entity_type: EntityType
    name: str = Field(..., example="Victor 'The Phantom' Zakhaev") # Full name for individual, registered name for org

    # Individual-specific
    date_of_birth: Optional[date] = Field(None, example="1970-01-15")
    nationality: Optional[str] = Field(None, example="RU") # ISO 3166-1 alpha-2 codes
    id_numbers: Optional[List[Dict[str, str]]] = Field(None, example=[{"type": "Passport", "value": "P12345RU"}])

    # Organization-specific
    registration_number: Optional[str] = Field(None, example="RC123456")
    country_of_incorporation: Optional[str] = Field(None, example="NG")

    # Common
    addresses: Optional[List[str]] = Field(None, example=["10 Downing Street, London, UK", "Unknown Hideout, Siberia"])
    aliases: Optional[List[str]] = Field(None, example=["The Phantom", "Viktor Z."])
    source_of_information: Optional[str] = Field(None, example="New Customer Onboarding: ONB-123")

    # Ensure either DOB/Nationality (for Individual) or RegNo/Country (for Org) is somewhat present if type matches
    # More complex validation can be added with @validator if needed.

class ScreeningRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"SCRREQ-{uuid.uuid4().hex[:10].upper()}")
    entities_to_screen: List[EntityToScreen] = Field(..., min_length=1) # min_items for older Pydantic
    checks_to_perform: List[ScreeningCheckType] = Field(..., example=["Sanctions", "PEP"])
    requestor_id: Optional[str] = Field(None, example="OnboardingAgent_ProcessXYZ") # Who initiated this
    reason_for_screening: Optional[str] = Field(None, example="New customer KYC")

# --- Response Models ---
class ScreeningHitDetails(BaseModel):
    list_name: str = Field(..., example="UN Consolidated Sanctions List")
    matched_name: str = Field(..., example="Viktor Zakhaev")
    match_strength: Optional[float] = Field(None, ge=0, le=1, example=0.95)
    hit_reason: Optional[str] = Field(None, example="Association with terrorist financing activities.")
    source_url: Optional[HttpUrl] = Field(None, example="https://scsanctions.un.org/viktor-zakhaev")
    additional_match_info: Optional[Dict[str, Any]] = None

class ScreeningResult(BaseModel):
    entity_id: str # From EntityToScreen
    input_name: str # Name provided in the request for this entity
    screening_status: ScreeningStatus = "Pending"
    overall_risk_rating: Optional[RiskRating] = None # Determined after all checks
    hits: Optional[List[ScreeningHitDetails]] = None
    errors: Optional[List[str]] = None # Errors specific to this entity's screening
    summary_message: Optional[str] = "Screening initiated."
    last_checked_at: Optional[datetime] = None

class ScreeningResponse(BaseModel):
    request_id: str # From ScreeningRequest
    response_timestamp: datetime = Field(default_factory=datetime.utcnow)
    overall_status: Literal["Pending", "Completed", "PartiallyCompleted", "Failed"] = "Pending"
    results_per_entity: List[ScreeningResult]

# --- SAR (Suspicious Activity Report) Data Input (Placeholder) ---
class SARDataInput(BaseModel):
    sar_id: Optional[str] = Field(None, description="System generated ID if creating new")
    case_reference_id: str = Field(..., example="ALERT-001-TXN-FRD", description="Link to internal case or alert")
    reporting_officer_id: str = Field(..., example="MLRO_JANE_DOE")
    date_of_suspicion: date = Field(..., example="2023-10-28")
    suspicion_summary: str = Field(..., example="Series of large, structured cash deposits followed by rapid international transfers to a high-risk jurisdiction by customer CUST-XYZ.")
    subject_entities: List[EntityToScreen] # Details of involved parties
    related_transaction_ids: Optional[List[str]] = None
    # ... more fields as per NFIU goAML requirements
    narrative: str = Field(..., description="Detailed narrative of the suspicious activity.")


if __name__ == "__main__":
    import json
    print("--- EntityToScreen Schema ---")
    print(json.dumps(EntityToScreen.model_json_schema(), indent=2))
    print("\n--- ScreeningRequest Schema ---")
    print(json.dumps(ScreeningRequest.model_json_schema(), indent=2))
    print("\n--- ScreeningResponse Schema ---")
    print(json.dumps(ScreeningResponse.model_json_schema(), indent=2))
    print("\n--- SARDataInput Schema (Placeholder) ---")
    print(json.dumps(SARDataInput.model_json_schema(), indent=2))

    # Example Instantiation
    # try:
    #     entity1 = EntityToScreen(entity_type="Individual", name="John Doe", date_of_birth="1980-01-01", nationality="NG")
    #     entity2 = EntityToScreen(entity_type="Organization", name="Acme Corp Ltd", registration_number="RC009988", country_of_incorporation="NG")
    #     req = ScreeningRequest(entities_to_screen=[entity1, entity2], checks_to_perform=["Sanctions", "PEP"])
    #     print("\nValid ScreeningRequest instance:\n", req.model_dump_json(indent=2))

    #     res_entity1 = ScreeningResult(entity_id=entity1.entity_id, input_name=entity1.name, screening_status="Clear", overall_risk_rating="Low")
    #     hit_detail = ScreeningHitDetails(list_name="Mock Watchlist", matched_name="Acme Corp", hit_reason="Adverse media regarding director.")
    #     res_entity2 = ScreeningResult(entity_id=entity2.entity_id, input_name=entity2.name, screening_status="PotentialHit", overall_risk_rating="Medium", hits=[hit_detail])
    #     resp = ScreeningResponse(request_id=req.request_id, overall_status="Completed", results_per_entity=[res_entity1, res_entity2])
    #     print("\nValid ScreeningResponse instance:\n", resp.model_dump_json(indent=2))

    # except Exception as e:
    #     print("\nError during schema instantiation example:", e)
    pass
