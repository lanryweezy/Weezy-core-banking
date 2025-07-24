# API Endpoints for Accounts & Ledger Management using FastAPI
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date # For date query params
import decimal

from . import services, schemas, models
from weezy_cbs.database import get_db

def get_current_user_placeholder(): return {"id": "user_SYSTEM", "username": "system"} # Mock
get_current_active_user = get_current_user_placeholder
def get_current_admin_user_placeholder(): return {"id": "admin_ACC", "username": "acc_admin"} # Mock
get_current_active_admin_user = get_current_admin_user_placeholder
def get_current_teller_or_system_user_placeholder(): return {"id": "teller01", "username": "teller_main"}
get_current_teller_or_system_user = get_current_teller_or_system_user_placeholder


router = APIRouter(
    prefix="/accounts-ledger", # Consistent prefix
    tags=["Accounts & Ledger Management"],
    responses={404: {"description": "Not found"}},
)

# --- Account Management Endpoints ---
@router.post("/accounts", response_model=schemas.AccountResponse, status_code=status.HTTP_201_CREATED)
def create_new_account_endpoint( # Renamed from create_customer_account for clarity
    account_in: schemas.AccountCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user) # User performing action (e.g. system, teller)
):
    """
    Create a new bank account for a customer, linked to a specific product code.
    - `customer_id` and `product_code` must be provided.
    - Account number (NUBAN) is system-generated.
    - `initial_deposit_amount` if provided, will trigger an initial credit transaction to the new account.
    """
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured for API.")
    user_id_str = str(current_user.get("id"))
    try:
        # Customer existence and product_code validity checks are now within the service
        account = services.create_account(db=db, account_in=account_in, created_by_user_id=user_id_str)
        return account
    except services.NotFoundException as e: # If customer or product_code not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e: # For other validation errors like min deposit
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

@router.get("/accounts/{account_number}", response_model=schemas.AccountResponse)
def read_account_by_account_number(account_number: str, db: Session = Depends(get_db)): # Renamed for clarity
    """Retrieve details of a specific account by its NUBAN account number."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    account = services.get_account_by_number(db, account_number=account_number)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account {account_number} not found")
    return account

@router.get("/customers/{customer_id}/accounts", response_model=schemas.PaginatedAccountResponse)
def read_all_accounts_for_customer( # Renamed for clarity
    customer_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
    # Auth: Ensure current user can view accounts for this customer_id
):
    """Retrieve all accounts associated with a given customer ID."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    # Customer existence check can be done here or assumed if accounts exist
    accounts = services.get_accounts_by_customer_id(db, customer_id=customer_id, skip=skip, limit=limit)
    # total_accounts = db.query(func.count(models.Account.id)).filter(models.Account.customer_id == customer_id).scalar_one_or_none() or 0 # Requires real DB
    total_accounts = len(accounts) if accounts else 0 # Mock total for now

    return schemas.PaginatedAccountResponse(
        items=[schemas.AccountResponse.from_orm(acc) for acc in accounts],
        total=total_accounts,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(accounts)
    )

@router.patch("/accounts/{account_number}/status", response_model=schemas.AccountResponse)
def update_account_status_admin_endpoint( # Renamed for clarity
    account_number: str,
    status_update_request: schemas.UpdateAccountStatusRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user) # Requires Admin permissions
):
    """
    Update the status of an account (e.g., ACTIVE, DORMANT, CLOSED, BLOCKED, PND).
    Requires appropriate admin permissions and reason for change.
    """
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    admin_id_str = str(current_admin.get("id"))
    try:
        updated_account = services.update_account_status(db, account_number, status_update_request, updated_by_user_id=admin_id_str)
        return updated_account
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e: # Catches zero balance rule for closure, missing reasons etc.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- Balance Inquiry Endpoint ---
@router.get("/accounts/{account_number}/balance", response_model=schemas.AccountBalanceResponse)
def get_current_account_balance_endpoint(account_number: str, db: Session = Depends(get_db)): # Renamed
    """Get the current ledger and available balance for a specific account."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    balance_info = services.get_account_balance(db, account_number=account_number)
    if balance_info is None: # Service returns None if account not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account {account_number} not found.")
    return balance_info

# --- Ledger Transaction Endpoints ---
# This endpoint is for internal systems to post already-vetted transactions.
# Not for direct end-user fund transfers typically. That would be in TransactionManagement.
@router.post("/ledger/internal-postings", response_model=schemas.InternalTransactionPostingResponse, status_code=status.HTTP_201_CREATED)
def post_internal_ledger_transaction( # Renamed from post_transaction_endpoint
    posting_request: schemas.InternalTransactionPostingRequest,
    db: Session = Depends(get_db),
    current_system_user: dict = Depends(get_current_teller_or_system_user) # System or authorized internal user
):
    """
    Post an internal financial transaction to the ledger. (System/Internal Use)
    This can be between two customer accounts, or involving GL accounts.
    Requires `financial_transaction_id` from a master transaction record.
    """
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    # user_id_str = str(current_system_user.get("id")) # For audit if needed by posting service
    try:
        # The service post_internal_transaction now handles the debit and credit legs.
        response = services.post_internal_transaction(db, request=posting_request)
        return response
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InsufficientFundsException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ledger posting failed: {str(e)}")

@router.get("/accounts/{account_number}/transaction-history", response_model=schemas.PaginatedLedgerEntryResponse) # Path changed
def get_account_transaction_history( # Renamed
    account_number: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200), # Default limit changed
    start_date: Optional[date] = Query(None, description="Format YYYY-MM-DD"), # Changed to date
    end_date: Optional[date] = Query(None, description="Format YYYY-MM-DD"),   # Changed to date
    db: Session = Depends(get_db)
    # Auth: Ensure current user can view this account's history
):
    """Retrieve ledger entries (transaction history) for a specific account."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    try:
        entries = services.get_transaction_history_for_account(db, account_number, skip, limit, start_date, end_date)
        # total_entries = db.query(func.count(models.LedgerEntry.id)).filter(models.LedgerEntry.account.has(account_number=account_number)).scalar_one_or_none() or 0 # Complex count
        # For mock/simplicity, if service doesn't give total:
        # This count needs to be accurate with filtering if using real DB.
        total_entries = len(entries) if entries else 0 # Placeholder for actual total count with filters.

        return schemas.PaginatedLedgerEntryResponse(
            items=[schemas.LedgerEntryResponse.from_orm(entry) for entry in entries],
            total=total_entries, # This should be the total count matching filters, not just len of current page
            page=(skip // limit) + 1 if limit > 0 else 1,
            size=len(entries)
        )
    except services.NotFoundException as e: # If account itself not found by service
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# --- Lien Management Endpoints (Admin/System) ---
@router.post("/accounts/{account_number}/liens", response_model=schemas.LienResponse) # Changed response
def place_new_lien_on_account( # Renamed
    account_number: str,
    lien_request: schemas.PlaceLienRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_admin_user) # Or specific risk/ops role
):
    """Place a lien on an account's funds. Reduces available balance. (Admin/System operation)"""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    user_id_str = str(current_user.get("id"))
    try:
        updated_account = services.place_lien_on_account(db, account_number, lien_request, placed_by_user_id=user_id_str)
        return schemas.LienResponse( # Return specific LienResponse
            account_number=updated_account.account_number,
            amount=lien_request.amount, # The amount of this specific lien placed
            reason=lien_request.reason,
            status="PLACED",
            remaining_lien_on_account=updated_account.lien_amount
        )
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (services.InsufficientFundsException, services.InvalidOperationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/accounts/{account_number}/liens", response_model=schemas.LienResponse) # Changed from POST to DELETE (or PATCH)
def release_part_or_all_lien_from_account( # Renamed
    account_number: str,
    release_request: schemas.ReleaseLienRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_admin_user)
):
    """Release a previously placed lien on an account. Increases available balance. (Admin/System operation)"""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    user_id_str = str(current_user.get("id"))
    try:
        updated_account = services.release_lien_on_account(db, account_number, release_request, released_by_user_id=user_id_str)
        return schemas.LienResponse(
            account_number=updated_account.account_number,
            amount=release_request.amount_to_release, # Amount that was requested to be released
            reason=release_request.reason,
            status="RELEASED", # Or PARTIALLY_RELEASED if logic supports it
            remaining_lien_on_account=updated_account.lien_amount
        )
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- Batch Process Triggers (Admin/System - often not public or highly secured) ---
# These are simplified; real batch triggers might take more specific params or be event-driven.

@router.post("/batch/accrue-daily-interest", response_model=List[schemas.AccountInterestAccrualResponse], summary="Trigger Daily Interest Accrual (Batch)", include_in_schema=False)
def trigger_daily_interest_accrual_batch(
    request_data: schemas.DailyInterestAccrualRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """System endpoint to trigger daily interest accrual for eligible accounts for a given calculation_date."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    # results = []
    # eligible_accounts = services.get_accounts_eligible_for_interest_accrual(db, request_data.calculation_date)
    # for acc_model in eligible_accounts:
    #     product_config = services.get_product_config_for_account(db, acc_model) # Get interest rate, min balance etc.
    #     if product_config and product_config.interest_rate_pa: # Simplified
    #         accrual_log = services.accrue_daily_interest_for_account(db, acc_model.id, request_data.calculation_date, product_config.interest_rate_pa, product_config.params)
    #         if accrual_log:
    #             results.append(schemas.AccountInterestAccrualResponse.from_orm(accrual_log)) # Map from log or return data
    # db.commit() # Commit all accruals for the batch
    # return results
    return [{"message": "Daily interest accrual batch trigger placeholder."}]


@router.post("/batch/post-monthly-interest", response_model=List[schemas.AccountInterestPostingResponse], summary="Trigger Monthly Interest Posting (Batch)", include_in_schema=False)
def trigger_monthly_interest_posting_batch(
    request_data: schemas.MonthlyInterestPostingRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """System endpoint to post accrued interest to accounts' ledger balances for a given posting_date."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    # results = []
    # accounts_with_accrued_interest = services.get_accounts_with_pending_interest_posting(db, request_data.posting_date)
    # ft_id_base = f"INT_POST_{request_data.posting_date.strftime('%Y%m')}"
    # for acc_model in accounts_with_accrued_interest:
    #     ledger_entry = services.post_accrued_interest_to_ledger(db, acc_model.id, request_data.posting_date, ft_id_base)
    #     if ledger_entry:
    #         # Construct response from ledger_entry and updated account
    #         results.append(...)
    # db.commit()
    return [{"message": "Monthly interest posting batch trigger placeholder."}]

@router.post("/batch/update-account-dormancy", summary="Process Account Dormancy Status (Batch)", include_in_schema=False)
def trigger_account_dormancy_update_batch(
    inactivity_days: int = Query(180, description="Days to mark account INACTIVE"),
    dormancy_days: int = Query(365*2, description="Days to mark account DORMANT (e.g. 2 years)"), # Example, CBN rules apply
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_active_admin_user)
):
    """System endpoint to update account statuses to INACTIVE or DORMANT based on last activity."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database not configured.")
    # count_inactive, count_dormant = services.run_batch_dormancy_processing(db, inactivity_days, dormancy_days)
    # return {"message": f"Dormancy processing complete. Marked inactive: {count_inactive}, Marked dormant: {count_dormant}."}
    return {"message": "Account dormancy update batch trigger placeholder."}

# Import func for count queries if used
from sqlalchemy import func
# Import date from datetime for date type hints
from datetime import date
