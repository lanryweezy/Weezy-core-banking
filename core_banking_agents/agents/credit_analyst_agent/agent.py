# LangChain/CrewAI agent logic for Credit Analyst Agent

from typing import Dict, Any, List, Optional
from datetime import datetime, date
import logging
import json

from .schemas import (
    LoanApplicationInput, DocumentProof, LoanAssessmentOutput,
    DocumentAnalysisResult, CreditBureauReportSummary, RiskAssessmentResult, LoanDecisionType
)
from .tools import document_analysis_tool, credit_scoring_tool, risk_rules_tool

from crewai import Agent, Task, Crew, Process
from langchain_community.llms.fake import FakeListLLM
# from ..core.config import core_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- LLM Configuration (Mocked for CrewAI) ---
# Responses for document analysis, scoring, rules, and final compilation.
mock_llm_credit_analyst_responses = [
    "Okay, I will start by analyzing all submitted documents for this loan application using DocumentAnalysisTool for each.", # Doc Analysis Task
    "Document analysis complete. Now, I will compile a financial summary and perform credit scoring using CreditScoringTool.", # Credit Scoring Task
    "Credit scoring complete. Proceeding to apply the bank's risk rules using RiskRulesTool.", # Risk Rules Task
    "All checks (documents, score, rules) are done. Now I will compile the final loan assessment, determine a decision, and provide reasons and conditions." # Final Assessment Task
] * 2 # Multiply for buffer
llm_credit_analyst = FakeListLLM(responses=mock_llm_credit_analyst_responses)

# --- Agent Definition ---
credit_analyst_tools = [document_analysis_tool, credit_scoring_tool, risk_rules_tool]

credit_analyst_ai_agent = Agent(
    role="AI Credit Analyst",
    goal="Assess loan applications by analyzing documents, running credit scores, and applying risk rules to make informed recommendations (Approve, Reject, ConditionalApproval, PendingReview).",
    backstory=(
        "A sophisticated AI agent designed to support or automate parts of the loan approval process for a Nigerian bank. "
        "It meticulously examines applicant information and financial documents, leverages credit scoring models, "
        "and evaluates applications against the bank's risk policies to ensure sound lending decisions."
    ),
    tools=credit_analyst_tools,
    llm=llm_credit_analyst,
    verbose=1, # Set to 1 or 2 for more details
    allow_delegation=False,
)

# --- Task Definitions for CrewAI ---
def create_credit_analysis_tasks(application_input_dict: Dict[str, Any]) -> List[Task]:
    tasks: List[Task] = []
    application_input_json = json.dumps(application_input_dict) # For task descriptions

    # Task 1: Document Analysis
    # This task might internally loop or call the tool multiple times if the LLM decides to.
    # Or, a more complex agent setup could have a "document processing manager" agent.
    # For this setup, we assume the agent given the list of documents will process them.
    doc_analysis_task = Task(
        description=f"""\
        Analyze ALL submitted documents for the loan application provided in this JSON input: '{application_input_json}'.
        The 'submitted_documents' key contains a list of documents, each with 'file_url' and 'document_category'.
        For EACH document, use the DocumentAnalysisTool.
        Consolidate all findings from each document analysis into a single list of results.
        """,
        expected_output="""\
        A JSON string containing a list of document analysis results. Each item in the list should be a dictionary
        with 'document_id' (from the input document), 'document_category_processed', 'status',
        'extracted_data' (or 'error_message' if failed).
        Example: '[{ "document_id": "DOC-XYZ", "document_category_processed": "IncomeProof", "status": "Success", "extracted_data": {...} }, ...]'
        """,
        agent=credit_analyst_ai_agent,
        # tools=[document_analysis_tool] # Agent already has this tool
    )
    tasks.append(doc_analysis_task)

    # Task 2: Credit Scoring
    credit_scoring_task = Task(
        description=f"""\
        Perform credit scoring for the applicant.
        The initial application data is in: '{application_input_json}'.
        The results of document analysis (from the previous task) will also be available in the context.
        Compile a 'financial_summary' for the applicant using data from both the application input
        (e.g., 'applicant_details.monthly_income_ngn') and any relevant 'extracted_data' from the document analysis
        (e.g., average bank balance, detected salary from bank statements, existing debts from credit reports if available).
        Then, use the CreditScoringTool with the applicant's ID and this compiled 'financial_summary'.
        """,
        expected_output="""\
        A JSON string containing the credit scoring result:
        {'applicant_id': ..., 'credit_score': ..., 'risk_level': ..., 'assessment_details': ..., 'model_version': ...}.
        """,
        agent=credit_analyst_ai_agent,
        context_tasks=[doc_analysis_task]
    )
    tasks.append(credit_scoring_task)

    # Task 3: Risk Rules Application
    risk_rules_task = Task(
        description=f"""\
        Apply the bank's risk rules to the loan application.
        The initial application data is in: '{application_input_json}'.
        The credit scoring results (from the previous task) will be available in the context.
        Use the RiskRulesTool, passing it the application data and the credit score result.
        """,
        expected_output="""\
        A JSON string detailing the outcome of risk rule checks:
        {'passed_rules': [...], 'failed_rules': [...], 'overall_risk_assessment_from_rules': ("Accept", "Reject", "Refer"), ...}.
        """,
        agent=credit_analyst_ai_agent,
        context_tasks=[credit_scoring_task]
    )
    tasks.append(risk_rules_task)

    # Task 4: Final Assessment Compilation
    final_assessment_compilation_task = Task(
        description=f"""\
        Compile all previous analysis results (document analysis, credit score, risk rules checks)
        for the loan application originally detailed in '{application_input_json}'.
        Based on all gathered information, determine a final loan 'decision' (e.g., 'Approved', 'Rejected', 'ConditionalApproval').
        Provide a 'decision_reason'.
        If 'Approved' or 'ConditionalApproval', specify 'approved_loan_amount_ngn', 'approved_loan_tenor_months', and 'approved_interest_rate_pa'.
        If 'ConditionalApproval', list any 'conditions_for_approval'.
        If more information is needed, set decision to 'InformationRequested' and list 'required_further_documents'.
        Structure this final assessment to align with the LoanAssessmentOutput schema.
        The output MUST be a single JSON string representing this comprehensive loan assessment.
        Include 'application_id', 'assessment_timestamp', and summaries of document analysis, credit bureau (mocked from score), and risk assessment.
        """,
        expected_output="A single JSON string that strictly matches the structure of the LoanAssessmentOutput schema.",
        agent=credit_analyst_ai_agent,
        context_tasks=[doc_analysis_task, credit_scoring_task, risk_rules_task] # Depends on all previous tasks
    )
    tasks.append(final_assessment_compilation_task)
    return tasks


# --- Main Workflow Function (Now using CrewAI structure) ---

async def start_credit_analysis_workflow_async(application_id: str, application_data_model: LoanApplicationInput) -> Dict[str, Any]:
    """
    Simulates the credit analysis workflow using a CrewAI structure.
    The actual execution of tools and LLM reasoning is mocked.
    """
    logger.info(f"Agent (CrewAI): Starting credit analysis for application ID: {application_id}")

    application_input_dict = application_data_model.model_dump(mode='json') # For CrewAI inputs/task descriptions

    analysis_tasks = create_credit_analysis_tasks(application_input_dict)

    credit_analysis_crew = Crew(
        agents=[credit_analyst_ai_agent],
        tasks=analysis_tasks,
        process=Process.sequential,
        verbose=0 # Set to 1 or 2 for detailed CrewAI logs if using real kickoff
    )

    # --- ACTUAL CREWAI KICKOFF (Commented out for pure mock, uncomment for FakeListLLM test) ---
    # logger.info(f"Agent (CrewAI): Kicking off crew for application {application_id}. Inputs: {application_input_dict}")
    # try:
    #     # The input dict is passed to the crew; tasks can access it or parts of it via their descriptions or context.
    #     # For tasks expecting specific JSON strings in description, those are already interpolated.
    #     crew_result_str = credit_analysis_crew.kickoff(inputs=application_input_dict)
    #     logger.info(f"Agent (CrewAI): Crew kickoff raw result for app '{application_id}': {crew_result_str[:500]}...")
    # except Exception as e:
    #     logger.error(f"Agent (CrewAI): Crew kickoff failed for app '{application_id}': {e}", exc_info=True)
    #     # Fallback to a basic error structure if kickoff fails
    #     crew_result_str = json.dumps({
    #         "application_id": application_id, "decision": "PendingReview", # type: ignore
    #         "decision_reason": f"Agent workflow execution error: {str(e)}",
    #         "assessment_timestamp": datetime.utcnow().isoformat()
    #     })
    # --- END ACTUAL CREWAI KICKOFF ---

    # --- MOCKING CREW EXECUTION (Simulating the final task's output string) ---
    if True: # Keep this block for controlled mocking until LLM is fully active
        logger.warning(f"Agent (CrewAI): Using MOCKED CrewAI execution path for application {application_id}.")

        # Simulate the sequence of tool calls the agent would make based on tasks
        doc_analysis_results_list = []
        all_extracted_doc_data = {}
        for doc_proof_dict in application_input_dict.get("submitted_documents", []):
            analysis_result = document_analysis_tool.run({
                "document_url": doc_proof_dict["file_url"],
                "document_category": doc_proof_dict["document_category"]
            })
            doc_analysis_results_list.append({
                "document_id": doc_proof_dict["document_id"],
                "document_category": analysis_result.get("document_category_processed", doc_proof_dict["document_category"]),
                "status": "Processed" if analysis_result.get("status") == "Success" else "ProcessingFailed",
                "key_extractions": analysis_result.get("extracted_data"),
                "validation_summary": analysis_result.get("error_message") # or a success message
            })
            if analysis_result.get("status") == "Success":
                all_extracted_doc_data.update(analysis_result.get("extracted_data", {}))

        financial_summary = {
            "monthly_income_ngn": application_input_dict.get("applicant_details",{}).get("monthly_income_ngn") or all_extracted_doc_data.get("net_monthly_pay_ngn", 0),
            "total_existing_debt_ngn": all_extracted_doc_data.get("total_outstanding_debt_ngn", random.uniform(0,100000)),
            "applicant_id": application_input_dict.get("applicant_details",{}).get("applicant_id") or application_id
        }
        credit_score_result = credit_scoring_tool.run({"applicant_id": financial_summary["applicant_id"], "financial_summary": financial_summary})

        risk_rules_result = risk_rules_tool.run({"application_data": application_input_dict, "credit_score_result": credit_score_result})

        # Mock consolidation by the final task
        mock_final_assessment_dict = {
            "application_id": application_id,
            "assessment_id": f"ASSESS-MOCK-{uuid.uuid4().hex[:6].upper()}",
            "assessment_timestamp": datetime.utcnow().isoformat(),
            "decision": risk_rules_result.get("overall_risk_assessment_from_rules", "PendingReview").capitalize(), # Align with LoanDecisionType
            "decision_reason": f"Mock assessment based on rules: {risk_rules_result.get('overall_risk_assessment_from_rules')}. Score: {credit_score_result.get('credit_score')}",
            "approved_loan_amount_ngn": application_input_dict.get("loan_amount_requested_ngn") if risk_rules_result.get("overall_risk_assessment_from_rules") == "Accept" else None,
            "approved_loan_tenor_months": application_input_dict.get("requested_loan_tenor_months") if risk_rules_result.get("overall_risk_assessment_from_rules") == "Accept" else None,
            "approved_interest_rate_pa": 21.75 if risk_rules_result.get("overall_risk_assessment_from_rules") == "Accept" else None,
            "conditions_for_approval": ["Mock condition: verify address again."] if risk_rules_result.get("overall_risk_assessment_from_rules") == "Refer" else None,
            "document_analysis_summary": doc_analysis_results_list,
            "credit_bureau_summary": {"bureau_name": "Mock Bureau via Scoring", "credit_score": credit_score_result.get("credit_score"), "summary_narrative": credit_score_result.get("assessment_details"), "report_date": date.today().isoformat()},
            "risk_assessment_summary": {"overall_risk_rating": credit_score_result.get("risk_level", "Medium").capitalize(), "key_risk_factors": risk_rules_result.get("failed_rules")}
        }
        # Adjust decision for Pydantic Literal
        if mock_final_assessment_dict["decision"] == "Accept": mock_final_assessment_dict["decision"] = "Approved"
        if mock_final_assessment_dict["decision"] == "Refer": mock_final_assessment_dict["decision"] = "ConditionalApproval"

        crew_result_str = json.dumps(mock_final_assessment_dict)
        logger.info(f"Agent (CrewAI): Mocked final JSON output for app '{application_id}': {crew_result_str[:500]}...")
    # --- END MOCKING CREW EXECUTION ---

    try:
        # The final output of a CrewAI task is a string, expected to be JSON here.
        final_assessment_dict_from_crew = json.loads(crew_result_str)
    except json.JSONDecodeError:
        logger.error(f"Agent (CrewAI): Error decoding JSON result for app '{application_id}': {crew_result_str}", exc_info=True)
        return { # Return a structure that can inform main.py of an error
            "application_id": application_id, "decision": "PendingReview",
            "decision_reason": "Agent returned malformed assessment (not JSON). Requires manual check.",
            "assessment_timestamp": datetime.utcnow().isoformat() # Ensure this is present
        }
    except TypeError: # If crew_result_str is None
        logger.error(f"Agent (CrewAI): Crew returned None or non-string result for app '{application_id}'.", exc_info=True)
        return {
            "application_id": application_id, "decision": "PendingReview",
            "decision_reason": "Agent workflow returned unexpected data type. Requires manual check.",
            "assessment_timestamp": datetime.utcnow().isoformat()
        }

    # Ensure the returned dictionary is compatible with LoanAssessmentOutput schema for FastAPI
    # The mock_final_assessment_dict is already structured like LoanAssessmentOutput.
    return final_assessment_dict_from_crew


if __name__ == "__main__":
    import asyncio
    from .schemas import ApplicantInformation # For constructing test input

    async def test_credit_analyst_crew_workflow():
        print("--- Testing Credit Analyst Agent Workflow (Simulated CrewAI) ---")

        test_app_data = LoanApplicationInput(
            # application_id will be auto-generated by Pydantic default_factory
            applicant_details=ApplicantInformation(
                first_name="CrewTest", last_name="ApplicantCA", date_of_birth=date(1990, 3, 15),
                email="crew.test.ca@example.com", phone_number="08099887766",
                bvn="33445566778", current_address="10 Agent Avenue, Lagos",
                employment_status="SelfEmployed", monthly_income_ngn=850000.00
            ),
            loan_amount_requested_ngn=1200000.00,
            loan_purpose="BusinessExpansion",
            requested_loan_tenor_months=18,
            submitted_documents=[
                DocumentProof(document_type_name="CAC Docs", document_category="BusinessDocument", file_url=HttpUrl("http://example.com/cac.pdf")),
                DocumentProof(document_type_name="Bank Statement Last 6M", document_category="BankStatement", file_url=HttpUrl("http://example.com/statement_biz.pdf")),
                DocumentProof(document_type_name="Driver's License", document_category="Identification", file_url=HttpUrl("http://example.com/dl_crew.jpg"))
            ]
        )
        test_app_id_for_agent = test_app_data.application_id # Get the auto-generated ID

        print(f"\nTesting with Application ID: {test_app_id_for_agent}")
        assessment_result_dict = await start_credit_analysis_workflow_async(test_app_id_for_agent, test_app_data)

        print("\n--- Final Assessment Result from Agent Workflow (Simulated CrewAI) ---")
        print(json.dumps(assessment_result_dict, indent=2, default=str))

        # Validate if it can be parsed by LoanAssessmentOutput
        try:
            parsed_output = LoanAssessmentOutput(**assessment_result_dict)
            print("\nSuccessfully parsed agent output into LoanAssessmentOutput schema.")
            # print(parsed_output.model_dump_json(indent=2))
        except Exception as e:
            print(f"\nError parsing agent output into LoanAssessmentOutput schema: {e}")

    # To run tests:
    # logging.basicConfig(level=logging.DEBUG) # For more verbose logs
    # asyncio.run(test_credit_analyst_crew_workflow())
    print("Credit Analyst Agent logic (agent.py) updated with CrewAI Agent and Task structure (simulated CrewAI kickoff, direct tool calls for mock output).")
