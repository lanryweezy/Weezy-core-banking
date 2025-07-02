# Pydantic schemas for Customer & Identity Management
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
import enum

# Enum for Account Tier (mirrors the one in models.py for validation)
class AccountTierSchema(str, enum.Enum):
    TIER1 = "Tier 1"
    TIER2 = "Tier 2"
    TIER3 = "Tier 3"

class CustomerBase(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: str = Field(..., min_length=11, max_length=15, description="Customer's primary phone number")
    first_name: str = Field(..., min_length=2)
    last_name: str = Field(..., min_length=2)
    middle_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None # Pydantic will parse ISO date strings
    address: Optional[str] = None
    bvn: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$")
    nin: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$")
    account_tier: Optional[AccountTierSchema] = AccountTierSchema.TIER1

    @validator('date_of_birth', pre=True, always=True)
    def parse_date_of_birth(cls, value):
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Invalid date format for date_of_birth. Use ISO format.")
        return value

class CustomerCreate(CustomerBase):
    # Specific fields for creation, if any, e.g., password for a portal user
    # For now, inherits all from CustomerBase
    pass

class CustomerUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, min_length=11, max_length=15)
    first_name: Optional[str] = Field(None, min_length=2)
    last_name: Optional[str] = Field(None, min_length=2)
    middle_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    address: Optional[str] = None
    bvn: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$") # Allow update if not set
    nin: Optional[str] = Field(None, min_length=11, max_length=11, pattern=r"^\d{11}$") # Allow update if not set
    account_tier: Optional[AccountTierSchema] = None
    is_active: Optional[bool] = None

class CustomerResponse(CustomerBase):
    id: int
    is_active: bool
    is_verified_bvn: bool
    is_verified_nin: bool
    is_verified_identity_document: bool
    is_verified_address: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True # For Pydantic to work with SQLAlchemy models directly
        use_enum_values = True # To serialize enum members to their values

class CustomerDocumentBase(BaseModel):
    document_type: str = Field(..., description="e.g., 'PASSPORT', 'NIN_SLIP', 'UTILITY_BILL', 'SELFIE'")
    document_url: str = Field(..., description="URL to the stored document")

class CustomerDocumentCreate(CustomerDocumentBase):
    customer_id: int

class CustomerDocumentResponse(CustomerDocumentBase):
    id: int
    customer_id: int
    uploaded_at: datetime
    verified_at: Optional[datetime] = None
    is_verified: bool

    class Config:
        orm_mode = True

class CustomerProfileResponse(CustomerResponse):
    # accounts: List[dict] = [] # Replace with actual AccountSchema from accounts_ledger_management
    documents: List[CustomerDocumentResponse] = []
    # Potentially more aggregated data for a 360 view

class BVNVerificationRequest(BaseModel):
    bvn: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    # Potentially other details required by NIBSS or internal checks like DOB, Phone
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None # YYYY-MM-DD

class BVNVerificationResponse(BaseModel):
    is_valid: bool
    message: str
    bvn_data: Optional[dict] = None # Data returned from NIBSS like name, dob, etc.

class NINVerificationRequest(BaseModel):
    nin: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    # Potentially other details

class NINVerificationResponse(BaseModel):
    is_valid: bool
    message: str
    nin_data: Optional[dict] = None

class KYCStatusUpdate(BaseModel):
    is_verified_bvn: Optional[bool] = None
    is_verified_nin: Optional[bool] = None
    is_verified_identity_document: Optional[bool] = None
    is_verified_address: Optional[bool] = None
    account_tier: Optional[AccountTierSchema] = None
    notes: Optional[str] = None # For audit logging

# Example for a paginated response
class PaginatedCustomerResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
    page: int
    size: int
    # pages: int # Can be calculated total / size
