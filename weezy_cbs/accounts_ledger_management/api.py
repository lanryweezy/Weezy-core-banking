# API Endpoints for Accounts & Ledger Management using FastAPI
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import decimal

from . import services, schemas, models
# from weezy_cbs.database import get_db # Assuming a get_db dependency
# Placeholder get_db
def get_db_placeholder(): yield None
get_db = get_db_placeholder

router = APIRouter(
    prefix="/accounts-ledger",
    tags=["Accounts & Ledger Management"],
    responses={404: {"description": "Not found"}},
)

# --- Account Endpoints ---
@router.post("/accounts", response_model=schemas.AccountResponse, status_code=status.HTTP_201_CREATED)
def create_customer_account(
    account_in: schemas.AccountCreate, # customer_id is in the payload
    db: Session = Depends(get_db)
):
    """
    Create a new bank account for a customer.
    - `customer_id` must be provided in the request body.
    - `account_number` can be optionally provided; if not, it's auto-generated.
    - `initial_deposit_amount` if provided, will trigger an initial credit transaction.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        # Customer ID is part of AccountCreate schema
        customer = db.query(models.Customer).filter(models.Customer.id == account_in.customer_id).first() # Check if customer exists
        if not customer:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer with ID {account_in.customer_id} not found.")

        account = services.create_account(db=db, account_in=account_in, customer_id=account_in.customer_id)
        return account
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during account creation.")

@router.get("/accounts/{account_number}", response_model=schemas.AccountResponse)
def read_account_by_number(account_number: str, db: Session = Depends(get_db)):
    """
    Retrieve details of a specific account by its account number.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    account = services.get_account_by_number(db, account_number=account_number)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account {account_number} not found")
    return account

@router.get("/customers/{customer_id}/accounts", response_model=schemas.PaginatedAccountResponse)
def read_accounts_for_customer(
    customer_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Retrieve all accounts associated with a given customer ID.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # Check if customer exists (optional, depends on desired strictness)
    # customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    # if not customer:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer with ID {customer_id} not found.")

    accounts = services.get_accounts_by_customer_id(db, customer_id=customer_id, skip=skip, limit=limit)
    total_accounts = db.query(func.count(models.Account.id)).filter(models.Account.customer_id == customer_id).scalar_one()

    return schemas.PaginatedAccountResponse(
        items=[schemas.AccountResponse.from_orm(acc) for acc in accounts],
        total=total_accounts,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(accounts)
    )

@router.patch("/accounts/{account_number}/status", response_model=schemas.AccountResponse)
def update_account_status_endpoint(
    account_number: str,
    status_update: schemas.UpdateAccountStatusRequest,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_active_admin_user) # TODO: Add Auth for admin ops
):
    """
    Update the status of an account (e.g., ACTIVE, DORMANT, CLOSED).
    Requires appropriate permissions.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        account = services.get_account_by_number(db, account_number)
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account {account_number} not found.")
        updated_account = services.update_account_status(db, account_id=account.id, status_in=status_update)
        return updated_account
    except services.NotFoundException as e: # Should be caught by the check above mostly
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Balance Inquiry Endpoint ---
@router.get("/accounts/{account_number}/balance", response_model=schemas.AccountBalanceResponse)
def get_account_balance_endpoint(account_number: str, db: Session = Depends(get_db)):
    """
    Get the current ledger and available balance for a specific account.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    balance_info = services.get_account_balance(db, account_number=account_number)
    if balance_info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account {account_number} not found or error fetching balance.")
    return balance_info

# --- Ledger Transaction Endpoints ---
@router.post("/transactions/post", response_model=schemas.PostTransactionResponse)
def post_transaction_endpoint(
    transaction_details: schemas.PostTransactionRequest,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_active_system_user_or_teller) # TODO: Auth
):
    """
    Post a double-entry financial transaction.
    This can be between two customer accounts, or a customer account and a GL account.
    Requires `from_account_number` (or `from_gl_code`) and `to_account_number` (or `to_gl_code`).
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        response = services.post_double_entry_transaction(db, trans_details=transaction_details)
        return response
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InsufficientFundsException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) # Or 422 Unprocessable Entity
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Transaction posting failed: {str(e)}")

@router.get("/accounts/{account_number}/ledger", response_model=schemas.PaginatedLedgerEntryResponse)
def get_account_ledger_entries(
    account_number: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    start_date: Optional[datetime] = Query(None, description="ISO Format YYYY-MM-DDTHH:MM:SS"),
    end_date: Optional[datetime] = Query(None, description="ISO Format YYYY-MM-DDTHH:MM:SS"),
    db: Session = Depends(get_db)
):
    """
    Retrieve ledger entries (transaction history) for a specific account.
    Supports pagination and date range filtering.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    account = services.get_account_by_number(db, account_number)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account {account_number} not found.")

    entries = services.get_ledger_entries_for_account(db, account_id=account.id, skip=skip, limit=limit, start_date=start_date, end_date=end_date)
    total_entries = services.get_ledger_entry_count_for_account(db, account_id=account.id, start_date=start_date, end_date=end_date)

    return schemas.PaginatedLedgerEntryResponse(
        items=[schemas.LedgerEntryResponse.from_orm(entry) for entry in entries],
        total=total_entries,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(entries)
    )

# --- Lien Management Endpoints ---
@router.post("/accounts/{account_number}/lien/place", response_model=schemas.AccountResponse) # Or a specific LienResponse
def place_lien_on_account(
    account_number: str,
    lien_request: schemas.PlaceLienRequest,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_active_admin_user_or_system) # TODO: Auth
):
    """
    Place a lien on an account's funds.
    Reduces available balance. Requires authorization.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        updated_account = services.place_lien(db, account_number, lien_request)
        # Could return a more specific LienResponse if individual liens are tracked with IDs
        return updated_account
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (services.InsufficientFundsException, services.InvalidOperationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/accounts/{account_number}/lien/release", response_model=schemas.AccountResponse) # Or a specific LienResponse
def release_lien_from_account(
    account_number: str,
    release_request: schemas.ReleaseLienRequest,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_active_admin_user_or_system) # TODO: Auth
):
    """
    Release a previously placed lien on an account.
    Increases available balance. Requires authorization.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        updated_account = services.release_lien(db, account_number, release_request)
        return updated_account
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- Interest & Dormancy Endpoints (Typically for batch/internal processes) ---
@router.post("/batch/accrue-interest",
    # response_model=List[schemas.AccrueInterestResponse], # Or a summary response
    summary="Accrue Daily Interest (Batch)",
    include_in_schema=False # Or True if admins can trigger parts of it
)
def batch_accrue_daily_interest(
    # request: schemas.AccrueInterestRequest, # Might take a date or run for "yesterday"
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_active_system_user) # TODO: Auth
):
    """
    System endpoint to trigger daily interest accrual process for eligible accounts.
    This is a placeholder; a real batch job would manage this.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # Example: Iterate through all eligible accounts and call service
    # all_savings_accounts = db.query(models.Account).filter(models.Account.account_type == models.AccountTypeEnum.SAVINGS, models.Account.status == models.AccountStatusEnum.ACTIVE).all()
    # results = []
    # for acc in all_savings_accounts:
    #     # Determine interest rate for this account (e.g., from product config)
    #     rate = decimal.Decimal("2.5") # Example rate
    #     res = services.calculate_and_accrue_daily_interest_for_account(db, acc.id, datetime.utcnow() - timedelta(days=1), rate)
    #     if res: results.append(res)
    # return results
    return {"message": "Interest accrual process placeholder. Not fully implemented in API."}

@router.post("/batch/post-interest",
    # response_model=List[schemas.PostAccruedInterestResponse], # Or a summary
    summary="Post Accrued Interest (Batch)",
    include_in_schema=False
)
def batch_post_accrued_interest(
    # request: schemas.PostAccruedInterestRequest, # Might take a posting date
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_active_system_user) # TODO: Auth
):
    """
    System endpoint to post accumulated interest to accounts' ledger balances.
    Typically run monthly or quarterly. Placeholder.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # Example: Iterate accounts with accrued_interest > 0
    # ... call services.post_accumulated_interest_to_account ...
    return {"message": "Interest posting process placeholder. Not fully implemented in API."}

@router.post("/batch/process-dormancy",
    summary="Process Account Dormancy (Batch)",
    include_in_schema=False
)
def batch_process_dormancy_status(
    dormancy_days: int = Query(365, description="Days of inactivity to be marked DORMANT"), # CBN rules might differ
    inactivity_days: int = Query(180, description="Days of inactivity to be marked INACTIVE"),
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_active_system_user) # TODO: Auth
):
    """
    System endpoint to update account statuses to INACTIVE or DORMANT based on activity.
    Placeholder for a batch job.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # result = services.process_dormant_accounts(db, dormancy_days, inactivity_days)
    # return result
    return {"message": "Dormancy processing placeholder. Not fully implemented in API."}
