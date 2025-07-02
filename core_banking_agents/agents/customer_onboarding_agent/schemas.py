# Pydantic schemas for Customer Onboarding Agent API requests and responses

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List

class OnboardingInput(BaseModel):
    name: str = Field(..., example="Adaobi Nwosu")
    bvn: Optional[str] = Field(None, min_length=11, max_length=11, example="12345678901")
    nin: Optional[str] = Field(None, min_length=11, max_length=11, example="98765432109")
    id_card_url: HttpUrl = Field(..., example="https://example.com/id_card.jpg")
    utility_bill_url: HttpUrl = Field(..., example="https://example.com/utility_bill.pdf")
    selfie_url: HttpUrl = Field(..., example="https://example.com/selfie.png")
    tier: Optional[str] = Field("Tier1", example="Tier1", description="Account tier (Tier1, Tier2, Tier3)")

class VerificationResult(BaseModel):
    check_type: str = Field(..., example="BVN Verification")
    status: str = Field(..., example="Verified") # Verified, Failed, Pending
    message: Optional[str] = Field(None, example="BVN details match.")
    details: Optional[dict] = Field(None)

class OnboardingResponse(BaseModel):
    onboarding_id: str = Field(..., example="ONB123456789")
    status: str = Field(..., example="Pending") # Pending, Approved, Rejected, NeedsReview
    message: Optional[str] = Field(None, example="Onboarding process initiated.")
    customer_id: Optional[str] = Field(None, example="CUST987654321")
    verifications: List[VerificationResult] = []
    next_steps: Optional[str] = Field(None, example="Upload proof of address if tier upgrade is needed.")

class DocumentData(BaseModel):
    document_type: str = Field(..., example="Passport")
    extracted_text: Optional[str] = None
    is_valid: bool = False

print("Customer Onboarding Agent Pydantic schemas placeholder.")
