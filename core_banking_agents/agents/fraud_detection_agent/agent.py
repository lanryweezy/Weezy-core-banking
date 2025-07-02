# LangChain/CrewAI agent logic for Fraud Detection Agent

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

# Assuming schemas are in the same directory or accessible via path
from .schemas import TransactionEventInput, FraudAnalysisOutput, FraudRuleMatch, RiskLevel, FraudActionRecommended
# Import the defined tools
from .tools import transaction_profile_tool, rule_engine_tool, anomaly_detection_tool

# from crewai import Agent, Task, Crew, Process
# from langchain_community.llms.fake import FakeListLLM
# from ..core.config import core_settings

logger = logging.getLogger(__name__)

# --- Agent Definition (Placeholder for CrewAI) ---
# llm_fraud_detector = FakeListLLM(responses=[
#     "Okay, I will analyze this transaction for potential fraud.",
#     "First, I'll fetch the customer's transaction profile.",
#     "Next, I'll apply the rule engine to the transaction and profile.",
#     "Then, I'll get an anomaly score from the ML model.",
#     "Finally, I will consolidate all findings and determine a fraud score and recommendation."
# ])

# fraud_detection_tools = [transaction_profile_tool, rule_engine_tool, anomaly_detection_tool]

# fraud_detector_agent = Agent(
#     role="AI Fraud Detection Analyst",
#     goal="Proactively identify and assess fraudulent transactions by analyzing transaction events, customer profiles, applying rules, and using anomaly detection models. Provide a clear fraud score, risk level, and recommended action.",
#     backstory=(
#         "A vigilant AI system dedicated to safeguarding the bank and its customers from financial fraud. "
#         "It processes transaction events in near real-time, correlating them with historical customer behavior, "
#         "checking against known fraud patterns and rules, and leveraging machine learning to detect subtle anomalies. "
#         "Its analysis results in actionable insights for fraud prevention and mitigation."
#     ),
#     tools=fraud_detection_tools,
#     llm=llm_fraud_detector,
#     verbose=True,
#     allow_delegation=False,
# )

# --- Task Definitions (Placeholders for CrewAI) ---
# def create_fraud_analysis_tasks(transaction_event_json: str) -> List[Task]:
#     tasks = []
#     # Task 1: Profile Fetching
#     profile_task = Task(
#         description=f"Fetch the transaction profile for the customer/account associated with the transaction event: '{transaction_event_json}'. Use TransactionProfileTool.",
#         expected_output="JSON string containing the customer's transaction profile or an indication if no profile was found.",
#         agent=fraud_detector_agent, tools=[transaction_profile_tool]
#     )
#     tasks.append(profile_task)

#     # Task 2: Rule Engine Application
#     rules_task = Task(
#         description=f"Apply fraud rules to the transaction event: '{transaction_event_json}', using the customer profile obtained from the previous task. Use RuleEngineTool.",
#         expected_output="JSON string listing all triggered fraud rules and their details.",
#         agent=fraud_detector_agent, tools=[rule_engine_tool], context_tasks=[profile_task]
#     )
#     tasks.append(rules_task)

#     # Task 3: Anomaly Detection
#     anomaly_task = Task(
#         description=f"Calculate an anomaly score for the transaction event: '{transaction_event_json}', using the customer profile. Use AnomalyDetectionTool.",
#         expected_output="JSON string containing the anomaly score and contributing factors.",
#         agent=fraud_detector_agent, tools=[anomaly_detection_tool], context_tasks=[profile_task]
#     )
#     tasks.append(anomaly_task)

#     # Task 4: Final Fraud Assessment (Consolidation)
#     assessment_task = Task(
#         description="Consolidate results from profile fetching, rule engine, and anomaly detection. Calculate an overall fraud score. Determine the risk level (Low, Medium, High, Critical) and recommend an action (Allow, FlagForReview, BlockTransaction, SuspendAccount).",
#         expected_output="JSON string matching the FraudAnalysisOutput schema, detailing the comprehensive fraud assessment.",
#         agent=fraud_detector_agent, context_tasks=[profile_task, rules_task, anomaly_task]
#     )
#     tasks.append(assessment_task)
#     return tasks


# --- Main Workflow Function (Direct Tool Usage for now, to be replaced by CrewAI kickoff) ---

async def analyze_transaction_for_fraud_async(event_data: TransactionEventInput) -> Dict[str, Any]:
    """
    Simulates the fraud detection workflow by directly calling tools.
    This will eventually be replaced by CrewAI agent execution.
    """
    logger.info(f"Agent: Starting fraud analysis for event ID: {event_data.event_id}, Transaction ID: {event_data.transaction_id}")
    event_dict = event_data.model_dump(mode='json') # Ensure datetime and other types are JSON serializable for tools if needed

    # 1. Fetch Customer/Account Profile
    logger.info(f"Agent: Fetching transaction profile for customer '{event_data.customer_id}' / account '{event_data.account_number}'.")
    profile_result = transaction_profile_tool.run({
        "customer_id": event_data.customer_id,
        "account_number": event_data.account_number
    })
    customer_profile_data = profile_result.get("profile_data", {}) if profile_result.get("status") == "Success" else {}
    logger.info(f"Agent: Profile fetched. Profile found: {profile_result.get('profile_found', False)}")

    # 2. Apply Rule Engine
    logger.info(f"Agent: Applying rule engine to transaction.")
    rules_result = rule_engine_tool.run({
        "transaction_event": event_dict,
        "customer_profile": {"profile_data": customer_profile_data} # Pass the nested structure if tool expects it
    })
    triggered_rules_raw = rules_result.get("triggered_rules", [])
    # Convert to FraudRuleMatch Pydantic models for structured output
    triggered_rules_objects: List[Dict[str, Any]] = [
        FraudRuleMatch(**rule).model_dump() for rule in triggered_rules_raw
    ]
    logger.info(f"Agent: Rule engine applied. {len(triggered_rules_objects)} rules triggered.")

    # 3. Anomaly Detection
    logger.info(f"Agent: Performing anomaly detection.")
    anomaly_result = anomaly_detection_tool.run({
        "transaction_event": event_dict,
        "customer_profile": {"profile_data": customer_profile_data}
    })
    anomaly_score = anomaly_result.get("anomaly_score", 0.0)
    anomaly_factors = anomaly_result.get("contributing_factors", [])
    logger.info(f"Agent: Anomaly detection complete. Score: {anomaly_score:.3f}")

    # 4. Combine Results and Score (Simplified Scoring Logic)
    base_score = 0.0
    # Add impact from rules
    for rule in triggered_rules_objects:
        base_score += rule.get("score_impact", 0)

    # Factor in anomaly score (e.g., scale it to 0-60 range and add)
    # Anomaly score is 0-1. If high (e.g., >0.7), it's very significant.
    if anomaly_score > 0.75:
        base_score += 40
    elif anomaly_score > 0.5:
        base_score += 20
    elif anomaly_score > 0.25:
        base_score += 10

    final_fraud_score = min(max(base_score, 0), 100) # Cap score between 0 and 100

    # Determine Risk Level and Recommended Action
    risk_level: RiskLevel = "Low" # type: ignore
    recommended_action: FraudActionRecommended = "Allow" # type: ignore
    reason_for_action = "Transaction appears normal."

    if final_fraud_score >= 80:
        risk_level = "Critical" # type: ignore
        recommended_action = "BlockTransaction" # type: ignore
        reason_for_action = "Critical fraud score due to multiple high-risk indicators."
    elif final_fraud_score >= 60:
        risk_level = "High" # type: ignore
        recommended_action = "BlockTransaction" # type: ignore
        reason_for_action = "High fraud score indicating significant risk."
    elif final_fraud_score >= 40:
        risk_level = "Medium" # type: ignore
        recommended_action = "FlagForReview" # type: ignore
        reason_for_action = "Medium fraud score warrants further review."
    elif final_fraud_score >= 20:
        risk_level = "Low" # type: ignore
        recommended_action = "Allow" # type: ignore
        reason_for_action = "Low fraud score, transaction appears to be low risk."

    if not triggered_rules_objects and anomaly_score < 0.2:
        reason_for_action = "No specific rules triggered and low anomaly score."


    logger.info(f"Agent: Final assessment for event {event_data.event_id} - Score: {final_fraud_score}, Risk: {risk_level}, Action: {recommended_action}")

    # Compile into FraudAnalysisOutput structure (as a dictionary)
    analysis_output_dict = {
        "event_id": event_data.event_id,
        # analysis_id and analysis_timestamp will be set by Pydantic model default_factory
        "fraud_score": final_fraud_score,
        "risk_level": risk_level,
        "triggered_rules": triggered_rules_objects, # List of dicts
        "anomaly_details": anomaly_factors,
        "recommended_action": recommended_action,
        "reason_for_action": reason_for_action,
        "status": "Completed" # type: ignore
    }

    return analysis_output_dict


if __name__ == "__main__":
    import asyncio
    from .schemas import DeviceInformation, Geolocation # For test data

    async def test_fraud_detection_workflow():
        print("--- Testing Fraud Detection Agent Workflow (Direct Tool Usage) ---")

        # Test Case 1: Low risk transaction
        event1_data = TransactionEventInput(
            transaction_id="TRN_SAFE_001", customer_id="CUST-SAFE-001", account_number="1234509876",
            transaction_type="CardPayment", amount=5000.00, currency="NGN", channel="WebApp",
            device_info=DeviceInformation(device_id="DEV_WEB_001", ip_address="192.168.1.10"),
            geolocation_info=Geolocation(city="Lagos", country_code="NG"),
            metadata={"merchant_category_code": "5411"} # Groceries
        )
        print(f"\nTesting Low Risk Event: {event1_data.event_id}")
        analysis1 = await analyze_transaction_for_fraud_async(event1_data)
        print(f"Analysis Result 1: Score={analysis1.get('fraud_score')}, Risk={analysis1.get('risk_level')}, Action={analysis1.get('recommended_action')}")
        print(f"  Triggered Rules: {json.dumps(analysis1.get('triggered_rules'), indent=2)}")
        print(f"  Anomaly Details: {analysis1.get('anomaly_details')}")


        # Test Case 2: High risk transaction
        event2_data = TransactionEventInput(
            transaction_id="TRN_RISKY_002", customer_id="CUST-RISKY-002", account_number="0987654321",
            transaction_type="NIPTransferOut", amount=750000.00, currency="NGN", channel="ThirdPartyAPI",
            counterparty_account_number="SUSP001", counterparty_bank_code="999", counterparty_name="Shady Co.",
            device_info=DeviceInformation(device_id="DEV_API_005", ip_address="203.0.113.45"), # Potentially risky IP
            geolocation_info=Geolocation(city="RiskyVille", country_code="XZ"), # Fictional risky country
            metadata={"beneficiary_added_recently": True, "is_new_device_for_customer": True}
        )
        print(f"\nTesting High Risk Event: {event2_data.event_id}")
        analysis2 = await analyze_transaction_for_fraud_async(event2_data)
        print(f"Analysis Result 2: Score={analysis2.get('fraud_score')}, Risk={analysis2.get('risk_level')}, Action={analysis2.get('recommended_action')}")
        print(f"  Triggered Rules: {json.dumps(analysis2.get('triggered_rules'), indent=2)}")
        print(f"  Anomaly Details: {analysis2.get('anomaly_details')}")

        # Test Case 3: Dormant account activity
        event3_data = TransactionEventInput(
            transaction_id="TRN_DORMANT_003", customer_id="CUST-DORMANT-003", account_number="1122334455",
            transaction_type="ATMWithdrawal", amount=150000.00, currency="NGN", channel="ATM",
            device_info=DeviceInformation(ip_address="196.46.244.10"), # ATM IP
            geolocation_info=Geolocation(city="Ibadan", country_code="NG"),
        )
        print(f"\nTesting Dormant Account Activity Event: {event3_data.event_id}")
        analysis3 = await analyze_transaction_for_fraud_async(event3_data)
        print(f"Analysis Result 3: Score={analysis3.get('fraud_score')}, Risk={analysis3.get('risk_level')}, Action={analysis3.get('recommended_action')}")
        print(f"  Triggered Rules: {json.dumps(analysis3.get('triggered_rules'), indent=2)}")
        print(f"  Anomaly Details: {analysis3.get('anomaly_details')}")

    # asyncio.run(test_fraud_detection_workflow())
    print("Fraud Detection Agent logic (agent.py). Contains workflow to analyze transactions using tools (mocked execution).")
