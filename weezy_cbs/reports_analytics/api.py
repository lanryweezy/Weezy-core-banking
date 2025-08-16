from typing import List, Optional, Any, Union

from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks, Query
from sqlalchemy.orm import Session

from weezy_cbs.database import get_db
from . import schemas, services, models
from .services import (
    report_definition_service, scheduled_report_service, generated_report_log_service,
    dashboard_layout_service, ReportGenerationService # ReportGenerationService needs instantiation
)
# Assuming an authentication dependency from core_infrastructure_config_engine
from weezy_cbs.core_infrastructure_config_engine.api import get_current_active_superuser, get_performing_user_username
from weezy_cbs.core_infrastructure_config_engine.models import User as CoreUser # For type hint

# Main router for Reports & Analytics
reports_api_router = APIRouter(
    prefix="/reports-analytics",
    tags=["Reports & Analytics"],
    dependencies=[Depends(get_current_active_superuser)] # All ops require authenticated staff
)

# --- ReportDefinition Endpoints ---
defs_router = APIRouter(prefix="/definitions", tags=["Report Definitions"])

@defs_router.post("/", response_model=schemas.ReportDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_report_definition_endpoint(
    def_in: schemas.ReportDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    return report_definition_service.create_definition(
        db, def_in=def_in, user_id=current_user.id, username=current_user.username
    )

@defs_router.get("/", response_model=schemas.PaginatedReportDefinitionResponse)
async def list_report_definitions_endpoint(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    defs, total = report_definition_service.get_definitions(db, skip=skip, limit=limit)
    return {"items": defs, "total": total, "page": (skip // limit) + 1, "size": limit}

@defs_router.get("/{definition_id}", response_model=schemas.ReportDefinitionResponse)
async def read_report_definition_endpoint(definition_id: int, db: Session = Depends(get_db)):
    db_def = report_definition_service.get_definition_by_id(db, definition_id)
    if not db_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report Definition not found")
    return db_def

@defs_router.get("/code/{report_code}", response_model=schemas.ReportDefinitionResponse)
async def read_report_definition_by_code_endpoint(report_code: str, db: Session = Depends(get_db)):
    db_def = report_definition_service.get_definition_by_code(db, report_code)
    if not db_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report Definition not found for this code.")
    return db_def

@defs_router.put("/{definition_id}", response_model=schemas.ReportDefinitionResponse)
async def update_report_definition_endpoint(
    definition_id: int,
    def_upd: schemas.ReportDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    updated_def = report_definition_service.update_definition(
        db, def_id=definition_id, def_upd=def_upd, username=current_user.username
    )
    if not updated_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report Definition not found")
    return updated_def

@defs_router.delete("/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_definition_endpoint(
    definition_id: int,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    if not report_definition_service.delete_definition(db, def_id=definition_id, username=current_user.username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report Definition not found")
    return None

# --- Report Execution & Logs Endpoints ---
exec_logs_router = APIRouter(tags=["Report Execution & Logs"])

@exec_logs_router.post("/definitions/{definition_id}/generate", response_model=schemas.GeneratedReportLogResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report_from_definition_endpoint(
    definition_id: int,
    background_tasks: BackgroundTasks,
    parameters: Optional[Dict[str, Any]] = Body(None, description="Parameters for the report"),
    output_format: str = Query("CSV", description="Desired output format (e.g., CSV, JSON, PDF)"),
    db: Session = Depends(get_db), # Pass db session to endpoint
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    report_def = report_definition_service.get_definition_by_id(db, definition_id)
    if not report_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report Definition not found")

    # Create initial log entry in PENDING state
    # The actual generation service needs a db session, so we pass it.
    # This is tricky if ReportGenerationService itself needs to be a dependency.
    # For background tasks, it's common to pass IDs and let the task fetch objects.

    # Instantiate generation service here, passing the current db session
    report_gen_service = ReportGenerationService(db, generated_report_log_service, report_definition_service)

    # Create initial log entry
    log_entry = generated_report_log_service.create_log_entry(
        db, report_name=report_def.report_name, generated_by_user_id=current_user.id,
        output_format=output_format.upper(), report_def_id=report_def.id, params_used=parameters
    )

    # Add generation to background tasks
    # Note: Background tasks need to handle their own DB sessions if they run truly async.
    # For simplicity here, if generate_report_from_definition is synchronous but long, this is okay.
    # If it's truly async, it would need to create its own session.
    # We are passing log_entry.id and other necessary data.
    background_tasks.add_task(
        report_gen_service.generate_report_from_definition, # This method needs to be callable by background task.
        def_id=definition_id,                               # It should not depend on FastAPI request scope.
        params=parameters,
        output_format=output_format.upper(),
        generated_by_user_id=current_user.id,
        username=current_user.username,
        # Pass the log_entry_id to the background task to update it, instead of the object itself.
        # The background task will then fetch the log entry using its ID.
        # This is a conceptual change if generate_report_from_definition is refactored for true async.
        # For now, the service updates the log entry passed to it.
    )

    return log_entry # Return the initial log entry (status PENDING)

@exec_logs_router.get("/generated-logs/{log_id}", response_model=schemas.GeneratedReportLogResponse)
async def get_generated_report_log_endpoint(log_id: int, db: Session = Depends(get_db)):
    log_entry = generated_report_log_service.get_log_by_id(db, log_id)
    if not log_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated Report Log not found")

    # Augment with report_definition_code if available
    response_data = schemas.GeneratedReportLogResponse.from_orm(log_entry).dict()
    if log_entry.report_definition:
        response_data["report_definition_code"] = log_entry.report_definition.report_code

    return response_data


@exec_logs_router.get("/generated-logs/", response_model=schemas.PaginatedGeneratedReportLogResponse)
async def list_generated_report_logs_endpoint(
    user_id: Optional[int] = None, # Filter by user who generated it
    definition_id: Optional[int] = None, # Filter by report definition
    skip: int = 0, limit: int = 20,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser) # For access control
):
    # If not superuser, restrict to user's own reports unless specific permissions allow broader view
    if not current_user.is_superuser and user_id != current_user.id:
        user_id = current_user.id # Force filter to current user's reports

    logs, total = generated_report_log_service.get_logs(db, user_id=user_id, definition_id=definition_id, skip=skip, limit=limit)

    # Augment with report_definition_code
    augmented_logs = []
    for log in logs:
        log_data = schemas.GeneratedReportLogResponse.from_orm(log).dict()
        if log.report_definition:
            log_data["report_definition_code"] = log.report_definition.report_code
        augmented_logs.append(log_data)

    return {"items": augmented_logs, "total": total, "page": (skip // limit) + 1, "size": limit}

# Conceptual: Endpoint to download a generated report file
# @exec_logs_router.get("/generated-logs/{log_id}/download")
# async def download_generated_report_file(log_id: int, db: Session = Depends(get_db), current_user: CoreUser = Depends(get_current_active_superuser)):
#     log_entry = generated_report_log_service.get_log_by_id(db, log_id)
#     if not log_entry or log_entry.status != models.ReportStatusEnum.SUCCESS or not log_entry.file_path_or_link:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found or not successfully generated.")
#     # Add permission check: current_user can access this report log_entry.generated_by_user_id
#     # In a real app, return FileResponse(log_entry.file_path_or_link, filename=log_entry.file_name)
#     # Or redirect to an S3 presigned URL.
#     return {"message": "Conceptual download", "file_path": log_entry.file_path_or_link, "file_name": log_entry.file_name}


# --- ScheduledReport Endpoints ---
schedules_router = APIRouter(prefix="/schedules", tags=["Scheduled Reports"])

@schedules_router.post("/", response_model=schemas.ScheduledReportResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_report_endpoint(
    sched_in: schemas.ScheduledReportCreate,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    return scheduled_report_service.create_schedule(
        db, sched_in=sched_in, user_id=current_user.id, username=current_user.username
    )

@schedules_router.get("/", response_model=schemas.PaginatedScheduledReportResponse)
async def list_scheduled_reports_endpoint(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    schedules, total = scheduled_report_service.get_schedules(db, skip=skip, limit=limit)
    return {"items": schedules, "total": total, "page": (skip // limit) + 1, "size": limit}

@schedules_router.get("/{schedule_id}", response_model=schemas.ScheduledReportResponse)
async def read_scheduled_report_endpoint(schedule_id: int, db: Session = Depends(get_db)):
    db_sched = scheduled_report_service.get_schedule_by_id(db, schedule_id)
    if not db_sched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled Report not found")
    return db_sched

@schedules_router.put("/{schedule_id}", response_model=schemas.ScheduledReportResponse)
async def update_scheduled_report_endpoint(
    schedule_id: int,
    sched_upd: schemas.ScheduledReportUpdate,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    updated_sched = scheduled_report_service.update_schedule(
        db, sched_id=schedule_id, sched_upd=sched_upd, username=current_user.username
    )
    if not updated_sched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled Report not found")
    return updated_sched

@schedules_router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_report_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    if not scheduled_report_service.delete_schedule(db, sched_id=schedule_id, username=current_user.username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled Report not found")
    return None

# --- DashboardLayout Endpoints ---
dashboards_router = APIRouter(prefix="/dashboards", tags=["Dashboard Layouts"])

@dashboards_router.post("/", response_model=schemas.DashboardLayoutResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard_layout_endpoint(
    layout_in: schemas.DashboardLayoutCreate,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    return dashboard_layout_service.create_layout(
        db, layout_in=layout_in, user_id=current_user.id, username=current_user.username
    )

@dashboards_router.get("/", response_model=List[schemas.DashboardLayoutResponse]) # Paginated if many per user
async def list_user_dashboard_layouts_endpoint(
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    return dashboard_layout_service.get_layouts_for_user(db, user_id=current_user.id)

@dashboards_router.get("/default", response_model=schemas.DashboardLayoutResponse)
async def get_default_dashboard_layout_endpoint(
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    default_layout = dashboard_layout_service.get_default_layout_for_user(db, user_id=current_user.id)
    if not default_layout: # Create a very basic one if none exists? Or 404.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No default dashboard layout found for user.")
    return default_layout


@dashboards_router.get("/{dashboard_id}", response_model=schemas.DashboardLayoutResponse)
async def read_dashboard_layout_endpoint(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    # Service method ensures user owns the dashboard
    db_layout = dashboard_layout_service.get_layout_by_id(db, layout_id=dashboard_id, user_id=current_user.id)
    if not db_layout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard Layout not found or not accessible.")
    return db_layout

@dashboards_router.put("/{dashboard_id}", response_model=schemas.DashboardLayoutResponse)
async def update_dashboard_layout_endpoint(
    dashboard_id: int,
    layout_upd: schemas.DashboardLayoutUpdate,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    updated_layout = dashboard_layout_service.update_layout(
        db, layout_id=dashboard_id, layout_upd=layout_upd, user_id=current_user.id, username=current_user.username
    )
    if not updated_layout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard Layout not found or not accessible.")
    return updated_layout

@dashboards_router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard_layout_endpoint(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: CoreUser = Depends(get_current_active_superuser)
):
    if not dashboard_layout_service.delete_layout(db, layout_id=dashboard_id, user_id=current_user.id, username=current_user.username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard Layout not found or not accessible.")
    return None

# Include all sub-routers into the main reports_analytics_api_router
reports_api_router.include_router(defs_router)
reports_api_router.include_router(exec_logs_router)
reports_api_router.include_router(schedules_router)
reports_api_router.include_router(dashboards_router)

# The main app would then do:
# from weezy_cbs.reports_analytics.api import reports_api_router
# app.include_router(reports_api_router)
