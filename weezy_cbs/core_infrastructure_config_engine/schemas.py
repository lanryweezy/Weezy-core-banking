# Pydantic schemas for Core Infrastructure & Config Engine
from pydantic import BaseModel, EmailStr, validator, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import json # Import json at the top level

from .models import ProductTypeEnum # Import the enum from models

# --- Branch Schemas ---
class BranchBase(BaseModel):
    branch_code: str = Field(..., max_length=10, description="Official branch code (e.g., CBN sort code part)")
    name: str = Field(..., max_length=100)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, max_length=50)
    country_code: str = Field("NG", max_length=2)
    is_active: bool = True
    opening_date: Optional[date] = None
    branch_manager_user_id: Optional[int] = None

class BranchCreate(BranchBase): # Renamed from BranchCreateRequest
    pass

class BranchUpdate(BaseModel): # Use BaseModel for partial updates
    branch_code: Optional[str] = Field(None, max_length=10)
    name: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, max_length=50)
    country_code: Optional[str] = Field(None, max_length=2)
    is_active: Optional[bool] = None
    opening_date: Optional[date] = None
    branch_manager_user_id: Optional[int] = None

class BranchResponse(BranchBase):
    id: int
    class Config:
        orm_mode = True

# --- Agent Schemas ---
class AgentBase(BaseModel):
    agent_external_id: str = Field(..., max_length=50, description="e.g., SANEF ID")
    business_name: str = Field(..., max_length=150)
    contact_person_name: Optional[str] = Field(None, max_length=100)
    phone_number: str = Field(..., max_length=15)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    gps_coordinates: Optional[str] = Field(None, max_length=50, description="latitude,longitude")
    supervising_branch_id: Optional[int] = None
    status: str = Field("ACTIVE", max_length=20, description="PENDING_APPROVAL, ACTIVE, SUSPENDED, TERMINATED")
    tier: Optional[str] = Field(None, max_length=20)
    max_transaction_limit: Optional[float] = None # Consider Decimal for monetary values
    commission_profile_id: Optional[str] = Field(None, max_length=50)
    user_id: Optional[int] = None # If agent logs in as a specific user type

class AgentCreate(AgentBase): # Renamed from AgentCreateRequest
    pass

class AgentUpdate(BaseModel): # Use BaseModel for partial updates
    agent_external_id: Optional[str] = Field(None, max_length=50)
    business_name: Optional[str] = Field(None, max_length=150)
    contact_person_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    gps_coordinates: Optional[str] = Field(None, max_length=50)
    supervising_branch_id: Optional[int] = None
    status: Optional[str] = Field(None, max_length=20)
    tier: Optional[str] = Field(None, max_length=20)
    max_transaction_limit: Optional[float] = None
    commission_profile_id: Optional[str] = Field(None, max_length=50)
    user_id: Optional[int] = None

class AgentResponse(AgentBase):
    id: int
    class Config:
        orm_mode = True

# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=150)
    staff_id: Optional[str] = Field(None, max_length=20, description="Internal staff ID")
    is_active: bool = True
    is_superuser: bool = False
    branch_id: Optional[int] = None

class UserCreate(UserBase): # Renamed from UserCreateRequest
    password: str = Field(..., min_length=8, description="Plain password, to be hashed by service")
    role_ids: Optional[List[int]] = Field([], description="List of role IDs to assign to the user")


class UserUpdate(BaseModel): # Renamed from UserUpdateRequest, use BaseModel for partial updates
    username: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=150)
    staff_id: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    branch_id: Optional[int] = None
    password: Optional[str] = Field(None, min_length=8, description="For password updates")
    role_ids: Optional[List[int]] = Field(None, description="List of role IDs to assign/update for the user")


class UserResponse(UserBase):
    id: int
    last_login_at: Optional[datetime] = None
    class Config:
        orm_mode = True

class UserLoginSchema(BaseModel):
    username: str
    password: str

class TokenSchema(BaseModel): # Schema for JWT token response
    access_token: str
    token_type: str
    user: UserResponse # Include user details in token response

# --- Role Schemas ---
class RoleBase(BaseModel):
    name: str = Field(..., max_length=50, description="e.g., TELLER, BRANCH_MANAGER, ADMIN")
    description: Optional[str] = None

class RoleCreate(RoleBase): # Renamed from RoleCreateRequest
    permission_ids: Optional[List[int]] = Field([], description="List of permission IDs to assign to this role")

class RoleUpdate(BaseModel): # Use BaseModel for partial updates
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = Field(None, description="To update assigned permissions")

class RoleResponse(RoleBase):
    id: int
    # permissions field will be populated by a service method if needed, using RoleWithPermissionsResponse
    class Config:
        orm_mode = True

# --- Permission Schemas ---
class PermissionBase(BaseModel):
    name: str = Field(..., max_length=100, description="e.g., CREATE_CUSTOMER, APPROVE_LOAN_TIER1")
    description: Optional[str] = None

class PermissionCreate(PermissionBase): # Renamed from PermissionCreateRequest
    pass

class PermissionUpdate(BaseModel): # Use BaseModel for partial updates
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None

class PermissionResponse(PermissionBase):
    id: int
    class Config:
        orm_mode = True


# --- ProductConfig Schemas ---
class ProductConfigBase(BaseModel):
    product_code: str = Field(..., max_length=20, description="e.g., SAV001, CUR002, LN_PERS003")
    product_name: str = Field(..., max_length=100)
    product_type: ProductTypeEnum
    config_parameters_json: Dict[str, Any] # Parsed as dict
    is_active: bool = True
    version: int = Field(1, ge=1)

    @validator('config_parameters_json', pre=True)
    def parse_json_string(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for config_parameters_json")
        return value

class ProductConfigCreate(ProductConfigBase): # Renamed from ProductConfigCreateRequest
    created_by_user_id: Optional[str] = Field(None, max_length=50)

class ProductConfigUpdate(BaseModel): # Renamed from ProductConfigUpdateRequest
    product_name: Optional[str] = Field(None, max_length=100)
    config_parameters_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    # version: Optional[int] = Field(None, ge=1) # Versioning might be handled by service (e.g., auto-increment)
    updated_by_user_id: Optional[str] = Field(None, max_length=50)

    @validator('config_parameters_json', pre=True)
    def parse_update_json_string(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for config_parameters_json")
        return value

class ProductConfigResponse(ProductConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[str] = None
    updated_by_user_id: Optional[str] = None

    class Config:
        orm_mode = True
        use_enum_values = True


# --- AuditLog Schemas ---
class AuditLogBase(BaseModel):
    username_performing_action: Optional[str] = Field(None, max_length=50)
    action_type: str = Field(..., max_length=50)
    entity_type: Optional[str] = Field(None, max_length=50)
    entity_id: Optional[str] = Field(None, max_length=50)
    details_before_json: Optional[Dict[str, Any]] = None
    details_after_json: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    ip_address: Optional[str] = Field(None, max_length=45)
    status: str = Field("SUCCESS", max_length=20)
    user_id: Optional[int] = None # For linking back to the User model

    @validator('details_before_json', 'details_after_json', pre=True)
    def parse_audit_json_string(cls, value):
        if value is None:
            return None
        if isinstance(value, str): # If it's a string, try to parse it
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for details_json fields")
        return value # If it's already a dict

class AuditLogCreate(AuditLogBase):
    pass # timestamp is server_default

class AuditLogResponse(AuditLogBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True

# --- APIManagementConfig Schemas ---
class APIManagementConfigBase(BaseModel): # Renamed from APIClientConfigBase
    api_client_id: str = Field(..., max_length=50)
    client_name: str = Field(..., max_length=100)
    requests_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    allowed_scopes_json: Optional[List[str]] = Field(None, description="JSON array of permission strings") # Store as list
    is_active: bool = True
    token_expiry_seconds: int = Field(3600, gt=0)

    @validator('allowed_scopes_json', pre=True)
    def parse_scopes_json_string(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for allowed_scopes_json")
        return value # Assumes it's already a list if not a string

class APIManagementConfigCreate(APIManagementConfigBase): # Renamed from APIClientConfigCreateRequest
    client_secret: str = Field(..., description="Client secret, will be hashed by the service.")

class APIManagementConfigUpdate(BaseModel): # Use BaseModel for partial updates
    client_name: Optional[str] = Field(None, max_length=100)
    requests_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    allowed_scopes_json: Optional[List[str]] = None
    is_active: Optional[bool] = None
    token_expiry_seconds: Optional[int] = Field(None, gt=0)
    # client_secret: Optional[str] = Field(None, description="Provide new secret to update. If None, secret remains unchanged.") # Optional: for updating secret

    @validator('allowed_scopes_json', pre=True)
    def parse_update_scopes_json_string(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for allowed_scopes_json")
        return value

class APIManagementConfigResponse(APIManagementConfigBase): # Renamed from APIClientConfigResponse
    id: int
    class Config:
        orm_mode = True

# --- SystemSetting Schemas ---
class SystemSettingBase(BaseModel): # Renamed from SystemSettingSchema
    setting_key: str = Field(..., max_length=100)
    setting_value: str # Stored as text, could be JSON, number, boolean string
    description: Optional[str] = None
    is_editable_by_admin: bool = True

class SystemSettingCreate(SystemSettingBase):
    last_updated_by: Optional[str] = Field(None, max_length=50, description="User ID or 'SYSTEM'")

class SystemSettingUpdate(BaseModel): # Use BaseModel for partial updates
    setting_value: Optional[str] = None
    description: Optional[str] = None
    is_editable_by_admin: Optional[bool] = None
    last_updated_by: Optional[str] = Field(None, max_length=50)

class SystemSettingResponse(SystemSettingBase):
    updated_at: datetime
    last_updated_by: Optional[str] = None

    class Config:
        orm_mode = True

# --- Helper Schemas for relationships in responses ---
class PermissionForRoleResponse(PermissionResponse):
    pass

class RoleWithPermissionsResponse(RoleResponse):
    permissions: List[PermissionForRoleResponse] = []

class RoleForUserResponse(RoleResponse):
    pass

class UserWithRolesResponse(UserResponse):
    roles: List[RoleForUserResponse] = []

class UserForAuditLogResponse(BaseModel):
    id: int
    username: str
    class Config:
        orm_mode = True

class AuditLogWithUserResponse(AuditLogResponse):
    user: Optional[UserForAuditLogResponse] = None

class UserForBranchManagerResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    class Config:
        orm_mode = True

class BranchWithManagerResponse(BranchResponse):
    branch_manager: Optional[UserForBranchManagerResponse] = None

class BranchForAgentResponse(BaseModel):
    id: int
    name: str
    branch_code: str
    class Config:
        orm_mode = True

class AgentWithBranchResponse(AgentResponse):
    supervising_branch: Optional[BranchForAgentResponse] = None

# --- RBAC Assignment Schemas ---
class AssignRolesToUserSchema(BaseModel): # Renamed from UserRoleAssignmentRequest
    user_id: int
    role_ids: List[int]

class AssignPermissionsToRoleSchema(BaseModel):
    role_id: int
    permission_ids: List[int]

# --- Paginated Responses (ensure all use *Response types) ---
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
    items: List[UserResponse] # Ensure this is UserResponse
    total: int
    page: int
    size: int

class PaginatedRoleResponse(BaseModel):
    items: List[RoleResponse] # Ensure this is RoleResponse
    total: int
    page: int
    size: int

class PaginatedProductConfigResponse(BaseModel):
    items: List[ProductConfigResponse] # Ensure this is ProductConfigResponse
    total: int
    page: int
    size: int

class PaginatedAuditLogResponse(BaseModel):
    items: List[AuditLogResponse] # Ensure this is AuditLogResponse
    total: int
    page: int
    size: int

class PaginatedPermissionResponse(BaseModel):
    items: List[PermissionResponse]
    total: int
    page: int
    size: int

class PaginatedAPIManagementConfigResponse(BaseModel):
    items: List[APIManagementConfigResponse]
    total: int
    page: int
    size: int

class PaginatedSystemSettingsResponse(BaseModel):
    items: List[SystemSettingResponse]
    total: int
    page: int
    size: int
