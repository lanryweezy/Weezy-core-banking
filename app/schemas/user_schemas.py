import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any

# Import enums from the SQLAlchemy model to ensure consistency
from app.models.user import UserStatus, AccountTier

class UserBase(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    username: str = Field(..., min_length=3, max_length=50, example="john_doe")
    full_name: Optional[str] = Field(None, max_length=100, example="John Doe")
    phone_number: Optional[str] = Field(None, max_length=20, example="+2348012345678")
    date_of_birth: Optional[datetime.date] = Field(None, example="1990-01-01")
    address: Optional[str] = Field(None, max_length=255, example="123 Main St, Lagos")

    # KYC and Identity - optional during base, but might be required in Create/Update
    bvn: Optional[str] = Field(None, min_length=11, max_length=11, example="12345678901")
    nin: Optional[str] = Field(None, min_length=11, max_length=11, example="98765432109")
    kyc_doc_references: Optional[Dict[str, Any]] = Field(None, example={"id_card": "doc_id_123", "utility_bill": "doc_id_456"})
    account_tier: AccountTier = Field(default=AccountTier.TIER1)

    is_sme_customer: bool = Field(default=False)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, example="strongpassword123")
    # BVN and NIN might be made mandatory here depending on bank policy for initial creation
    bvn: str = Field(..., min_length=11, max_length=11, example="12345678901")
    nin: Optional[str] = Field(None, min_length=11, max_length=11, example="98765432109") # NIN might be optional initially for some tiers

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, example="user@example.com")
    full_name: Optional[str] = Field(None, max_length=100, example="John Doe")
    phone_number: Optional[str] = Field(None, max_length=20, example="+2348012345678")
    date_of_birth: Optional[datetime.date] = Field(None, example="1990-01-01")
    address: Optional[str] = Field(None, max_length=255, example="123 Main St, Lagos")

    # KYC and Identity updates
    bvn: Optional[str] = Field(None, min_length=11, max_length=11, example="12345678901") # Usually BVN is not updatable once set
    nin: Optional[str] = Field(None, min_length=11, max_length=11, example="98765432109")
    kyc_doc_references: Optional[Dict[str, Any]] = Field(None, example={"id_card": "doc_id_789"})
    account_tier: Optional[AccountTier] = None
    kyc_status: Optional[str] = Field(None, example="PENDING_VERIFICATION") # Allow manual update of KYC status by admin

    is_sme_customer: Optional[bool] = None
    status: Optional[UserStatus] = None # Allow user status updates by admin/system

class UserResponse(UserBase):
    id: int
    status: UserStatus
    kyc_status: str
    is_staff: bool
    is_admin: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    last_login_at: Optional[datetime.datetime] = None

    class Config:
        orm_mode = True # Changed from from_attributes = True for Pydantic v1 compatibility if needed, orm_mode for general use

# Schemas for authentication
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Schema for password update
class UserPasswordUpdate(BaseModel):
    current_password: str = Field(..., example="currentstrongpassword")
    new_password: str = Field(..., min_length=8, example="newstrongpassword123")
