import json
from typing import List, Optional, Type, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from fastapi import HTTPException, status
from passlib.context import CryptContext # For password hashing
import secrets # For generating API client secrets
from datetime import datetime, timedelta

from . import models, schemas
# from weezy_cbs.database import SessionLocal # Assuming global session management

# --- Password Hashing & Token Generation ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# In a real app, JWT_SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES would come from config
JWT_SECRET_KEY = "your-secret-key-needs-to-be-secure-and-from-config" # Placeholder: Use environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    from jose import jwt # Import here to avoid top-level dependency if not always used
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "sub": str(data.get("sub"))}) # Ensure sub is string for JWT standard
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Generic CRUD Service Base (Optional, for reducing boilerplate) ---
class BaseCRUDService:
    def __init__(self, model: Type[models.Base]):
        self.model = model

    def get_by_id(self, db: Session, item_id: int) -> Optional[models.Base]:
        return db.query(self.model).filter(self.model.id == item_id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[models.Base]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def remove(self, db: Session, item_id: int, performing_user: Optional[str] = "SYSTEM") -> Optional[models.Base]:
        db_item = db.query(self.model).get(item_id)
        if db_item:
            item_repr = f"{self.model.__name__} ID {item_id}" # Generic representation
            try:
                item_repr = f"{self.model.__name__} '{db_item.name}' (ID: {item_id})"
            except AttributeError:
                pass # Not all models have 'name'

            db.delete(db_item)
            db.commit()
            AuditLogService.create_audit_log_entry(
                db,
                username_performing_action=performing_user,
                action_type=f"{self.model.__name__.upper()}_DELETE",
                entity_type=self.model.__name__,
                entity_id=str(item_id),
                summary=f"{item_repr} deleted."
            )
        return db_item

# --- AuditLog Services (defined early as it's used by others) ---
class AuditLogService(BaseCRUDService):
    def __init__(self):
        super().__init__(models.AuditLog)

    @staticmethod
    def create_audit_log_entry(
        db: Session,
        action_type: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        summary: Optional[str] = None,
        details_before_json: Optional[str] = None,
        details_after_json: Optional[str] = None,
        status: str = "SUCCESS",
        ip_address: Optional[str] = None, # Should be captured from request context
        user_id_performing_action: Optional[int] = None,
        username_performing_action: Optional[str] = "SYSTEM" # Default to SYSTEM if not provided
    ) -> models.AuditLog:

        db_log = models.AuditLog(
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            details_before_json=details_before_json,
            details_after_json=details_after_json,
            status=status,
            ip_address=ip_address,
            user_id=user_id_performing_action,
            username_performing_action=username_performing_action
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log

    def get_audit_logs(self, db: Session, skip: int = 0, limit: int = 100,
                       action_type: Optional[str] = None,
                       entity_type: Optional[str] = None,
                       entity_id: Optional[str] = None,
                       username: Optional[str] = None,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None
                       ) -> (List[models.AuditLog], int):
        query = db.query(models.AuditLog)
        if action_type:
            query = query.filter(models.AuditLog.action_type.ilike(f"%{action_type}%"))
        if entity_type:
            query = query.filter(models.AuditLog.entity_type.ilike(f"%{entity_type}%"))
        if entity_id:
            query = query.filter(models.AuditLog.entity_id == entity_id)
        if username:
            query = query.filter(models.AuditLog.username_performing_action.ilike(f"%{username}%"))
        if start_date:
            query = query.filter(models.AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(models.AuditLog.timestamp <= end_date)

        total = query.count()
        logs = query.order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
        return logs, total

# --- Branch Services ---
class BranchService(BaseCRUDService):
    def __init__(self):
        super().__init__(models.Branch)

    def create_branch(self, db: Session, branch_in: schemas.BranchCreate, performing_user: str) -> models.Branch:
        if db.query(models.Branch).filter(models.Branch.branch_code == branch_in.branch_code).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Branch with code '{branch_in.branch_code}' already exists.")
        db_branch = models.Branch(**branch_in.dict())
        db.add(db_branch)
        db.commit()
        db.refresh(db_branch)
        AuditLogService.create_audit_log_entry(
            db, username_performing_action=performing_user, action_type="BRANCH_CREATE",
            entity_type="Branch", entity_id=str(db_branch.id), summary=f"Branch '{db_branch.name}' created."
        )
        return db_branch

    def update_branch(self, db: Session, branch_id: int, branch_in: schemas.BranchUpdate, performing_user: str) -> Optional[models.Branch]:
        db_branch = self.get_by_id(db, branch_id)
        if not db_branch:
            return None

        if branch_in.branch_code and branch_in.branch_code != db_branch.branch_code:
            if db.query(models.Branch).filter(models.Branch.branch_code == branch_in.branch_code, models.Branch.id != branch_id).first():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Branch with code '{branch_in.branch_code}' already exists.")

        update_data = branch_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_branch, field, value)

        db.add(db_branch)
        db.commit()
        db.refresh(db_branch)
        AuditLogService.create_audit_log_entry(
            db, username_performing_action=performing_user, action_type="BRANCH_UPDATE",
            entity_type="Branch", entity_id=str(db_branch.id), summary=f"Branch '{db_branch.name}' updated."
        )
        return db_branch

    def get_branch_by_code(self, db: Session, branch_code: str) -> Optional[models.Branch]:
        return db.query(models.Branch).filter(models.Branch.branch_code == branch_code).first()

# --- Agent Services ---
class AgentService(BaseCRUDService):
    def __init__(self):
        super().__init__(models.Agent)

    def create_agent(self, db: Session, agent_in: schemas.AgentCreate, performing_user: str) -> models.Agent:
        if db.query(models.Agent).filter(models.Agent.agent_external_id == agent_in.agent_external_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Agent with external ID '{agent_in.agent_external_id}' already exists.")
        if agent_in.supervising_branch_id:
            if not BranchService().get_by_id(db, agent_in.supervising_branch_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Supervising branch with ID {agent_in.supervising_branch_id} not found.")
        if agent_in.user_id:
             if not UserService().get_by_id(db, agent_in.user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with ID {agent_in.user_id} for agent linking not found.")


        db_agent = models.Agent(**agent_in.dict())
        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="AGENT_CREATE", entity_type="Agent", entity_id=str(db_agent.id), summary=f"Agent '{db_agent.business_name}' created.")
        return db_agent

    def update_agent(self, db: Session, agent_id: int, agent_in: schemas.AgentUpdate, performing_user: str) -> Optional[models.Agent]:
        db_agent = self.get_by_id(db, agent_id)
        if not db_agent:
            return None

        update_data = agent_in.dict(exclude_unset=True)
        if "supervising_branch_id" in update_data and update_data["supervising_branch_id"] is not None:
            if not BranchService().get_by_id(db, update_data["supervising_branch_id"]):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Supervising branch with ID {update_data['supervising_branch_id']} not found.")
        if "user_id" in update_data and update_data["user_id"] is not None:
            if not UserService().get_by_id(db, update_data["user_id"]):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with ID {update_data['user_id']} for agent linking not found.")
        if "agent_external_id" in update_data and update_data["agent_external_id"] != db_agent.agent_external_id:
            if db.query(models.Agent).filter(models.Agent.agent_external_id == update_data["agent_external_id"], models.Agent.id != agent_id).first():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Agent with external ID '{update_data['agent_external_id']}' already exists.")


        for field, value in update_data.items():
            setattr(db_agent, field, value)

        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="AGENT_UPDATE", entity_type="Agent", entity_id=str(db_agent.id), summary=f"Agent '{db_agent.business_name}' updated.")
        return db_agent

    def get_agent_by_external_id(self, db: Session, external_id: str) -> Optional[models.Agent]:
        return db.query(models.Agent).filter(models.Agent.agent_external_id == external_id).first()

# --- User Services (System Users) ---
class UserService(BaseCRUDService):
    def __init__(self):
        super().__init__(models.User)

    def get_user_by_username(self, db: Session, username: str) -> Optional[models.User]:
        return db.query(models.User).filter(func.lower(models.User.username) == func.lower(username)).first()

    def get_user_by_email(self, db: Session, email: str) -> Optional[models.User]:
        return db.query(models.User).filter(func.lower(models.User.email) == func.lower(email)).first()

    def create_user(self, db: Session, user_in: schemas.UserCreate, performing_user: str) -> models.User:
        if self.get_user_by_username(db, user_in.username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        if self.get_user_by_email(db, user_in.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        if user_in.staff_id and db.query(models.User).filter(models.User.staff_id == user_in.staff_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Staff ID already registered")


        hashed_password = get_password_hash(user_in.password)
        db_user_data = user_in.dict(exclude={"password", "role_ids"})
        db_user = models.User(**db_user_data, hashed_password=hashed_password)

        db.add(db_user)
        # Must commit here to get db_user.id for role assignment and audit logging
        try:
            db.commit()
            db.refresh(db_user)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating user: {e}")


        if user_in.role_ids:
            self.assign_roles_to_user(db, user_id=db_user.id, role_ids=user_in.role_ids, performing_user=performing_user, is_new_user=True)
            db.refresh(db_user)

        AuditLogService.create_audit_log_entry(
            db, username_performing_action=performing_user, action_type="USER_CREATE",
            entity_type="User", entity_id=str(db_user.id), summary=f"User '{db_user.username}' created."
        )
        return db_user

    def update_user(self, db: Session, user_id: int, user_in: schemas.UserUpdate, performing_user: str) -> Optional[models.User]:
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return None

        update_data = user_in.dict(exclude_unset=True, exclude={"password", "role_ids"})

        if "username" in update_data and update_data["username"].lower() != db_user.username.lower():
            if self.get_user_by_username(db, update_data["username"]):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        if "email" in update_data and update_data["email"].lower() != db_user.email.lower():
            if self.get_user_by_email(db, update_data["email"]):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        if "staff_id" in update_data and update_data["staff_id"] != db_user.staff_id:
            if db.query(models.User).filter(models.User.staff_id == update_data["staff_id"], models.User.id != user_id).first():
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Staff ID already registered by another user.")

        for field, value in update_data.items():
            setattr(db_user, field, value)

        if user_in.password:
            db_user.hashed_password = get_password_hash(user_in.password)

        if user_in.role_ids is not None:
             self.assign_roles_to_user(db, user_id=db_user.id, role_ids=user_in.role_ids, performing_user=performing_user, clear_existing=True)

        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        AuditLogService.create_audit_log_entry(
            db, username_performing_action=performing_user, action_type="USER_UPDATE",
            entity_type="User", entity_id=str(db_user.id), summary=f"User '{db_user.username}' updated."
        )
        return db_user

    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[models.User]:
        user = self.get_user_by_username(db, username)
        if not user or not user.is_active: # Also check if user is active
            AuditLogService.create_audit_log_entry(db, username_performing_action=username, action_type="USER_LOGIN_FAIL", entity_type="User", entity_id=username, summary=f"Login failed for user '{username}': User not found or inactive.")
            return None
        if not verify_password(password, user.hashed_password):
            AuditLogService.create_audit_log_entry(db, username_performing_action=username, action_type="USER_LOGIN_FAIL", entity_type="User", entity_id=username, summary=f"Login failed for user '{username}': Invalid password.")
            return None

        user.last_login_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        AuditLogService.create_audit_log_entry(db, username_performing_action=username, action_type="USER_LOGIN_SUCCESS", entity_type="User", entity_id=str(user.id), summary=f"User '{username}' logged in successfully.")
        return user

    def assign_roles_to_user(self, db: Session, user_id: int, role_ids: List[int], performing_user: str, clear_existing: bool = True, is_new_user: bool = False) -> Optional[models.User]:
        user = db.query(models.User).options(joinedload(models.User.roles)).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        roles = db.query(models.Role).filter(models.Role.id.in_(role_ids)).all()
        valid_role_ids = {role.id for role in roles}

        invalid_role_ids = set(role_ids) - valid_role_ids
        if invalid_role_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role IDs: {invalid_role_ids}")

        if clear_existing:
            user.roles = roles
        else:
            existing_role_ids = {role.id for role in user.roles}
            for role in roles:
                if role.id not in existing_role_ids:
                    user.roles.append(role)

        # No separate commit if called during user creation before initial commit
        if not is_new_user:
            db.commit()
            db.refresh(user)
            AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="USER_ROLES_ASSIGN", entity_type="User", entity_id=str(user.id), summary=f"Roles updated for user '{user.username}'. Assigned roles: {[r.name for r in roles]}")
        return user

    def get_user_permissions(self, db: Session, user_id: int) -> List[str]:
        user = db.query(models.User).options(
            joinedload(models.User.roles).joinedload(models.Role.permissions)
        ).filter(models.User.id == user_id).first()

        if not user or not user.is_active: # Ensure user is active to have permissions
            return []

        permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                permissions.add(perm.name)
        return list(permissions)

# --- Role & Permission Services ---
class RoleService(BaseCRUDService):
    def __init__(self):
        super().__init__(models.Role)

    def create_role(self, db: Session, role_in: schemas.RoleCreate, performing_user: str) -> models.Role:
        if db.query(models.Role).filter(func.lower(models.Role.name) == func.lower(role_in.name)).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role with name '{role_in.name}' already exists.")

        db_role_data = role_in.dict(exclude={"permission_ids"})
        db_role = models.Role(**db_role_data)

        if role_in.permission_ids:
            permissions = db.query(models.Permission).filter(models.Permission.id.in_(role_in.permission_ids)).all()
            valid_permission_ids = {p.id for p in permissions}
            invalid_permission_ids = set(role_in.permission_ids) - valid_permission_ids
            if invalid_permission_ids:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid permission IDs: {invalid_permission_ids}")
            db_role.permissions = permissions

        db.add(db_role)
        db.commit()
        db.refresh(db_role)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="ROLE_CREATE", entity_type="Role", entity_id=str(db_role.id), summary=f"Role '{db_role.name}' created.")
        return db_role

    def update_role(self, db: Session, role_id: int, role_in: schemas.RoleUpdate, performing_user: str) -> Optional[models.Role]:
        db_role = db.query(models.Role).options(joinedload(models.Role.permissions)).filter(models.Role.id == role_id).first()
        if not db_role:
            return None

        update_data = role_in.dict(exclude_unset=True, exclude={"permission_ids"})
        if "name" in update_data and update_data["name"].lower() != db_role.name.lower():
            if db.query(models.Role).filter(func.lower(models.Role.name) == func.lower(update_data["name"]), models.Role.id != role_id).first():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role with name '{update_data['name']}' already exists.")

        for field, value in update_data.items():
            setattr(db_role, field, value)

        if role_in.permission_ids is not None:
            permissions = db.query(models.Permission).filter(models.Permission.id.in_(role_in.permission_ids)).all()
            valid_permission_ids = {p.id for p in permissions}
            invalid_permission_ids = set(role_in.permission_ids) - valid_permission_ids
            if invalid_permission_ids:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid permission IDs: {invalid_permission_ids}")
            db_role.permissions = permissions

        db.add(db_role)
        db.commit()
        db.refresh(db_role)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="ROLE_UPDATE", entity_type="Role", entity_id=str(db_role.id), summary=f"Role '{db_role.name}' updated.")
        return db_role

    def get_role_with_permissions(self, db: Session, role_id: int) -> Optional[models.Role]:
        return db.query(models.Role).options(joinedload(models.Role.permissions)).filter(models.Role.id == role_id).first()

class PermissionService(BaseCRUDService):
    def __init__(self):
        super().__init__(models.Permission)

    def create_permission(self, db: Session, permission_in: schemas.PermissionCreate, performing_user: str) -> models.Permission:
        if db.query(models.Permission).filter(func.lower(models.Permission.name) == func.lower(permission_in.name)).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Permission with name '{permission_in.name}' already exists.")
        db_permission = models.Permission(**permission_in.dict())
        db.add(db_permission)
        db.commit()
        db.refresh(db_permission)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="PERMISSION_CREATE", entity_type="Permission", entity_id=str(db_permission.id), summary=f"Permission '{db_permission.name}' created.")
        return db_permission

    def update_permission(self, db: Session, permission_id: int, permission_in: schemas.PermissionUpdate, performing_user: str) -> Optional[models.Permission]:
        db_permission = self.get_by_id(db, permission_id)
        if not db_permission:
            return None

        update_data = permission_in.dict(exclude_unset=True)
        if "name" in update_data and update_data["name"].lower() != db_permission.name.lower():
            if db.query(models.Permission).filter(func.lower(models.Permission.name) == func.lower(update_data["name"]), models.Permission.id != permission_id).first():
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Permission with name '{update_data['name']}' already exists.")

        for field, value in update_data.items():
            setattr(db_permission, field, value)

        db.add(db_permission)
        db.commit()
        db.refresh(db_permission)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="PERMISSION_UPDATE", entity_type="Permission", entity_id=str(db_permission.id), summary=f"Permission '{db_permission.name}' updated.")
        return db_permission

# --- ProductConfig Services ---
class ProductConfigService(BaseCRUDService):
    def __init__(self):
        super().__init__(models.ProductConfig)

    def create_product_config(self, db: Session, product_in: schemas.ProductConfigCreate, performing_user: str) -> models.ProductConfig:
        existing = db.query(models.ProductConfig).filter(
            models.ProductConfig.product_code == product_in.product_code,
            models.ProductConfig.version == product_in.version
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product config with code '{product_in.product_code}' and version {product_in.version} already exists.")

        db_product = models.ProductConfig(
            **product_in.dict(exclude={"config_parameters_json", "created_by_user_id"}), # created_by_user_id is from schema
            config_parameters_json=json.dumps(product_in.config_parameters_json),
            created_by_user_id=performing_user # Use the username
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="PRODUCT_CONFIG_CREATE", entity_type="ProductConfig", entity_id=str(db_product.id), summary=f"Product config '{db_product.product_name}' (Code: {db_product.product_code}, V{db_product.version}) created.")
        return db_product

    def update_product_config(self, db: Session, product_id: int, product_in: schemas.ProductConfigUpdate, performing_user: str) -> Optional[models.ProductConfig]:
        db_product = self.get_by_id(db, product_id)
        if not db_product:
            return None

        update_data = product_in.dict(exclude_unset=True, exclude={"updated_by_user_id"})

        if "config_parameters_json" in update_data and update_data["config_parameters_json"] is not None:
            # Logic for versioning: if core parameters change, a new version should ideally be created.
            # This example updates in place for simplicity.
            # A robust system might compare new params with old, and if different, create a new version.
            db_product.config_parameters_json = json.dumps(update_data.pop("config_parameters_json"))
            # db_product.version += 1 # This would be for a new version strategy

        for field, value in update_data.items():
            setattr(db_product, field, value)

        db_product.updated_by_user_id = performing_user
        db_product.updated_at = datetime.utcnow()

        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="PRODUCT_CONFIG_UPDATE", entity_type="ProductConfig", entity_id=str(db_product.id), summary=f"Product config '{db_product.product_name}' (Code: {db_product.product_code}, V{db_product.version}) updated.")
        return db_product

    def get_product_config_by_code(self, db: Session, product_code: str, version: Optional[int] = None, only_active: bool = True) -> Optional[models.ProductConfig]:
        query = db.query(models.ProductConfig).filter(models.ProductConfig.product_code == product_code)
        if only_active:
            query = query.filter(models.ProductConfig.is_active == True)
        if version:
            query = query.filter(models.ProductConfig.version == version)
        else:
            query = query.order_by(models.ProductConfig.version.desc())
        return query.first()

    def get_all_versions_of_product(self, db: Session, product_code: str) -> List[models.ProductConfig]:
        return db.query(models.ProductConfig).filter(models.ProductConfig.product_code == product_code).order_by(models.ProductConfig.version.desc()).all()

# --- APIManagementConfig Services ---
class APIManagementConfigService(BaseCRUDService):
    def __init__(self):
        super().__init__(models.APIManagementConfig)

    def create_api_client(self, db: Session, client_in: schemas.APIManagementConfigCreate, performing_user: str) -> models.APIManagementConfig:
        if db.query(models.APIManagementConfig).filter(models.APIManagementConfig.api_client_id == client_in.api_client_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"API Client ID '{client_in.api_client_id}' already exists.")

        hashed_secret = get_password_hash(client_in.client_secret)

        db_client_data = client_in.dict(exclude={"client_secret", "allowed_scopes_json"})
        db_client = models.APIManagementConfig(
            **db_client_data,
            client_secret_hashed=hashed_secret,
            allowed_scopes_json=json.dumps(client_in.allowed_scopes_json) if client_in.allowed_scopes_json else None
        )
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="API_CLIENT_CREATE", entity_type="APIManagementConfig", entity_id=str(db_client.id), summary=f"API Client '{db_client.client_name}' (ID: {db_client.api_client_id}) created.")
        return db_client

    def update_api_client(self, db: Session, client_pk_id: int, client_in: schemas.APIManagementConfigUpdate, performing_user: str) -> Optional[models.APIManagementConfig]:
        db_client = self.get_by_id(db, client_pk_id) # pk_id is the primary key (id), not api_client_id
        if not db_client:
            return None

        update_data = client_in.dict(exclude_unset=True)

        # To update client_secret, a separate method/flow is safer (e.g., regenerate secret)
        # if "client_secret" in update_data and update_data["client_secret"]:
        #     db_client.client_secret_hashed = get_password_hash(update_data.pop("client_secret"))

        if "allowed_scopes_json" in update_data and update_data["allowed_scopes_json"] is not None:
            db_client.allowed_scopes_json = json.dumps(update_data.pop("allowed_scopes_json"))

        for field, value in update_data.items():
            setattr(db_client, field, value)

        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="API_CLIENT_UPDATE", entity_type="APIManagementConfig", entity_id=str(db_client.id), summary=f"API Client '{db_client.client_name}' (ID: {db_client.api_client_id}) updated.")
        return db_client

    def get_client_by_api_id(self, db: Session, api_client_id_str: str) -> Optional[models.APIManagementConfig]: # param renamed for clarity
        return db.query(models.APIManagementConfig).filter(models.APIManagementConfig.api_client_id == api_client_id_str).first()

    def verify_client_secret(self, db: Session, api_client_id_str: str, plain_secret: str) -> bool:
        client = self.get_client_by_api_id(db, api_client_id_str)
        if not client or not client.is_active or not client.client_secret_hashed:
            return False
        return verify_password(plain_secret, client.client_secret_hashed)

# --- SystemSetting Services ---
class SystemSettingService(BaseCRUDService): # BaseCRUDService expects 'id' PK. SystemSetting uses 'setting_key'.
    def __init__(self):
        # super().__init__(models.SystemSetting) # Cannot use BaseCRUDService directly due to PK difference
        self.model = models.SystemSetting


    def get_setting_by_key(self, db: Session, key: str) -> Optional[models.SystemSetting]:
        return db.query(self.model).filter(self.model.setting_key == key).first()

    def create_setting(self, db: Session, setting_in: schemas.SystemSettingCreate, performing_user: str) -> models.SystemSetting:
        if self.get_setting_by_key(db, setting_in.setting_key):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"System setting with key '{setting_in.setting_key}' already exists.")

        db_setting_data = setting_in.dict() # No exclude_unset on create
        db_setting_data["last_updated_by"] = performing_user
        db_setting = self.model(**db_setting_data)

        db.add(db_setting)
        db.commit()
        db.refresh(db_setting)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="SYSTEM_SETTING_CREATE", entity_type="SystemSetting", entity_id=db_setting.setting_key, summary=f"System setting '{db_setting.setting_key}' created/set to '{db_setting.setting_value}'.")
        return db_setting

    def update_setting(self, db: Session, setting_key: str, setting_in: schemas.SystemSettingUpdate, performing_user: str) -> Optional[models.SystemSetting]:
        db_setting = self.get_setting_by_key(db, setting_key)
        if not db_setting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"System setting with key '{setting_key}' not found.")

        if not db_setting.is_editable_by_admin and performing_user != "SYSTEM_INTERNAL":
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"System setting '{setting_key}' is not editable by admin.")

        update_data = setting_in.dict(exclude_unset=True)
        update_data["last_updated_by"] = performing_user

        old_value = db_setting.setting_value

        for field, value in update_data.items():
            setattr(db_setting, field, value)

        db_setting.updated_at = datetime.utcnow()

        db.add(db_setting)
        db.commit()
        db.refresh(db_setting)
        AuditLogService.create_audit_log_entry(db, username_performing_action=performing_user, action_type="SYSTEM_SETTING_UPDATE", entity_type="SystemSetting", entity_id=db_setting.setting_key, summary=f"System setting '{db_setting.setting_key}' updated from '{old_value}' to '{db_setting.setting_value}'.")
        return db_setting

    def get_all_settings(self, db: Session, skip: int = 0, limit: int = 100) -> (List[models.SystemSetting], int):
        query = db.query(self.model)
        total = query.count()
        settings = query.order_by(self.model.setting_key).offset(skip).limit(limit).all()
        return settings, total

    def remove_setting(self, db: Session, setting_key: str, performing_user: Optional[str] = "SYSTEM") -> Optional[models.SystemSetting]:
        db_item = self.get_setting_by_key(db, setting_key)
        if db_item:
            db.delete(db_item)
            db.commit()
            AuditLogService.create_audit_log_entry(
                db,
                username_performing_action=performing_user,
                action_type=f"{self.model.__name__.upper()}_DELETE",
                entity_type=self.model.__name__,
                entity_id=setting_key,
                summary=f"SystemSetting '{setting_key}' deleted."
            )
        return db_item


# Instantiate services for easier import elsewhere, or manage via dependency injection
branch_service = BranchService()
agent_service = AgentService()
user_service = UserService()
role_service = RoleService()
permission_service = PermissionService()
product_config_service = ProductConfigService()
# audit_log_service is used via static method: AuditLogService.create_audit_log_entry
api_management_config_service = APIManagementConfigService()
system_setting_service = SystemSettingService()
