# FastAPI app for Teller Agent
from fastapi import FastAPI, HTTPException, status, Body, BackgroundTasks
from typing import Dict, Union, Any
import logging
from datetime import datetime

from .schemas import (
    TransactionRequest, DepositRequest, WithdrawalRequest, TransferRequest, BillPaymentRequest,
    TransactionResponse, BalanceResponse, TransactionStatus, CurrencyCode
)
# Import agent interaction logic
from .agent import process_teller_transaction_async, get_account_balance_async

# --- Logging Setup ---
logger = logging.getLogger(__name__)
# Ensure basicConfig is called only once, typically at a higher level or managed by Uvicorn
if not logger.handlers: # Avoid adding multiple handlers if uvicorn already configured root logger
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- In-memory Store (Mock Database for Accounts and Balances) ---
MOCK_ACCOUNTS_DB: Dict[str, Dict[str, Any]] = {
    "1234509876": {"account_name": "Alice Wonderland", "balance": 150000.00, "currency": "NGN", "customer_id": "CUST-TELLER-001", "min_balance": 0},
    "0987654321": {"account_name": "Bob The Builder", "balance": 75000.50, "currency": "NGN", "customer_id": "CUST-TELLER-002", "min_balance": 0},
    "1122334455": {"account_name": "Charles Xavier", "balance": 1200000.00, "currency": "NGN", "customer_id": "CUST-TELLER-003", "min_balance": 1000},
    "5566778899": {"account_name": "Diana Prince", "balance": 500.00, "currency": "USD", "customer_id": "CUST-TELLER-004", "min_balance": 10},
}

app = FastAPI(
    title="Teller Agent API (CrewAI Integrated - Mocked)",
    description="Handles deposits, withdrawals, transfers, bill payments, and balance checks via an AI Agent.",
    version="0.1.2", # Incremented version
    contact={
        "name": "Core Banking AI Team",
        "email": "ai-devs@examplebank.ng",
    },
)

@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Teller Agent."""
    logger.info("Teller Agent root endpoint accessed.")
    return {"message": "Teller Agent is running. CrewAI integration active (mocked execution). See /docs for API details."}

@app.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_200_OK, tags=["Transactions"])
async def handle_transaction(
    request: Union[DepositRequest, WithdrawalRequest, TransferRequest, BillPaymentRequest] = Body(..., discriminator='transaction_type')
):
    """
    Processes various financial transactions via the Teller AI Agent.
    The agent handles OTP (if applicable) and core banking interactions.
    This endpoint AWAITS the (mocked) agent's processing before responding.
    """
    logger.info(f"API: Received transaction request: {request.request_id}, Type: {request.transaction_type}, Amount: {getattr(request, 'amount', 'N/A')}")

    agent_result = await process_teller_transaction_async(request.model_dump(mode='json')) # mode='json' for Pydantic v2 if sending complex types

    logger.info(f"API: Agent processing result for {request.request_id}: {agent_result}")

    # The agent_result is expected to have: "request_id", "status" (Successful/Failed), "message", "transaction_id" (optional), "additional_details" (raw tool output)

    # Update MOCK_ACCOUNTS_DB based on successful agent execution reported by the agent
    # The agent's `additional_details` should contain the tool's output which might have `new_balance_preview` etc.
    if agent_result.get("status") == "Successful":
        try:
            # Extract details from the original request for DB update, as agent confirms *feasibility*
            # The actual amounts and accounts are from the client's request.
            # The agent's `additional_details` (tool output) might have `new_balance_preview` which can be used for verification but not directly for update here.

            if request.transaction_type == "deposit":
                acc_num = request.account_number
                amount = request.amount
                if acc_num in MOCK_ACCOUNTS_DB:
                    MOCK_ACCOUNTS_DB[acc_num]["balance"] += amount
                else: # Simulate account creation on first deposit if tool logic supports it (tool mock does)
                    MOCK_ACCOUNTS_DB[acc_num] = {"balance": amount, "currency": request.currency, "min_balance": 0, "account_name": "New Account (Mock)"}
                logger.info(f"API: Mock DB updated for deposit to {acc_num}. New balance: {MOCK_ACCOUNTS_DB[acc_num]['balance']}")

            elif request.transaction_type == "withdrawal":
                acc_num = request.account_number
                amount = request.amount
                if acc_num in MOCK_ACCOUNTS_DB: # Should always be true if agent said success
                    MOCK_ACCOUNTS_DB[acc_num]["balance"] -= amount
                    logger.info(f"API: Mock DB updated for withdrawal from {acc_num}. New balance: {MOCK_ACCOUNTS_DB[acc_num]['balance']}")

            elif request.transaction_type == "bill_payment": # Assuming it was processed as a withdrawal by the tool
                acc_num = request.source_account_number
                amount = request.amount
                if acc_num in MOCK_ACCOUNTS_DB:
                    MOCK_ACCOUNTS_DB[acc_num]["balance"] -= amount
                    logger.info(f"API: Mock DB updated for bill_payment from {acc_num}. New balance: {MOCK_ACCOUNTS_DB[acc_num]['balance']}")

            elif request.transaction_type in ["transfer_intra_bank", "transfer_inter_bank_nip"]:
                source_acc_num = request.source_account.account_number
                amount = request.amount
                if source_acc_num in MOCK_ACCOUNTS_DB:
                    MOCK_ACCOUNTS_DB[source_acc_num]["balance"] -= amount
                    logger.info(f"API: Mock DB updated for transfer debit from {source_acc_num}. New balance: {MOCK_ACCOUNTS_DB[source_acc_num]['balance']}")

                if request.transaction_type == "transfer_intra_bank":
                    dest_acc_num = request.destination_account.account_number
                    if dest_acc_num in MOCK_ACCOUNTS_DB: # Agent should have verified this for intra-bank success
                        MOCK_ACCOUNTS_DB[dest_acc_num]["balance"] += amount
                        logger.info(f"API: Mock DB updated for transfer credit to {dest_acc_num}. New balance: {MOCK_ACCOUNTS_DB[dest_acc_num]['balance']}")
                    else: # This case implies an issue if agent said success for intra-bank to non-existent acc
                         logger.error(f"API: Intra-bank transfer success reported by agent, but dest account {dest_acc_num} not in mock DB. Inconsistency!")
                         # Potentially reverse debit or flag for investigation. For now, log it.
                         # agent_result["message"] += " (Warning: Destination account update in mock DB failed post-agent success)"
                         # agent_result["status"] = "Failed" # Or a special status like "PartialSuccess"

        except KeyError as e: # If expected fields are missing in request for DB update
            logger.error(f"API: KeyError updating MOCK_ACCOUNTS_DB for successful agent transaction {request.request_id}: {e}. This indicates a mismatch between request schema and DB update logic.", exc_info=True)
            agent_result["message"] = f"Successful by agent, but internal error updating balances: {e}"
            # agent_result["status"] = "Failed" # Or a special status
        except Exception as e:
            logger.error(f"API: Error updating MOCK_ACCOUNTS_DB after successful agent transaction {request.request_id}: {e}", exc_info=True)
            agent_result["message"] = f"Successful by agent, but internal error updating balances: {e}"
            # agent_result["status"] = "Failed" # Or a special status

    # Construct and return the final TransactionResponse using agent's result
    return TransactionResponse(
        request_id=agent_result.get("request_id", request.request_id), # Prioritize agent's request_id if it differs (shouldn't)
        status=agent_result.get("status", "Failed"), # type: ignore # Agent result should have 'Successful' or 'Failed'
        message=agent_result.get("message", "Error processing transaction."),
        transaction_id=agent_result.get("transaction_id"),
        additional_details=agent_result.get("additional_details") # This contains the raw tool output
    )


@app.get("/accounts/{account_number}/balance", response_model=BalanceResponse, tags=["Accounts"])
async def get_account_balance_endpoint(account_number: str):
    """
    Retrieves the current balance for a given account number via the Teller AI Agent.
    """
    logger.info(f"API: Balance inquiry for account: {account_number}")

    agent_result = await get_account_balance_async(account_number) # Customer ID is optional for agent function
    logger.info(f"API: Agent result for balance inquiry on {account_number}: {agent_result}")

    if agent_result.get("error"): # Check for custom error flag from agent
        status_code_to_raise = agent_result.get("status_code", 500)
        detail_message = agent_result.get("message", "Failed to retrieve account balance.")
        if status_code_to_raise == 404:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_message)
        else: # Any other error from agent (e.g. 500)
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail_message)

    # If successful, agent_result should match BalanceResponse structure or contain necessary fields
    # The agent's get_account_balance_async is designed to return fields matching BalanceResponse
    return BalanceResponse(**agent_result)


# --- Main block for Uvicorn ---
if __name__ == "__main__":
    # This ensures logging is configured if running directly, though uvicorn usually handles it.
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Teller Agent FastAPI application (CrewAI integrated - mocked). To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.teller_agent.main:app --reload --port 8002`")
    pass
