# Pydantic schemas for Customer Onboarding Agent API requests and responses

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import uuid

# --- Enums for controlled vocabularies ---
class DocumentType(BaseModel):
    type_name: Literal["NationalID", "DriversLicense", "Passport", "UtilityBill", "BVN Slip", "NIN Slip", "Selfie", "Signature"]
    url: HttpUrl

class VerificationStatus(BaseModel):
    status: Literal["NotStarted", "Pending", "InProgress", "Verified", "Failed", "RequiresManualReview", "Expired"] = Field("NotStarted")
    message: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None # e.g., specific error codes, matched data

class VerificationStepResult(BaseModel):
    step_name: Literal["BVNVerification", "NINVerification", "IDDocumentCheck", "FaceMatch", "AddressVerification", "AMLScreening"]
    status: VerificationStatus = Field(default_factory=VerificationStatus)

class AccountTier(BaseModel):
    tier: Literal["Tier1", "Tier2", "Tier3"] = "Tier1"
    # Add specific limits or requirements if needed by the agent directly
    # daily_limit_ngn: Optional[float] = None
    # max_balance_ngn: Optional[float] = None


# --- Request Models ---
class OnboardingRequest(BaseModel):
    title: Optional[Literal["Mr", "Mrs", "Ms", "Chief", "Dr"]] = None
    first_name: str = Field(..., example="Adewale")
    last_name: str = Field(..., example="Ogunseye")
    middle_name: Optional[str] = None
    date_of_birth: str = Field(..., example="1990-01-15", description="YYYY-MM-DD") # Using str for flexibility, validation can be added
    gender: Optional[Literal["Male", "Female", "Other"]] = None
    phone_number: str = Field(..., example="08012345678")
    email_address: EmailStr = Field(..., example="adewale.ogunseye@example.com")

    bvn: Optional[str] = Field(None, min_length=11, max_length=11, example="12345678901")
    nin: Optional[str] = Field(None, min_length=11, max_length=11, example="98765432109")

    street_address: Optional[str] = Field(None, example="123, Main Street, Ikeja")
    city: Optional[str] = Field(None, example="Lagos")
    state: Optional[str] = Field(None, example="Lagos")
    # postal_code: Optional[str] = Field(None, example="100001")
    country: str = Field("NG", example="NG")

    requested_account_tier: AccountTier = Field(default_factory=AccountTier)
    documents: List[DocumentType] = Field(..., description="List of documents provided by the customer. Include Selfie, ID, Utility Bill as appropriate for tier.")

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "Adewale",
                "last_name": "Ogunseye",
                "date_of_birth": "1990-01-15",
                "phone_number": "08012345678",
                "email_address": "adewale.ogunseye@example.com",
                "bvn": "12345678901",
                "requested_account_tier": {"tier": "Tier1"},
                "documents": [
                    {"type_name": "Selfie", "url": "https://example.com/selfie.jpg"},
                    {"type_name": "NIN Slip", "url": "https://example.com/ninslip.pdf"} # For Tier 1, BVN/NIN is key
                ]
            }
        }

# --- Response Models ---
class OnboardingProcess(BaseModel):
    onboarding_id: str = Field(default_factory=lambda: f"ONB-{uuid.uuid4().hex[:12].upper()}")
    customer_id: Optional[str] = None # Assigned upon successful account creation
    status: Literal["Initiated", "PendingVerification", "VerificationFailed", "PendingAccountCreation", "Completed", "RequiresManualIntervention", "Cancelled"] = "Initiated"
    message: Optional[str] = "Onboarding process initiated."
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)

    requested_tier: AccountTier
    achieved_tier: Optional[AccountTier] = None # Tier achieved after verification

    verification_steps: List[VerificationStepResult] = []

    # Store a copy of the initial request data for reference (optional, could be large)
    # request_details: Optional[OnboardingRequest] = None

    next_actions: Optional[List[str]] = Field(None, description="Suggested next steps for the customer or bank staff.")

    class Config:
        json_schema_extra = {
            "example": {
                "onboarding_id": "ONB-A1B2C3D4E5F6",
                "status": "PendingVerification",
                "message": "BVN and document verification in progress.",
                "created_at": "2023-10-28T10:00:00Z",
                "last_updated_at": "2023-10-28T10:05:00Z",
                "requested_tier": {"tier": "Tier1"},
                "verification_steps": [
                    {
                        "step_name": "BVNVerification",
                        "status": {"status": "InProgress", "last_updated": "2023-10-28T10:05:00Z"}
                    },
                    {
                        "step_name": "IDDocumentCheck",
                        "status": {"status": "NotStarted", "last_updated": "2023-10-28T10:00:00Z"}
                    }
                ]
            }
        }

# This can be the same as OnboardingProcess if the GET status returns the full object
OnboardingStatusResponse = OnboardingProcess

if __name__ == "__main__":
    # Example usage for generating schema for documentation or testing
    import json

    print("--- OnboardingRequest Schema ---")
    print(json.dumps(OnboardingRequest.model_json_schema(), indent=2))

    print("\n--- OnboardingStatusResponse Schema ---")
    print(json.dumps(OnboardingStatusResponse.model_json_schema(), indent=2))

    # Example instantiation
    # try:
    #     req_example = OnboardingRequest(
    #         first_name="Bola",
    #         last_name="Adekunle",
    #         date_of_birth="1985-05-20",
    #         phone_number="07098765432",
    #         email_address="bola@example.com",
    #         bvn="09876543210",
    #         requested_account_tier={"tier": "Tier2"},
    #         documents=[
    #             {"type_name": "Selfie", "url": "http://example.com/bola_selfie.jpg"},
    #             {"type_name": "NationalID", "url": "http://example.com/bola_id.pdf"},
    #             {"type_name": "UtilityBill", "url": "http://example.com/bola_bill.pdf"}
    #         ]
    #     )
    #     print("\n--- Valid OnboardingRequest instance ---")
    #     print(req_example.model_dump_json(indent=2))

    #     resp_example = OnboardingStatusResponse(
    #         onboarding_id="ONB-TEST123",
    #         status="PendingVerification",
    #         requested_tier=req_example.requested_account_tier,
    #         verification_steps=[
    #             VerificationStepResult(step_name="BVNVerification", status={"status": "InProgress"}),
    #             VerificationStepResult(step_name="IDDocumentCheck", status={"status": "Pending"})
    #         ]
    #     )
    #     print("\n--- Valid OnboardingStatusResponse instance ---")
    #     print(resp_example.model_dump_json(indent=2))

    # except ValidationError as e:
    #     print(e.errors())
    pass
