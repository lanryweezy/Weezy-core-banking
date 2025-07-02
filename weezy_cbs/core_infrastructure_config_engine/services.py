# Service layer for Core Infrastructure & Config Engine
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
# from weezy_cbs.shared import exceptions, security_utils # For password hashing, audit logging utils
import json
from datetime import datetime

# Placeholder for shared exceptions (should be in a shared module)
class NotFoundException(Exception): pass
class DuplicateEntryException(Exception): pass
class InvalidOperationException(Exception): pass

# --- Password Hashing (Placeholder - use a strong library like passlib) ---
def get_password_hash(password: str) -> str:
    # return security_utils.hash_password(password)
    return f"hashed_{password}" # Placeholder

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # return security_utils.verify_password(plain_password, hashed_password)
    return f"hashed_{plain_password}" == hashed_password # Placeholder

# --- Branch Services ---
def create_branch(db: Session, branch_in: schemas.BranchCreateRequest) -> models.Branch:
    existing_branch = db.query(models.Branch).filter(models.Branch.branch_code == branch_in.branch_code).first()
    if existing_branch:
        raise DuplicateEntryException(f"Branch with code {branch_in.branch_code} already exists.")
    db_branch = models.Branch(**branch_in.dict())
    db.add(db_branch)
    db.commit()
    db.refresh(db_branch)
    # _log_audit(db, action="CREATE_BRANCH", entity_id=db_branch.id, details_after=branch_in.dict())
    return db_branch

def get_branch(db: Session, branch_id: int) -> Optional[models.Branch]:
    return db.query(models.Branch).filter(models.Branch.id == branch_id).first()

def get_branches(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[models.Branch]:
    query = db.query(models.Branch)
    if active_only:
        query = query.filter(models.Branch.is_active == True)
    return query.order_by(models.Branch.name).offset(skip).limit(limit).all()

# --- Agent Services ---
def create_agent(db: Session, agent_in: schemas.AgentCreateRequest) -> models.Agent:
    existing_agent = db.query(models.Agent).filter(models.Agent.agent_external_id == agent_in.agent_external_id).first()
    if existing_agent:
        raise DuplicateEntryException(f"Agent with external ID {agent_in.agent_external_id} already exists.")
    db_agent = models.Agent(**agent_in.dict())
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    # _log_audit(db, action="CREATE_AGENT", entity_id=db_agent.id, details_after=agent_in.dict())
    return db_agent

# --- User Services (System Users) ---
def create_user(db: Session, user_in: schemas.UserCreateRequest, role_ids: Optional[List[int]] = None) -> models.User:
    if db.query(models.User).filter(models.User.username == user_in.username).first():
        raise DuplicateEntryException(f"Username '{user_in.username}' already exists.")
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise DuplicateEntryException(f"Email '{user_in.email}' already registered.")

    hashed_password = get_password_hash(user_in.password)
    db_user = models.User(
        **user_in.dict(exclude={"password"}), # Exclude plain password from direct model mapping
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit() # Commit to get user ID for role assignment

    if role_ids:
        assign_roles_to_user(db, db_user.id, role_ids)

    db.refresh(db_user)
    # _log_audit(db, action="CREATE_USER", entity_id=db_user.id, details_after=user_in.dict(exclude={'password'}))
    return db_user

def get_user(db: Session, user_id: Optional[int]=None, username: Optional[str]=None) -> Optional[models.User]:
    if user_id:
        return db.query(models.User).filter(models.User.id == user_id).first()
    if username:
        return db.query(models.User).filter(models.User.username == username).first()
    return None

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdateRequest) -> Optional[models.User]:
    db_user = get_user(db, user_id=user_id)
    if not db_user:
        return None # Or raise NotFoundException

    # Store current state for audit log
    # details_before = { "email": db_user.email, "full_name": db_user.full_name, "is_active": db_user.is_active }

    update_data = user_update.dict(exclude_unset=True, exclude={"role_ids"}) # Exclude role_ids for now
    for key, value in update_data.items():
        setattr(db_user, key, value)

    if user_update.role_ids is not None: # Handle role update separately
        assign_roles_to_user(db, user_id, user_update.role_ids, replace_existing=True)

    db.commit()
    db.refresh(db_user)
    # _log_audit(db, action="UPDATE_USER", entity_id=db_user.id, details_before=details_before, details_after=user_update.dict(exclude_unset=True))
    return db_user

def change_user_password(db: Session, user_id: int, password_change: schemas.UserPasswordChangeRequest) -> bool:
    db_user = get_user(db, user_id=user_id)
    if not db_user:
        raise NotFoundException("User not found.")
    if not verify_password(password_change.current_password, db_user.hashed_password):
        # _log_audit(db, action="CHANGE_PASSWORD_FAILED_AUTH", entity_id=user_id)
        return False # Or raise AuthenticationFailed

    db_user.hashed_password = get_password_hash(password_change.new_password)
    db.commit()
    # _log_audit(db, action="CHANGE_PASSWORD_SUCCESS", entity_id=user_id)
    return True

# --- RBAC Services (Role, Permission, Assignments) ---
def create_role(db: Session, role_in: schemas.RoleCreateRequest) -> models.Role:
    if db.query(models.Role).filter(models.Role.name == role_in.name).first():
        raise DuplicateEntryException(f"Role '{role_in.name}' already exists.")

    db_role = models.Role(name=role_in.name, description=role_in.description)
    db.add(db_role)
    db.commit() # Commit to get role ID

    if role_in.permission_ids:
        assign_permissions_to_role(db, db_role.id, role_in.permission_ids)

    db.refresh(db_role)
    # _log_audit(db, action="CREATE_ROLE", entity_id=db_role.id, details_after=role_in.dict())
    return db_role

def get_role_with_permissions(db: Session, role_id: int) -> Optional[models.Role]:
    # This requires relationships to be set up on models.Role (e.g. role.permissions)
    # return db.query(models.Role).options(joinedload(models.Role.permissions)).filter(models.Role.id == role_id).first()
    return db.query(models.Role).filter(models.Role.id == role_id).first() # Simpler version for now

def assign_roles_to_user(db: Session, user_id: int, role_ids: List[int], replace_existing: bool = True):
    user = get_user(db, user_id=user_id)
    if not user: raise NotFoundException("User not found for role assignment.")

    if replace_existing: # Delete current roles for this user
        db.query(models.UserRole).filter(models.UserRole.user_id == user_id).delete()

    for role_id in set(role_ids): # Use set to avoid duplicate role_ids
        role = db.query(models.Role.id).filter(models.Role.id == role_id).first() # Check role exists
        if not role:
            # db.rollback() # Or collect errors and raise at the end
            raise NotFoundException(f"Role with ID {role_id} not found.")

        # Avoid adding duplicates if not replacing existing and role already assigned
        if not replace_existing and db.query(models.UserRole).filter_by(user_id=user_id, role_id=role_id).first():
            continue

        user_role = models.UserRole(user_id=user_id, role_id=role_id)
        db.add(user_role)
    db.commit()
    # _log_audit(db, action="ASSIGN_ROLES_TO_USER", entity_id=user_id, details_after={"role_ids": role_ids})

def assign_permissions_to_role(db: Session, role_id: int, permission_ids: List[int], replace_existing: bool = True):
    # Similar logic to assign_roles_to_user, but for RolePermission
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role: raise NotFoundException("Role not found for permission assignment.")

    if replace_existing:
        db.query(models.RolePermission).filter(models.RolePermission.role_id == role_id).delete()

    for perm_id in set(permission_ids):
        permission = db.query(models.Permission.id).filter(models.Permission.id == perm_id).first()
        if not permission:
            raise NotFoundException(f"Permission with ID {perm_id} not found.")
        if not replace_existing and db.query(models.RolePermission).filter_by(role_id=role_id, permission_id=perm_id).first():
            continue
        role_permission = models.RolePermission(role_id=role_id, permission_id=perm_id)
        db.add(role_permission)
    db.commit()
    # _log_audit(db, action="ASSIGN_PERMISSIONS_TO_ROLE", entity_id=role_id, details_after={"permission_ids": permission_ids})


# --- ProductConfig Services ---
def create_product_config(db: Session, product_in: schemas.ProductConfigCreateRequest, user_id: str) -> models.ProductConfig:
    # Check if product_code and version already exist
    existing_product = db.query(models.ProductConfig).filter(
        models.ProductConfig.product_code == product_in.product_code,
        models.ProductConfig.version == product_in.version
    ).first()
    if existing_product:
        raise DuplicateEntryException(f"Product config {product_in.product_code} version {product_in.version} already exists.")

    db_product = models.ProductConfig(
        **product_in.dict(exclude_unset=True),
        config_parameters_json=json.dumps(product_in.config_parameters_json), # Ensure it's stored as JSON string
        # created_by_user_id=user_id
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    # _log_audit(db, action="CREATE_PRODUCT_CONFIG", entity_id=db_product.id, details_after=product_in.dict())
    return db_product

def get_product_config(db: Session, product_code: str, version: Optional[int] = None, active_only: bool = True) -> Optional[models.ProductConfig]:
    query = db.query(models.ProductConfig).filter(models.ProductConfig.product_code == product_code)
    if active_only:
        query = query.filter(models.ProductConfig.is_active == True)
    if version:
        query = query.filter(models.ProductConfig.version == version)
    else: # Get latest active version if no version specified
        query = query.order_by(models.ProductConfig.version.desc())
    return query.first()

def update_product_config(db: Session, product_config_id: int, update_in: schemas.ProductConfigUpdateRequest, user_id: str) -> models.ProductConfig:
    # This typically means creating a new version rather than updating in-place,
    # unless it's a minor non-breaking change to the current version (e.g. toggling is_active).
    # For simplicity here, we'll allow direct update. A real system would have versioning strategy.
    db_config = db.query(models.ProductConfig).filter(models.ProductConfig.id == product_config_id).first()
    if not db_config:
        raise NotFoundException("Product configuration not found.")

    update_data = update_in.dict(exclude_unset=True)
    if "config_parameters_json" in update_data and update_data["config_parameters_json"] is not None:
        db_config.config_parameters_json = json.dumps(update_data["config_parameters_json"])
        del update_data["config_parameters_json"]

    for key, value in update_data.items():
        setattr(db_config, key, value)

    # db_config.updated_by_user_id = user_id
    db_config.updated_at = datetime.utcnow() # Manual update if onupdate not working for some fields
    db.commit()
    db.refresh(db_config)
    # _log_audit(db, action="UPDATE_PRODUCT_CONFIG", entity_id=db_config.id, details_after=update_in.dict())
    return db_config

# --- Audit Log Services ---
def _log_audit_entry(
    db: Session, action_type: str,
    username: Optional[str] = None,
    entity_type: Optional[str] = None, entity_id: Optional[Any] = None,
    details_before: Optional[Dict] = None, details_after: Optional[Dict] = None,
    summary: Optional[str] = None, ip_address: Optional[str] = None, status: str = "SUCCESS"
):
    log = models.AuditLog(
        username_performing_action=username,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details_before_json=json.dumps(details_before) if details_before else None,
        details_after_json=json.dumps(details_after) if details_after else None,
        summary=summary,
        ip_address=ip_address,
        status=status
    )
    db.add(log)
    db.commit() # Commit audit log independently or as part of main transaction
    # Be cautious with committing independently if main transaction might roll back.

def get_audit_logs(db: Session, skip: int = 0, limit: int = 100, action_type: Optional[str]=None, entity_id: Optional[str]=None) -> List[models.AuditLog]:
    query = db.query(models.AuditLog)
    if action_type:
        query = query.filter(models.AuditLog.action_type == action_type)
    if entity_id:
        query = query.filter(models.AuditLog.entity_id == entity_id)
    return query.order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

# --- API Client Config Services ---
# Similar CRUD operations for APIClientConfig would go here.

# --- System Settings Service (Conceptual) ---
# def get_system_setting(db: Session, key: str) -> Optional[str]:
#     setting = db.query(models.SystemSetting).filter(models.SystemSetting.setting_key == key).first()
#     return setting.setting_value if setting else None

# def set_system_setting(db: Session, key: str, value: str, description: Optional[str]=None, user_id: str):
#     setting = db.query(models.SystemSetting).filter(models.SystemSetting.setting_key == key).first()
#     if setting:
#         setting.setting_value = value
#         if description: setting.description = description
#     else:
#         setting = models.SystemSetting(setting_key=key, setting_value=value, description=description)
#         db.add(setting)
#     db.commit()
#     _log_audit(db, user_id, "SET_SYSTEM_SETTING", entity_id=key, details_after={"value": value})

# Note: This module's services are crucial for setting up and managing the operational parameters
# and security of the entire CBS. Audit logging should be integrated into all sensitive operations
# across all modules, potentially by calling `_log_audit_entry` from other services.
# For RBAC, a decorator or dependency in FastAPI endpoints is typically used to check permissions.
# Example: `Depends(require_permission("CREATE_CUSTOMER"))`
# This would internally check user's roles and role's permissions.
# The actual permission checking logic is not implemented here but would use these RBAC models.

# Helper to get list of permissions for a user (conceptual)
# def get_user_permissions(db: Session, user_id: int) -> List[str]:
#     user = db.query(models.User).options(joinedload(models.User.roles).joinedload(models.Role.permissions)).filter(models.User.id == user_id).first()
#     if not user: return []
#     user_permissions = set()
#     for role in user.roles:
#         for perm in role.permissions:
#             user_permissions.add(perm.name)
#     return list(user_permissions)
