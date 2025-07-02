# LangChain/CrewAI agent logic for Teller Agent

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import json # For parsing task outputs

from .schemas import TransactionRequest, BalanceResponse, TransactionStatus, CurrencyCode
from .tools import core_banking_api_tool, otp_verification_tool

from crewai import Agent, Task, Crew, Process
from langchain_community.llms.fake import FakeListLLM # For mocking CrewAI execution
# from ..core.config import core_settings # For OPENAI_API_KEY if needed

logger = logging.getLogger(__name__)

# --- LLM Configuration (Mocked for CrewAI) ---
# The number of responses should be enough for the agent's internal processing for each task.
# For simple sequential tool use, one or two "thoughts" per task might be enough.
llm_teller = FakeListLLM(responses=[
    "Okay, I need to process this transaction. If OTP is present, I'll verify it first.", # For transaction task
    "OTP verified or not needed. Now I'll call the core banking tool.",                 # For transaction task
    "Okay, I need to get the account balance using the core banking tool."              # For balance task
])

# --- Agent Definition ---
teller_tools = [core_banking_api_tool, otp_verification_tool]

teller_ai_agent = Agent(
    role="Bank Teller AI",
    goal="Handle customer financial transactions like deposits, withdrawals, transfers, bill payments, and balance inquiries accurately and securely, using available banking tools and verifying OTP when required.",
    backstory=(
        "An efficient AI designed to simulate the functions of a bank teller for a Nigerian bank. "
        "It interacts with the core banking system APIs to perform transactions, verifies customer identity using OTP for sensitive operations, "
        "and ensures all operations are logged. It can understand requests for common teller operations and strives for quick, secure processing."
    ),
    tools=teller_tools,
    llm=llm_teller,
    verbose=True,
    allow_delegation=False,
)

# --- Task Definitions for CrewAI ---

def create_process_transaction_task(request_details_json: str) -> Task:
    return Task(
        description=f"""\
        Process a financial transaction based on the provided request details.
        Request Details (JSON string): '{request_details_json}'

        Determine the transaction type from the request.
        If an OTP (One-Time Password) is included in the request details AND the transaction type typically requires OTP
        (e.g., withdrawal, transfer, bill_payment), first use the 'OTPVerificationTool'.
        If OTP verification fails, the process should stop, and the output should clearly indicate the OTP failure.

        If OTP is verified or not required/provided for this transaction type (e.g. deposit),
        proceed to use the 'CoreBankingAPITool' to perform the financial operation.
        The 'action' for CoreBankingAPITool should be one of: 'perform_deposit', 'perform_withdrawal', 'perform_transfer'.
        For 'bill_payment', you can map it to 'perform_withdrawal' conceptually for this mock, or a more specific action if the tool supports it.
        Ensure all necessary parameters (account_number, amount, currency, destination_account_number, etc.) are passed to the CoreBankingAPITool.
        """,
        expected_output="""\
        A JSON string detailing the transaction outcome.
        For success: {"status": "success", "message": "Transaction completed.", "transaction_id": "CBS_TRN_123", "new_balance_preview": 50000.00, "source_new_balance_preview": 48000.00}
        For OTP failure: {"status": "failed", "message": "Invalid OTP entered."}
        For core banking failure: {"status": "failed", "message": "Insufficient funds."}
        The output must be a valid JSON string.
        """,
        agent=teller_ai_agent,
        tools=[otp_verification_tool, core_banking_api_tool]
    )

def create_balance_inquiry_task(account_number_str: str) -> Task:
    return Task(
        description=f"""\
        Retrieve the account balance for the given account number: '{account_number_str}'.
        Use the 'CoreBankingAPITool' with the 'get_balance' action.
        """,
        expected_output="""\
        A JSON string with the account balance details.
        Example: {"status": "success", "message": "Balance retrieved successfully.", "account_number": "123...", "balance": 75000.50, "currency": "NGN"}
        If the account is not found, the tool will return a status of "failed". Ensure this is reflected.
        The output must be a valid JSON string.
        """,
        agent=teller_ai_agent,
        tools=[core_banking_api_tool]
    )

# --- Main Workflow Functions (Now using CrewAI) ---

async def process_teller_transaction_async(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a teller transaction using the TellerAI Agent and relevant tasks.
    """
    transaction_type = request_data.get("transaction_type")
    logger.info(f"Agent (CrewAI): Processing transaction type '{transaction_type}' with data: {request_data.get('request_id')}")

    # Prepare input for the task (must be a dictionary of strings for CrewAI context)
    # Pydantic models are not directly passable into task context in current CrewAI versions easily.
    # So, we pass the JSON string representation of the request.
    task_input_json = json.dumps(request_data)

    transaction_task = create_process_transaction_task(task_input_json)

    crew = Crew(
        agents=[teller_ai_agent],
        tasks=[transaction_task],
        process=Process.sequential,
        verbose=1 # Can be 0, 1, or 2
    )

    # --- MOCKING CREW EXECUTION ---
    logger.info(f"Agent (CrewAI): Simulating kickoff for transaction task: {request_data.get('request_id')}")
    # In a real scenario: result_str = crew.kickoff(inputs={"request_details_json": task_input_json})

    # Mocked result based on direct tool calls (as before, but now framed as agent's final output)
    # This part needs careful mocking to reflect what the LLM + tools would actually produce.
    # Let's simulate the agent deciding which tool to call.

    otp_to_verify = request_data.get("otp")
    mock_crew_output = {}

    if transaction_type in ["withdrawal", "transfer_intra_bank", "transfer_inter_bank_nip", "bill_payment"] and otp_to_verify:
        otp_result = otp_verification_tool.run({
            "otp_value": otp_to_verify, "customer_id": request_data.get("customer_id"), "transaction_ref": request_data.get("request_id")
        })
        if otp_result.get("status") != "verified":
            mock_crew_output = {"status": "failed", "message": otp_result.get("message", "OTP verification failed by agent.")}

    if not mock_crew_output: # If OTP was good or not needed
        core_banking_payload: Dict[str, Any] = {"account_number": request_data.get("account_number")}
        if transaction_type == "deposit":
            core_banking_payload.update({"action": "perform_deposit", "amount": request_data.get("amount"), "currency": request_data.get("currency")})
        elif transaction_type == "withdrawal":
            core_banking_payload.update({"action": "perform_withdrawal", "amount": request_data.get("amount"), "currency": request_data.get("currency")})
        elif transaction_type in ["transfer_intra_bank", "transfer_inter_bank_nip"]:
            source_acc = request_data.get("source_account", {})
            dest_acc = request_data.get("destination_account", {})
            core_banking_payload.update({
                "action": "perform_transfer", "account_number": source_acc.get("account_number"),
                "amount": request_data.get("amount"), "currency": request_data.get("currency"),
                "destination_account_number": dest_acc.get("account_number"), "destination_bank_code": dest_acc.get("bank_code"),
                "narration": request_data.get("narration")
            })
        elif transaction_type == "bill_payment": # Simplified
            core_banking_payload.update({
                "action": "perform_withdrawal", "account_number": request_data.get("source_account_number"),
                "amount": request_data.get("amount"), "currency": request_data.get("currency"),
                "narration": request_data.get("narration", f"BillPay: {request_data.get('biller_id')}")
            })
        else:
            mock_crew_output = {"status": "failed", "message": f"Agent does not support transaction type: {transaction_type}"}

        if not mock_crew_output: # if action was determined
            mock_crew_output = core_banking_api_tool.run(core_banking_payload)
            # The tool returns status "success" or "failed". We map this to TransactionStatus for consistency.
            mock_crew_output["status"] = "Successful" if mock_crew_output.get("status") == "success" else "Failed"


    result_str = json.dumps(mock_crew_output)
    logger.info(f"Agent (CrewAI): Mocked kickoff result for transaction task: {result_str}")
    # --- END MOCKING CREW EXECUTION ---

    try:
        processed_result = json.loads(result_str)
    except json.JSONDecodeError:
        logger.error(f"Agent (CrewAI): Error decoding JSON result from transaction task: {result_str}")
        processed_result = {"status": "Failed", "message": "Agent returned malformed result."} # type: ignore

    # Ensure the output structure matches what the FastAPI endpoint expects for TransactionResponse
    return {
        "request_id": request_data.get("request_id"),
        "status": processed_result.get("status", "Failed"), # type: ignore
        "message": processed_result.get("message", "Error processing transaction."),
        "transaction_id": processed_result.get("transaction_id"),
        "additional_details": processed_result # Pass through the raw details from the agent/tool
    }


async def get_account_balance_async(account_number: str, customer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves account balance using the TellerAI Agent and balance inquiry task.
    """
    logger.info(f"Agent (CrewAI): Getting balance for account '{account_number}', customer_id='{customer_id}'")

    balance_task = create_balance_inquiry_task(account_number)

    crew = Crew(
        agents=[teller_ai_agent],
        tasks=[balance_task],
        process=Process.sequential,
        verbose=1
    )

    # --- MOCKING CREW EXECUTION ---
    logger.info(f"Agent (CrewAI): Simulating kickoff for balance task: {account_number}")
    # In a real scenario: result_str = crew.kickoff(inputs={"account_number": account_number})
    mock_tool_result = core_banking_api_tool.run({"action": "get_balance", "account_number": account_number})
    result_str = json.dumps(mock_tool_result) # Agent's task is expected to return a JSON string
    logger.info(f"Agent (CrewAI): Mocked kickoff result for balance task: {result_str}")
    # --- END MOCKING CREW EXECUTION ---

    try:
        core_result = json.loads(result_str)
    except json.JSONDecodeError:
        logger.error(f"Agent (CrewAI): Error decoding JSON result from balance task: {result_str}")
        return {"error": True, "message": "Agent returned malformed balance result.", "status_code": 500}

    if core_result.get("status") == "success":
        # Try to get account_name from the MOCK_CORE_BANKING_ACCOUNTS in tools.py as a fallback for this mock
        # In a real system, the core banking tool/API would return this.
        mock_account_info = core_banking_api_tool.MOCK_CORE_BANKING_ACCOUNTS.get(account_number, {})

        return {
            "account_number": core_result.get("account_number"),
            "account_name": core_result.get("account_name", mock_account_info.get("account_name")),
            "available_balance": core_result.get("balance"),
            "ledger_balance": core_result.get("balance"), # Simplified
            "currency": core_result.get("currency"),
            "last_updated_at": datetime.utcnow()
        }
    else:
        return {
            "error": True,
            "message": core_result.get("message", f"Could not retrieve balance for account {account_number} via agent."),
            "status_code": 404 if "not found" in core_result.get("message","").lower() else 500
        }


if __name__ == "__main__":
    import asyncio

    async def test_teller_agent_crew_logic():
        print("--- Testing Teller Agent Logic (Simulated CrewAI) ---")

        # Test Deposit
        deposit_req = {"transaction_type": "deposit", "account_number": "1234509876", "amount": 1000.0, "currency": "NGN", "request_id": "DEP001_CREW"}
        print(f"\nTesting Deposit with Crew: {deposit_req}")
        dep_res = await process_teller_transaction_async(deposit_req)
        print(f"Deposit Crew Result: {dep_res}")

        # Test Withdrawal (with OTP)
        withdraw_req_otp = {"transaction_type": "withdrawal", "account_number": "0987654321", "amount": 500.0, "otp": "123456", "request_id": "WDR001_CREW"}
        print(f"\nTesting Withdrawal with OTP with Crew: {withdraw_req_otp}")
        wd_otp_res = await process_teller_transaction_async(withdraw_req_otp)
        print(f"Withdrawal OTP Crew Result: {wd_otp_res}")

        # Test Transfer (Intra-bank, OTP fail)
        transfer_req_otp_fail = {
            "transaction_type": "transfer_intra_bank",
            "source_account": {"account_number": "1122334455"},
            "destination_account": {"account_number": "1234509876"},
            "amount": 100.0, "otp": "BADOTP", "request_id": "TRF001_CREW_OTPFAIL"
        }
        print(f"\nTesting Transfer Intra-bank (OTP Fail) with Crew: {transfer_req_otp_fail}")
        trf_otp_fail_res = await process_teller_transaction_async(transfer_req_otp_fail)
        print(f"Transfer OTP Fail Crew Result: {trf_otp_fail_res}")

        # Test Balance Inquiry
        print("\nTesting Balance Inquiry with Crew (Success):")
        bal_res_succ = await get_account_balance_async("1234509876")
        print(f"Balance Crew Result (Success): {bal_res_succ}")

        print("\nTesting Balance Inquiry with Crew (Not Found):")
        bal_res_fail = await get_account_balance_async("0000000000")
        print(f"Balance Crew Result (Not Found): {bal_res_fail}")

    # asyncio.run(test_teller_agent_crew_logic())
    print("Teller Agent logic (agent.py) updated with CrewAI Agent and Task structure (mocked execution).")
