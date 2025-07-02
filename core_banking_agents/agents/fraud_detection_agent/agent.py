# LangChain/CrewAI agent logic for Fraud Detection Agent

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

from .schemas import TransactionEventInput, FraudAnalysisOutput, FraudRuleMatch, RiskLevel, FraudActionRecommended
from .tools import transaction_profile_tool, rule_engine_tool, anomaly_detection_tool

from crewai import Agent, Task, Crew, Process
from langchain_community.llms.fake import FakeListLLM
# from ..core.config import core_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- LLM Configuration (Mocked for CrewAI) ---
mock_llm_fraud_responses = [
    "Okay, I need to analyze this transaction for fraud. First, I'll get the customer's profile.", # Profile Task
    "Profile fetched. Now, I'll apply fraud rules.", # Rule Engine Task
    "Rules applied. Next, I'll get the anomaly detection score.", # Anomaly Detection Task
    "All data gathered. I will now consolidate to give a final fraud assessment, score, and recommendation." # Final Assessment Task
] * 2
llm_fraud_detector = FakeListLLM(responses=mock_llm_fraud_responses)

# --- Agent Definition ---
fraud_detection_tools = [transaction_profile_tool, rule_engine_tool, anomaly_detection_tool]

fraud_detector_agent = Agent(
    role="AI Fraud Detection Analyst",
    goal="Proactively identify and assess fraudulent transactions by analyzing transaction events, customer profiles, applying rules, and using anomaly detection models. Provide a clear fraud score, risk level, and recommended action.",
    backstory=(
        "A vigilant AI system dedicated to safeguarding the bank and its customers from financial fraud. "
        "It processes transaction events in near real-time, correlating them with historical customer behavior, "
        "checking against known fraud patterns and rules, and leveraging machine learning to detect subtle anomalies. "
        "Its analysis results in actionable insights for fraud prevention and mitigation."
    ),
    tools=fraud_detection_tools,
    llm=llm_fraud_detector,
    verbose=1,
    allow_delegation=False,
)

# --- Task Definitions for CrewAI ---
def create_fraud_analysis_tasks(transaction_event_dict: Dict[str, Any]) -> List[Task]:
    tasks: List[Task] = []
    transaction_event_json_str = json.dumps(transaction_event_dict) # For use in task descriptions

    # Task 1: Profile Fetching
    profile_task = Task(
        description=f"""\
        Fetch the transaction profile for the customer/account associated with the transaction event.
        Transaction Event (JSON string): '{transaction_event_json_str}'.
        Extract 'customer_id' and 'account_number' from the event to pass to the TransactionProfileTool.
        """,
        expected_output="A JSON string from TransactionProfileTool: {'status': ..., 'profile_found': ..., 'profile_data': {...}}.",
        agent=fraud_detector_agent,
    )
    tasks.append(profile_task)

    # Task 2: Rule Engine Application
    rules_task = Task(
        description=f"""\
        Apply fraud rules to the transaction event: '{transaction_event_json_str}'.
        Use the customer profile obtained from the previous task (output of profile_task) as context.
        Pass the transaction event and customer profile to the RuleEngineTool.
        """,
        expected_output="A JSON string from RuleEngineTool: {'triggered_rules': [{'rule_id': ..., 'name': ..., 'score_impact': ...}, ...]}",
        agent=fraud_detector_agent,
        context_tasks=[profile_task] # Depends on profile_task
    )
    tasks.append(rules_task)

    # Task 3: Anomaly Detection
    anomaly_task = Task(
        description=f"""\
        Calculate an anomaly score for the transaction event: '{transaction_event_json_str}'.
        Use the customer profile obtained from profile_task as context.
        Pass the transaction event and customer profile to the AnomalyDetectionTool.
        """,
        expected_output="A JSON string from AnomalyDetectionTool: {'anomaly_score': ..., 'contributing_factors': [...], 'model_version': ...}",
        agent=fraud_detector_agent,
        context_tasks=[profile_task] # Depends on profile_task
    )
    tasks.append(anomaly_task)

    # Task 4: Final Fraud Assessment (Consolidation)
    assessment_task = Task(
        description=f"""\
        Consolidate all findings: customer profile (from profile_task), triggered rules (from rules_task),
        and anomaly detection results (from anomaly_task) for the transaction event: '{transaction_event_json_str}'.
        Calculate an overall 'fraud_score' (0-100).
        Determine a 'risk_level' (Low, Medium, High, Critical).
        Recommend an 'action' (Allow, FlagForReview, BlockTransaction, SuspendAccount).
        Provide a 'reason_for_action'.
        The final output MUST be a single JSON string that includes:
        'event_id', 'fraud_score', 'risk_level', 'triggered_rules' (list of dicts),
        'anomaly_details' (list of strings), 'recommended_action', 'reason_for_action', and 'status' ('Completed').
        This structure should align with the FraudAnalysisOutput schema.
        """,
        expected_output="A single JSON string structured like the FraudAnalysisOutput schema, summarizing the comprehensive fraud assessment.",
        agent=fraud_detector_agent,
        context_tasks=[profile_task, rules_task, anomaly_task] # Depends on all previous tasks
    )
    tasks.append(assessment_task)
    return tasks


# --- Main Workflow Function (Now using CrewAI structure) ---

async def analyze_transaction_for_fraud_async(event_data_model: TransactionEventInput) -> Dict[str, Any]:
    """
    Analyzes a transaction event for fraud using a CrewAI agent and tasks.
    The actual execution of tools and LLM reasoning is mocked.
    """
    event_id = event_data_model.event_id
    logger.info(f"Agent (CrewAI): Starting fraud analysis for event ID: {event_id}, Transaction ID: {event_data_model.transaction_id}")

    event_data_dict = event_data_model.model_dump(mode='json') # For CrewAI inputs/task descriptions

    analysis_tasks = create_fraud_analysis_tasks(event_data_dict)

    fraud_analysis_crew = Crew(
        agents=[fraud_detector_agent],
        tasks=analysis_tasks,
        process=Process.sequential,
        verbose=0 # 1 or 2 for more detailed logs if using real kickoff
    )

    # --- ACTUAL CREWAI KICKOFF (Commented out for pure mock) ---
    # logger.info(f"Agent (CrewAI): Kicking off crew for fraud analysis of event {event_id}. Inputs: {event_data_dict}")
    # try:
    #     # The input dict is passed to the crew; tasks can access it via their descriptions or context.
    #     crew_result_str = fraud_analysis_crew.kickoff(inputs=event_data_dict)
    #     logger.info(f"Agent (CrewAI): Crew kickoff raw result for event '{event_id}': {crew_result_str[:500]}...")
    # except Exception as e:
    #     logger.error(f"Agent (CrewAI): Crew kickoff failed for event '{event_id}': {e}", exc_info=True)
    #     crew_result_str = json.dumps({
    #         "event_id": event_id, "status": "FailedToAnalyze", # type: ignore
    #         "reason_for_action": f"Agent workflow execution error: {str(e)}"
    #     })
    # --- END ACTUAL CREWAI KICKOFF ---

    # --- MOCKING CREW EXECUTION (Simulating the final task's output string) ---
    if True: # Keep this block for controlled mocking until LLM is fully active
        logger.warning(f"Agent (CrewAI): Using MOCKED CrewAI execution path for event {event_id}.")

        # Simulate the sequence of tool calls the agent would make
        profile_res = transaction_profile_tool.run({"customer_id": event_data_model.customer_id, "account_number": event_data_model.account_number})
        customer_profile = profile_res if profile_res.get("status") == "Success" else {"profile_data": {}} # Ensure profile_data key exists

        rules_res = rule_engine_tool.run({"transaction_event": event_data_dict, "customer_profile": customer_profile})
        triggered_rules_raw = rules_res.get("triggered_rules", [])

        anomaly_res = anomaly_detection_tool.run({"transaction_event": event_data_dict, "customer_profile": customer_profile})
        anomaly_score = anomaly_res.get("anomaly_score", 0.0)
        anomaly_factors = anomaly_res.get("contributing_factors", [])

        # Mock consolidation logic from the final task
        base_score = sum(rule.get("score_impact", 0) for rule in triggered_rules_raw)
        if anomaly_score > 0.75: base_score += 40
        elif anomaly_score > 0.5: base_score += 20
        elif anomaly_score > 0.25: base_score += 10
        final_fraud_score = min(max(base_score, 0), 100)

        risk_level_val: RiskLevel = "Low" # type: ignore
        recommended_action_val: FraudActionRecommended = "Allow" # type: ignore
        reason = "Transaction appears normal (mocked consolidation)."
        if final_fraud_score >= 80: risk_level_val, recommended_action_val, reason = "Critical", "BlockTransaction", "Critical fraud score from multiple indicators." # type: ignore
        elif final_fraud_score >= 60: risk_level_val, recommended_action_val, reason = "High", "BlockTransaction", "High fraud score." # type: ignore
        elif final_fraud_score >= 40: risk_level_val, recommended_action_val, reason = "Medium", "FlagForReview", "Medium fraud score, requires review." # type: ignore

        mock_final_assessment_dict = {
            "event_id": event_id, "analysis_timestamp": datetime.utcnow().isoformat(),
            "fraud_score": final_fraud_score, "risk_level": risk_level_val,
            "triggered_rules": [FraudRuleMatch(**r).model_dump() for r in triggered_rules_raw], # Ensure schema match
            "anomaly_details": anomaly_factors,
            "recommended_action": recommended_action_val, "reason_for_action": reason,
            "status": "Completed" # type: ignore
        }
        crew_result_str = json.dumps(mock_final_assessment_dict)
        logger.info(f"Agent (CrewAI): Mocked final JSON output for event '{event_id}': {crew_result_str[:500]}...")
    # --- END MOCKING CREW EXECUTION ---

    try:
        # The final output of a CrewAI task is a string, expected to be JSON here.
        final_analysis_dict_from_crew = json.loads(crew_result_str)
    except json.JSONDecodeError:
        logger.error(f"Agent (CrewAI): Error decoding JSON result for event '{event_id}': {crew_result_str}", exc_info=True)
        return { "event_id": event_id, "status": "FailedToAnalyze", "reason_for_action": "Agent returned malformed analysis (not JSON)." } # type: ignore
    except TypeError: # If crew_result_str is None
        logger.error(f"Agent (CrewAI): Crew returned None or non-string result for event '{event_id}'.", exc_info=True)
        return { "event_id": event_id, "status": "FailedToAnalyze", "reason_for_action": "Agent workflow returned unexpected data type." } # type: ignore

    # The mock_final_assessment_dict is already structured like FraudAnalysisOutput.
    return final_analysis_dict_from_crew


if __name__ == "__main__":
    import asyncio
    from .schemas import DeviceInformation, Geolocation # For test data

    async def test_fraud_detection_crew_workflow():
        print("--- Testing Fraud Detection Agent Workflow (Simulated CrewAI) ---")

        event1_data = TransactionEventInput(
            transaction_id="TRN_SAFE_CREW_001", customer_id="CUST-SAFE-001",
            transaction_type="CardPayment", amount=5000.00, currency="NGN", channel="WebApp",
        )
        print(f"\nTesting Low Risk Event with Crew: {event1_data.event_id}")
        analysis1 = await analyze_transaction_for_fraud_async(event1_data)
        print(f"Analysis Result 1 (Crew): Score={analysis1.get('fraud_score')}, Risk={analysis1.get('risk_level')}, Action={analysis1.get('recommended_action')}")
        # print(json.dumps(analysis1, indent=2, default=str))


        event2_data = TransactionEventInput(
            transaction_id="TRN_RISKY_CREW_002", customer_id="CUST-RISKY-002",
            transaction_type="NIPTransferOut", amount=750000.00, currency="NGN", channel="ThirdPartyAPI",
            counterparty_account_number="SUSP001", counterparty_bank_code="999",
            geolocation_info=Geolocation(city="RiskyVille", country_code="XZ"),
            metadata={"beneficiary_added_recently": True, "is_new_device_for_customer": True}
        )
        print(f"\nTesting High Risk Event with Crew: {event2_data.event_id}")
        analysis2 = await analyze_transaction_for_fraud_async(event2_data)
        print(f"Analysis Result 2 (Crew): Score={analysis2.get('fraud_score')}, Risk={analysis2.get('risk_level')}, Action={analysis2.get('recommended_action')}")
        # print(json.dumps(analysis2, indent=2, default=str))

    # To run tests:
    # logging.basicConfig(level=logging.DEBUG) # For more verbose logs
    # asyncio.run(test_fraud_detection_crew_workflow())
    print("Fraud Detection Agent logic (agent.py) updated with CrewAI Agent and Task structure (simulated CrewAI kickoff).")
