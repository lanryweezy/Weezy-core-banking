# Pydantic schemas for Reports & Analytics Module
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import decimal

# --- ReportDefinition Schemas (Admin/Setup) ---
class ReportDefinitionBase(BaseModel):
    report_code: str = Field(..., min_length=3, pattern=r"^[A-Z0-9_]+$")
    report_name: str
    description: Optional[str] = None
    # source_data_description_json: Optional[Dict[str, Any]] = None
    # parameters_schema_json: Optional[Dict[str, Any]] = Field({}, description="JSON schema for report parameters")
    # default_output_format: str = "CSV"
    # query_template: Optional[str] = None # Or query_generator_function_name

class ReportDefinitionCreateRequest(ReportDefinitionBase):
    pass

class ReportDefinitionResponse(ReportDefinitionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config:
        orm_mode = True

# --- SavedQuery Schemas (User-specific) ---
class SavedQueryBase(BaseModel):
    query_name: str
    description: Optional[str] = None
    query_language: str = "SQL_WEEZYQL" # Or "RAW_SQL" (admin only)
    query_text_or_params_json: Dict[str, Any] # If WEEZYQL, this is params. If RAW_SQL, this is {"sql_query": "SELECT ..."}

class SavedQueryCreateRequest(SavedQueryBase):
    # user_id: int # From authenticated context
    pass

class SavedQueryResponse(SavedQueryBase):
    id: int
    # user_id: int
    created_at: datetime
    last_run_at: Optional[datetime] = None
    class Config:
        orm_mode = True

# --- DashboardDefinition Schemas (Admin/User-specific setup) ---
class DashboardWidgetConfig(BaseModel):
    id: str # Unique ID for the widget instance on the dashboard
    widget_type: str # e.g., "KPI_DISPLAY", "LINE_CHART", "BAR_CHART", "DATA_TABLE"
    report_definition_code: Optional[str] = None # Link to a ReportDefinition for data
    # kpi_code: Optional[str] = None # Link to a KPIDefinition
    title: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = Field({}, description="Parameters for the report/KPI")
    # position_and_size: Optional[Dict[str, int]] = None # e.g. {"row": 0, "col": 0, "rowSpan": 1, "colSpan": 1}

class DashboardDefinitionBase(BaseModel):
    dashboard_code: str = Field(..., min_length=3, pattern=r"^[A-Z0-9_]+$")
    dashboard_name: str
    # layout_config_json: List[DashboardWidgetConfig] = Field([], description="Configuration of widgets on the dashboard")
    is_default: bool = False

class DashboardDefinitionCreateRequest(DashboardDefinitionBase):
    # user_id_owner: Optional[int] = None # If user creating their own dashboard
    # role_id_default: Optional[int] = None # If setting as default for a role
    pass

class DashboardDefinitionResponse(DashboardDefinitionBase):
    id: int
    created_at: datetime
    class Config:
        orm_mode = True

# --- Report Execution/Instance Schemas ---
class ReportExecutionRequest(BaseModel):
    report_code: Optional[str] = None # If running a predefined report
    # If ad-hoc query:
    # query_language: Optional[str] = "SQL_WEEZYQL"
    # query_text_or_params_json: Optional[Dict[str, Any]] = None

    parameters: Optional[Dict[str, Any]] = Field({}, description="Parameters for the report or query")
    output_format: str = Field("JSON", description="Desired output: JSON, CSV, PDF, XLSX") # Default to JSON for API

class ReportExecutionResult(BaseModel): # This is what the API returns
    instance_id: int # ID of the GeneratedReportInstance record
    report_code_or_name: str
    status: str # PENDING, GENERATING, COMPLETED, FAILED
    generated_at: Optional[datetime] = None
    output_format: str
    # For JSON output, data might be embedded or link provided
    data: Optional[Any] = None # Can be List[Dict] for tabular data, or Dict for summary data
    # file_url: Optional[HttpUrl] = None # If output is CSV/PDF/XLSX and stored
    error_message: Optional[str] = None

    class Config:
        orm_mode = True # If mapping from GeneratedReportInstance model directly for some fields
        json_encoders = { decimal.Decimal: str } # If data contains decimals

class GeneratedReportInstanceResponse(BaseModel): # For listing past reports
    id: int
    report_code_or_name: str
    # parameters_used_json: Optional[Dict[str, Any]] = None
    # generated_by_user_id: int
    generated_at: datetime
    output_format: str
    # file_path_or_url: Optional[str] = None
    status: str
    # error_message: Optional[str] = None
    class Config:
        orm_mode = True

# --- KPI Schemas (Conceptual) ---
class KPIDefinitionResponse(BaseModel):
    kpi_code: str
    kpi_name: str
    # Other metadata
    class Config:
        orm_mode = True

class KPISnapshotResponse(BaseModel):
    kpi_code: str # Denormalized from KPIDefinition for convenience
    snapshot_timestamp: datetime
    value: decimal.Decimal
    # status_derived: Optional[str] = None # NORMAL, WARNING, CRITICAL
    class Config:
        orm_mode = True
        json_encoders = { decimal.Decimal: str }

# --- Paginated Responses ---
class PaginatedReportDefinitionResponse(BaseModel):
    items: List[ReportDefinitionResponse]
    total: int
    page: int
    size: int

class PaginatedSavedQueryResponse(BaseModel):
    items: List[SavedQueryResponse]
    total: int
    page: int
    size: int

class PaginatedDashboardDefinitionResponse(BaseModel):
    items: List[DashboardDefinitionResponse]
    total: int
    page: int
    size: int

class PaginatedGeneratedReportInstanceResponse(BaseModel):
    items: List[GeneratedReportInstanceResponse]
    total: int
    page: int
    size: int

# Import decimal for fields that might handle it, though most data is Any/Dict here
import decimal
