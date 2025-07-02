# API Endpoints for Compliance & Regulatory Reporting Module (mostly Admin/System)
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_admin_user, get_current_active_compliance_officer

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_admin_user_placeholder(): return {"id": "admin01", "role": "admin"}
get_current_active_admin_user = get_current_active_admin_user_placeholder
def get_current_active_compliance_officer_placeholder(): return {"id": "compliance01", "role": "compliance_officer"}
get_current_active_compliance_officer = get_current_active_compliance_officer_placeholder


router = APIRouter(
    prefix="/compliance-reporting",
    tags=["Compliance & Regulatory Reporting"],
    responses={404: {"description": "Not found"}},
)

# --- Regulatory Report Management Endpoints (Admin) ---
@router.post("/reports/generate-request", response_model=schemas.GeneratedReportLogResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_regulatory_report_generation(
    report_request: schemas.ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """
    Request the generation of a regulatory report for a specific period. (Admin operation)
    The report generation is an asynchronous process.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        report_log = services.create_report_log_entry(db, report_request, user_id=current_admin.get("id"))
        # Add generation to background tasks
        background_tasks.add_task(services.generate_report_file, db, report_log.id)
        return report_log
    except services.ReportGenerationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to request report generation: {str(e)}")

@router.get("/reports", response_model=schemas.PaginatedReportLogResponse)
def list_generated_reports(
    report_name: Optional[models.ReportNameEnum] = Query(None),
    status: Optional[models.ReportStatusEnum] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """List all generated (or pending) regulatory reports. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    reports = services.get_all_report_logs(db, skip, limit, report_name, status)
    total = db.query(func.count(models.GeneratedReportLog.id)) # Simplified count for example
    if report_name: total = total.filter(models.GeneratedReportLog.report_name == report_name)
    if status: total = total.filter(models.GeneratedReportLog.status == status)
    total = total.scalar_one_or_none() or 0

    return schemas.PaginatedReportLogResponse(items=reports, total=total, page=(skip//limit)+1, size=len(reports))


@router.get("/reports/{report_log_id}", response_model=schemas.GeneratedReportLogResponse)
def get_specific_report_log(report_log_id: int, db: Session = Depends(get_db), current_admin: dict = Depends(get_current_active_admin_user)):
    """Get details of a specific generated report log. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    report_log = services.get_report_log(db, report_log_id)
    if not report_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report log not found.")
    return report_log

@router.patch("/reports/{report_log_id}/status", response_model=schemas.GeneratedReportLogResponse)
def manually_update_report_status(
    report_log_id: int,
    status_update: schemas.ReportStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Manually update status or details of a report log (e.g., after manual submission). (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.update_report_log_status(db, report_log_id, status_update.new_status, status_update)
    except services.ReportGenerationException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) # If log not found

# --- AML Rule Management Endpoints (Admin) ---
@router.post("/aml-rules", response_model=schemas.AMLRuleResponse, status_code=status.HTTP_201_CREATED)
def create_new_aml_rule(
    rule_in: schemas.AMLRuleCreateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Create a new AML monitoring rule. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.create_aml_rule(db, rule_in)
    except services.InvalidOperationException as e: # e.g. rule code exists
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.put("/aml-rules/{rule_id}", response_model=schemas.AMLRuleResponse)
def update_existing_aml_rule(
    rule_id: int,
    rule_update: schemas.AMLRuleUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Update an existing AML monitoring rule. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.update_aml_rule(db, rule_id, rule_update)
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/aml-rules", response_model=List[schemas.AMLRuleResponse])
def list_aml_rules(active_only: bool = Query(True), db: Session = Depends(get_db), current_admin: dict = Depends(get_current_active_admin_user)):
    """List AML monitoring rules. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    return services.get_aml_rules(db, active_only)

# --- Suspicious Activity Management Endpoints (Compliance Officer/Admin) ---
@router.get("/suspicious-activities", response_model=schemas.PaginatedSuspiciousActivityLogResponse)
def list_suspicious_activities(
    status: Optional[str] = Query(None, description="Filter by status (e.g., OPEN, UNDER_INVESTIGATION)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_co: dict = Depends(get_current_active_compliance_officer)
):
    """List flagged suspicious activities. (Compliance Officer operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    query = db.query(models.SuspiciousActivityLog)
    if status:
        query = query.filter(models.SuspiciousActivityLog.status == status.upper())

    total = query.count()
    items = query.order_by(models.SuspiciousActivityLog.flagged_at.desc()).offset(skip).limit(limit).all()
    return schemas.PaginatedSuspiciousActivityLogResponse(items=items, total=total, page=(skip//limit)+1, size=len(items))

@router.patch("/suspicious-activities/{log_id}/status", response_model=schemas.SuspiciousActivityLogResponse)
def update_suspicious_activity_log_status(
    log_id: int,
    update_request: schemas.SuspiciousActivityStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_co: dict = Depends(get_current_active_compliance_officer)
):
    """Update the status and notes of a suspicious activity log. (Compliance Officer operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.update_suspicious_activity_status(db, log_id, update_request, user_id=current_co.get("id"))
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# --- Sanction Screening Endpoints ---
@router.post("/sanction-screening", response_model=schemas.SanctionScreeningResult)
def perform_on_demand_sanction_screen(
    screen_request: schemas.SanctionScreeningRequest,
    db: Session = Depends(get_db),
    current_co: dict = Depends(get_current_active_compliance_officer) # Or any authorized user
):
    """Perform an on-demand sanction screening for a name/entity. (Compliance/Authorized User operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.perform_sanction_screening(db, screen_request)
    except services.SanctionScreeningException as e: # If external service fails
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

@router.get("/sanction-screening/logs", response_model=schemas.PaginatedSanctionScreeningLogResponse)
def list_sanction_screening_logs(
    bvn: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    match_found: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_co: dict = Depends(get_current_active_compliance_officer)
):
    """List historical sanction screening logs. (Compliance Officer operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    logs = services.get_sanction_screening_logs(db, skip, limit, bvn, name, match_found)

    # Simplified total count for pagination example
    query = db.query(func.count(models.SanctionScreeningLog.id))
    if bvn: query = query.filter(models.SanctionScreeningLog.bvn_screened == bvn)
    if name: query = query.filter(models.SanctionScreeningLog.name_screened.ilike(f"%{name}%"))
    if match_found is not None: query = query.filter(models.SanctionScreeningLog.match_found == match_found)
    total = query.scalar_one_or_none() or 0

    return schemas.PaginatedSanctionScreeningLogResponse(items=logs, total=total, page=(skip//limit)+1, size=len(logs))

# Note: AML Transaction Monitoring and batch Sanction Screening are typically background processes,
# not directly triggered via API by users, but their results (SuspiciousActivityLog, SanctionScreeningLog) are queryable.
# Report submission to regulators might also be a mix of automated (if APIs exist) and manual processes.

# Import func for count queries if not already at top
from sqlalchemy import func
