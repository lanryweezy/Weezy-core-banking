# LangChain/CrewAI agent logic for Teller Agent

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .schemas import TransactionRequest, BalanceResponse, TransactionStatus, CurrencyCode # Assuming schemas are in the same directory
from .tools import core_banking_api_tool, otp_verification_tool # Import your tools

# from crewai import Agent, Task, Crew, Process
# from langchain_community.llms.fake import FakeListLLM # For mocking CrewAI execution
# from ..core.config import core_settings # For OPENAI_API_KEY if needed

logger = logging.getLogger(__name__)

# --- Agent Definition (Placeholder for CrewAI) ---
# llm_teller = FakeListLLM(responses=["Okay, I will process this transaction.", "Fetching account balance."]) # Mock LLM

# teller_ai_agent = Agent(
#     role="Bank Teller AI",
#     goal="Handle customer financial transactions like deposits, withdrawals, transfers, bill payments, and balance inquiries accurately and securely, using available banking tools and verifying OTP when required.",
#     backstory=(
#         "An efficient AI designed to simulate the functions of a bank teller for a Nigerian bank. "
#         "It interacts with the core banking system APIs to perform transactions, verifies customer identity using OTP for sensitive operations, "
#         "and ensures all operations are logged. It can understand requests for common teller operations and strives for quick, secure processing."
#     ),
#     tools=[core_banking_api_tool, otp_verification_tool],
#     llm=llm_teller, # Replace with actual LLM in production
#     verbose=True,
#     allow_delegation=False, # Teller tasks are usually direct
# )

# --- Task Definitions (Placeholders for CrewAI) ---
# Example Task for a generic transaction:
# process_transaction_task = Task(
#     description="""\
#     Process a financial transaction based on the provided request details.
#     Request Details: {request_details_json}
#     If OTP is provided and seems necessary (e.g., for withdrawals or transfers above a certain limit, or for bill payments),
#     first use the OTPVerificationTool. If OTP verification fails, stop and report failure.
#     Then, use the CoreBankingAPITool to perform the specified transaction (deposit, withdrawal, transfer, bill_payment).
#     Return the outcome of the transaction.
#     """,
#     expected_output="""\
#     A JSON string detailing the transaction outcome.
#     Example for success: {"status": "Successful", "message": "Transaction completed.", "transaction_id": "CBS_TRN_123", "new_balance_preview": 50000.00}
#     Example for OTP failure: {"status": "Failed", "message": "Invalid OTP entered."}
#     Example for core banking failure: {"status": "Failed", "message": "Insufficient funds."}
#     """,
#     agent=teller_ai_agent,
#     tools=[otp_verification_tool, core_banking_api_tool] # Explicitly list tools for clarity
# )

# balance_inquiry_task = Task(
# description="""\
#     Retrieve the account balance for the given account number: {account_number}.
#     Use the CoreBankingAPITool with the 'get_balance' action.
#     """,
#     expected_output="""\
#     A JSON string with the account balance details.
#     Example: {"status": "success", "message": "Balance retrieved successfully.", "account_number": "123...", "balance": 75000.50, "currency": "NGN"}
#     """,
#     agent=teller_ai_agent,
#     tools=[core_banking_api_tool]
# )


# --- Main Workflow Functions (Direct Tool Usage for now, to be replaced by CrewAI kickoff) ---

async def process_teller_transaction_async(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a teller transaction by directly calling tools.
    This will be replaced by CrewAI agent execution.
    """
    transaction_type = request_data.get("transaction_type")
    logger.info(f"Agent: Processing transaction type '{transaction_type}' with data: {request_data}")

    # --- OTP Check (Simulated: Assume OTP is needed for withdrawals and transfers) ---
    otp_to_verify = request_data.get("otp")
    otp_verified = True # Default to true if no OTP provided or not needed for this mock

    if transaction_type in ["withdrawal", "transfer_intra_bank", "transfer_inter_bank_nip", "bill_payment"] and otp_to_verify:
        logger.info(f"Agent: OTP '{otp_to_verify}' provided for {transaction_type}, verifying...")
        otp_result = otp_verification_tool.run({
            "otp_value": otp_to_verify,
            "customer_id": request_data.get("customer_id"),
            "transaction_ref": request_data.get("request_id")
        })
        if otp_result.get("status") != "verified":
            logger.warning(f"Agent: OTP verification failed for request {request_data.get('request_id')}: {otp_result.get('message')}")
            return {
                "request_id": request_data.get("request_id"),
                "status": "Failed", # type: ignore
                "message": otp_result.get("message", "OTP verification failed."),
                "transaction_id": None
            }
        logger.info(f"Agent: OTP verified successfully for request {request_data.get('request_id')}")
        otp_verified = True
    elif transaction_type in ["withdrawal", "transfer_intra_bank", "transfer_inter_bank_nip", "bill_payment"] and not otp_to_verify:
        # This is a simplified policy; real system would have complex rules for when OTP is mandatory
        logger.warning(f"Agent: OTP not provided for {transaction_type} request {request_data.get('request_id')}. Proceeding without OTP (mock behavior).")
        # In a real system, might return "RequiresOTP" here if mandatory and missing.
        # For this mock, we'll allow it to proceed to simulate cases where OTP isn't always needed or for testing core logic.


    # --- Core Banking Action ---
    core_banking_payload: Dict[str, Any] = {"account_number": request_data.get("account_number")} # Common field

    if transaction_type == "deposit":
        core_banking_payload["action"] = "perform_deposit"
        core_banking_payload["amount"] = request_data.get("amount")
        core_banking_payload["currency"] = request_data.get("currency")
    elif transaction_type == "withdrawal":
        core_banking_payload["action"] = "perform_withdrawal"
        core_banking_payload["amount"] = request_data.get("amount")
        core_banking_payload["currency"] = request_data.get("currency")
    elif transaction_type in ["transfer_intra_bank", "transfer_inter_bank_nip"]:
        core_banking_payload["action"] = "perform_transfer"
        source_account_details = request_data.get("source_account", {})
        dest_account_details = request_data.get("destination_account", {})
        core_banking_payload["account_number"] = source_account_details.get("account_number") # Source for transfer
        core_banking_payload["amount"] = request_data.get("amount")
        core_banking_payload["currency"] = request_data.get("currency")
        core_banking_payload["destination_account_number"] = dest_account_details.get("account_number")
        core_banking_payload["destination_bank_code"] = dest_account_details.get("bank_code")
        core_banking_payload["narration"] = request_data.get("narration")
    elif transaction_type == "bill_payment":
        # Bill payment might call a different tool or a different action on CoreBankingAPITool
        # For this mock, we'll simulate it as a type of "transfer" or "debit" conceptually
        logger.info(f"Agent: Bill payment for Biller ID {request_data.get('biller_id')} (mocked as debit).")
        # This would typically involve a more specific tool or integration with a bill payment aggregator.
        # Simulating it as a withdrawal for now for ledger effect.
        core_banking_payload["action"] = "perform_withdrawal" # Simplified: treat as debit
        core_banking_payload["account_number"] = request_data.get("source_account_number")
        core_banking_payload["amount"] = request_data.get("amount")
        core_banking_payload["currency"] = request_data.get("currency")
        core_banking_payload["narration"] = request_data.get("narration", f"BillPay: {request_data.get('biller_id')}")
    else:
        logger.error(f"Agent: Unsupported transaction_type '{transaction_type}' in agent logic.")
        return {
            "request_id": request_data.get("request_id"), "status": "Failed", # type: ignore
            "message": f"Unsupported transaction type by agent: {transaction_type}", "transaction_id": None
        }

    logger.info(f"Agent: Calling CoreBankingAPITool with payload: {core_banking_payload}")
    core_result = core_banking_api_tool.run(core_banking_payload)
    logger.info(f"Agent: CoreBankingAPITool result: {core_result}")

    # Map core_result to TransactionResponse fields
    response_status: TransactionStatus = "Failed" # Default
    if core_result.get("status") == "success":
        response_status = "Successful"

    # This is where the agent would update the actual MOCK_ACCOUNTS_DB in main.py if it had direct access
    # or if the tool itself modified a shared state. Since tools are ideally pure, the main.py
    # will use this response to update its MOCK_ACCOUNTS_DB.

    return {
        "request_id": request_data.get("request_id"),
        "status": response_status,
        "message": core_result.get("message", "Error processing transaction with core banking system."),
        "transaction_id": core_result.get("transaction_id"), # From core banking tool
        "additional_details": core_result # Include full core_result for now
    }


async def get_account_balance_async(account_number: str, customer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves account balance by directly calling the CoreBankingAPITool.
    This will be replaced by CrewAI agent execution.
    """
    logger.info(f"Agent: Getting balance for account '{account_number}', customer_id='{customer_id}'")

    core_result = core_banking_api_tool.run({
        "action": "get_balance",
        "account_number": account_number
    })
    logger.info(f"Agent: CoreBankingAPITool result for balance: {core_result}")

    if core_result.get("status") == "success":
        return {
            "account_number": core_result.get("account_number"),
            "account_name": core_result.get("account_name", MOCK_CORE_BANKING_ACCOUNTS.get(account_number, {}).get("account_name")), # Try to get from tool, fallback to mock
            "available_balance": core_result.get("balance"),
            "ledger_balance": core_result.get("balance"), # Simplified for mock
            "currency": core_result.get("currency"),
            "last_updated_at": datetime.utcnow()
        }
    else:
        # Return a structure that can be identified as an error by the caller
        return {
            "error": True, # Custom flag
            "message": core_result.get("message", f"Could not retrieve balance for account {account_number}."),
            "status_code": 404 if "not found" in core_result.get("message","").lower() else 500
        }


if __name__ == "__main__":
    import asyncio

    async def test_teller_agent_logic():
        print("--- Testing Teller Agent Logic (Direct Tool Usage) ---")

        # Test Deposit
        deposit_req = {"transaction_type": "deposit", "account_number": "1234509876", "amount": 1000.0, "currency": "NGN", "request_id": "DEP001"}
        print(f"\nTesting Deposit: {deposit_req}")
        dep_res = await process_teller_transaction_async(deposit_req)
        print(f"Deposit Result: {dep_res}")

        # Test Withdrawal (with OTP)
        withdraw_req_otp = {"transaction_type": "withdrawal", "account_number": "0987654321", "amount": 500.0, "otp": "123456", "request_id": "WDR001"}
        print(f"\nTesting Withdrawal with OTP: {withdraw_req_otp}")
        wd_otp_res = await process_teller_transaction_async(withdraw_req_otp)
        print(f"Withdrawal OTP Result: {wd_otp_res}")

        # Test Withdrawal (insufficient funds)
        withdraw_req_insufficient = {"transaction_type": "withdrawal", "account_number": "0987654321", "amount": 1000000.0, "request_id": "WDR002"}
        print(f"\nTesting Withdrawal Insufficient: {withdraw_req_insufficient}")
        wd_ins_res = await process_teller_transaction_async(withdraw_req_insufficient)
        print(f"Withdrawal Insufficient Result: {wd_ins_res}")

        # Test Transfer (Intra-bank)
        transfer_req = {
            "transaction_type": "transfer_intra_bank",
            "source_account": {"account_number": "1122334455"},
            "destination_account": {"account_number": "1234509876"},
            "amount": 2000.0, "otp": "654321", "request_id": "TRF001"
        }
        print(f"\nTesting Transfer Intra-bank: {transfer_req}")
        trf_res = await process_teller_transaction_async(transfer_req)
        print(f"Transfer Result: {trf_res}")

        # Test Balance Inquiry
        print("\nTesting Balance Inquiry (Success):")
        bal_res_succ = await get_account_balance_async("1234509876")
        print(f"Balance Result (Success): {bal_res_succ}")

        print("\nTesting Balance Inquiry (Not Found):")
        bal_res_fail = await get_account_balance_async("0000000000")
        print(f"Balance Result (Not Found): {bal_res_fail}")

    # asyncio.run(test_teller_agent_logic())
    print("Teller Agent logic (agent.py). Contains functions to process transactions and get balances using tools (mocked execution).")
