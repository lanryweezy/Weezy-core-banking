# FastAPI app for Teller Agent
from fastapi import FastAPI
# from .schemas import TransactionRequest, TransactionResponse, BalanceResponse

app = FastAPI(
    title="Teller Agent API",
    description="Handles deposits, withdrawals, transfers, and balance checks.",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "Teller Agent is running."}

# @app.post("/transaction", response_model=TransactionResponse)
# async def process_transaction(request: TransactionRequest):
#     # Logic to interact with agent.py
#     # result = run_teller_workflow(request.dict())
#     # return result
#     return {"transaction_id": "TXN123", "status": "pending", "message": "Not implemented"}


# @app.get("/balance/{account_number}", response_model=BalanceResponse)
# async def get_balance(account_number: str):
#     # Logic to interact with agent.py
#     # result = run_balance_check_workflow(account_number)
#     # return result
#     return {"account_number": account_number, "available_balance": 0.0, "ledger_balance": 0.0, "currency": "NGN"}

print("Teller Agent FastAPI app placeholder.")
