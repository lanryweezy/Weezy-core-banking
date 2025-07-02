# FastAPI app for Teller Agent
from fastapi import FastAPI, HTTPException, status, Body
from typing import Dict, Union # Union is used by FastAPI for request body with multiple types
import logging
from datetime import datetime

from .schemas import (
    TransactionRequest, DepositRequest, WithdrawalRequest, TransferRequest, BillPaymentRequest,
    TransactionResponse, BalanceResponse, TransactionStatus, CurrencyCode
)
# Placeholder for agent interaction logic (to be developed in agent.py)
# from .agent import process_teller_transaction_async, get_account_balance_async

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Store (Mock Database for Accounts and Balances) ---
# In a real application, this would interact with the core banking ledger.
MOCK_ACCOUNTS_DB: Dict[str, Dict[str, Any]] = {
    "1234509876": {"account_name": "Alice Wonderland", "balance": 150000.00, "currency": "NGN", "customer_id": "CUST-TELLER-001"},
    "0987654321": {"account_name": "Bob The Builder", "balance": 75000.50, "currency": "NGN", "customer_id": "CUST-TELLER-002"},
    "1122334455": {"account_name": "Charles Xavier", "balance": 1200000.00, "currency": "NGN", "customer_id": "CUST-TELLER-003"},
    "5566778899": {"account_name": "Diana Prince", "balance": 500.00, "currency": "USD", "customer_id": "CUST-TELLER-004"}, # USD Account
}

app = FastAPI(
    title="Teller Agent API",
    description="Handles deposits, withdrawals, transfers, bill payments, and balance checks.",
    version="0.1.0",
    contact={
        "name": "Core Banking AI Team",
        "email": "ai-devs@examplebank.ng",
    },
)

@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Teller Agent."""
    logger.info("Teller Agent root endpoint accessed.")
    return {"message": "Teller Agent is running. See /docs for API details."}

@app.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Transactions"])
async def handle_transaction(
    request: Union[DepositRequest, WithdrawalRequest, TransferRequest, BillPaymentRequest] = Body(..., discriminator='transaction_type')
):
    """
    Processes various financial transactions:
    - `deposit`: Credits funds to an account.
    - `withdrawal`: Debits funds from an account.
    - `transfer_intra_bank`: Moves funds between two accounts within this bank.
    - `transfer_inter_bank_nip`: Initiates an NIP transfer to an external bank.
    - `bill_payment`: Pays a bill from an account.

    The actual transaction processing might be asynchronous via an AI agent.
    This endpoint acknowledges the request and returns an initial status.
    """
    logger.info(f"Received transaction request: {request.request_id}, Type: {request.transaction_type}, Amount: {getattr(request, 'amount', 'N/A')}")

    # TODO: Integrate with agent.py: process_teller_transaction_async(request.model_dump())
    # For now, simulate direct processing and update mock DB.

    # --- Mock Processing Logic ---
    # This is highly simplified and synchronous for now.
    # A real agent would handle complex validation, limits, fees, OTP (if applicable), and ledger updates.

    if request.transaction_type == "deposit":
        if request.account_number not in MOCK_ACCOUNTS_DB:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account {request.account_number} not found.")
        MOCK_ACCOUNTS_DB[request.account_number]["balance"] += request.amount
        message = f"Deposit of {request.currency} {request.amount:.2f} to account {request.account_number} successful."
        tx_status: TransactionStatus = "Successful"

    elif request.transaction_type == "withdrawal":
        if request.account_number not in MOCK_ACCOUNTS_DB:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account {request.account_number} not found.")
        if MOCK_ACCOUNTS_DB[request.account_number]["balance"] < request.amount:
            message = f"Insufficient funds for withdrawal from account {request.account_number}."
            tx_status = "Failed"
            # No HTTPException here, return a failed transaction response
        else:
            MOCK_ACCOUNTS_DB[request.account_number]["balance"] -= request.amount
            message = f"Withdrawal of {request.currency} {request.amount:.2f} from account {request.account_number} successful."
            tx_status = "Successful"

    elif request.transaction_type in ["transfer_intra_bank", "transfer_inter_bank_nip"]:
        source_acc_num = request.source_account.account_number
        dest_acc_num = request.destination_account.account_number

        if source_acc_num not in MOCK_ACCOUNTS_DB:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source account {source_acc_num} not found.")

        if MOCK_ACCOUNTS_DB[source_acc_num]["balance"] < request.amount:
            message = f"Insufficient funds in source account {source_acc_num} for transfer."
            tx_status = "Failed"
        else:
            MOCK_ACCOUNTS_DB[source_acc_num]["balance"] -= request.amount
            if request.transaction_type == "transfer_intra_bank":
                if dest_acc_num not in MOCK_ACCOUNTS_DB:
                    # In real world, this might reverse the debit or hold funds in suspense
                    message = f"Destination account {dest_acc_num} not found for intra-bank transfer. Debit reversed (simulated)."
                    MOCK_ACCOUNTS_DB[source_acc_num]["balance"] += request.amount # Simulate reversal
                    tx_status = "Failed"
                else:
                    MOCK_ACCOUNTS_DB[dest_acc_num]["balance"] += request.amount
                    message = f"Intra-bank transfer of {request.currency} {request.amount:.2f} from {source_acc_num} to {dest_acc_num} successful."
                    tx_status = "Successful"
            else: # transfer_inter_bank_nip
                # Mock NIP processing - assume successful for now
                message = f"NIP transfer of {request.currency} {request.amount:.2f} from {source_acc_num} to {dest_acc_num} (Bank: {request.destination_account.bank_code}) initiated successfully."
                tx_status = "Successful" # Or "Processing" if it's truly async

    elif request.transaction_type == "bill_payment":
        if request.source_account_number not in MOCK_ACCOUNTS_DB:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source account {request.source_account_number} not found.")
        if MOCK_ACCOUNTS_DB[request.source_account_number]["balance"] < request.amount:
            message = f"Insufficient funds for bill payment from account {request.source_account_number}."
            tx_status = "Failed"
        else:
            MOCK_ACCOUNTS_DB[request.source_account_number]["balance"] -= request.amount
            message = f"Bill payment of {request.currency} {request.amount:.2f} for Biller ID {request.biller_id} (Customer: {request.customer_identifier}) successful."
            tx_status = "Successful"
    else:
        # Should not happen due to Pydantic validation of transaction_type literal
        logger.error(f"Unknown transaction type received: {request.transaction_type}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown transaction type.")

    logger.info(f"Transaction {request.request_id} result: {tx_status} - {message}")
    return TransactionResponse(
        request_id=request.request_id,
        status=tx_status,
        message=message
    )


@app.get("/accounts/{account_number}/balance", response_model=BalanceResponse, tags=["Accounts"])
async def get_account_balance(account_number: str):
    """
    Retrieves the current balance for a given account number.
    """
    logger.info(f"Balance inquiry for account: {account_number}")

    # TODO: Integrate with agent.py: get_account_balance_async(account_number)
    # For now, read directly from mock DB.

    account = MOCK_ACCOUNTS_DB.get(account_number)
    if not account:
        logger.warning(f"Account {account_number} not found for balance inquiry.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")

    # Ledger balance might be different from available in a real system (e.g., uncleared funds)
    # Here, we'll assume they are the same for simplicity of the mock.
    return BalanceResponse(
        account_number=account_number,
        account_name=account.get("account_name"),
        available_balance=account["balance"],
        ledger_balance=account["balance"], # Simplified
        currency=account.get("currency", "NGN"), # type: ignore
        last_updated_at=datetime.utcnow() # In real system, this would be actual ledger update time
    )

# --- Main block for Uvicorn ---
if __name__ == "__main__":
    logger.info("Teller Agent FastAPI application. To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.teller_agent.main:app --reload --port 8002`")
    pass
