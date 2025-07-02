# API Endpoints for Cards & Wallets Management using FastAPI
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_user

# Placeholder get_db and get_current_active_user
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_user_placeholder(): return {"id": 1, "username": "testuser", "customer_id": 101} # Mock user with customer_id
get_current_active_user = get_current_active_user_placeholder

router = APIRouter(
    prefix="/cards-wallets",
    tags=["Cards & Wallets Management"],
    responses={404: {"description": "Not found"}},
)

# --- Card Management Endpoints ---
@router.post("/cards/request", response_model=schemas.CardResponse, status_code=status.HTTP_201_CREATED)
def request_customer_card(
    card_request: schemas.CardCreateRequest,
    # account_id: int = Query(..., description="Primary bank account ID to link the card to"), # Or get from user's profile
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Request a new debit/prepaid card (Virtual or Physical) for the authenticated customer.
    Requires customer_id (from auth) and account_id to link.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = current_user.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not associated with a customer profile.")

    # Determine account_id, e.g., from user's primary account or a request param
    # For this example, let's assume a default or provided account_id.
    # This needs robust logic to select the correct account for the card.
    # For now, placeholder:
    linked_account_id = 1 # Replace with actual logic to get user's account ID

    try:
        card = services.request_new_card(db, card_request, customer_id, linked_account_id)
        return card
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/cards", response_model=schemas.PaginatedCardResponse)
def list_customer_cards(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    List all cards associated with the authenticated customer.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = current_user.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not associated with a customer profile.")

    cards = services.get_cards_for_customer(db, customer_id, skip=skip, limit=limit)
    total_count = db.query(func.count(models.Card.id)).filter(models.Card.customer_id == customer_id).scalar_one_or_none() or 0

    return schemas.PaginatedCardResponse(
        items=[schemas.CardResponse.from_orm(card) for card in cards],
        total=total_count,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(cards)
    )

@router.get("/cards/{card_id}", response_model=schemas.CardDetailResponse)
def get_card_details(card_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_active_user)):
    """Get details of a specific card owned by the authenticated customer."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    card = services.get_card_by_id(db, card_id)
    if not card or card.customer_id != current_user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found or access denied.")
    return card

@router.post("/cards/{card_id}/activate", response_model=schemas.CardResponse)
def activate_customer_card(
    card_id: int,
    activation_req: schemas.CardActivationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Activate a new or reissued card."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    card = services.get_card_by_id(db, card_id) # Initial fetch to check ownership
    if not card or card.customer_id != current_user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found or access denied.")
    try:
        return services.activate_card(db, card_id, activation_req)
    except services.NotFoundException: # Should be caught by above check
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/cards/{card_id}/set-pin", response_model=schemas.CardResponse)
def set_new_card_pin(
    card_id: int,
    pin_request: schemas.CardPinSetRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Set or change the PIN for a card."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    card = services.get_card_by_id(db, card_id)
    if not card or card.customer_id != current_user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found or access denied.")
    try:
        # In a real system, PIN change might require current PIN or other auth factors
        return services.set_card_pin(db, card_id, pin_request)
    except services.NotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.ExternalServiceException as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"PIN operation failed: {str(e)}")


@router.patch("/cards/{card_id}/status", response_model=schemas.CardResponse)
def update_customer_card_status(
    card_id: int,
    status_update: schemas.CardStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Update card status (e.g., temporarily block, report lost/stolen)."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    card = services.get_card_by_id(db, card_id)
    if not card or card.customer_id != current_user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found or access denied.")
    try:
        return services.update_card_status(db, card_id, status_update)
    except services.NotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Wallet Account Endpoints ---
@router.post("/wallets", response_model=schemas.WalletAccountResponse, status_code=status.HTTP_201_CREATED)
def create_new_wallet(
    wallet_req: schemas.WalletAccountCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new e-wallet account for the authenticated customer."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = current_user.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not associated with a customer profile.")
    try:
        return services.create_wallet_account(db, wallet_req, customer_id)
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/wallets", response_model=List[schemas.WalletAccountResponse])
def list_customer_wallets(db: Session = Depends(get_db), current_user: dict = Depends(get_current_active_user)):
    """List all wallet accounts for the authenticated customer."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = current_user.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not associated with a customer profile.")
    return services.get_wallet_accounts_for_customer(db, customer_id)

@router.get("/wallets/{wallet_external_id}", response_model=schemas.WalletAccountResponse)
def get_wallet_details(wallet_external_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_active_user)):
    """Get details of a specific wallet owned by the authenticated customer."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    wallet = services.get_wallet_account_by_external_id(db, wallet_external_id)
    if not wallet or wallet.customer_id != current_user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found or access denied.")
    return wallet

@router.post("/wallets/{wallet_external_id}/top-up", response_model=schemas.WalletAccountResponse) # Or a specific transaction response
def top_up_wallet(
    wallet_external_id: str,
    top_up_req: schemas.WalletTopUpRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Top-up (fund) a wallet account."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    wallet = services.get_wallet_account_by_external_id(db, wallet_external_id)
    if not wallet or wallet.customer_id != current_user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found or access denied.")
    try:
        return services.top_up_wallet_account(db, wallet.id, top_up_req)
    except services.NotFoundException: # Should be caught by above
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found.")
    except (services.InvalidOperationException, services.ExternalServiceException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/wallets/{wallet_external_id}/withdraw", response_model=schemas.WalletAccountResponse)
def withdraw_from_wallet(
    wallet_external_id: str,
    withdrawal_req: schemas.WalletWithdrawalRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Withdraw funds from a wallet to a bank account or other destination."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    wallet = services.get_wallet_account_by_external_id(db, wallet_external_id)
    if not wallet or wallet.customer_id != current_user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found or access denied.")
    try:
        return services.withdraw_from_wallet_account(db, wallet.id, withdrawal_req)
    except services.NotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found.")
    except (services.InsufficientFundsException, services.InvalidOperationException, services.ExternalServiceException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/wallets/p2p-transfer", response_model=List[schemas.WalletAccountResponse]) # Returns updated source and dest wallets
def transfer_between_wallets(
    p2p_req: schemas.WalletP2PTransferRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Transfer funds from the authenticated user's wallet to another user's wallet."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = current_user.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not associated with a customer profile.")

    # Find the source wallet for the current user (assuming one NGN wallet for simplicity)
    source_wallet = db.query(models.WalletAccount).filter(
        models.WalletAccount.customer_id == customer_id,
        models.WalletAccount.currency == p2p_req.currency # Match currency
    ).first()
    if not source_wallet:
        raise HTTPException(status_code=404, detail=f"Source {p2p_req.currency.value} wallet not found for current user.")

    try:
        updated_source, updated_dest = services.p2p_wallet_transfer(db, p2p_req, source_wallet.id)
        return [updated_source, updated_dest]
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (services.InsufficientFundsException, services.InvalidOperationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- Cardless Withdrawal Endpoints ---
@router.post("/cardless-withdrawal/generate-token", response_model=schemas.CardlessWithdrawalTokenResponse)
def generate_cardless_token(
    request_in: schemas.CardlessWithdrawalRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate a token for cardless withdrawal from the user's primary account."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = current_user.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not associated with a customer profile.")

    # Assume a primary bank account ID for the customer
    # This needs proper logic to determine which account to debit
    primary_account_id_placeholder = 1 # Replace with actual logic

    try:
        token_model = services.generate_cardless_withdrawal_token(db, request_in, primary_account_id_placeholder)
        return schemas.CardlessWithdrawalTokenResponse.from_orm(token_model)
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (services.InsufficientFundsException, services.InvalidOperationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/cardless-withdrawal/redeem", response_model=schemas.CardlessWithdrawalRedemptionResponse)
def redeem_cardless_token(
    redemption_req: schemas.CardlessWithdrawalRedemptionRequest,
    db: Session = Depends(get_db)
    # This endpoint would typically be called by an ATM/Agent, not a customer directly.
    # Auth would be system-to-system (e.g. API key for ATM network).
):
    """
    Redeem a cardless withdrawal token (e.g., at an ATM).
    (System/ATM initiated endpoint)
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    status_message = services.redeem_cardless_withdrawal_token(db, redemption_req)

    # This is simplified; actual response would depend on ATM protocol
    if status_message == "SUCCESSFUL":
        token_info = db.query(models.CardlessWithdrawalToken).filter(models.CardlessWithdrawalToken.token == redemption_req.token).first()
        return schemas.CardlessWithdrawalRedemptionResponse(
            status=status_message,
            amount_dispensed=token_info.amount if token_info else None, # Get amount from token
            transaction_reference="CW_TXN_" + redemption_req.token # Example ref
        )
    else:
        return schemas.CardlessWithdrawalRedemptionResponse(status=status_message)


# --- Transaction History Endpoints ---
@router.get("/wallets/{wallet_external_id}/transactions", response_model=schemas.PaginatedWalletTransactionResponse)
def get_wallet_transaction_history(
    wallet_external_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    wallet = services.get_wallet_account_by_external_id(db, wallet_external_id)
    if not wallet or wallet.customer_id != current_user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found or access denied.")

    transactions = services.get_wallet_transactions(db, wallet.id, skip=skip, limit=limit)
    total_count = db.query(func.count(models.WalletTransaction.id)).filter(models.WalletTransaction.wallet_account_id == wallet.id).scalar_one_or_none() or 0

    return schemas.PaginatedWalletTransactionResponse(
        items=[schemas.WalletTransactionResponse.from_orm(tx) for tx in transactions],
        total=total_count,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(transactions)
    )

@router.get("/cards/{card_id}/transactions", response_model=schemas.PaginatedCardTransactionResponse)
def get_card_transaction_history(
    card_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    card = services.get_card_by_id(db, card_id)
    if not card or card.customer_id != current_user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found or access denied.")

    transactions = services.get_card_transactions_log(db, card_id, skip=skip, limit=limit)
    total_count = db.query(func.count(models.CardTransaction.id)).filter(models.CardTransaction.card_id == card_id).scalar_one_or_none() or 0

    return schemas.PaginatedCardTransactionResponse(
        items=[schemas.CardTransactionResponse.from_orm(tx) for tx in transactions],
        total=total_count,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(transactions)
    )

# TODO: Endpoints for specific card processor callbacks (e.g., transaction notifications from Interswitch).
# These would be webhook-style endpoints.
