from pydantic import BaseModel, Field, validator, Json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import json

from .models import (
    ReportQueryLogicTypeEnum, ReportStatusEnum, ScheduledReportStatusEnum
)

# --- Helper Schemas for JSON fields ---
# These are illustrative; actual validation of complex JSON structures might require more detailed Pydantic models.

class ReportParameterDefinition(BaseModel): # For individual parameters in parameters_schema_json
    name: str
    type: str = Field("string", description="e.g., string, integer, date, boolean, enum")
    label: Optional[str] = None
    required: bool = False
    default_value: Optional[Any] = None
    options: Optional[List[Any]] = Field(None, description="For enum type") # List of allowed values for enum

class ReportParametersSchema(BaseModel): # For the overall parameters_schema_json
    parameters: List[ReportParameterDefinition] = []


class QueryDetailsSQL(BaseModel):
    sql_template: str = Field(..., description="SQL query with placeholders like :param_name")

class QueryDetailsDynamicFilters(BaseModel):
    base_model_name: str = Field(..., description="e.g., Customer, Account, Transaction") # Name of the primary SQLAlchemy model to query
    # List of field names from base_model_name that are allowed to be filtered on.
    # Client would send {"field_name": "operator:value"} e.g. {"customer_tier": "eq:TIER_1", "created_at": "gte:2023-01-01"}
    allowed_filter_fields: List[str]
    # Optional: Define default select fields or allow client to specify
    default_select_fields: Optional[List[str]] = None
    # Optional: Define default sort order
    default_sort_by: Optional[str] = None # e.g., "created_at:desc"


class DashboardWidgetConfig(BaseModel):
    id: str = Field(..., description="Unique ID for the widget on the dashboard")
    report_code: Optional[str] = Field(None, description="ReportDefinition code to source data for this widget")
    metric_key: Optional[str] = Field(None, description="Specific metric key (if not a full report, e.g. a single KPI value)")
    viz_type: str = Field(..., description="e.g., LINE_CHART, BAR_CHART, KPI_VALUE, TABLE")
    title: Optional[str] = None
    # Position and size for a grid-based layout
    col: int
    row: int
    width: int
    height: int
    # Specific parameters to pass to the report_code for this widget instance
    report_params: Optional[Dict[str, Any]] = None
    # Additional visualization options specific to viz_type
    viz_options: Optional[Dict[str, Any]] = None


# --- ReportDefinition Schemas ---
class ReportDefinitionBase(BaseModel):
    report_code: str = Field(..., max_length=50, pattern=r"^[A-Z0-9_]+$", description="Unique code, e.g., REG_CBN_001")
    report_name: str = Field(..., max_length=150)
    description: Optional[str] = None
    source_modules_json: Optional[List[str]] = Field(None, description='JSON array of source modules, e.g., ["accounts", "transactions"]')
    query_logic_type: ReportQueryLogicTypeEnum
    query_details_json: Union[QueryDetailsSQL, QueryDetailsDynamicFilters, Dict[str, Any]] # Actual SQL, or filter config, or script path
    parameters_schema_json: Optional[ReportParametersSchema] = Field(None, description="JSON schema for report parameters")
    default_output_formats_json: Optional[List[str]] = Field(["CSV", "JSON"], description='Default output formats, e.g., ["CSV", "PDF"]')
    allowed_roles_json: Optional[List[str]] = Field(None, description="JSON array of role names that can access")
    is_system_report: bool = False
    version: int = Field(1, ge=1)

    @validator('source_modules_json', 'default_output_formats_json', 'allowed_roles_json', 'query_details_json', 'parameters_schema_json', pre=True)
    def parse_json_fields(cls, value, field):
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                # Further validation based on field.name if needed by Pydantic model for that field
                if field.name == 'parameters_schema_json' and parsed_value is not None:
                    return ReportParametersSchema.parse_obj(parsed_value) # Validate against helper schema
                # Add similar for query_details based on query_logic_type if it was a string
                return parsed_value
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON string for {field.name}")
        # If already parsed or meant to be a specific Pydantic model (like query_details_json)
        if field.name == 'parameters_schema_json' and isinstance(value, dict) and value is not None:
             return ReportParametersSchema.parse_obj(value)
        # Add specific parsing for query_details_json based on query_logic_type if it's a dict
        # This is complex with Union, might need a root_validator or manual parsing in service based on type
        return value


class ReportDefinitionCreate(ReportDefinitionBase):
    # created_by_user_id is set by the service from authenticated user
    pass

class ReportDefinitionUpdate(BaseModel): # Partial updates
    report_name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    source_modules_json: Optional[List[str]] = None
    query_logic_type: Optional[ReportQueryLogicTypeEnum] = None
    query_details_json: Optional[Union[QueryDetailsSQL, QueryDetailsDynamicFilters, Dict[str, Any]]] = None
    parameters_schema_json: Optional[ReportParametersSchema] = None
    default_output_formats_json: Optional[List[str]] = None
    allowed_roles_json: Optional[List[str]] = None
    is_system_report: Optional[bool] = None
    version: Optional[int] = Field(None, ge=1) # Consider if version update is manual or auto

    @validator('source_modules_json', 'default_output_formats_json', 'allowed_roles_json', 'query_details_json', 'parameters_schema_json', pre=True)
    def parse_update_json_fields(cls, value, field): # Duplicate for updates
        if value is None: return None
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                if field.name == 'parameters_schema_json' and parsed_value is not None:
                    return ReportParametersSchema.parse_obj(parsed_value)
                return parsed_value
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON string for {field.name}")
        if field.name == 'parameters_schema_json' and isinstance(value, dict) and value is not None:
             return ReportParametersSchema.parse_obj(value)
        return value

class ReportDefinitionResponse(ReportDefinitionBase):
    id: int
    created_by_user_id: Optional[int] = None
    # created_by_username: Optional[str] = None # Added by service
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True # For query_logic_type


# --- ScheduledReport Schemas ---
class ScheduledReportBase(BaseModel):
    report_definition_id: int
    schedule_name: Optional[str] = Field(None, max_length=150)
    cron_expression: str = Field(..., max_length=100, description='e.g., "0 0 * * MON"')
    parameters_values_json: Optional[Dict[str, Any]] = Field(None, description="JSON object of parameter values")
    output_format: str = Field("CSV", max_length=10)
    recipients_json: Optional[List[str]] = Field(None, description='JSON array of email addresses or user IDs')
    status: ScheduledReportStatusEnum = ScheduledReportStatusEnum.ACTIVE

    @validator('parameters_values_json', 'recipients_json', pre=True)
    def parse_json_fields_scheduled(cls, value):
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: raise ValueError("Invalid JSON string")
        return value

class ScheduledReportCreate(ScheduledReportBase):
    # created_by_user_id from authenticated user
    pass

class ScheduledReportUpdate(BaseModel): # Partial updates
    schedule_name: Optional[str] = Field(None, max_length=150)
    cron_expression: Optional[str] = Field(None, max_length=100)
    parameters_values_json: Optional[Dict[str, Any]] = None
    output_format: Optional[str] = Field(None, max_length=10)
    recipients_json: Optional[List[str]] = None
    status: Optional[ScheduledReportStatusEnum] = None

    @validator('parameters_values_json', 'recipients_json', pre=True)
    def parse_update_json_fields_scheduled(cls, value): # Duplicate
        if value is None: return None
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: raise ValueError("Invalid JSON string")
        return value

class ScheduledReportResponse(ScheduledReportBase):
    id: int
    report_definition: Optional[ReportDefinitionResponse] = None # Nested for context
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_run_status: Optional[ReportStatusEnum] = None
    last_error_message: Optional[str] = None
    created_by_user_id: int
    # created_by_username: Optional[str] = None # Added by service
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True # For status enums


# --- GeneratedReportLog Schemas ---
class GeneratedReportLogResponse(BaseModel):
    id: int
    report_definition_id: Optional[int] = None
    scheduled_report_id: Optional[int] = None
    report_name_generated: str
    generated_by_user_id: int
    # generated_by_username: Optional[str] = None # Added by service
    generation_timestamp: datetime
    parameters_used_json: Optional[Dict[str, Any]] = None
    output_format: str
    status: ReportStatusEnum
    file_name: Optional[str] = None
    file_path_or_link: Optional[str] = None # Could be a presigned URL
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[int] = None

    report_definition_code: Optional[str] = None # Added by service for context

    @validator('parameters_used_json', pre=True)
    def parse_params_json(cls, value):
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: return None
        return value

    class Config:
        orm_mode = True
        use_enum_values = True


# --- DashboardLayout Schemas ---
class DashboardLayoutBase(BaseModel):
    dashboard_name: str = Field(..., max_length=100)
    layout_config_json: List[DashboardWidgetConfig] # Expecting a list of widget configs
    is_default: bool = False

    @validator('layout_config_json', pre=True)
    def parse_layout_json(cls, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list): # Ensure it's a list of widgets
                    return [DashboardWidgetConfig.parse_obj(item) for item in parsed]
                raise ValueError("layout_config_json must be a list of widget configurations")
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for layout_config_json")
        elif isinstance(value, list): # Already a list, validate items
             return [DashboardWidgetConfig.parse_obj(item) for item in value]
        return value


class DashboardLayoutCreate(DashboardLayoutBase):
    # user_id from authenticated user
    pass

class DashboardLayoutUpdate(BaseModel): # Partial updates
    dashboard_name: Optional[str] = Field(None, max_length=100)
    layout_config_json: Optional[List[DashboardWidgetConfig]] = None
    is_default: Optional[bool] = None

    @validator('layout_config_json', pre=True)
    def parse_update_layout_json(cls, value): # Duplicate for update
        if value is None: return None
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [DashboardWidgetConfig.parse_obj(item) for item in parsed]
                raise ValueError("layout_config_json must be a list of widget configurations")
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for layout_config_json")
        elif isinstance(value, list):
             return [DashboardWidgetConfig.parse_obj(item) for item in value]
        return value


class DashboardLayoutResponse(DashboardLayoutBase):
    id: int
    user_id: int
    # username: Optional[str] = None # Added by service
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- AdHoc Report Request & Response ---
class AdHocReportRequest(BaseModel):
    report_name: str = Field("Ad-hoc Report", max_length=200)
    query_logic_type: ReportQueryLogicTypeEnum # e.g., DYNAMIC_FILTERS_ON_MODEL
    query_details: Union[QueryDetailsSQL, QueryDetailsDynamicFilters, Dict[str, Any]] # The actual query or filter config
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters for the ad-hoc query")
    output_format: str = Field("JSON", description="Desired output: JSON, CSV") # PDF might be complex for ad-hoc

class ReportDataResponse(BaseModel):
    report_name: str
    generation_timestamp: datetime
    output_format: str
    data: Union[List[Dict[str, Any]], str, Dict[str, Any]] # List of dicts for JSON, string for CSV, or link to file
    row_count: Optional[int] = None
    error_message: Optional[str] = None
    log_id: Optional[int] = Field(None, description="ID of the GeneratedReportLog entry")


# --- Paginated Responses ---
class PaginatedReportDefinitionResponse(BaseModel):
    items: List[ReportDefinitionResponse]
    total: int
    page: int
    size: int

class PaginatedScheduledReportResponse(BaseModel):
    items: List[ScheduledReportResponse]
    total: int
    page: int
    size: int

class PaginatedGeneratedReportLogResponse(BaseModel):
    items: List[GeneratedReportLogResponse]
    total: int
    page: int
    size: int

class PaginatedDashboardLayoutResponse(BaseModel):
    items: List[DashboardLayoutResponse]
    total: int
    page: int
    size: int
