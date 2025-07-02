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
    version="0.1.1", # Incremented version
    contact={
        "name": "Core Banking AI Team",
        "email": "ai-devs@examplebank.ng",
    },
)

# --- Background Task Runner for Agent ---
# (If transactions were to be fully async from API perspective)
# async def run_teller_agent_workflow(request_id: str, request_data: Dict[str, Any]):
#     logger.info(f"Background task started for Teller request_id: {request_id}")
#     agent_result = await process_teller_transaction_async(request_data)
#     # Here, you would typically update a persistent store with agent_result
#     # For now, main MOCK_ACCOUNTS_DB update is synchronous after await in the endpoint.
#     logger.info(f"Background task completed for Teller request_id: {request_id}. Agent result: {agent_result.get('status')}")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Teller Agent."""
    logger.info("Teller Agent root endpoint accessed.")
    return {"message": "Teller Agent is running. CrewAI integration active (mocked execution). See /docs for API details."}

@app.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_200_OK, tags=["Transactions"]) # Changed to 200 OK as we await agent result
async def handle_transaction(
    # background_tasks: BackgroundTasks, # Uncomment if making fully async from API
    request: Union[DepositRequest, WithdrawalRequest, TransferRequest, BillPaymentRequest] = Body(..., discriminator='transaction_type')
):
    """
    Processes various financial transactions via the Teller AI Agent.
    The agent handles OTP (if applicable) and core banking interactions.
    This endpoint now AWAITS the (mocked) agent's processing before responding.
    """
    logger.info(f"API: Received transaction request: {request.request_id}, Type: {request.transaction_type}, Amount: {getattr(request, 'amount', 'N/A')}")

    # Call the agent to process the transaction.
    # The agent now encapsulates tool calls (OTP, CoreBanking) and returns a structured result.
    agent_result = await process_teller_transaction_async(request.model_dump())

    logger.info(f"API: Agent processing result for {request.request_id}: {agent_result}")

    # Update MOCK_ACCOUNTS_DB based on successful agent execution
    # This simulates the final ledger update after the agent confirms the transaction feasibility.
    if agent_result.get("status") == "Successful":
        try:
            additional_details = agent_result.get("additional_details", {})
            if request.transaction_type == "deposit":
                acc_num = getattr(request, "account_number")
                amount = getattr(request, "amount")
                if acc_num in MOCK_ACCOUNTS_DB:
                    MOCK_ACCOUNTS_DB[acc_num]["balance"] += amount
                else: # Simulate account creation on first deposit if tool logic supports it
                    MOCK_ACCOUNTS_DB[acc_num] = {"balance": amount, "currency": getattr(request, "currency", "NGN"), "min_balance": 0, "account_name": "New Account"}
                logger.info(f"API: Mock DB updated for deposit to {acc_num}. New balance: {MOCK_ACCOUNTS_DB[acc_num]['balance']}")

            elif request.transaction_type == "withdrawal" or (request.transaction_type == "bill_payment" and additional_details.get("action") == "perform_withdrawal"):
                acc_num = getattr(request, "account_number", getattr(request, "source_account_number", None))
                amount = getattr(request, "amount")
                if acc_num and acc_num in MOCK_ACCOUNTS_DB:
                    MOCK_ACCOUNTS_DB[acc_num]["balance"] -= amount
                    logger.info(f"API: Mock DB updated for withdrawal/bill_payment from {acc_num}. New balance: {MOCK_ACCOUNTS_DB[acc_num]['balance']}")

            elif request.transaction_type in ["transfer_intra_bank", "transfer_inter_bank_nip"]:
                source_acc_num = request.source_account.account_number
                amount = request.amount
                if source_acc_num in MOCK_ACCOUNTS_DB:
                    MOCK_ACCOUNTS_DB[source_acc_num]["balance"] -= amount
                    logger.info(f"API: Mock DB updated for transfer debit from {source_acc_num}. New balance: {MOCK_ACCOUNTS_DB[source_acc_num]['balance']}")

                if request.transaction_type == "transfer_intra_bank":
                    dest_acc_num = request.destination_account.account_number
                    if dest_acc_num in MOCK_ACCOUNTS_DB:
                        MOCK_ACCOUNTS_DB[dest_acc_num]["balance"] += amount
                        logger.info(f"API: Mock DB updated for transfer credit to {dest_acc_num}. New balance: {MOCK_ACCOUNTS_DB[dest_acc_num]['balance']}")
                    # If dest_acc_num not in MOCK_ACCOUNTS_DB for intra-bank, agent should have flagged, or it's an error state.
                    # The agent's "Successful" status implies this was handled if it was an issue.
        except Exception as e:
            logger.error(f"API: Error updating MOCK_ACCOUNTS_DB after successful agent transaction {request.request_id}: {e}", exc_info=True)
            # Transaction was successful by agent, but local mock DB update failed. This is an inconsistency.
            # In a real system, this would be part of a distributed transaction or have compensating actions.
            # For now, we proceed with agent's success status but log the error.


    return TransactionResponse(
        request_id=agent_result.get("request_id", request.request_id),
        status=agent_result.get("status", "Failed"), # type: ignore
        message=agent_result.get("message", "Error processing transaction."),
        transaction_id=agent_result.get("transaction_id"), # This should come from agent/core_banking_tool
        additional_details=agent_result.get("additional_details")
    )


@app.get("/accounts/{account_number}/balance", response_model=BalanceResponse, tags=["Accounts"])
async def get_account_balance_endpoint(account_number: str):
    """
    Retrieves the current balance for a given account number via the Teller AI Agent.
    """
    logger.info(f"API: Balance inquiry for account: {account_number}")

    agent_result = await get_account_balance_async(account_number)
    logger.info(f"API: Agent result for balance inquiry on {account_number}: {agent_result}")

    if agent_result.get("error"): # Check for custom error flag from agent
        status_code = agent_result.get("status_code", 500)
        if status_code == 404:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=agent_result.get("message"))
        else:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=agent_result.get("message"))

    # If successful, agent_result should match BalanceResponse structure or contain necessary fields
    return BalanceResponse(
        account_number=agent_result.get("account_number", account_number),
        account_name=agent_result.get("account_name"),
        available_balance=agent_result.get("available_balance", 0.0),
        ledger_balance=agent_result.get("ledger_balance", 0.0), # Simplified
        currency=agent_result.get("currency", "NGN"), # type: ignore
        last_updated_at=agent_result.get("last_updated_at", datetime.utcnow())
    )

# --- Main block for Uvicorn ---
if __name__ == "__main__":
    logger.info("Teller Agent FastAPI application (CrewAI integrated - mocked). To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.teller_agent.main:app --reload --port 8002`")
    pass
