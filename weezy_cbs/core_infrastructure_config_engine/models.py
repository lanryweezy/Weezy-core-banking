# Database models for Core Infrastructure & Config Engine
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLAlchemyEnum, UniqueConstraint, Date, Numeric
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

from weezy_cbs.database import Base # Use the shared Base

import enum

class ProductTypeEnum(enum.Enum):
    SAVINGS_ACCOUNT = "SAVINGS_ACCOUNT"; CURRENT_ACCOUNT = "CURRENT_ACCOUNT"
    FIXED_DEPOSIT = "FIXED_DEPOSIT"; LOAN_PRODUCT = "LOAN_PRODUCT"
    CARD_PRODUCT = "CARD_PRODUCT"; WALLET_PRODUCT = "WALLET_PRODUCT"
    # Add more

class Branch(Base):
    __tablename__ = "branches"
    id = Column(Integer, primary_key=True, index=True)
    branch_code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(50), nullable=True)
    state = Column(String(50), nullable=True)
    country_code = Column(String(2), default="NG", nullable=False)
    is_active = Column(Boolean, default=True)
    opening_date = Column(Date, nullable=True)
    branch_manager_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    users = relationship("User", back_populates="branch")
    agents = relationship("Agent", back_populates="supervising_branch")

class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, index=True)
    agent_external_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True) # If agent is also a system User
    business_name = Column(String(150), nullable=False)
    contact_person_name = Column(String(100), nullable=True)
    phone_number = Column(String(15), nullable=False)
    email = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    gps_coordinates = Column(String(50), nullable=True)
    supervising_branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    status = Column(String(20), default="ACTIVE", index=True)
    tier = Column(String(20), nullable=True)
    max_transaction_limit = Column(Numeric(precision=18, scale=2), nullable=True)
    commission_profile_id = Column(String(50), nullable=True) # Link to a commission profile code/ID

    supervising_branch = relationship("Branch", back_populates="agents")
    user = relationship("User") # If linked to a system user

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    full_name = Column(String(150), nullable=True)
    staff_id = Column(String(20), unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    is_superuser = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)

    branch = relationship("Branch", back_populates="users")
    roles = relationship("Role", secondary="user_roles", back_populates="users")

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")
    users = relationship("User", secondary="user_roles", back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)

class ProductConfig(Base):
    __tablename__ = "product_configs"
    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String(20), nullable=False, index=True)
    product_name = Column(String(100), nullable=False)
    product_type = Column(SQLAlchemyEnum(ProductTypeEnum), nullable=False)
    config_parameters_json = Column(Text, nullable=False) # Store as JSON string
    is_active = Column(Boolean, default=True, index=True)
    version = Column(Integer, default=1, nullable=False)
    created_by_user_id = Column(String(50), nullable=True)
    updated_by_user_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint('product_code', 'version', name='uq_product_code_version'),)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username_performing_action = Column(String(50), nullable=True)
    action_type = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(String(50), nullable=True, index=True)
    details_before_json = Column(Text, nullable=True)
    details_after_json = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    status = Column(String(20), default="SUCCESS", index=True)

class APIManagementConfig(Base):
    __tablename__ = "api_management_configs"
    id = Column(Integer, primary_key=True, index=True)
    api_client_id = Column(String(50), unique=True, nullable=False, index=True)
    client_name = Column(String(100), nullable=False)
    client_secret_hashed = Column(String(128), nullable=True)
    requests_per_minute = Column(Integer, nullable=True)
    requests_per_day = Column(Integer, nullable=True)
    allowed_scopes_json = Column(Text, nullable=True) # JSON array of permission strings
    is_active = Column(Boolean, default=True)
    token_expiry_seconds = Column(Integer, default=3600)

class SystemSetting(Base):
    __tablename__ = "system_settings"
    setting_key = Column(String(100), primary_key=True, index=True)
    setting_value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_editable_by_admin = Column(Boolean, default=True)
    last_updated_by = Column(String(50), nullable=True) # User ID or "SYSTEM"
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
