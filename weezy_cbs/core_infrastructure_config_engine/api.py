# API Endpoints for Core Infrastructure & Config Engine (mostly Admin)
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_admin_user, get_current_active_user (for some ops)

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_admin_user_placeholder(): return {"id": "admin01", "username": "admin", "role": "admin"}
get_current_active_admin_user = get_current_active_admin_user_placeholder
def get_current_active_user_placeholder(): return {"id": "user01", "username": "testuser"} # Generic user
get_current_active_user = get_current_active_user_placeholder


router = APIRouter(
    prefix="/core-config",
    tags=["Core Infrastructure & Configuration"],
    responses={404: {"description": "Not found"}},
)

# --- Branch Management Endpoints (Admin) ---
@router.post("/branches", response_model=schemas.BranchResponse, status_code=status.HTTP_201_CREATED)
def create_new_branch(
    branch_in: schemas.BranchCreateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Create a new bank branch. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.create_branch(db, branch_in)
    except services.DuplicateEntryException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/branches", response_model=schemas.PaginatedBranchResponse)
def list_all_branches(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(True),
    db: Session = Depends(get_db) # Publicly viewable or admin only?
):
    """List all bank branches."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    branches = services.get_branches(db, skip, limit, active_only)
    total = db.query(func.count(models.Branch.id))
    if active_only: total = total.filter(models.Branch.is_active == True)
    total = total.scalar_one_or_none() or 0
    return schemas.PaginatedBranchResponse(items=branches, total=total, page=(skip//limit)+1, size=len(branches))

# --- Agent Management Endpoints (Admin/Agent Ops) ---
@router.post("/agents", response_model=schemas.AgentResponse, status_code=status.HTTP_201_CREATED)
def register_new_agent(
    agent_in: schemas.AgentCreateRequest,
    db: Session = Depends(get_db),
    current_admin_or_ops: dict = Depends(get_current_active_admin_user) # Or specific agent ops role
):
    """Register a new banking agent. (Admin/Agent Ops operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.create_agent(db, agent_in)
    except services.DuplicateEntryException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

# --- User Management Endpoints (Admin) ---
@router.post("/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_new_system_user(
    user_in: schemas.UserCreateRequest,
    role_ids: Optional[List[int]] = Query(None, description="List of Role IDs to assign to the new user"),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Create a new system user (staff, admin, etc.). (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.create_user(db, user_in, role_ids)
    except services.DuplicateEntryException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.NotFoundException as e: # If a role_id is not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_system_user_details(
    user_id: int,
    user_update: schemas.UserUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Update details or roles for an existing system user. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        updated_user = services.update_user(db, user_id, user_update)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found.")
        return updated_user
    except services.NotFoundException as e: # If user or a role_id not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/users/{user_id}/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password_for_user( # Admin changing password for a user
    user_id: int,
    new_password: str = Query(..., min_length=8), # Admin sets new password directly
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Change password for a user. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # services.admin_change_user_password(db, user_id, new_password)
    # Placeholder for a direct password set by admin
    user = services.get_user(db, user_id=user_id)
    if not user: raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = services.get_password_hash(new_password)
    db.commit()
    # services._log_audit(db, current_admin.get("username"), "ADMIN_PASSWORD_CHANGE", entity_id=user_id)
    return

@router.post("/users/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
def user_changes_own_password( # User changing their own password
    password_change: schemas.UserPasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user) # Authenticated user
):
    """Allows authenticated user to change their own password."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    user_id = current_user.get("id") # Assuming user object from auth has 'id'
    if not user_id: raise HTTPException(status_code=403, detail="User context not found.")

    if not services.change_user_password(db, user_id, password_change):
        raise HTTPException(status_code=400, detail="Incorrect current password or other error.")
    return

# --- RBAC: Role Management Endpoints (Admin) ---
@router.post("/roles", response_model=schemas.RoleResponse, status_code=status.HTTP_201_CREATED)
def create_new_role_with_permissions(
    role_in: schemas.RoleCreateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Create a new role and assign permissions to it. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.create_role(db, role_in)
    except services.DuplicateEntryException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.NotFoundException as e: # If a permission_id is not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/roles/{role_id}", response_model=schemas.RoleResponse)
def get_role_and_its_permissions(role_id: int, db: Session = Depends(get_db)):
    """Get details of a role, including its assigned permissions."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    role = services.get_role_with_permissions(db, role_id) # This service needs to fetch permissions
    if not role:
        raise HTTPException(status_code=404, detail="Role not found.")
    # Manually construct permissions if not eager loaded by service for this example
    # perms_models = db.query(models.Permission).join(models.RolePermission).filter(models.RolePermission.role_id == role.id).all()
    # role.permissions = [schemas.PermissionResponse.from_orm(p) for p in perms_models]
    return role

# --- Product Configuration Endpoints (Admin/Product Manager) ---
@router.post("/product-configs", response_model=schemas.ProductConfigResponse, status_code=status.HTTP_201_CREATED)
def create_new_product_configuration(
    product_in: schemas.ProductConfigCreateRequest,
    db: Session = Depends(get_db),
    current_admin_or_pm: dict = Depends(get_current_active_admin_user) # Or product manager role
):
    """Create a new product configuration (e.g., for a savings account type, loan product). (Admin/Product Mgr operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        user_id_str = str(current_admin_or_pm.get("id"))
        return services.create_product_config(db, product_in, user_id_str)
    except services.DuplicateEntryException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/product-configs/{product_code}", response_model=schemas.ProductConfigResponse)
def get_active_product_configuration(
    product_code: str,
    version: Optional[int] = Query(None, description="Specific version, if None, latest active is returned"),
    db: Session = Depends(get_db)
):
    """Get the active configuration for a given product code (optionally a specific version)."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    config = services.get_product_config(db, product_code, version, active_only=True if version is None else False)
    if not config:
        raise HTTPException(status_code=404, detail=f"Product configuration for {product_code} (version {version or 'latest active'}) not found.")
    return config

# --- Audit Log Endpoints (Admin/Compliance) ---
@router.get("/audit-logs", response_model=schemas.PaginatedAuditLogResponse)
def view_audit_logs(
    action_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_admin_or_co: dict = Depends(get_current_active_admin_user) # Or compliance officer
):
    """View system audit logs. (Admin/Compliance operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    logs = services.get_audit_logs(db, skip, limit, action_type, entity_id)

    # Simplified total count for pagination
    query = db.query(func.count(models.AuditLog.id))
    if action_type: query = query.filter(models.AuditLog.action_type == action_type)
    if entity_id: query = query.filter(models.AuditLog.entity_id == entity_id)
    total = query.scalar_one_or_none() or 0

    return schemas.PaginatedAuditLogResponse(items=logs, total=total, page=(skip//limit)+1, size=len(logs))

# TODO: Endpoints for Permissions CRUD, assigning permissions to roles, assigning roles to users,
#       managing API client configurations.

# Import func for count queries if not already at top
from sqlalchemy import func
