# Database models for Core Infrastructure & Config Engine
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLAlchemyEnum, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

# from weezy_cbs.database import Base # Assuming a shared declarative base
Base = declarative_base() # Local Base for now

import enum

class ProductTypeEnum(enum.Enum):
    SAVINGS_ACCOUNT = "SAVINGS_ACCOUNT"
    CURRENT_ACCOUNT = "CURRENT_ACCOUNT"
    FIXED_DEPOSIT = "FIXED_DEPOSIT"
    LOAN_PRODUCT = "LOAN_PRODUCT"
    CARD_PRODUCT = "CARD_PRODUCT"
    WALLET_PRODUCT = "WALLET_PRODUCT"
    # Add more CBS product types

class Branch(Base):
    __tablename__ = "branches"
    id = Column(Integer, primary_key=True, index=True)
    branch_code = Column(String, unique=True, nullable=False, index=True) # Official branch code (e.g., CBN sort code part)
    name = Column(String, nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    # country_code = Column(String(2), default="NG")
    is_active = Column(Boolean, default=True)
    # opening_date = Column(Date, nullable=True)
    # branch_manager_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # users = relationship("User", back_populates="branch") # Users working at this branch
    # agents = relationship("Agent", back_populates="supervising_branch") # Agents supervised by this branch

class Agent(Base): # For agent banking (SANEF agents etc.)
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, index=True)
    agent_external_id = Column(String, unique=True, nullable=False, index=True) # e.g., SANEF ID
    # user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True) # If agent logs in as a specific user type
    business_name = Column(String, nullable=False)
    contact_person_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=False)
    email = Column(String, nullable=True)
    address = Column(Text)
    # gps_coordinates = Column(String, nullable=True) # "latitude,longitude"

    # supervising_branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    status = Column(String, default="ACTIVE") # PENDING_APPROVAL, ACTIVE, SUSPENDED, TERMINATED

    # tier = Column(String, nullable=True) # Agent tier if applicable
    # max_transaction_limit = Column(Numeric(precision=18, scale=2), nullable=True)
    # commission_profile_id = Column(Integer, ForeignKey("commission_profiles.id"), nullable=True)

    # supervising_branch = relationship("Branch", back_populates="agents")

class User(Base): # CBS System Users (staff, admins, tellers, agents with system access)
    __tablename__ = "users" # Consider a more generic name if it conflicts with app users for digital channels
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False) # Store hashed passwords ONLY

    full_name = Column(String, nullable=True)
    # staff_id = Column(String, unique=True, nullable=True) # If internal staff

    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False) # For admin privileges
    # last_login_at = Column(DateTime(timezone=True), nullable=True)

    # branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True) # Branch the user belongs to
    # branch = relationship("Branch", back_populates="users")
    # roles = relationship("Role", secondary="user_roles", back_populates="users") # Many-to-many with Role

class Role(Base): # Role-Based Access Control (RBAC)
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # e.g., "TELLER", "BRANCH_MANAGER", "ADMIN", "COMPLIANCE_OFFICER"
    description = Column(Text, nullable=True)
    # permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")

class Permission(Base): # Specific permissions
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # e.g., "CREATE_CUSTOMER", "APPROVE_LOAN_TIER1", "VIEW_REPORTS"
    description = Column(Text, nullable=True)

# --- Association Tables for Many-to-Many relationships ---
class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)

class ProductConfig(Base): # Generic Product Configuration (No-code/Low-code approach)
    __tablename__ = "product_configs"
    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String, unique=True, nullable=False, index=True) # e.g., "SAV001", "CUR002", "LN_PERS003"
    product_name = Column(String, nullable=False)
    product_type = Column(SQLAlchemyEnum(ProductTypeEnum), nullable=False)

    # Configuration parameters stored as JSON. Schema for this JSON would vary by product_type.
    # e.g., For SAVINGS_ACCOUNT: {"min_balance": 1000, "interest_rate_pa": 2.5, "monthly_ledger_fee_code": "ACC_MAINT_SAV"}
    # e.g., For LOAN_PRODUCT: links to loan_products table or stores simplified loan params here.
    config_parameters_json = Column(Text, nullable=False)

    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1) # For versioning product configurations

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # created_by_user_id = Column(Integer, ForeignKey("users.id"))

    __table_args__ = (UniqueConstraint('product_code', 'version', name='uq_product_code_version'),)


class AuditLog(Base): # For critical system actions and changes
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True) # User performing the action
    username_performing_action = Column(String, nullable=True) # Denormalized username

    action_type = Column(String, nullable=False, index=True) # e.g., "CUSTOMER_CREATE", "LOAN_APPROVE", "USER_LOGIN", "CONFIG_UPDATE"
    entity_type = Column(String, nullable=True, index=True) # e.g., "Customer", "LoanApplication", "ProductConfig"
    entity_id = Column(String, nullable=True, index=True) # ID of the affected entity

    # Storing before/after state as JSON can be verbose but useful for auditing.
    # Be mindful of PII and data size.
    details_before_json = Column(Text, nullable=True) # State of entity before change
    details_after_json = Column(Text, nullable=True)  # State of entity after change
    summary = Column(Text, nullable=True) # Human-readable summary of the action

    ip_address = Column(String, nullable=True)
    # user_agent = Column(String, nullable=True)
    status = Column(String, default="SUCCESS") # SUCCESS, FAILED (if action attempted but failed)

class APIManagementConfig(Base): # Configuration for bank's own exposed APIs
    __tablename__ = "api_management_configs"
    id = Column(Integer, primary_key=True, index=True)
    api_client_id = Column(String, unique=True, nullable=False, index=True) # For third-party integrators
    # client_name = Column(String, nullable=False)
    # client_secret_hashed = Column(String, nullable=False) # Hashed secret for the client

    # Rate Limiting (example)
    # requests_per_minute = Column(Integer, nullable=True)
    # requests_per_day = Column(Integer, nullable=True)

    # Access Scopes/Permissions (JSON array of permission strings or link to specific API permissions)
    # allowed_scopes_json = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    # token_expiry_seconds = Column(Integer, default=3600) # For OAuth tokens issued to this client

# This module is central for operational setup and security.
# ProductConfig allows dynamic creation/modification of banking products.
# RBAC (User, Role, Permission) is crucial for security.
# AuditLog tracks important changes across the system.
# Branch/Agent management defines the physical/operational structure.
# APIManagementConfig would be for external entities consuming the bank's APIs (BaaS model).
