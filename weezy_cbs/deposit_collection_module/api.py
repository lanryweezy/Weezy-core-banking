# API Endpoints for Deposit & Collection Module using FastAPI
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_teller_or_agent, get_current_active_admin_user

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_teller_or_agent_placeholder(): return {"id": "teller01", "branch_code": "B001", "role": "teller"}
get_current_active_teller_or_agent = get_current_active_teller_or_agent_placeholder
def get_current_active_admin_user_placeholder(): return {"id": "admin01", "role": "admin"}
get_current_active_admin_user = get_current_active_admin_user_placeholder

router = APIRouter(
    prefix="/deposits-collections",
    tags=["Deposits & Collections"],
    responses={404: {"description": "Not found"}},
)

# --- Cash Deposit Endpoints ---
@router.post("/cash-deposits", response_model=schemas.CashDepositResponse, status_code=status.HTTP_201_CREATED)
def log_new_cash_deposit(
    deposit_in: schemas.CashDepositCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_teller_or_agent) # Teller or Agent context
):
    """
    Log a new cash deposit made at a branch or by an agent.
    Requires teller/agent authentication.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    teller_id = current_user.get("id")
    branch_code = current_user.get("branch_code") # Assuming agent also has a branch/zone code

    try:
        deposit_log = services.log_cash_deposit(db, deposit_in, teller_id, branch_code)
        return deposit_log
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to log cash deposit: {str(e)}")

@router.get("/cash-deposits/account/{account_number}", response_model=schemas.PaginatedCashDepositResponse)
def get_cash_deposits_for_account(
    account_number: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
    # auth: User = Depends(get_current_user_with_account_access_permission_or_admin)
):
    """Get cash deposit history for a specific account."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    items = services.get_paginated_deposits(db, models.CashDepositLog, skip, limit, account_number=account_number)
    total = services.count_deposits(db, models.CashDepositLog, account_number=account_number)
    return schemas.PaginatedCashDepositResponse(items=items, total=total, page=(skip // limit) + 1, size=len(items))


# --- Cheque Deposit Endpoints ---
@router.post("/cheque-deposits", response_model=schemas.ChequeDepositResponse, status_code=status.HTTP_201_CREATED)
def log_new_cheque_deposit(
    deposit_in: schemas.ChequeDepositCreateRequest,
    # cheque_image_front: Optional[UploadFile] = File(None), # For actual image upload
    # cheque_image_back: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_teller_or_agent)
):
    """
    Log a new cheque deposit. Images can be uploaded separately or URLs provided.
    Requires teller/agent authentication.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    teller_id = current_user.get("id")
    branch_code = current_user.get("branch_code")

    # Handle file uploads here if `UploadFile` is used
    # e.g., save files to S3/local storage, get URLs
    # deposit_in.cheque_image_front_url = await save_uploaded_file(cheque_image_front) if cheque_image_front else None

    try:
        cheque_log = services.log_cheque_deposit(db, deposit_in, teller_id, branch_code)
        return cheque_log
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.patch("/cheque-deposits/{log_id}/status", response_model=schemas.ChequeDepositResponse)
def update_cheque_status(
    log_id: int,
    status_update: schemas.ChequeStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_admin_user) # Or a clearing operations user
):
    """
    Update the status of a cheque deposit after clearing process. (Internal/Admin operation)
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.update_cheque_deposit_status(db, log_id, status_update)
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/cheque-deposits/account/{account_number}", response_model=schemas.PaginatedChequeDepositResponse)
def get_cheque_deposits_for_account(
    account_number: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get cheque deposit history for a specific account."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    items = services.get_paginated_deposits(db, models.ChequeDepositLog, skip, limit, account_number=account_number)
    total = services.count_deposits(db, models.ChequeDepositLog, account_number=account_number)
    return schemas.PaginatedChequeDepositResponse(items=items, total=total, page=(skip // limit) + 1, size=len(items))


# --- Collection Service Management Endpoints (Admin) ---
@router.post("/collection-services", response_model=schemas.CollectionServiceResponse, status_code=status.HTTP_201_CREATED)
def create_new_collection_service_config(
    service_in: schemas.CollectionServiceCreateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Configure a new service for which the bank will collect payments. (Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.create_collection_service(db, service_in)
    except services.NotFoundException as e: # e.g. if merchant_account_id is invalid
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/collection-services", response_model=List[schemas.CollectionServiceResponse])
def list_all_collection_services(db: Session = Depends(get_db)):
    """List all configured collection services."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # return db.query(models.CollectionService).filter(models.CollectionService.is_active == True).all()
    # Mock response:
    return [
        schemas.CollectionServiceResponse(id=1, service_name="School Fees A", merchant_id_external="SCH001", is_active=True),
        schemas.CollectionServiceResponse(id=2, service_name="Utility Bill X", merchant_id_external="UTIL00X", is_active=True),
    ]

# --- Collection Payment Logging Endpoints ---
@router.post("/collection-services/{service_id}/payments", response_model=schemas.CollectionPaymentResponse, status_code=status.HTTP_201_CREATED)
def log_new_collection_payment(
    service_id: int,
    payment_in: schemas.CollectionPaymentCreateRequest,
    db: Session = Depends(get_db)
    # current_user: dict = Depends(get_current_active_teller_or_agent_or_system) # Depending on channel
):
    """Log a payment made for a configured collection service."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.log_collection_payment(db, payment_in, service_id)
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e: # e.g. if customer validation fails
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/collection-services/{service_id}/payments", response_model=schemas.PaginatedCollectionPaymentResponse)
def get_payments_for_collection_service(
    service_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    customer_identifier: Optional[str] = Query(None, description="Filter by customer ID at merchant"),
    db: Session = Depends(get_db)
    # auth: User = Depends(get_current_admin_or_merchant_user_for_service_id)
):
    """Get payment history for a specific collection service."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    query = db.query(models.CollectionPaymentLog).filter(models.CollectionPaymentLog.collection_service_id == service_id)
    if customer_identifier:
        query = query.filter(models.CollectionPaymentLog.customer_identifier_at_merchant == customer_identifier)

    total = query.count()
    items = query.order_by(models.CollectionPaymentLog.payment_date.desc()).offset(skip).limit(limit).all()
    return schemas.PaginatedCollectionPaymentResponse(items=items, total=total, page=(skip//limit)+1, size=len(items))

# --- POS Reconciliation Endpoints (Admin/Internal) ---
@router.post("/pos-reconciliation/batches", response_model=schemas.POSReconciliationBatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_pos_settlement_file_for_reconciliation(
    batch_date: date = Query(..., description="Date for which the reconciliation batch applies"),
    source_file: Optional[UploadFile] = File(None, description="Settlement file from POS acquirer/switch"),
    # Or allow providing file name if file is placed in a shared location
    source_file_name_param: Optional[str] = Query(None, alias="sourceFileName"),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """
    Initiate a POS reconciliation batch by providing a settlement file. (Admin/System operation)
    The file is processed asynchronously.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")

    file_name_to_log = source_file.filename if source_file else source_file_name_param
    if not file_name_to_log:
        raise HTTPException(status_code=400, detail="Either source_file upload or sourceFileName query parameter must be provided.")

    batch_create_schema = schemas.POSReconciliationBatchCreate(batch_date=batch_date, source_file_name=file_name_to_log)
    try:
        batch = services.initiate_pos_reconciliation_batch(db, batch_create_schema)

        if source_file:
            # In a real app, save source_file to a processing location (e.g. S3, local disk)
            # file_path = await save_uploaded_file_async(source_file, f"pos_recon_{batch.id}_{source_file.filename}")
            # Trigger async processing:
            # background_tasks.add_task(services.process_pos_reconciliation_file, db, batch.id, file_path)
            pass # Placeholder for file saving & async task trigger
        elif source_file_name_param:
            # Assume file is already at a known location based on source_file_name_param
            # background_tasks.add_task(services.process_pos_reconciliation_file_from_path, db, batch.id, source_file_name_param)
            pass

        return batch # Returns initial batch record; actual processing is async
    except services.InvalidOperationException as e: # e.g. batch already exists
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/pos-reconciliation/batches/{batch_id}", response_model=schemas.POSReconciliationBatchResponse)
def get_pos_reconciliation_batch_status(batch_id: int, db: Session = Depends(get_db)):
    """Get the status and summary of a POS reconciliation batch."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    batch = db.query(models.POSReconciliationBatch).filter(models.POSReconciliationBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="POS Reconciliation Batch not found.")
    return batch

@router.get("/pos-reconciliation/batches/{batch_id}/discrepancies", response_model=List[schemas.POSReconciliationDiscrepancyResponse])
def get_discrepancies_for_pos_batch(
    batch_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get detailed discrepancies for a completed POS reconciliation batch."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # Check batch exists
    batch = db.query(models.POSReconciliationBatch.id).filter(models.POSReconciliationBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="POS Reconciliation Batch not found.")

    discrepancies = db.query(models.POSReconciliationDiscrepancy).filter(
        models.POSReconciliationDiscrepancy.batch_id == batch_id
    ).offset(skip).limit(limit).all()
    return discrepancies

# Import necessary modules if not already imported at the top
from datetime import date # For query param typing
from sqlalchemy import func # For count queries if needed
