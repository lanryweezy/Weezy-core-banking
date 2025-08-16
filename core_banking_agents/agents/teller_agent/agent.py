# LangChain/CrewAI agent logic for Teller Agent

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import json # For parsing task outputs

from .schemas import TransactionRequest, BalanceResponse, TransactionStatus, CurrencyCode
from .tools import core_banking_api_tool, otp_verification_tool

from crewai import Agent, Task, Crew, Process
from langchain_community.llms.fake import FakeListLLM
# from ..core.config import core_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- LLM Configuration (Mocked for CrewAI) ---
# Provide enough mock "thoughts" or tool selection responses for the agent's processing.
llm_teller_responses = [
    # For process_transaction_task
    "The user wants to perform a transaction. I need to check if OTP is provided and required.", # Thought 1
    "OTP is '123456'. I will use OTPVerificationTool.", # Tool selection for OTP
    "OTP verified. Now I need to perform the core banking transaction. I will use CoreBankingAPITool.", # Thought 2 + Tool selection for Core Banking
    "Transaction successful.", # Mock final thought after core banking tool (tool itself returns JSON)

    # For balance_inquiry_task
    "The user wants to check an account balance. I will use CoreBankingAPITool with 'get_balance' action.", # Thought 1 + Tool selection
    "Balance retrieved." # Mock final thought
] * 2 # Multiply to have enough responses if CrewAI makes more internal calls with verbose > 0
llm_teller = FakeListLLM(responses=llm_teller_responses)

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
    verbose=1, # 0, 1, or 2. 1 shows basic flow.
    allow_delegation=False,
)

# --- Task Definitions for CrewAI ---

def create_process_transaction_task(request_details_json_str: str) -> Task:
    """
    Creates a CrewAI Task to process a financial transaction.
    The agent will decide to use OTP tool first if applicable, then the core banking tool.
    """
    return Task(
        description=f"""\
        Process a financial transaction based on the provided request details JSON string: '{request_details_json_str}'.

        First, analyze the 'transaction_type' and 'otp' field from the request details.
        If an OTP is provided AND the transaction type is one of ('withdrawal', 'transfer_intra_bank', 'transfer_inter_bank_nip', 'bill_payment'),
        you MUST use the 'OTPVerificationTool' first. Pass the 'otp_value' and other relevant context like 'customer_id' or 'request_id' to it.
        If OTP verification fails (tool output 'status' is not 'verified'), your final output MUST indicate this failure and stop further processing.

        If OTP verification is successful, OR if OTP was not required/provided (e.g., for 'deposit'),
        then proceed to use the 'CoreBankingAPITool'.
        Determine the correct 'action' parameter for CoreBankingAPITool based on 'transaction_type':
        - 'deposit' -> 'perform_deposit'
        - 'withdrawal' -> 'perform_withdrawal'
        - 'transfer_intra_bank' or 'transfer_inter_bank_nip' -> 'perform_transfer'
        - 'bill_payment' -> 'perform_withdrawal' (as a simplified debit for this mock, include biller info in narration)

        Pass all necessary parameters from the request_details (like 'account_number', 'amount', 'currency',
        'source_account.account_number', 'destination_account.account_number', 'destination_account.bank_code', 'narration')
        to the CoreBankingAPITool.

        Your final output MUST be the JSON string result from the CoreBankingAPITool if successful,
        or the JSON string result from OTPVerificationTool if OTP failed.
        """,
        expected_output="""\
        A single JSON string representing the result of the operation.
        If OTP failed: '{"status": "failed", "message": "Invalid OTP entered."}'
        If Core Banking action successful: '{"status": "success", "message": "Deposit successful (simulated).", "transaction_id": "CBS_TRN_...", "deposited_amount": ..., "new_balance_preview": ...}'
        If Core Banking action failed: '{"status": "failed", "message": "Insufficient funds for withdrawal."}'
        """,
        agent=teller_ai_agent,
        # Tools are available to the agent, task description guides their use.
    )

def create_balance_inquiry_task(account_number_str: str) -> Task:
    """Creates a CrewAI Task to inquire about account balance."""
    return Task(
        description=f"""\
        Retrieve the account balance for the account number: '{account_number_str}'.
        You MUST use the 'CoreBankingAPITool' with the 'action' parameter set to 'get_balance'.
        Pass the 'account_number' to the tool.
        """,
        expected_output="""\
        A single JSON string containing the balance details from the CoreBankingAPITool.
        Example: '{"status": "success", "message": "Balance retrieved successfully.", "account_number": "...", "balance": ..., "currency": "NGN"}'
        If account not found: '{"status": "failed", "message": "Account ... not found."}'
        """,
        agent=teller_ai_agent,
    )

# --- Main Workflow Functions (Now using CrewAI) ---

async def process_teller_transaction_async(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a teller transaction using the TellerAI Agent and relevant tasks.
    """
    request_id = request_data.get("request_id", "N/A_REQ_ID")
    logger.info(f"Agent (CrewAI): Processing transaction request_id '{request_id}', Type: {request_data.get('transaction_type')}")

    task_input_json = json.dumps(request_data) # Pass the whole request as JSON string

    transaction_task = create_process_transaction_task(task_input_json)

    teller_crew = Crew(
        agents=[teller_ai_agent],
        tasks=[transaction_task],
        process=Process.sequential,
        verbose=0 # Set to 1 or 2 for debugging CrewAI steps. For production, usually 0.
    )

    # --- ACTUAL CREWAI KICKOFF (Commented out for pure mock, uncomment for FakeListLLM test) ---
    # logger.info(f"Agent (CrewAI): Kicking off crew for transaction task: {request_id}")
    # try:
    #     # Inputs dict keys must match placeholders in task descriptions if any, or be general context
    #     crew_result_str = teller_crew.kickoff(inputs={'request_details_json_str': task_input_json})
    #     logger.info(f"Agent (CrewAI): Crew kickoff raw result for transaction task '{request_id}': {crew_result_str}")
    # except Exception as e:
    #     logger.error(f"Agent (CrewAI): Crew kickoff failed for transaction task '{request_id}': {e}", exc_info=True)
    #     crew_result_str = json.dumps({"status": "Failed", "message": f"Agent workflow execution error: {e}"})
    # --- END ACTUAL CREWAI KICKOFF ---

    # --- MOCKING CREW EXECUTION (Simulating agent's final output string) ---
    # This simulates what the agent's final task (process_transaction_task) would return as a string.
    # The agent, guided by the task description, would call tools and its LLM would synthesize the final JSON string.
    if True: # Keep this block for controlled mocking
        logger.warning(f"Agent (CrewAI): Using MOCKED CrewAI execution path for transaction task: {request_id}")

        mock_agent_final_output_dict = {}
        otp_to_verify = request_data.get("otp")
        transaction_type = request_data.get("transaction_type")

        if transaction_type in ["withdrawal", "transfer_intra_bank", "transfer_inter_bank_nip", "bill_payment"] and otp_to_verify:
            otp_result = otp_verification_tool.run({ # Agent uses tool
                "otp_value": otp_to_verify, "customer_id": request_data.get("customer_id"), "transaction_ref": request_id
            })
            if otp_result.get("status") != "verified":
                mock_agent_final_output_dict = otp_result # OTP failure is the final result

        if not mock_agent_final_output_dict: # If OTP good or not needed
            core_banking_payload = {"account_number": request_data.get("account_number")}
            if transaction_type == "deposit":
                core_banking_payload.update({"action": "perform_deposit", "amount": request_data.get("amount"), "currency": request_data.get("currency")})
            elif transaction_type == "withdrawal":
                core_banking_payload.update({"action": "perform_withdrawal", "amount": request_data.get("amount"), "currency": request_data.get("currency")})
            elif transaction_type in ["transfer_intra_bank", "transfer_inter_bank_nip"]:
                source_acc, dest_acc = request_data.get("source_account",{}), request_data.get("destination_account",{})
                core_banking_payload.update({"action": "perform_transfer", "account_number": source_acc.get("account_number"),
                                             "amount": request_data.get("amount"), "currency": request_data.get("currency"),
                                             "destination_account_number": dest_acc.get("account_number"),
                                             "destination_bank_code": dest_acc.get("bank_code"), "narration": request_data.get("narration")})
            elif transaction_type == "bill_payment":
                core_banking_payload.update({"action": "perform_withdrawal", "account_number": request_data.get("source_account_number"),
                                             "amount": request_data.get("amount"), "currency": request_data.get("currency"),
                                             "narration": request_data.get("narration", f"BillPay: {request_data.get('biller_id')}")})
            else: # Should not happen if request_data is validated by schema
                mock_agent_final_output_dict = {"status": "Failed", "message": f"Unsupported transaction type by agent: {transaction_type}"}

            if not mock_agent_final_output_dict:
                mock_agent_final_output_dict = core_banking_api_tool.run(core_banking_payload) # Agent uses tool

        crew_result_str = json.dumps(mock_agent_final_output_dict)
        logger.info(f"Agent (CrewAI): Mocked final JSON string output for transaction task '{request_id}': {crew_result_str}")
    # --- END MOCKING CREW EXECUTION ---

    try:
        # The final output of a CrewAI task is a string, expected to be JSON here.
        processed_result = json.loads(crew_result_str)
    except json.JSONDecodeError:
        logger.error(f"Agent (CrewAI): Error decoding JSON result from transaction task '{request_id}': {crew_result_str}", exc_info=True)
        processed_result = {"status": "Failed", "message": "Agent returned malformed result (not JSON)."}
    except TypeError: # If crew_result_str is None or not string-like
        logger.error(f"Agent (CrewAI): Crew returned None or non-string result for transaction task '{request_id}'.", exc_info=True)
        processed_result = {"status": "Failed", "message": "Agent workflow returned unexpected data type."}


    # Map the direct tool output (which is what our mocked agent returns) to the expected API response structure
    return {
        "request_id": request_id,
        "status": "Successful" if processed_result.get("status") == "success" else "Failed", # type: ignore
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

    teller_crew = Crew(
        agents=[teller_ai_agent],
        tasks=[balance_task],
        process=Process.sequential,
        verbose=0 # Less verbose for balance check
    )

    # --- ACTUAL CREWAI KICKOFF (Commented out for pure mock) ---
    # logger.info(f"Agent (CrewAI): Kicking off crew for balance task: {account_number}")
    # try:
    #     crew_result_str = teller_crew.kickoff(inputs={'account_number_str': account_number})
    #     logger.info(f"Agent (CrewAI): Crew kickoff raw result for balance task '{account_number}': {crew_result_str}")
    # except Exception as e:
    #     logger.error(f"Agent (CrewAI): Crew kickoff failed for balance task '{account_number}': {e}", exc_info=True)
    #     crew_result_str = json.dumps({"status": "failed", "message": f"Agent workflow execution error: {e}"})
    # --- END ACTUAL CREWAI KICKOFF ---

    # --- MOCKING CREW EXECUTION (Simulating agent's final output string) ---
    if True: # Keep this block for controlled mocking
        logger.warning(f"Agent (CrewAI): Using MOCKED CrewAI execution path for balance task: {account_number}")
        mock_tool_result = core_banking_api_tool.run({"action": "get_balance", "account_number": account_number}) # Agent uses tool
        crew_result_str = json.dumps(mock_tool_result)
        logger.info(f"Agent (CrewAI): Mocked final JSON string output for balance task '{account_number}': {crew_result_str}")
    # --- END MOCKING CREW EXECUTION ---

    try:
        core_result = json.loads(crew_result_str)
    except json.JSONDecodeError:
        logger.error(f"Agent (CrewAI): Error decoding JSON result from balance task '{account_number}': {crew_result_str}", exc_info=True)
        return {"error": True, "message": "Agent returned malformed balance result (not JSON).", "status_code": 500}
    except TypeError:
        logger.error(f"Agent (CrewAI): Crew returned None or non-string result for balance task '{account_number}'.", exc_info=True)
        return {"error": True, "message": "Agent workflow returned unexpected data type for balance.", "status_code": 500}


    if core_result.get("status") == "success":
        # Try to get account_name from the MOCK_CORE_BANKING_ACCOUNTS in tools.py as a fallback for this mock
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

    # To run tests:
    # logging.basicConfig(level=logging.DEBUG) # For more verbose logs from agent/tools during test
    # asyncio.run(test_teller_agent_crew_logic())
    print("Teller Agent logic (agent.py) updated with CrewAI Agent and Task structure (simulated CrewAI kickoff, direct tool calls for mock output).")
