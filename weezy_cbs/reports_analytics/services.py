# Service layer for Reports & Analytics Module
from sqlalchemy.orm import Session
from sqlalchemy import text # For executing raw SQL if needed (with caution)
from . import models, schemas
import json
import csv
import io
from datetime import datetime, date
import decimal # For handling decimal data from DB

# Placeholder for other service integrations & data sources
# from weezy_cbs.customer_identity_management.services import get_customer_data_for_report_xyz
# from weezy_cbs.transaction_management.services import get_transaction_summary_for_period
# from weezy_cbs.shared import exceptions, file_storage_service, query_builder_utility (for safe query building)

class ReportExecutionError(Exception): pass
class QueryBuildingError(Exception): pass
class NotFoundException(Exception): pass # If a report def or saved query not found

# --- ReportDefinition Services (Admin/Setup) ---
def create_report_definition(db: Session, report_def_in: schemas.ReportDefinitionCreateRequest) -> models.ReportDefinition:
    existing = db.query(models.ReportDefinition).filter(models.ReportDefinition.report_code == report_def_in.report_code).first()
    if existing:
        raise ValueError(f"Report definition with code {report_def_in.report_code} already exists.")

    db_report_def = models.ReportDefinition(
        **report_def_in.dict()
        # source_data_description_json=json.dumps(report_def_in.source_data_description_json) if report_def_in.source_data_description_json else None,
        # parameters_schema_json=json.dumps(report_def_in.parameters_schema_json) if report_def_in.parameters_schema_json else None,
    )
    db.add(db_report_def)
    db.commit()
    db.refresh(db_report_def)
    return db_report_def

def get_report_definition(db: Session, report_code: str) -> Optional[models.ReportDefinition]:
    return db.query(models.ReportDefinition).filter(models.ReportDefinition.report_code == report_code).first()

# --- SavedQuery Services (User-specific) ---
def save_user_query(db: Session, query_in: schemas.SavedQueryCreateRequest, user_id: int) -> models.SavedQuery:
    db_saved_query = models.SavedQuery(
        user_id=user_id,
        query_name=query_in.query_name,
        description=query_in.description,
        query_language=query_in.query_language,
        query_text_or_params_json=json.dumps(query_in.query_text_or_params_json) # Store as JSON string
    )
    db.add(db_saved_query)
    db.commit()
    db.refresh(db_saved_query)
    return db_saved_query

# --- Report Execution Services ---
def _fetch_data_for_report(db: Session, report_code: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Conceptual function to fetch data based on report_code and parameters.
    This would involve complex logic:
    - Getting the ReportDefinition.
    - Using its query_template or query_generator_function_name.
    - Safely substituting params into template or calling generator.
    - Executing the query against appropriate DBs/services.
    - Returning data as List[Dict].
    """
    # Example: Hardcoded logic for a mock report
    if report_code == "DAILY_TRANSACTION_SUMMARY":
        # start_date = params.get("start_date", date.today().isoformat())
        # end_date = params.get("end_date", date.today().isoformat())
        # MOCK DATA:
        return [
            {"channel": "NIP", "volume": 1500, "value": decimal.Decimal("75000000.00")},
            {"channel": "POS", "volume": 8000, "value": decimal.Decimal("12000000.00")},
            {"channel": "ATM", "volume": 3000, "value": decimal.Decimal("9000000.00")},
        ]
    elif report_code == "CUSTOMER_ACTIVITY_MONTHLY":
        # MOCK DATA:
        return [
            {"customer_id": 101, "name": "Ada Eze", "login_count": 25, "transaction_count": 15},
            {"customer_id": 102, "name": "Ben Ola", "login_count": 10, "transaction_count": 5},
        ]
    elif report_code == "KPI_TOTAL_ACTIVE_CUSTOMERS": # For a KPI widget
        # count = db.query(func.count(Customer.id)).filter(Customer.is_active==True).scalar()
        return [{"kpi_name": "Total Active Customers", "value": random.randint(10000, 15000)}]

    raise ReportExecutionError(f"Data fetching logic for report code '{report_code}' not implemented.")

def _format_report_data(data: List[Dict[str, Any]], output_format: str) -> Any:
    """Formats data into the desired output string (CSV, JSON str) or object (for direct API response)."""
    if not data:
        return "No data available for this report." if output_format != "JSON" else []

    if output_format.upper() == "JSON":
        # For direct JSON response, ensure Decimals are handled if Pydantic doesn't do it upstream
        def decimal_default(obj):
            if isinstance(obj, decimal.Decimal):
                return str(obj) # Or float(obj) if precision loss is acceptable
            raise TypeError
        return json.loads(json.dumps(data, default=decimal_default)) # Return as Python list/dict

    elif output_format.upper() == "CSV":
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return output.getvalue()

    # elif output_format.upper() == "PDF" or output_format.upper() == "XLSX":
    #     # Requires libraries like reportlab/weasyprint for PDF, openpyxl/xlsxwriter for Excel
    #     raise NotImplementedError(f"Output format {output_format} requires dedicated library.")
    else:
        raise ReportExecutionError(f"Unsupported output format: {output_format}")


def execute_report(db: Session, exec_request: schemas.ReportExecutionRequest, user_id: str) -> schemas.ReportExecutionResult:
    if not exec_request.report_code: # Ad-hoc query not fully supported in this simplified version
        raise NotImplementedError("Ad-hoc query execution not fully implemented. Please use a predefined report_code.")

    report_def = get_report_definition(db, exec_request.report_code)
    if not report_def:
        raise NotFoundException(f"Report definition for code '{exec_request.report_code}' not found.")

    # Log the instance of report generation
    instance_log = models.GeneratedReportInstance(
        report_code_or_name=report_def.report_code,
        # parameters_used_json=json.dumps(exec_request.parameters),
        # generated_by_user_id=user_id,
        output_format=exec_request.output_format.upper(),
        status="PENDING"
    )
    db.add(instance_log)
    db.commit()
    db.refresh(instance_log)

    try:
        instance_log.status = "GENERATING"
        db.commit() # Commit status before potentially long operation

        report_data_list_of_dicts = _fetch_data_for_report(db, report_def.report_code, exec_request.parameters)

        formatted_output = None
        file_url_for_log = None

        if exec_request.output_format.upper() == "JSON":
            formatted_output = _format_report_data(report_data_list_of_dicts, "JSON")
            # instance_log.data_preview_json = json.dumps(formatted_output[:10]) # Preview first 10 if large
        else: # CSV, PDF, XLSX would be files
            file_content_str = _format_report_data(report_data_list_of_dicts, exec_request.output_format.upper())
            # file_path = file_storage_service.save_generated_report(
            #     instance_log.id, report_def.report_code, exec_request.output_format, file_content_str
            # )
            # file_url_for_log = file_storage_service.get_report_url(file_path) # Conceptual
            file_url_for_log = f"/generated_reports/{instance_log.id}.{exec_request.output_format.lower()}" # Mock URL
            # For API response, if not JSON, we'd typically return a link or trigger download.
            # Here, the `data` field in ReportExecutionResult would be None if file_url is set.

        instance_log.status = "COMPLETED"
        # instance_log.file_path_or_url = file_url_for_log
        instance_log.generated_at = datetime.utcnow() # Should be set automatically but good to ensure
        db.commit()
        db.refresh(instance_log)

        return schemas.ReportExecutionResult(
            instance_id=instance_log.id,
            report_code_or_name=instance_log.report_code_or_name,
            status=instance_log.status,
            generated_at=instance_log.generated_at,
            output_format=instance_log.output_format,
            data=formatted_output if exec_request.output_format.upper() == "JSON" else None,
            # file_url=file_url_for_log if exec_request.output_format.upper() != "JSON" else None
        )

    except Exception as e:
        instance_log.status = "FAILED"
        instance_log.error_message = str(e)
        db.commit()
        db.refresh(instance_log)
        raise ReportExecutionError(f"Failed to execute report {exec_request.report_code}: {str(e)}")

def get_generated_report_instance(db: Session, instance_id: int) -> Optional[models.GeneratedReportInstance]:
    return db.query(models.GeneratedReportInstance).filter(models.GeneratedReportInstance.id == instance_id).first()


# --- Dashboard Services (Conceptual) ---
def get_dashboard_definition(db: Session, dashboard_code: str) -> Optional[models.DashboardDefinition]:
    return db.query(models.DashboardDefinition).filter(models.DashboardDefinition.dashboard_code == dashboard_code).first()

def get_dashboard_data(db: Session, dashboard_code: str, user_id: str) -> Dict[str, Any]:
    """
    Fetches data for all widgets defined in a dashboard.
    Returns a dictionary where keys are widget_ids and values are ReportExecutionResult-like data.
    """
    dashboard_def = get_dashboard_definition(db, dashboard_code)
    if not dashboard_def:
        raise NotFoundException(f"Dashboard definition '{dashboard_code}' not found.")

    # layout_config = json.loads(dashboard_def.layout_config_json or "{}")
    # widgets = layout_config.get("widgets", [])
    widgets_mock = [ # Mocking the widget config that would come from layout_config_json
        {"id": "widget1", "report_definition_code": "KPI_TOTAL_ACTIVE_CUSTOMERS", "parameters": {}, "output_format": "JSON"},
        {"id": "widget2", "report_definition_code": "DAILY_TRANSACTION_SUMMARY", "parameters": {"date_range": "TODAY"}, "output_format": "JSON"}
    ]

    dashboard_data = {}
    for widget_conf_dict in widgets_mock: # Iterate over actual widgets from layout_config
        widget_id = widget_conf_dict.get("id")
        report_code = widget_conf_dict.get("report_definition_code") # Or kpi_code
        params = widget_conf_dict.get("parameters", {})
        output_format = widget_conf_dict.get("output_format", "JSON") # Default to JSON for dashboard widgets

        if not report_code or not widget_id:
            dashboard_data[widget_id or f"unknown_widget_{random.randint(1,100)}"] = {"error": "Widget misconfigured: missing report_code or id"}
            continue

        try:
            # For dashboards, we usually want direct data, not just a log entry.
            # So, we might call a simplified execute_report that returns data directly or an error.
            # This is a conceptual call pattern.
            report_exec_req = schemas.ReportExecutionRequest(report_code=report_code, parameters=params, output_format=output_format)
            # Using the main execute_report for consistency, it returns data for JSON format.
            widget_data_result = execute_report(db, report_exec_req, user_id)
            dashboard_data[widget_id] = widget_data_result # This is ReportExecutionResult schema
        except Exception as e:
            dashboard_data[widget_id] = {"error": str(e), "report_code": report_code, "params": params}

    return dashboard_data

# --- KPI Services (Conceptual) ---
# def calculate_and_store_kpi_snapshot(db: Session, kpi_code: str):
#     kpi_def = db.query(models.KPIDefinition).filter(models.KPIDefinition.kpi_code == kpi_code).first()
#     if not kpi_def: raise NotFoundException(f"KPI Definition {kpi_code} not found.")
#
#     # Execute kpi_def.data_source_query_or_logic to get the value
#     # value = _execute_kpi_query(db, kpi_def.data_source_query_or_logic)
#     mock_value = decimal.Decimal(random.uniform(100, 10000)) # Mock
#
#     snapshot = models.KPISnapshot(kpi_definition_id=kpi_def.id, snapshot_timestamp=datetime.utcnow(), value=mock_value)
#     db.add(snapshot)
#     db.commit()
#     return snapshot

# This module acts as an aggregator and presenter.
# It needs robust read access to potentially many other modules' data.
# Performance considerations (query optimization, caching, read replicas, or even a separate data warehouse/data lake)
# are very important for a real-world Reports & Analytics module.
# The `_fetch_data_for_report` is the heart of this and would be very complex.

# Import random for mock data generation
import random
# Import func for count queries if used
from sqlalchemy import func
