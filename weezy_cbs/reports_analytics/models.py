# Database models for Reports & Analytics Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLAlchemyEnum, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

from weezy_cbs.database import Base # Use the shared Base

class ReportQueryLogicTypeEnum(enum.Enum):
    PREDEFINED_SQL = "PREDEFINED_SQL"
    DYNAMIC_FILTERS_ON_MODEL = "DYNAMIC_FILTERS_ON_MODEL"
    PYTHON_SCRIPT = "PYTHON_SCRIPT"

class ReportStatusEnum(enum.Enum):
    PENDING = "PENDING"; PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"; FAILED = "FAILED"; CANCELLED = "CANCELLED"

class ScheduledReportStatusEnum(enum.Enum):
    ACTIVE = "ACTIVE"; PAUSED = "PAUSED"; ERROR_STATE = "ERROR_STATE"; COMPLETED_ONCE = "COMPLETED_ONCE"


class ReportDefinition(Base):
    __tablename__ = "report_definitions"
    id = Column(Integer, primary_key=True, index=True)
    report_code = Column(String(50), unique=True, nullable=False, index=True)
    report_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)

    source_modules_json = Column(Text, nullable=True) # JSON array: ["accounts", "transactions", "customers"]

    query_logic_type = Column(SQLAlchemyEnum(ReportQueryLogicTypeEnum), nullable=False)
    query_details_json = Column(Text, nullable=False)

    parameters_schema_json = Column(Text, nullable=True) # JSON Schema for parameters

    default_output_formats_json = Column(Text, nullable=True) # JSON array: ["CSV", "PDF", "JSON"]
    allowed_roles_json = Column(Text, nullable=True) # JSON array of role names (from core_infra users.roles)

    is_system_report = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)

    # Ensure User model (core_infra) has: report_definitions_created = relationship("ReportDefinition", foreign_keys="[ReportDefinition.created_by_user_id]", back_populates="created_by_user")
    created_by_user_id = Column(Integer, ForeignKey("users.id", name="fk_reportdef_createdby"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # created_by_user = relationship("User", foreign_keys=[created_by_user_id]) # If User model is importable
    scheduled_reports = relationship("ScheduledReport", back_populates="report_definition", cascade="all, delete-orphan")
    generated_logs = relationship("GeneratedReportLog", back_populates="report_definition", cascade="all, delete-orphan") # If a def is deleted, logs might be orphaned or deleted.


class ScheduledReport(Base):
    __tablename__ = "scheduled_reports"
    id = Column(Integer, primary_key=True, index=True)
    report_definition_id = Column(Integer, ForeignKey("report_definitions.id", name="fk_schedrep_repdef", ondelete="CASCADE"), nullable=False)

    schedule_name = Column(String(150), nullable=True)
    cron_expression = Column(String(100), nullable=False)

    parameters_values_json = Column(Text, nullable=True)
    output_format = Column(String(10), default="CSV", nullable=False)
    recipients_json = Column(Text, nullable=True) # JSON array of email addresses or user IDs

    status = Column(SQLAlchemyEnum(ScheduledReportStatusEnum), default=ScheduledReportStatusEnum.ACTIVE, nullable=False, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_run_status = Column(SQLAlchemyEnum(ReportStatusEnum), nullable=True)
    last_error_message = Column(Text, nullable=True)

    # Ensure User model (core_infra) has: scheduled_reports_created = relationship("ScheduledReport", foreign_keys="[ScheduledReport.created_by_user_id]", back_populates="created_by_user")
    created_by_user_id = Column(Integer, ForeignKey("users.id", name="fk_schedrep_createdby"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    report_definition = relationship("ReportDefinition", back_populates="scheduled_reports")
    # created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    # generated_logs = relationship("GeneratedReportLog", back_populates="scheduled_report") # If linking logs back to schedule


class GeneratedReportLog(Base):
    __tablename__ = "generated_report_logs"
    id = Column(Integer, primary_key=True, index=True)
    report_definition_id = Column(Integer, ForeignKey("report_definitions.id", name="fk_genlog_repdef", ondelete="SET NULL"), nullable=True) # Keep log even if def is deleted
    scheduled_report_id = Column(Integer, ForeignKey("scheduled_reports.id", name="fk_genlog_schedrep", ondelete="SET NULL"), nullable=True)

    report_name_generated = Column(String(200), nullable=False)
    # Ensure User model (core_infra) has: reports_generated = relationship("GeneratedReportLog", foreign_keys="[GeneratedReportLog.generated_by_user_id]", back_populates="generated_by_user")
    generated_by_user_id = Column(Integer, ForeignKey("users.id", name="fk_genlog_generatedby"), nullable=False)
    generation_timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    parameters_used_json = Column(Text, nullable=True)
    output_format = Column(String(10), nullable=False)

    status = Column(SQLAlchemyEnum(ReportStatusEnum), default=ReportStatusEnum.PENDING, nullable=False, index=True)
    file_name = Column(String(255), nullable=True)
    file_path_or_link = Column(Text, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time_seconds = Column(Integer, nullable=True)

    report_definition = relationship("ReportDefinition", back_populates="generated_logs")
    scheduled_report = relationship("ScheduledReport") # Add back_populates="generated_logs" to ScheduledReport if bi-directional
    # generated_by_user = relationship("User", foreign_keys=[generated_by_user_id])


class DashboardLayout(Base):
    __tablename__ = "dashboard_layouts"
    id = Column(Integer, primary_key=True, index=True)
    # Ensure User model (core_infra) has: dashboard_layouts = relationship("DashboardLayout", foreign_keys="[DashboardLayout.user_id]", back_populates="user", cascade="all, delete-orphan")
    user_id = Column(Integer, ForeignKey("users.id", name="fk_dash_user", ondelete="CASCADE"), nullable=False)
    dashboard_name = Column(String(100), nullable=False)

    layout_config_json = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # user = relationship("User", foreign_keys=[user_id]) # If User model is importable
    __table_args__ = (UniqueConstraint('user_id', 'dashboard_name', name='uq_user_dashboard_name'),)

# Notes on Foreign Keys and Relationships:
# - `users.id` refers to the User model in `core_infrastructure_config_engine`.
# - `ondelete="CASCADE"` on `ScheduledReport.report_definition_id` means if a ReportDefinition is deleted,
#   all its schedules are also deleted.
# - `ondelete="SET NULL"` on `GeneratedReportLog.report_definition_id` and `scheduled_report_id` means
#   if the definition or schedule is deleted, the log entry remains but the foreign key is set to NULL.
#   This preserves the log history.
# - Bi-directional relationships (using `back_populates`) require corresponding relationship definitions
#   in the other models (e.g., in User, ReportDefinition, ScheduledReport).
# - Assumes a shared SQLAlchemy `Base` or careful handling of metadata for cross-module FKs.
#   Table names like "users", "report_definitions" must be globally known to SQLAlchemy.
#   If using DB schemas (e.g., "core_infra.users"), FKs must reflect that.
#   For this project, we're assuming simple table names for now.
