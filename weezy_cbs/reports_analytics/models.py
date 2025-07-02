# Database models for Reports & Analytics Module
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum as SQLAlchemyEnum, Date
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

# from weezy_cbs.database import Base
Base = declarative_base() # Local Base for now

import enum

class ReportDefinition(Base): # For user-defined or frequently used reports
    __tablename__ = "report_definitions"
    id = Column(Integer, primary_key=True, index=True)
    report_code = Column(String, unique=True, nullable=False, index=True) # e.g., "DAILY_TRANSACTION_SUMMARY", "CUSTOMER_ACTIVITY_MONTHLY"
    report_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Source modules/tables this report queries from (informational or for dynamic query building)
    # source_data_description_json = Column(Text) # e.g. {"modules": ["TransactionManagement", "CustomerIdentity"], "tables": ["financial_transactions", "customers"]}

    # Parameters required by the report (JSON schema for parameters)
    # parameters_schema_json = Column(Text) # e.g. {"type": "object", "properties": {"start_date": {"type": "string", "format": "date"}, "end_date": {"type": "string", "format": "date"}, "branch_code": {"type": "string"}}}

    # Default output format
    # default_output_format = Column(String, default="CSV") # CSV, PDF, XLSX, JSON

    # Query template or reference to a stored procedure / query generation logic
    # query_template = Column(Text, nullable=True) # SQL template with placeholders for parameters
    # query_generator_function_name = Column(String, nullable=True) # Name of a function in services.py that builds the query

    # access_role_required = Column(String, nullable=True) # Role needed to run this report

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # created_by_user_id = Column(Integer, ForeignKey("users.id"))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SavedQuery(Base): # For users saving their custom ad-hoc queries
    __tablename__ = "saved_queries"
    id = Column(Integer, primary_key=True, index=True)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True) # User who saved the query
    query_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # The query itself (e.g. SQL, or parameters for a query builder)
    # This can be risky if storing raw SQL from users. Parameterized query builder is safer.
    query_language = Column(String, default="SQL_WEEZYQL") # "SQL_WEEZYQL" (our safe query DSL) or "RAW_SQL" (admin only)
    query_text_or_params_json = Column(Text, nullable=False)

    # Sharing settings
    # is_shared = Column(Boolean, default=False)
    # shared_with_roles_json = Column(Text, nullable=True) # JSON array of role names

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_run_at = Column(DateTime(timezone=True), nullable=True)

    # user = relationship("User")

class DashboardDefinition(Base): # Configuration for user dashboards
    __tablename__ = "dashboard_definitions"
    id = Column(Integer, primary_key=True, index=True)
    dashboard_code = Column(String, unique=True, nullable=False, index=True) # e.g., "BRANCH_PERFORMANCE_MAIN", "AGENT_KPI_TRACKER"
    dashboard_name = Column(String, nullable=False)
    # user_id_owner = Column(Integer, ForeignKey("users.id"), nullable=True) # If user-specific dashboard
    # role_id_default = Column(Integer, ForeignKey("roles.id"), nullable=True) # Default dashboard for a role

    # Layout and widgets configuration (JSON)
    # layout_config_json = Column(Text)
    # e.g. {"grid_type": "2x2", "widgets": [
    #    {"id": "widget1", "type": "KPI_TOTAL_CUSTOMERS", "report_def_code": "KPI_001", "params": {}, "position": "0,0"},
    #    {"id": "widget2", "type": "CHART_TXN_VOLUME", "report_def_code": "CHART_002", "params": {"period": "LAST_7_DAYS"}, "position": "0,1"}
    # ]}

    is_default = Column(Boolean, default=False) # Is this a default dashboard for new users/roles?
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class GeneratedReportInstance(Base): # Log of actual report instances generated from definitions or ad-hoc
    __tablename__ = "generated_report_instances" # Different from compliance reports
    id = Column(Integer, primary_key=True, index=True)
    # report_definition_id = Column(Integer, ForeignKey("report_definitions.id"), nullable=True) # If from a definition
    report_code_or_name = Column(String, nullable=False, index=True) # Code if from def, or ad-hoc name

    # parameters_used_json = Column(Text, nullable=True) # JSON of parameters used for this instance
    # generated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    output_format = Column(String) # CSV, PDF, JSON, XLSX
    # file_path_or_url = Column(String, nullable=True) # Link to the generated file
    # data_preview_json = Column(Text, nullable=True) # Small preview of data (e.g. first 10 rows) if not file based

    status = Column(String, default="COMPLETED") # PENDING, GENERATING, COMPLETED, FAILED
    # error_message = Column(Text, nullable=True) # If failed
    # execution_time_ms = Column(Integer, nullable=True)

    # report_definition = relationship("ReportDefinition")
    # user = relationship("User")

# This module typically doesn't store primary business data but rather metadata about reports,
# configurations for dashboards, and instances of generated analytical outputs.
# The main work is in the `services.py` to query other modules, aggregate data, and format it.

# Key Performance Indicator (KPI) Definitions (could be a type of ReportDefinition)
# class KPIDefinition(Base):
#     __tablename__ = "kpi_definitions"
#     id = Column(Integer, primary_key=True, index=True)
#     kpi_code = Column(String, unique=True, nullable=False, index=True) # e.g. "TOTAL_ACTIVE_CUSTOMERS", "NPL_RATIO"
#     kpi_name = Column(String, nullable=False)
#     # data_source_query_or_logic = Column(Text) # How to calculate this KPI
#     # target_value = Column(Numeric, nullable=True)
#     # threshold_critical = Column(Numeric, nullable=True)
#     # threshold_warning = Column(Numeric, nullable=True)
#     # calculation_frequency = Column(String) # HOURLY, DAILY, WEEKLY

# class KPISnapshot(Base): # Stores calculated KPI values over time
#     __tablename__ = "kpi_snapshots"
#     id = Column(Integer, primary_key=True, index=True)
#     kpi_definition_id = Column(Integer, ForeignKey("kpi_definitions.id"), nullable=False)
#     snapshot_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
#     value = Column(Numeric(precision=20, scale=4), nullable=False)
#     # status_derived = Column(String) # NORMAL, WARNING, CRITICAL (based on thresholds)

# The core data for reports and analytics will come from other modules:
# - CustomerIdentityManagement: Customer demographics, KYC status, segments.
# - AccountsLedgerManagement: Account balances, types, statuses, interest.
# - LoanManagementModule: Loan portfolio, NPLs, disbursements, repayments.
# - TransactionManagement: Transaction volumes, values, channels, trends.
# - CardsWalletsManagement: Card usage, wallet balances, e-channel activity.
# - FeesChargesCommissionEngine: Fee income, waivers.
# - CRMSupport: Ticket volumes, resolution times, campaign effectiveness.
# - TreasuryLiquidity: Bank positions, FX rates, investment yields.

# This module's services will need robust (read-only) access to those modules' data,
# potentially via their service layers or direct DB queries (if optimized for reporting, e.g. read replicas or data warehouse).
