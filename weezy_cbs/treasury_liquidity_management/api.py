# API Endpoints for Treasury & Liquidity Management (mostly Admin/System/Trader)
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_treasury_user, get_current_active_admin_user

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_treasury_user_placeholder(): return {"id": "trader01", "role": "treasury_trader"}
get_current_active_treasury_user = get_current_active_treasury_user_placeholder
def get_current_active_admin_user_placeholder(): return {"id": "admin01", "role": "admin"}
get_current_active_admin_user = get_current_active_admin_user_placeholder


router = APIRouter(
    prefix="/treasury-liquidity",
    tags=["Treasury & Liquidity Management"],
    responses={404: {"description": "Not found"}},
)

# --- Bank Cash Position Endpoints ---
@router.post("/cash-positions", response_model=schemas.BankCashPositionResponse, status_code=status.HTTP_201_CREATED)
def record_or_update_daily_cash_position(
    position_data: schemas.BankCashPositionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_admin_user) # Or a specific treasury ops role
):
    """
    Record or update the bank's daily cash position. (System/Admin operation)
    This is typically an end-of-day automated process, but API allows manual input/override.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.record_daily_cash_position(db, position_data)
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to record cash position: {str(e)}")

@router.get("/cash-positions/latest/{currency}", response_model=schemas.BankCashPositionResponse)
def get_latest_bank_cash_position(currency: models.CurrencyEnum, db: Session = Depends(get_db)):
    """Get the latest recorded daily cash position for a currency."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    position = services.get_latest_cash_position(db, currency)
    if not position:
        raise HTTPException(status_code=404, detail=f"No cash position found for currency {currency.value}")
    return position

@router.get("/cash-positions/{position_date}/{currency}", response_model=schemas.BankCashPositionResponse)
def get_specific_bank_cash_position(position_date: date, currency: models.CurrencyEnum, db: Session = Depends(get_db)):
    """Get cash position for a specific date and currency."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    position = services.get_cash_position(db, position_date, currency)
    if not position:
        raise HTTPException(status_code=404, detail=f"Cash position for {position_date} and {currency.value} not found")
    return position

# --- FX Transaction Endpoints (Treasury Trader) ---
@router.post("/fx-deals", response_model=schemas.FXTransactionResponse, status_code=status.HTTP_201_CREATED)
def create_new_fx_deal(
    fx_deal_in: schemas.FXTransactionCreateRequest,
    db: Session = Depends(get_db),
    current_trader: dict = Depends(get_current_active_treasury_user)
):
    """Create a new Foreign Exchange transaction/deal. (Treasury Trader operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.create_fx_transaction(db, fx_deal_in, user_id=current_trader.get("id"))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create FX deal: {str(e)}")

@router.get("/fx-deals/{deal_reference}", response_model=schemas.FXTransactionResponse)
def get_fx_deal_by_reference(deal_reference: str, db: Session = Depends(get_db)):
    """Get details of a specific FX deal by its reference."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    deal = services.get_fx_transaction(db, deal_reference=deal_reference)
    if not deal:
        raise HTTPException(status_code=404, detail="FX Deal not found.")
    return deal

@router.patch("/fx-deals/{deal_id}/status", response_model=schemas.FXTransactionResponse)
def update_fx_deal_status(
    deal_id: int,
    status_update: schemas.FXTransactionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_treasury_user) # Or treasury ops role
):
    """Update the status of an FX deal (e.g., mark as SETTLED). (Treasury Ops/System operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.update_fx_transaction_status(db, deal_id, status_update)
    except services.NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- Treasury Bill Investment Endpoints (Treasury Trader/Ops) ---
@router.post("/tbill-investments", response_model=schemas.TreasuryBillInvestmentResponse, status_code=status.HTTP_201_CREATED)
def record_new_tbill_investment(
    tbill_in: schemas.TreasuryBillInvestmentCreateRequest,
    db: Session = Depends(get_db),
    current_trader: dict = Depends(get_current_active_treasury_user)
):
    """Record a new investment in Treasury Bills. (Treasury Trader/Ops operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.create_tbill_investment(db, tbill_in)
    except services.CalculationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Calculation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to record T-Bill investment: {str(e)}")

@router.post("/tbill-investments/{investment_id}/mature", response_model=schemas.TreasuryBillInvestmentResponse)
def mark_tbill_as_matured(
    investment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_treasury_user) # Or treasury ops
):
    """Mark a T-Bill investment as matured. (Treasury Ops/System operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.mark_tbill_matured(db, investment_id)
    except services.NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- Interbank Placement Endpoints (Treasury Trader/Ops) ---
@router.post("/interbank-placements", response_model=schemas.InterbankPlacementResponse, status_code=status.HTTP_201_CREATED)
def create_new_interbank_placement(
    placement_in: schemas.InterbankPlacementCreateRequest,
    db: Session = Depends(get_db),
    current_trader: dict = Depends(get_current_active_treasury_user)
):
    """Record a new interbank lending or borrowing placement. (Treasury Trader/Ops operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # Add validation for placement_type if needed
    if placement_in.placement_type.upper() not in ["LENDING", "BORROWING"]:
        raise HTTPException(status_code=400, detail="Invalid placement_type. Must be LENDING or BORROWING.")
    try:
        return services.create_interbank_placement(db, placement_in)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create interbank placement: {str(e)}")

# --- Liquidity Forecast Endpoint (Treasury/ALM Role) ---
@router.post("/liquidity-forecast", response_model=schemas.LiquidityForecastResponse)
def generate_bank_liquidity_forecast(
    forecast_request: schemas.LiquidityForecastRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_treasury_user) # Or ALM specific role
):
    """
    Generate a liquidity gap forecast based on current positions and expected flows.
    (Treasury/ALM operation)
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        return services.generate_liquidity_forecast(db, forecast_request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate liquidity forecast: {str(e)}")

# Paginated listing endpoints for FX, T-Bills, Interbank Placements (similar structure)
@router.get("/fx-deals", response_model=schemas.PaginatedFXTransactionResponse)
def list_all_fx_deals(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
    # auth if needed
):
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    deals = db.query(models.FXTransaction).order_by(models.FXTransaction.trade_date.desc()).offset(skip).limit(limit).all()
    total = db.query(func.count(models.FXTransaction.id)).scalar_one_or_none() or 0
    return schemas.PaginatedFXTransactionResponse(items=deals, total=total, page=(skip//limit)+1, size=len(deals))

# Similar paginated GET endpoints can be added for:
# - /tbill-investments
# - /interbank-placements
# - /cbn-repo-operations

# TODO: Endpoints for CBN Repo Operations management.
# TODO: Endpoints for managing reconciliation with CBN settlement accounts (if any manual triggers/overviews).

# Import necessary modules if not already at top
from datetime import date
from sqlalchemy import func
