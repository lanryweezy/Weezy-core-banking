# API Endpoints for Reports & Analytics Module
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_user_with_reporting_perms

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_user_with_reporting_perms_placeholder(): return {"id": "reporter01", "username": "reporter_user", "role": "reporting_user"}
get_current_active_user_with_reporting_perms = get_current_active_user_with_reporting_perms_placeholder
def get_current_active_admin_user_placeholder(): return {"id": "admin01", "username": "admin_user", "role": "admin"} # For admin tasks like defining reports
get_current_active_admin_user = get_current_active_admin_user_placeholder


router = APIRouter(
    prefix="/reports-analytics",
    tags=["Reports & Analytics"],
    responses={404: {"description": "Not found"}},
)

# --- ReportDefinition Endpoints (Admin/Setup) ---
@router.post("/report-definitions", response_model=schemas.ReportDefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_new_report_definition(
    report_def_in: schemas.ReportDefinitionCreateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Define a new reusable report template. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.create_report_definition(db, report_def_in)
    except ValueError as e: # Handles duplicate code
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/report-definitions/{report_code}", response_model=schemas.ReportDefinitionResponse)
def get_details_of_report_definition(report_code: str, db: Session = Depends(get_db)):
    """Get details of a specific report definition."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    report_def = services.get_report_definition(db, report_code)
    if not report_def:
        raise HTTPException(status_code=404, detail="Report definition not found.")
    return report_def

@router.get("/report-definitions", response_model=schemas.PaginatedReportDefinitionResponse)
def list_all_report_definitions(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all available report definitions."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # items = db.query(models.ReportDefinition).offset(skip).limit(limit).all()
    # total = db.query(func.count(models.ReportDefinition.id)).scalar_one_or_none() or 0
    # Mock
    items = [models.ReportDefinition(id=i, report_code=f"REP00{i}", report_name=f"Sample Report {i}") for i in range(1,3)]
    total = 2
    return schemas.PaginatedReportDefinitionResponse(items=items, total=total, page=(skip//limit)+1, size=len(items))

# --- Report Execution Endpoint ---
@router.post("/execute-report", response_model=schemas.ReportExecutionResult, status_code=status.HTTP_202_ACCEPTED)
async def execute_a_report( # Async if report generation can be lengthy
    exec_request: schemas.ReportExecutionRequest,
    background_tasks: BackgroundTasks, # For potentially long-running reports
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user_with_reporting_perms)
):
    """
    Execute a predefined report or an ad-hoc query.
    For formats like CSV, PDF, XLSX, the actual file download might be a separate step using the instance_id or a returned URL.
    For JSON, data may be returned directly if small enough.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    user_id_str = str(current_user.get("id"))

    # For long reports, it's better to run in background and provide a way to check status / get results later.
    # This example will run synchronously for simplicity if JSON, or log for file-based.

    # If we want to use background tasks for all:
    # report_instance_log = services.create_report_instance_log_pending(db, exec_request, user_id_str)
    # background_tasks.add_task(services.execute_report_async_and_update_log, db, report_instance_log.id, exec_request, user_id_str)
    # return schemas.ReportExecutionResult(instance_id=report_instance_log.id, report_code_or_name=exec_request.report_code or "AdHoc", status="PENDING", output_format=exec_request.output_format)

    # Synchronous execution (can be long):
    try:
        result = services.execute_report(db, exec_request, user_id_str)
        return result
    except services.NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except services.ReportExecutionError as e:
        raise HTTPException(status_code=500, detail=f"Report execution failed: {str(e)}")
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))

@router.get("/report-instances/{instance_id}", response_model=schemas.GeneratedReportInstanceResponse) # Or ReportExecutionResult if data is needed
def get_generated_report_instance_details(instance_id: int, db: Session = Depends(get_db)):
    """Get metadata of a specific generated report instance."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    instance = services.get_generated_report_instance(db, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Report instance not found.")
    # TODO: Add auth check: user who generated it or has general report viewing rights.
    return instance

# --- Dashboard Data Endpoint ---
@router.get("/dashboards/{dashboard_code}/data", response_model=Dict[str, Any]) # Response is map of widget_id to widget_data
def get_data_for_dashboard(
    dashboard_code: str,
    # Date range or other global dashboard filters can be passed as query params
    # start_date: Optional[date] = Query(None),
    # end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user_with_reporting_perms)
):
    """
    Fetch data for all widgets configured on a specific dashboard.
    Each widget's data will be under its ID in the response.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    user_id_str = str(current_user.get("id"))
    try:
        # dashboard_filters = {"start_date": start_date, "end_date": end_date} # Pass to service
        dashboard_data = services.get_dashboard_data(db, dashboard_code, user_id_str) # Pass filters
        return dashboard_data
    except services.NotFoundException as e: # If dashboard_code not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")


# --- Saved Query Endpoints (User-specific) ---
@router.post("/saved-queries", response_model=schemas.SavedQueryResponse, status_code=status.HTTP_201_CREATED)
def save_new_user_query(
    query_in: schemas.SavedQueryCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user_with_reporting_perms)
):
    """Save a custom query for the authenticated user."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    user_id = current_user.get("id")
    return services.save_user_query(db, query_in, user_id)

# TODO: Add GET, PUT, DELETE for /saved-queries/{query_id}
# TODO: Add CRUD for DashboardDefinition (Admin/User for their own dashboards)
# TODO: Add endpoints for listing/fetching KPI data (if KPIDefinition/KPISnapshot models are used)

# Import func for count queries if used
from sqlalchemy import func
# Import date for query param typing if not already at top
from datetime import date
