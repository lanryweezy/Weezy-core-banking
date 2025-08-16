from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm # For login form
from sqlalchemy.orm import Session

from weezy_cbs.database import get_db # Assuming get_db is in root database.py
from . import schemas, services, models
from .services import (
    branch_service, agent_service, user_service, role_service, permission_service,
    product_config_service, api_management_config_service, system_setting_service,
    AuditLogService, # For direct use if needed, though mostly static
    create_access_token
)

# --- Authentication & Authorization Dependencies ---

# Placeholder for a more robust current_user dependency
# In a real app, this would decode JWT and fetch user, check active status etc.
# For now, we'll simulate a superuser or pass username for auditing.
async def get_current_active_superuser(
    # This would typically take: token: str = Depends(oauth2_scheme)
    # For now, let's assume a header or a mock for simplicity in this phase
    # current_user: models.User = Depends(get_current_user_from_token) # A proper function
    db: Session = Depends(get_db) # Example, not fully implemented for mock
) -> models.User:
    # Mocking a superuser for now. Replace with actual JWT token processing.
    user = user_service.get_user_by_username(db, "admin") # Assuming an 'admin' user exists
    if not user or not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required for this operation."
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user

# A simpler dependency that just gets a username, perhaps from a header or a default
# This is a placeholder for how performing_user could be obtained.
async def get_performing_user_username(current_user: models.User = Depends(get_current_active_superuser)) -> str:
    return current_user.username


router = APIRouter(
    prefix="/core-config",
    tags=["Core Infrastructure & Configuration"],
    # dependencies=[Depends(get_current_active_superuser)] # Apply to all routes in this router if needed
)

# --- Authentication Endpoint ---
auth_router = APIRouter(tags=["Authentication"])

@auth_router.post("/login/token", response_model=schemas.TokenSchema)
async def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = user_service.authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username, "user_id": user.id}) # "sub" is standard for subject (username)
    return {"access_token": access_token, "token_type": "bearer", "user": schemas.UserResponse.from_orm(user)}

# --- Branch Endpoints ---
@router.post("/branches/", response_model=schemas.BranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch(
    branch_in: schemas.BranchCreate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    return branch_service.create_branch(db=db, branch_in=branch_in, performing_user=performing_user)

@router.get("/branches/{branch_id}", response_model=schemas.BranchResponse)
def read_branch(branch_id: int, db: Session = Depends(get_db)):
    db_branch = branch_service.get_by_id(db, branch_id)
    if db_branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return db_branch

@router.get("/branches/", response_model=schemas.PaginatedBranchResponse)
def read_branches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    branches = branch_service.get_multi(db, skip=skip, limit=limit)
    total = db.query(models.Branch).count() # Simple count for now
    return {"items": branches, "total": total, "page": (skip // limit) + 1, "size": limit}


@router.put("/branches/{branch_id}", response_model=schemas.BranchResponse)
def update_branch(
    branch_id: int,
    branch_in: schemas.BranchUpdate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    updated_branch = branch_service.update_branch(db=db, branch_id=branch_id, branch_in=branch_in, performing_user=performing_user)
    if updated_branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return updated_branch

@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    deleted_branch = branch_service.remove(db=db, item_id=branch_id, performing_user=performing_user)
    if deleted_branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return None

# --- Agent Endpoints ---
@router.post("/agents/", response_model=schemas.AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_in: schemas.AgentCreate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    return agent_service.create_agent(db=db, agent_in=agent_in, performing_user=performing_user)

@router.get("/agents/{agent_id}", response_model=schemas.AgentResponse) # Consider AgentWithBranchResponse
def read_agent(agent_id: int, db: Session = Depends(get_db)):
    db_agent = agent_service.get_by_id(db, agent_id) # Add options for joinedload if using AgentWithBranchResponse
    if db_agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return db_agent

@router.get("/agents/", response_model=schemas.PaginatedAgentResponse)
def read_agents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    agents = agent_service.get_multi(db, skip=skip, limit=limit)
    total = db.query(models.Agent).count()
    return {"items": agents, "total": total, "page": (skip // limit) + 1, "size": limit}

@router.put("/agents/{agent_id}", response_model=schemas.AgentResponse)
def update_agent(
    agent_id: int,
    agent_in: schemas.AgentUpdate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    updated_agent = agent_service.update_agent(db=db, agent_id=agent_id, agent_in=agent_in, performing_user=performing_user)
    if updated_agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return updated_agent

@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    deleted_agent = agent_service.remove(db=db, item_id=agent_id, performing_user=performing_user)
    if deleted_agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return None

# --- User Endpoints ---
@router.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED) # Consider UserWithRolesResponse
def create_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    return user_service.create_user(db=db, user_in=user_in, performing_user=performing_user)

@router.get("/users/me", response_model=schemas.UserWithRolesResponse) # Example of a "me" endpoint
async def read_users_me(current_user: models.User = Depends(get_current_active_superuser), db: Session = Depends(get_db)):
    # To make UserWithRolesResponse work, you need to ensure roles are loaded.
    # UserService.get_by_id might need options(joinedload(models.User.roles)) or a specific method.
    user_with_roles = db.query(models.User).options(joinedload(models.User.roles)).filter(models.User.id == current_user.id).first()
    if not user_with_roles:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current user not found in DB (should not happen).")
    return user_with_roles


@router.get("/users/{user_id}", response_model=schemas.UserWithRolesResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    # db_user = user_service.get_by_id(db, user_id) # This won't load roles by default
    db_user = db.query(models.User).options(joinedload(models.User.roles)).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

@router.get("/users/", response_model=schemas.PaginatedUserResponse) # Consider PaginatedUserWithRolesResponse
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # users = user_service.get_multi(db, skip=skip, limit=limit) # This won't load roles
    users = db.query(models.User).options(joinedload(models.User.roles)).offset(skip).limit(limit).all()
    total = db.query(models.User).count()
    return {"items": users, "total": total, "page": (skip // limit) + 1, "size": limit}

@router.put("/users/{user_id}", response_model=schemas.UserResponse) # Consider UserWithRolesResponse
def update_user(
    user_id: int,
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    updated_user = user_service.update_user(db=db, user_id=user_id, user_in=user_in, performing_user=performing_user)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    # Ensure not deleting self, or handle appropriately
    # current_user_obj = await get_current_active_superuser(db) # If needed to check against self
    # if current_user_obj.id == user_id:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete self.")
    deleted_user = user_service.remove(db=db, item_id=user_id, performing_user=performing_user)
    if deleted_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None

@router.post("/users/assign-roles", response_model=schemas.UserWithRolesResponse) # Changed from UserResponse
def assign_roles_to_user(
    assignment: schemas.AssignRolesToUserSchema,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    user = user_service.assign_roles_to_user(db, user_id=assignment.user_id, role_ids=assignment.role_ids, performing_user=performing_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found for role assignment")
    return user


# --- Role Endpoints ---
@router.post("/roles/", response_model=schemas.RoleWithPermissionsResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role_in: schemas.RoleCreate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    return role_service.create_role(db=db, role_in=role_in, performing_user=performing_user)

@router.get("/roles/{role_id}", response_model=schemas.RoleWithPermissionsResponse)
def read_role(role_id: int, db: Session = Depends(get_db)):
    db_role = role_service.get_role_with_permissions(db, role_id) # Use specific method to load permissions
    if db_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return db_role

@router.get("/roles/", response_model=schemas.PaginatedRoleResponse) # Consider PaginatedRoleWithPermissionsResponse
def read_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # roles = role_service.get_multi(db, skip=skip, limit=limit) # This won't load permissions
    roles = db.query(models.Role).options(joinedload(models.Role.permissions)).offset(skip).limit(limit).all()
    total = db.query(models.Role).count()
    return {"items": roles, "total": total, "page": (skip // limit) + 1, "size": limit}

@router.put("/roles/{role_id}", response_model=schemas.RoleWithPermissionsResponse)
def update_role(
    role_id: int,
    role_in: schemas.RoleUpdate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    updated_role = role_service.update_role(db=db, role_id=role_id, role_in=role_in, performing_user=performing_user)
    if updated_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return updated_role

@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    # Check if role is in use by any user?
    # users_with_role = db.query(models.User).join(models.User.roles).filter(models.Role.id == role_id).count()
    # if users_with_role > 0:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role is currently assigned to {users_with_role} user(s) and cannot be deleted.")
    deleted_role = role_service.remove(db=db, item_id=role_id, performing_user=performing_user)
    if deleted_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return None

# --- Permission Endpoints ---
@router.post("/permissions/", response_model=schemas.PermissionResponse, status_code=status.HTTP_201_CREATED)
def create_permission(
    permission_in: schemas.PermissionCreate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    return permission_service.create_permission(db=db, permission_in=permission_in, performing_user=performing_user)

@router.get("/permissions/{permission_id}", response_model=schemas.PermissionResponse)
def read_permission(permission_id: int, db: Session = Depends(get_db)):
    db_permission = permission_service.get_by_id(db, permission_id)
    if db_permission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return db_permission

@router.get("/permissions/", response_model=schemas.PaginatedPermissionResponse)
def read_permissions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    permissions = permission_service.get_multi(db, skip=skip, limit=limit)
    total = db.query(models.Permission).count()
    return {"items": permissions, "total": total, "page": (skip // limit) + 1, "size": limit}

@router.put("/permissions/{permission_id}", response_model=schemas.PermissionResponse)
def update_permission(
    permission_id: int,
    permission_in: schemas.PermissionUpdate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    updated_permission = permission_service.update_permission(db=db, permission_id=permission_id, permission_in=permission_in, performing_user=performing_user)
    if updated_permission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return updated_permission

@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    # Check if permission is in use by any role?
    # roles_with_permission = db.query(models.Role).join(models.Role.permissions).filter(models.Permission.id == permission_id).count()
    # if roles_with_permission > 0:
    #    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Permission is currently assigned to {roles_with_permission} role(s) and cannot be deleted.")
    deleted_permission = permission_service.remove(db=db, item_id=permission_id, performing_user=performing_user)
    if deleted_permission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return None

# --- ProductConfig Endpoints ---
@router.post("/product-configs/", response_model=schemas.ProductConfigResponse, status_code=status.HTTP_201_CREATED)
def create_product_config(
    product_in: schemas.ProductConfigCreate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    return product_config_service.create_product_config(db=db, product_in=product_in, performing_user=performing_user)

@router.get("/product-configs/{product_id}", response_model=schemas.ProductConfigResponse)
def read_product_config(product_id: int, db: Session = Depends(get_db)):
    db_product = product_config_service.get_by_id(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product Configuration not found")
    return db_product

@router.get("/product-configs/code/{product_code}", response_model=schemas.ProductConfigResponse, summary="Get product config by code (latest active version or specific version)")
def read_product_config_by_code(product_code: str, version: Optional[int] = None, db: Session = Depends(get_db)):
    db_product = product_config_service.get_product_config_by_code(db, product_code=product_code, version=version, only_active=True if version is None else False)
    if db_product is None:
        detail_msg = f"Product Configuration with code '{product_code}'"
        if version:
            detail_msg += f" and version {version}"
        detail_msg += " not found or not active."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_msg)
    return db_product


@router.get("/product-configs/", response_model=schemas.PaginatedProductConfigResponse)
def read_product_configs(
    product_code: Optional[str] = None,
    product_type: Optional[schemas.ProductTypeEnum] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(models.ProductConfig)
    if product_code:
        query = query.filter(models.ProductConfig.product_code.ilike(f"%{product_code}%"))
    if product_type:
        query = query.filter(models.ProductConfig.product_type == product_type)
    if is_active is not None:
        query = query.filter(models.ProductConfig.is_active == is_active)

    total = query.count()
    products = query.order_by(models.ProductConfig.product_code, models.ProductConfig.version.desc()).offset(skip).limit(limit).all()
    return {"items": products, "total": total, "page": (skip // limit) + 1, "size": limit}


@router.put("/product-configs/{product_id}", response_model=schemas.ProductConfigResponse)
def update_product_config(
    product_id: int,
    product_in: schemas.ProductConfigUpdate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    updated_product = product_config_service.update_product_config(db=db, product_id=product_id, product_in=product_in, performing_user=performing_user)
    if updated_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product Configuration not found")
    return updated_product

@router.delete("/product-configs/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_config(
    product_id: int,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    # Consider if product config is in use before deleting (e.g., linked to accounts)
    deleted_product = product_config_service.remove(db=db, item_id=product_id, performing_user=performing_user)
    if deleted_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product Configuration not found")
    return None

# --- APIManagementConfig Endpoints ---
@router.post("/api-clients/", response_model=schemas.APIManagementConfigResponse, status_code=status.HTTP_201_CREATED)
def create_api_client(
    client_in: schemas.APIManagementConfigCreate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    return api_management_config_service.create_api_client(db=db, client_in=client_in, performing_user=performing_user)

@router.get("/api-clients/{client_pk_id}", response_model=schemas.APIManagementConfigResponse)
def read_api_client(client_pk_id: int, db: Session = Depends(get_db)):
    db_client = api_management_config_service.get_by_id(db, client_pk_id)
    if db_client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Client Configuration not found")
    return db_client

@router.get("/api-clients/", response_model=schemas.PaginatedAPIManagementConfigResponse)
def read_api_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    clients = api_management_config_service.get_multi(db, skip=skip, limit=limit)
    total = db.query(models.APIManagementConfig).count()
    return {"items": clients, "total": total, "page": (skip // limit) + 1, "size": limit}

@router.put("/api-clients/{client_pk_id}", response_model=schemas.APIManagementConfigResponse)
def update_api_client(
    client_pk_id: int,
    client_in: schemas.APIManagementConfigUpdate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    updated_client = api_management_config_service.update_api_client(db=db, client_pk_id=client_pk_id, client_in=client_in, performing_user=performing_user)
    if updated_client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Client Configuration not found")
    return updated_client

@router.delete("/api-clients/{client_pk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_client(
    client_pk_id: int,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    deleted_client = api_management_config_service.remove(db=db, item_id=client_pk_id, performing_user=performing_user)
    if deleted_client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Client Configuration not found")
    return None

# --- SystemSetting Endpoints ---
@router.post("/system-settings/", response_model=schemas.SystemSettingResponse, status_code=status.HTTP_201_CREATED)
def create_system_setting(
    setting_in: schemas.SystemSettingCreate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    return system_setting_service.create_setting(db=db, setting_in=setting_in, performing_user=performing_user)

@router.get("/system-settings/{setting_key}", response_model=schemas.SystemSettingResponse)
def read_system_setting(setting_key: str, db: Session = Depends(get_db)):
    db_setting = system_setting_service.get_setting_by_key(db, setting_key)
    if db_setting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System Setting not found")
    return db_setting

@router.get("/system-settings/", response_model=schemas.PaginatedSystemSettingsResponse)
def read_system_settings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    settings, total = system_setting_service.get_all_settings(db, skip=skip, limit=limit)
    return {"items": settings, "total": total, "page": (skip // limit) + 1, "size": limit}

@router.put("/system-settings/{setting_key}", response_model=schemas.SystemSettingResponse)
def update_system_setting(
    setting_key: str,
    setting_in: schemas.SystemSettingUpdate,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    updated_setting = system_setting_service.update_setting(db=db, setting_key=setting_key, setting_in=setting_in, performing_user=performing_user)
    if updated_setting is None: # Should not happen due to check in service, but good practice
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System Setting not found for update")
    return updated_setting

@router.delete("/system-settings/{setting_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_system_setting(
    setting_key: str,
    db: Session = Depends(get_db),
    performing_user: str = Depends(get_performing_user_username)
):
    deleted_setting = system_setting_service.remove_setting(db=db, setting_key=setting_key, performing_user=performing_user)
    if deleted_setting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System Setting not found")
    return None

# --- AuditLog Endpoints ---
audit_log_router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
    dependencies=[Depends(get_current_active_superuser)] # Audit logs should be protected
)

@audit_log_router.get("/", response_model=schemas.PaginatedAuditLogResponse)
def read_audit_logs(
    action_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    username: Optional[str] = None,
    start_date: Optional[str] = None, # Expect ISO date string e.g. "2023-01-01T00:00:00Z"
    end_date: Optional[str] = None,   # Expect ISO date string
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    parsed_start_date = None
    if start_date:
        try:
            parsed_start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid start_date format. Use ISO format.")

    parsed_end_date = None
    if end_date:
        try:
            parsed_end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid end_date format. Use ISO format.")

    logs, total = AuditLogService().get_audit_logs( # Instantiate or use static if all methods are static
        db, skip=skip, limit=limit,
        action_type=action_type, entity_type=entity_type, entity_id=entity_id,
        username=username, start_date=parsed_start_date, end_date=parsed_end_date
    )
    return {"items": logs, "total": total, "page": (skip // limit) + 1, "size": limit}

# Include this auth_router in your main FastAPI app
# And the main `router` from this file as well.
# e.g., app.include_router(core_infra_api.auth_router)
#       app.include_router(core_infra_api.router)
#       app.include_router(core_infra_api.audit_log_router)
