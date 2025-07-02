# Pydantic schemas for Core Infrastructure & Config Engine
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from .models import ProductTypeEnum # Import enums

# --- Branch Schemas ---
class BranchBase(BaseModel):
    branch_code: str = Field(..., min_length=3, max_length=10) # e.g. Sort code prefix
    name: str = Field(..., min_length=3)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    is_active: bool = True

class BranchCreateRequest(BranchBase):
    pass

class BranchResponse(BranchBase):
    id: int
    class Config:
        orm_mode = True

# --- Agent Schemas ---
class AgentBase(BaseModel):
    agent_external_id: str = Field(..., description="e.g., SANEF ID")
    business_name: str
    contact_person_name: Optional[str] = None
    phone_number: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    status: str = "ACTIVE" # PENDING_APPROVAL, ACTIVE, SUSPENDED
    # supervising_branch_id: Optional[int] = None

class AgentCreateRequest(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: int
    # user_id: Optional[int] = None # If agent has a system user account
    class Config:
        orm_mode = True

# --- User Schemas (System Users) ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    # branch_id: Optional[int] = None

class UserCreateRequest(UserBase):
    password: str = Field(..., min_length=8) # Plain password for creation, will be hashed

class UserUpdateRequest(BaseModel): # For updating user details
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    # branch_id: Optional[int] = None
    # role_ids: Optional[List[int]] = None # List of role IDs to assign/update

class UserResponse(UserBase):
    id: int
    # staff_id: Optional[str] = None
    # last_login_at: Optional[datetime] = None
    # roles: List[RoleResponse] = [] # Include roles associated with the user

    class Config:
        orm_mode = True

class UserPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

# --- Role & Permission Schemas (RBAC) ---
class PermissionBase(BaseModel):
    name: str = Field(..., description="e.g., CREATE_CUSTOMER, APPROVE_LOAN_TIER1")
    description: Optional[str] = None

class PermissionCreateRequest(PermissionBase):
    pass

class PermissionResponse(PermissionBase):
    id: int
    class Config:
        orm_mode = True

class RoleBase(BaseModel):
    name: str = Field(..., description="e.g., TELLER, BRANCH_MANAGER, ADMIN")
    description: Optional[str] = None

class RoleCreateRequest(RoleBase):
    permission_ids: List[int] = [] # List of permission IDs to assign to this role

class RoleResponse(RoleBase):
    id: int
    permissions: List[PermissionResponse] = []
    class Config:
        orm_mode = True

class UserRoleAssignmentRequest(BaseModel):
    user_id: int
    role_ids: List[int] # List of role IDs to assign to the user

# --- ProductConfig Schemas ---
class ProductConfigBase(BaseModel):
    product_code: str = Field(..., min_length=3, max_length=20, pattern=r"^[A-Z0-9_]+$")
    product_name: str
    product_type: ProductTypeEnum
    config_parameters_json: Dict[str, Any] = Field(..., description="JSON object for product-specific parameters")
    is_active: bool = True
    version: int = Field(1, ge=1)

class ProductConfigCreateRequest(ProductConfigBase):
    pass

class ProductConfigUpdateRequest(BaseModel): # For updating an existing version or creating new version
    product_name: Optional[str] = None
    config_parameters_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    # To create a new version, client might indicate 'increment_version=True' or similar

class ProductConfigResponse(ProductConfigBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # created_by_user_id: Optional[int] = None

    class Config:
        orm_mode = True
        use_enum_values = True
        # Pydantic automatically handles JSON string to dict for config_parameters_json if model field is Text/JSONB

# --- AuditLog Schemas ---
class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    username_performing_action: Optional[str] = None
    action_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    # details_before_json: Optional[Dict[str, Any]] = None # Parsed from Text by Pydantic
    # details_after_json: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    ip_address: Optional[str] = None
    status: str

    class Config:
        orm_mode = True

# --- APIManagementConfig Schemas (for external API clients) ---
class APIClientConfigBase(BaseModel):
    api_client_id: str = Field(..., description="Unique ID for the API client/consumer")
    # client_name: str
    # allowed_scopes_json: Optional[List[str]] = Field([], description="List of permissions/scopes for this client")
    is_active: bool = True
    # requests_per_minute: Optional[int] = None
    # token_expiry_seconds: Optional[int] = 3600

class APIClientConfigCreateRequest(APIClientConfigBase):
    # client_secret_plain: Optional[str] = None # If generating/providing a secret, hash it in service layer

class APIClientConfigResponse(APIClientConfigBase):
    id: int
    # Indicates if secret is set, not the secret itself
    # has_client_secret: bool

    class Config:
        orm_mode = True

# --- System Settings / Global Configurations (Conceptual) ---
class SystemSettingSchema(BaseModel):
    setting_key: str = Field(..., description="e.g., MAX_LOGIN_ATTEMPTS, DEFAULT_CURRENCY, CBN_BANK_CODE")
    setting_value: str # Store all values as string, parse in application logic
    description: Optional[str] = None
    is_editable_by_admin: bool = True # Some settings might be system-locked

    class Config:
        orm_mode = True # If fetched from a DB model

# --- Paginated Responses ---
class PaginatedBranchResponse(BaseModel):
    items: List[BranchResponse]
    total: int
    page: int
    size: int

class PaginatedAgentResponse(BaseModel):
    items: List[AgentResponse]
    total: int
    page: int
    size: int

class PaginatedUserResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    size: int

class PaginatedRoleResponse(BaseModel):
    items: List[RoleResponse]
    total: int
    page: int
    size: int

class PaginatedProductConfigResponse(BaseModel):
    items: List[ProductConfigResponse]
    total: int
    page: int
    size: int

class PaginatedAuditLogResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    size: int
