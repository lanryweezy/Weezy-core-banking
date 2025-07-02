# Pydantic schemas for Teller Agent API requests and responses

from pydantic import BaseModel, Field
from typing import Optional, Literal

class TransactionRequest(BaseModel):
    transaction_type: Literal["deposit", "withdrawal", "transfer", "balance_inquiry"] = Field(..., example="transfer")
    amount: Optional[float] = Field(None, gt=0, example=5000.50)
    currency: str = Field("NGN", example="NGN")
    from_account: Optional[str] = Field(None, example="1234567890")
    to_account: Optional[str] = Field(None, example="0987654321")
    description: Optional[str] = Field(None, example="Monthly allowance")
    otp: Optional[str] = Field(None, example="123456", description="OTP for verification if required")
    customer_id: Optional[str] = Field(None, example="CUST12345") # For context

class TransactionResponse(BaseModel):
    transaction_id: Optional[str] = Field(None, example="TXN20231027ABC001")
    status: str = Field(..., example="Success") # Success, Failed, Pending, RequiresOTP
    message: str = Field(..., example="Transaction processed successfully.")
    new_balance: Optional[float] = Field(None, example=15000.00)
    details: Optional[dict] = Field(None)

class BalanceResponse(BaseModel):
    account_number: str = Field(..., example="1234567890")
    available_balance: float = Field(..., example=12500.75)
    ledger_balance: float = Field(..., example=12800.75)
    currency: str = Field("NGN", example="NGN")
    last_updated: Optional[str] = Field(None, example="2023-10-27T10:30:00Z")

print("Teller Agent Pydantic schemas placeholder.")
