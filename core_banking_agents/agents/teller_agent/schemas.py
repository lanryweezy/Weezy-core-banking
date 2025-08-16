# Pydantic schemas for Teller Agent API requests and responses

from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, Dict, Any
from datetime import datetime
import uuid

# --- Enums and Helper Models ---
TransactionType = Literal["deposit", "withdrawal", "transfer_intra_bank", "transfer_inter_bank_nip", "balance_inquiry", "bill_payment"]
TransactionStatus = Literal["Pending", "Successful", "Failed", "RequiresOTP", "Processing", "Reversed"]
CurrencyCode = Literal["NGN", "USD", "EUR", "GBP"] # Extend as needed

class AccountDetails(BaseModel):
    account_number: str = Field(..., example="0123456789", min_length=10, max_length=10)
    account_name: Optional[str] = Field(None, example="John Emeka Doe")
    bank_code: Optional[str] = Field(None, example="058", description="CBN Bank Code, required for inter-bank transfers")


# --- Request Models ---
class BaseTransactionRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"TREQ-{uuid.uuid4().hex[:10].upper()}")
    channel: Optional[str] = Field("API", example="MobileApp")
    customer_id: Optional[str] = Field(None, example="CUST-TELLER-001") # Contextual customer ID

class DepositRequest(BaseTransactionRequest):
    transaction_type: Literal["deposit"] = "deposit"
    account_number: str = Field(..., example="1234509876")
    amount: float = Field(..., gt=0, example=50000.75)
    currency: CurrencyCode = "NGN"
    narration: Optional[str] = Field("Cash deposit", example="Cash deposit by agent 007")
    teller_id: Optional[str] = Field(None, example="TELLER001")

class WithdrawalRequest(BaseTransactionRequest):
    transaction_type: Literal["withdrawal"] = "withdrawal"
    account_number: str = Field(..., example="1234509876")
    amount: float = Field(..., gt=0, example=10000.00)
    currency: CurrencyCode = "NGN"
    narration: Optional[str] = Field("Cash withdrawal", example="ATM withdrawal Marina")
    otp: Optional[str] = Field(None, example="123456", description="OTP if required for this withdrawal type/amount")

class TransferRequest(BaseTransactionRequest):
    transaction_type: Literal["transfer_intra_bank", "transfer_inter_bank_nip"]
    source_account: AccountDetails
    destination_account: AccountDetails
    amount: float = Field(..., gt=0, example=5000.00)
    currency: CurrencyCode = "NGN"
    narration: Optional[str] = Field("Funds transfer", example="Payment for services")
    otp: Optional[str] = Field(None, example="654321")

    @validator('destination_account')
    def check_destination_bank_code_for_inter_bank(cls, v, values):
        if values.get('transaction_type') == "transfer_inter_bank_nip" and not v.bank_code:
            raise ValueError("Destination bank_code is required for inter-bank NIP transfers.")
        return v

class BillPaymentRequest(BaseTransactionRequest):
    transaction_type: Literal["bill_payment"] = "bill_payment"
    source_account_number: str = Field(..., example="1234509876")
    biller_id: str = Field(..., example="DSTV001") # e.g., DSTV, EKEDC
    product_id: Optional[str] = Field(None, example="COMPACT_BOUQUET") # Specific product under biller
    customer_identifier: str = Field(..., example="1234567890", description="e.g., Smartcard number, Meter number")
    amount: float = Field(..., gt=0, example=5500.00)
    currency: CurrencyCode = "NGN"
    narration: Optional[str] = Field("Bill payment", example="DSTV Subscription")
    otp: Optional[str] = Field(None, example="112233")

# Union type for POST /transactions endpoint
TransactionRequest = DepositRequest | WithdrawalRequest | TransferRequest | BillPaymentRequest


# --- Response Models ---
class TransactionResponse(BaseModel):
    transaction_id: str = Field(..., example=f"TRN-{uuid.uuid4().hex[:12].upper()}")
    request_id: str # From the original request
    status: TransactionStatus
    message: str = Field(..., example="Transaction successful.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # fee: Optional[float] = Field(None, example=52.50) # NIP fee + VAT
    # available_balance_after: Optional[float] = Field(None, example=150000.25) # For source account
    additional_details: Optional[Dict[str, Any]] = None # e.g., NIP session ID, reversal info

class BalanceResponse(BaseModel):
    account_number: str
    account_name: Optional[str] = None
    available_balance: float = Field(..., example=12500.75)
    ledger_balance: float = Field(..., example=12800.75)
    currency: CurrencyCode = "NGN"
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
    # minimum_balance: Optional[float] = None
    # lien_amount: Optional[float] = None


if __name__ == "__main__":
    import json
    print("--- DepositRequest Schema ---")
    print(json.dumps(DepositRequest.model_json_schema(), indent=2))
    print("\n--- TransferRequest Schema ---")
    print(json.dumps(TransferRequest.model_json_schema(), indent=2))
    print("\n--- TransactionResponse Schema ---")
    print(json.dumps(TransactionResponse.model_json_schema(), indent=2))
    print("\n--- BalanceResponse Schema ---")
    print(json.dumps(BalanceResponse.model_json_schema(), indent=2))

    # Example instantiation
    # try:
    #     transfer_payload = {
    #         "transaction_type": "transfer_inter_bank_nip",
    #         "source_account": {"account_number": "1234567890"},
    #         "destination_account": {"account_number": "0987654321", "bank_code": "058"}, # GTB
    #         "amount": 100.0,
    #         "narration": "Test NIP"
    #     }
    #     transfer_req = TransferRequest(**transfer_payload)
    #     print("\nValid TransferRequest:", transfer_req.model_dump_json(indent=2))

    #     invalid_transfer_payload = {
    #         "transaction_type": "transfer_inter_bank_nip",
    #         "source_account": {"account_number": "1234567890"},
    #         "destination_account": {"account_number": "0987654321"}, # Missing bank_code
    #         "amount": 100.0
    #     }
    #     # This should raise a ValueError due to the validator
    #     # TransferRequest(**invalid_transfer_payload)
    # except Exception as e:
    #     print("\nError during instantiation (expected for invalid):", e)
    pass
