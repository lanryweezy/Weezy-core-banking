# API Endpoints for Fees, Charges & Commission Engine
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_admin_user, get_current_active_system_user

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_admin_user_placeholder(): return {"id": "fee_admin", "role": "admin"}
get_current_active_admin_user = get_current_active_admin_user_placeholder
def get_current_active_system_user_placeholder(): return {"id": "SYSTEM_FEE_PROCESSOR", "role": "system"}
get_current_active_system_user = get_current_active_system_user_placeholder

router = APIRouter(
    prefix="/fees-engine",
    tags=["Fees, Charges & Commissions"],
    responses={404: {"description": "Not found"}},
)

# --- Fee Configuration Endpoints (Admin) ---
@router.post("/configs", response_model=schemas.FeeConfigResponse, status_code=status.HTTP_201_CREATED)
def create_fee_configuration(
    fee_config_in: schemas.FeeConfigCreateRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """Create a new fee, charge, or commission configuration. (Admin operation)"""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    admin_id_str = str(current_admin.get("id"))
    try:
        return services.create_fee_config(db, fee_config_in, created_by_user_id=admin_id_str)
    except services.InvalidOperationException as e: # Catches duplicate fee_code
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.NotFoundException as e: # E.g. if GL codes are validated and not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create fee config: {str(e)}")

@router.get("/configs/{fee_code}", response_model=schemas.FeeConfigResponse)
def get_fee_configuration_by_code(fee_code: str, db: Session = Depends(get_db)):
    """Get details of a specific fee configuration by its code."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    fee_config = services.get_fee_config_by_code(db, fee_code)
    if not fee_config:
        raise HTTPException(status_code=404, detail=f"Fee configuration with code '{fee_code}' not found.")
    return fee_config

@router.get("/configs", response_model=schemas.PaginatedFeeConfigResponse)
def list_fee_configurations(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all fee configurations."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    items = services.list_fee_configs(db, skip, limit)
    # total = db.query(func.count(models.FeeConfig.id)).scalar_one_or_none() or 0 # Requires real DB
    total = len(items) if items else 0 # Mock total
    return schemas.PaginatedFeeConfigResponse(items=items, total=total, page=(skip//limit)+1, size=len(items))

# TODO: Add PUT /configs/{fee_config_id_or_code} for updates

# --- Fee Calculation Endpoint (Internal/System Call) ---
@router.post("/calculate-fees", response_model=schemas.FeeCalculationResponse)
def calculate_applicable_fees_for_context(
    context: schemas.FeeCalculationContext,
    db: Session = Depends(get_db),
    # auth: dict = Depends(get_current_active_system_user) # Or service principal
):
    """
    Calculate all applicable fees, taxes, and waivers for a given transaction/event context.
    Does not apply or charge the fees, only returns calculation details.
    (Typically called by other CBS modules before finalizing an operation)
    """
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    try:
        return services.calculate_fees_for_context(db, context)
    except services.FeeCalculationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Fee calculation error: {str(e)}")
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error during fee calculation: {str(e)}")

# --- Fee Application Endpoint (Internal/System Call) ---
@router.post("/apply-fees", response_model=List[schemas.AppliedFeeLogResponse], status_code=status.HTTP_201_CREATED)
def apply_and_log_calculated_fees(
    financial_transaction_id: str = Query(..., description="The master FT ID this fee is associated with"),
    # account_id_to_debit_fee: Optional[int] = Query(None, description="DB ID of the account to debit for fees, if applicable"),
    account_number_to_debit_fee: Optional[str] = Query(None, description="Account number to debit for fees, if applicable"), # Changed to account_number
    calculated_fees_payload: schemas.FeeCalculationResponse, # Output from /calculate-fees (or internal call)
    db: Session = Depends(get_db),
    current_system: dict = Depends(get_current_active_system_user)
):
    """
    Applies calculated fees by posting to ledger and logs the applied fees.
    This is typically called after fees have been calculated and confirmed. (System operation)
    """
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    system_user_id = str(current_system.get("id"))

    # Fetch account_id from account_number_to_debit_fee if provided
    acc_id_to_debit = None
    # if account_number_to_debit_fee:
    #     acc = services.alm_get_account_by_number(db, account_number_to_debit_fee) # Conceptual
    #     if not acc: raise HTTPException(status_code=404, detail=f"Account {account_number_to_debit_fee} for fee debit not found.")
    #     acc_id_to_debit = acc.id

    try:
        applied_logs = services.apply_and_log_fees(
            db,
            financial_transaction_id=financial_transaction_id,
            customer_id=calculated_fees_payload.context.customer_id, # Get customer from context
            account_id_to_debit_fee=acc_id_to_debit, # Pass the DB ID
            calculated_fees=calculated_fees_payload.applicable_fees,
            applied_by_user_id=system_user_id
        )
        return applied_logs
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.LedgerPostingException as e: # If ALM posting fails
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Ledger posting for fees failed: {str(e)}")
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error applying fees: {str(e)}")


# --- Applied Fee Log Endpoint (Reporting/Admin) ---
@router.get("/applied-fees", response_model=schemas.PaginatedAppliedFeeLogResponse)
def list_applied_fee_logs(
    financial_transaction_id: Optional[str] = Query(None, max_length=40),
    fee_code_applied: Optional[str] = Query(None, max_length=50),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """View logs of applied fees. (Admin/Reporting operation)"""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    # query = db.query(models.AppliedFeeLog)
    # if financial_transaction_id: query = query.filter(models.AppliedFeeLog.financial_transaction_id == financial_transaction_id)
    # if fee_code_applied: query = query.filter(models.AppliedFeeLog.fee_code_applied == fee_code_applied)
    # if start_date: query = query.filter(models.AppliedFeeLog.applied_at >= datetime.combine(start_date, datetime.min.time()))
    # if end_date: query = query.filter(models.AppliedFeeLog.applied_at <= datetime.combine(end_date, datetime.max.time()))
    # total = query.count()
    # items = query.order_by(models.AppliedFeeLog.applied_at.desc()).offset(skip).limit(limit).all()
    # Mock response
    items = []
    total = 0
    return schemas.PaginatedAppliedFeeLogResponse(items=items, total=total, page=(skip//limit)+1, size=len(items))

# TODO: Endpoints for FeeWaiverPromo CRUD (Admin)

# Import func for count queries if used
from sqlalchemy import func
# Import date for query param typing if not already at top
from datetime import date
