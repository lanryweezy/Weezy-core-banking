# Tools for Teller Agent

from langchain.tools import tool
from typing import Optional, Dict, Any, Literal
import random
import logging

logger = logging.getLogger(__name__)

# --- Mock Core Banking System Interaction ---
# This mock DB should ideally be the same one used in main.py for consistency in this phase.
# However, tools typically don't import from FastAPI app modules directly.
# For now, we'll operate on a conceptual shared state or pass necessary data through agent.
# For a more robust mock, this tool could call back to an API endpoint that manages the mock DB.
# Or, the agent itself would manage state changes based on tool outputs.

# Let's assume MOCK_ACCOUNTS_DB is conceptually accessible or changes are reported back.
# For simplicity in this tool, we'll just return what *would* happen.
# The agent.py or main.py would be responsible for actually committing these changes to MOCK_ACCOUNTS_DB.

MOCK_CORE_BANKING_ACCOUNTS = { # A local view for tool simulation, not directly tied to main.py's DB
    "1234509876": {"balance": 150000.00, "currency": "NGN", "min_balance": 0},
    "0987654321": {"balance": 75000.50, "currency": "NGN", "min_balance": 0},
    "1122334455": {"balance": 1200000.00, "currency": "NGN", "min_balance": 1000}, # Has min balance
    "5566778899": {"balance": 500.00, "currency": "USD", "min_balance": 10},
}


@tool("CoreBankingAPITool")
def core_banking_api_tool(
    action: Literal["get_balance", "perform_deposit", "perform_withdrawal", "perform_transfer"],
    account_number: str,
    amount: Optional[float] = None,
    currency: Optional[str] = "NGN",
    destination_account_number: Optional[str] = None,
    destination_bank_code: Optional[str] = None, # For inter-bank
    narration: Optional[str] = None
) -> Dict[str, Any]:
    """
    Simulates interaction with a Core Banking System API.
    Handles actions like getting balance, performing deposits, withdrawals, and transfers.

    Args:
        action (str): The action to perform: "get_balance", "perform_deposit", "perform_withdrawal", "perform_transfer".
        account_number (str): The primary account number for the operation.
        amount (Optional[float]): The amount for deposit, withdrawal, or transfer. Required for these actions.
        currency (Optional[str]): Currency code (e.g., "NGN"). Defaults to "NGN".
        destination_account_number (Optional[str]): Required for "perform_transfer".
        destination_bank_code (Optional[str]): Required for inter-bank transfers.
        narration (Optional[str]): Transaction narration.

    Returns:
        Dict[str, Any]: A dictionary with the result of the operation.
                        Includes 'status' ("success", "failed"), 'message', and other relevant data
                        like 'balance', 'new_balance', 'transaction_id'.
    """
    logger.info(f"CoreBankingAPITool called: action='{action}', account='{account_number}', amount='{amount}'")

    if account_number not in MOCK_CORE_BANKING_ACCOUNTS and action != "perform_transfer": # For transfer, dest might be external
        if action == "perform_deposit" and account_number.startswith("NEW_"): # Simulate creating account on first deposit
             MOCK_CORE_BANKING_ACCOUNTS[account_number] = {"balance": 0.00, "currency": currency or "NGN", "min_balance": 0}
             logger.info(f"Mock account {account_number} created on first deposit.")
        else:
            return {"status": "failed", "message": f"Account {account_number} not found."}

    account_data = MOCK_CORE_BANKING_ACCOUNTS.get(account_number)

    if action == "get_balance":
        if account_data:
            return {"status": "success", "message": "Balance retrieved successfully.",
                    "account_number": account_number, "balance": account_data["balance"], "currency": account_data["currency"]}
        else: # Should have been caught above, but as a safeguard
            return {"status": "failed", "message": f"Account {account_number} not found."}


    if amount is None or amount <= 0:
        return {"status": "failed", "message": "Amount must be positive and provided for this action."}

    mock_transaction_id = f"CBS_TRN_{random.randint(100000, 999999)}"

    if action == "perform_deposit":
        # new_balance = account_data["balance"] + amount # Agent would update the actual DB
        # MOCK_CORE_BANKING_ACCOUNTS[account_number]["balance"] = new_balance # Don't modify global here, tool should be pure
        return {"status": "success", "message": "Deposit successful (simulated).",
                "transaction_id": mock_transaction_id, "account_number": account_number,
                "deposited_amount": amount, "new_balance_preview": account_data["balance"] + amount} # type: ignore

    elif action == "perform_withdrawal":
        min_bal = account_data.get("min_balance", 0) # type: ignore
        if account_data["balance"] - amount < min_bal: # type: ignore
            return {"status": "failed", "message": "Insufficient funds for withdrawal (considering minimum balance).",
                    "current_balance": account_data["balance"], "requested_amount": amount} # type: ignore
        # new_balance = account_data["balance"] - amount
        return {"status": "success", "message": "Withdrawal successful (simulated).",
                "transaction_id": mock_transaction_id, "account_number": account_number,
                "withdrawn_amount": amount, "new_balance_preview": account_data["balance"] - amount} # type: ignore

    elif action == "perform_transfer":
        if not destination_account_number:
            return {"status": "failed", "message": "Destination account number is required for transfer."}

        min_bal = account_data.get("min_balance", 0) # type: ignore
        if account_data["balance"] - amount < min_bal: # type: ignore
            return {"status": "failed", "message": "Insufficient funds in source account for transfer (considering minimum balance).",
                    "current_balance": account_data["balance"], "requested_amount": amount} # type: ignore

        # Simulate transfer:
        # For inter-bank, destination_bank_code would be used.
        # Here, we just acknowledge. The agent would handle updating source and (if intra-bank) destination.
        transfer_type_narration = "Intra-bank" if destination_account_number in MOCK_CORE_BANKING_ACCOUNTS else "Inter-bank (NIP)"
        if transfer_type_narration == "Inter-bank (NIP)" and not destination_bank_code:
            return {"status": "failed", "message": "Destination bank code is required for inter-bank NIP transfer."}

        return {"status": "success",
                "message": f"{transfer_type_narration} transfer initiated successfully (simulated).",
                "transaction_id": mock_transaction_id,
                "source_account": account_number,
                "destination_account": destination_account_number,
                "destination_bank_code": destination_bank_code,
                "transferred_amount": amount,
                "source_new_balance_preview": account_data["balance"] - amount} # type: ignore
    else:
        return {"status": "failed", "message": f"Unknown core banking action: {action}"}


@tool("OTPVerificationTool")
def otp_verification_tool(otp_value: str, customer_id: Optional[str] = None, transaction_ref: Optional[str] = None) -> Dict[str, Any]:
    """
    Simulates verification of a One-Time Password (OTP).

    Args:
        otp_value (str): The OTP value entered by the customer.
        customer_id (Optional[str]): The customer ID associated with the OTP (for context).
        transaction_ref (Optional[str]): The transaction reference this OTP is for (for context).

    Returns:
        Dict[str, Any]: A dictionary with 'status' ("verified" or "failed") and an optional 'message'.
    """
    logger.info(f"OTPVerificationTool called: otp='{otp_value}', customer_id='{customer_id}', ref='{transaction_ref}'")

    # Mock OTPs for testing
    valid_otps = ["123456", "654321", "112233"]

    if otp_value in valid_otps:
        return {"status": "verified", "message": "OTP verified successfully."}
    elif otp_value == "EXPIRED":
        return {"status": "failed", "message": "OTP has expired. Please request a new one."}
    else:
        return {"status": "failed", "message": "Invalid OTP entered."}


if __name__ == "__main__":
    print("--- Testing CoreBankingAPITool ---")
    # Balance Check
    print("\nBalance Check (Success):")
    print(core_banking_api_tool.run({"action": "get_balance", "account_number": "1234509876"}))
    print("\nBalance Check (Not Found):")
    print(core_banking_api_tool.run({"action": "get_balance", "account_number": "0000000000"}))

    # Deposit
    print("\nDeposit (Success):")
    print(core_banking_api_tool.run({"action": "perform_deposit", "account_number": "1234509876", "amount": 5000}))

    # Withdrawal
    print("\nWithdrawal (Success):")
    print(core_banking_api_tool.run({"action": "perform_withdrawal", "account_number": "0987654321", "amount": 1000}))
    print("\nWithdrawal (Insufficient Funds):")
    print(core_banking_api_tool.run({"action": "perform_withdrawal", "account_number": "1234509876", "amount": 2000000})) # More than balance

    # Transfer
    print("\nTransfer (Intra-bank Success):")
    print(core_banking_api_tool.run({
        "action": "perform_transfer", "account_number": "1122334455", "amount": 5000,
        "destination_account_number": "0987654321", "narration": "Payment for goods"
    }))
    print("\nTransfer (Inter-bank NIP Success):")
    print(core_banking_api_tool.run({
        "action": "perform_transfer", "account_number": "1122334455", "amount": 7000,
        "destination_account_number": "EXTERNAL001", "destination_bank_code": "058", "narration": "NIP to GTB"
    }))
    print("\nTransfer (NIP, missing bank code):")
    print(core_banking_api_tool.run({
        "action": "perform_transfer", "account_number": "1122334455", "amount": 7000,
        "destination_account_number": "EXTERNAL001", "narration": "NIP to GTB" # Missing dest bank code
    }))


    print("\n--- Testing OTPVerificationTool ---")
    print("\nOTP (Valid):")
    print(otp_verification_tool.run({"otp_value": "123456", "customer_id": "CUST123"}))
    print("\nOTP (Invalid):")
    print(otp_verification_tool.run({"otp_value": "999999", "transaction_ref": "TRNXYZ123"}))
    print("\nOTP (Expired):")
    print(otp_verification_tool.run({"otp_value": "EXPIRED"}))

    print("\nTeller Agent tools (CoreBankingAPITool, OTPVerificationTool) implemented with mocks.")
