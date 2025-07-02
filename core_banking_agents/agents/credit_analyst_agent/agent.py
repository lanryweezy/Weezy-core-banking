# LangChain/CrewAI agent logic for Credit Analyst Agent

from typing import Dict, Any, List
from datetime import datetime, date
import logging
import json

# Assuming schemas are in the same directory or accessible via path
from .schemas import LoanApplicationInput, DocumentProof, LoanAssessmentOutput, DocumentAnalysisResult, CreditBureauReportSummary, RiskAssessmentResult, LoanDecisionType
# Import the defined tools
from .tools import document_analysis_tool, credit_scoring_tool, risk_rules_tool

# from crewai import Agent, Task, Crew, Process
# from langchain_community.llms.fake import FakeListLLM
# from ..core.config import core_settings

logger = logging.getLogger(__name__)

# --- Agent Definition (Placeholder for CrewAI) ---
# llm_credit_analyst = FakeListLLM(responses=[
#     "Okay, I will start by analyzing the submitted documents.",
#     "Documents analyzed. Now, I will perform credit scoring.",
#     "Credit scoring complete. Proceeding to apply risk rules.",
#     "Risk rules applied. Compiling the final assessment."
# ])

# credit_analyst_tools = [document_analysis_tool, credit_scoring_tool, risk_rules_tool]

# credit_analyst_ai_agent = Agent(
#     role="AI Credit Analyst",
#     goal="Assess loan applications by analyzing documents, running credit scores, and applying risk rules to make informed recommendations (Approve, Reject, ConditionalApproval, Refer).",
#     backstory=(
#         "A sophisticated AI agent designed to support or automate parts of the loan approval process for a Nigerian bank. "
#         "It meticulously examines applicant information and financial documents, leverages credit scoring models, "
#         "and evaluates applications against the bank's risk policies to ensure sound lending decisions."
#     ),
#     tools=credit_analyst_tools,
#     llm=llm_credit_analyst,
#     verbose=True,
#     allow_delegation=False, # Typically, this agent follows a structured analytical flow
# )

# --- Task Definitions (Placeholders for CrewAI) ---
# def create_credit_analysis_tasks(application_input_json: str) -> List[Task]:
#     tasks = []
#     # Task 1: Document Analysis (could be one task or broken down if documents are very different)
#     doc_analysis_task = Task(
#         description=f"Analyze all submitted documents for the loan application provided in the JSON input: '{application_input_json}'. Use the DocumentAnalysisTool for each document. Consolidate the findings.",
#         expected_output="A JSON string containing a list of document analysis results, each with 'document_id', 'status', and 'extracted_data'.",
#         agent=credit_analyst_ai_agent,
#         tools=[document_analysis_tool]
#     )
#     tasks.append(doc_analysis_task)

#     # Task 2: Credit Scoring (would use context from application_input_json and doc_analysis_task output)
#     credit_scoring_task = Task(
#         description=f"Perform credit scoring for the applicant based on their details in '{application_input_json}' and the document analysis results (from previous task). Use the CreditScoringTool.",
#         expected_output="A JSON string with 'applicant_id', 'credit_score', 'risk_level', and 'assessment_details'.",
#         agent=credit_analyst_ai_agent,
#         tools=[credit_scoring_tool],
#         context=[doc_analysis_task] # Depends on doc_analysis_task
#     )
#     tasks.append(credit_scoring_task)

#     # Task 3: Risk Rules Application
#     risk_rules_task = Task(
#         description=f"Apply bank's risk rules to the loan application ('{application_input_json}') using the credit scoring results (from previous task). Use the RiskRulesTool.",
#         expected_output="A JSON string with 'passed_rules', 'failed_rules', and 'overall_risk_assessment_from_rules'.",
#         agent=credit_analyst_ai_agent,
#         tools=[risk_rules_tool],
#         context=[credit_scoring_task] # Depends on credit_scoring_task
#     )
#     tasks.append(risk_rules_task)

#     # Task 4: Final Assessment Compilation
#     final_assessment_compilation_task = Task(
#         description="Compile all previous results (document analysis, credit score, risk rules) into a comprehensive loan assessment report. Determine a final decision (Approved, Rejected, ConditionalApproval, PendingReview) and provide reasons and any conditions.",
#         expected_output="A JSON string matching the LoanAssessmentOutput schema, summarizing the entire analysis and final decision.",
#         agent=credit_analyst_ai_agent,
#         # This task might not use tools directly but synthesizes information.
#         context=tasks # Depends on all previous tasks
#     )
#     tasks.append(final_assessment_compilation_task)
#     return tasks


# --- Main Workflow Function (Direct Tool Usage for now, to be replaced by CrewAI kickoff) ---

async def start_credit_analysis_workflow_async(application_id: str, application_data: LoanApplicationInput) -> Dict[str, Any]:
    """
    Simulates the credit analysis workflow by directly calling tools.
    This will eventually be replaced by CrewAI agent execution.
    """
    logger.info(f"Agent: Starting credit analysis workflow for application ID: {application_id}")

    # 1. Document Analysis
    doc_analysis_results_list: List[Dict[str, Any]] = [] # For LoanAssessmentOutput schema
    all_extracted_doc_data: Dict[str, Any] = {} # To compile for financial summary

    for doc_proof in application_data.submitted_documents:
        logger.info(f"Agent: Analyzing document '{doc_proof.document_type_name}' (Category: {doc_proof.document_category}) for app ID {application_id}")
        # tool_input = {"document_url": str(doc_proof.file_url), "document_category": doc_proof.document_category.value} # If DocumentCategory is Enum
        tool_input = {"document_url": doc_proof.file_url, "document_category": doc_proof.document_category}

        analysis_result = document_analysis_tool.run(tool_input)

        doc_analysis_results_list.append({
            "document_id": doc_proof.document_id,
            "document_category": analysis_result.get("document_category_processed", doc_proof.document_category),
            "status": "Processed" if analysis_result.get("status") == "Success" else "ProcessingFailed",
            "key_extractions": analysis_result.get("extracted_data"),
            "validation_summary": analysis_result.get("error_message") if analysis_result.get("status") == "Failed" else "Mock document analysis successful."
        })
        if analysis_result.get("status") == "Success" and analysis_result.get("extracted_data"):
            # Merge extracted data, prioritizing more specific sources if conflicts (not handled in this simple merge)
            all_extracted_doc_data.update(analysis_result.get("extracted_data", {}))

    logger.info(f"Agent: Document analysis phase complete for {application_id}. Results: {len(doc_analysis_results_list)} documents processed.")

    # 2. Compile Financial Summary (Simplified)
    # In a real system, this would be more sophisticated, reconciling data from multiple sources.
    financial_summary = {
        "monthly_income_ngn": application_data.applicant_details.monthly_income_ngn or all_extracted_doc_data.get("net_monthly_pay_ngn", 0),
        "total_existing_debt_ngn": all_extracted_doc_data.get("total_outstanding_debt_ngn", random.uniform(0, 500000)), # Mocked existing debt
        "credit_history_length_months": all_extracted_doc_data.get("credit_history_length_months", random.randint(6, 60)), # Mocked
        "bureau_score_if_any": all_extracted_doc_data.get("bureau_score", None) # If a tool provided this
    }
    # Add any other relevant fields from application_data or all_extracted_doc_data
    financial_summary["applicant_id"] = application_data.applicant_details.applicant_id or application_id

    logger.info(f"Agent: Compiled financial summary for {application_id}: {financial_summary}")

    # 3. Credit Scoring
    logger.info(f"Agent: Performing credit scoring for {application_id}")
    credit_score_input = {"applicant_id": financial_summary["applicant_id"], "financial_summary": financial_summary}
    credit_score_result = credit_scoring_tool.run(credit_score_input)
    logger.info(f"Agent: Credit scoring complete for {application_id}. Score: {credit_score_result.get('credit_score')}, Risk: {credit_score_result.get('risk_level')}")

    # Prepare CreditBureauReportSummary for output (mocked from credit score result)
    mock_bureau_summary = CreditBureauReportSummary(
        bureau_name="Mock Combined Bureau",
        credit_score=credit_score_result.get("credit_score"),
        summary_narrative=credit_score_result.get("assessment_details")
    ).model_dump()


    # 4. Risk Rules Application
    logger.info(f"Agent: Applying risk rules for {application_id}")
    # Pass application_data as dict and credit_score_result as dict
    risk_rules_input = {"application_data": application_data.model_dump(), "credit_score_result": credit_score_result}
    risk_rules_result = risk_rules_tool.run(risk_rules_input)
    logger.info(f"Agent: Risk rules application complete for {application_id}. Assessment: {risk_rules_result.get('overall_risk_assessment_from_rules')}")

    # Prepare RiskAssessmentResult for output
    mock_risk_assessment = RiskAssessmentResult(
        overall_risk_rating=credit_score_result.get("risk_level", "Medium"), # type: ignore # Use score's risk level or rules'
        key_risk_factors=risk_rules_result.get("failed_rules", [])
    ).model_dump()
    if risk_rules_result.get("overall_risk_assessment_from_rules") == "Reject":
        mock_risk_assessment["overall_risk_rating"] = "High" # Override if rules dictate rejection


    # 5. Compile Final Assessment (into LoanAssessmentOutput structure)
    logger.info(f"Agent: Compiling final assessment for {application_id}")

    final_decision: LoanDecisionType = "PendingReview" # type: ignore
    decision_reason = "Further review required by credit officer."
    approved_amount = None
    approved_tenor = None
    approved_rate = None
    conditions: Optional[List[str]] = None

    rules_assessment = risk_rules_result.get("overall_risk_assessment_from_rules")
    applicant_score = credit_score_result.get("credit_score", 0)

    if rules_assessment == "Accept":
        final_decision = "Approved" # type: ignore
        decision_reason = "Application meets all automated credit criteria."
        approved_amount = application_data.loan_amount_requested_ngn # Mock: approve full amount
        approved_tenor = application_data.requested_loan_tenor_months
        approved_rate = 20.0 + random.uniform(-2.0, 2.0) # Mock rate
    elif rules_assessment == "Reject":
        final_decision = "Rejected" # type: ignore
        decision_reason = f"Application did not meet critical risk rules. Failed rules: {', '.join(risk_rules_result.get('failed_rules',[]))}"
    elif rules_assessment == "Refer":
        final_decision = "ConditionalApproval" # type: ignore # Or "PendingReview" / "InformationRequested"
        decision_reason = f"Application requires manual review due to rule flags: {', '.join(risk_rules_result.get('failed_rules',[]))}. Possible conditional approval."
        # Example condition
        if "DTIRatio" in str(risk_rules_result.get("failed_rules",[])):
            conditions = ["Reduce loan amount or provide proof of additional income."]
        elif applicant_score < 650 : # Example for conditional
             conditions = ["Provide suitable guarantor or collateral."]
        approved_amount = application_data.loan_amount_requested_ngn * 0.8 # Offer less
        approved_tenor = application_data.requested_loan_tenor_months
        approved_rate = 22.5 + random.uniform(-1.0, 3.0)


    assessment_output_dict = {
        "application_id": application_id,
        # assessment_id is auto-generated by Pydantic model default_factory
        "assessment_timestamp": datetime.utcnow(),
        "decision": final_decision,
        "decision_reason": decision_reason,
        "approved_loan_amount_ngn": approved_amount,
        "approved_loan_tenor_months": approved_tenor,
        "approved_interest_rate_pa": round(approved_rate,2) if approved_rate else None,
        "conditions_for_approval": conditions,
        "document_analysis_summary": [DocumentAnalysisResult(**das).model_dump() for das in doc_analysis_results_list], # Parse to ensure schema match
        "credit_bureau_summary": mock_bureau_summary, # Already a dict
        "risk_assessment_summary": mock_risk_assessment, # Already a dict
    }

    logger.info(f"Agent: Final assessment compiled for {application_id}. Decision: {final_decision}")
    # This dictionary structure should be compatible with LoanAssessmentOutput for FastAPI response
    return assessment_output_dict


# Placeholder for getting status if workflow was truly async and stateful via agent memory
# async def get_loan_assessment_from_workflow(application_id: str) -> Optional[Dict[str, Any]]:
#    logger.info(f"Agent: Requesting status for application {application_id} (mocked).")
#    # This would query a persistent store updated by the agent/crew.
#    return MOCK_LOAN_APPLICATIONS_DB.get(application_id) # Example if agent updated a shared dict

if __name__ == "__main__":
    import asyncio
    from .schemas import ApplicantInformation # For constructing test input

    async def test_credit_analyst_workflow():
        print("--- Testing Credit Analyst Agent Workflow (Direct Tool Usage) ---")

        test_app_data = LoanApplicationInput(
            applicant_details=ApplicantInformation(
                first_name="Test", last_name="Applicant", date_of_birth=date(1985, 1, 1),
                email="test.applicant@example.com", phone_number="08012345670",
                bvn="12312312312", current_address="1 Test Street, Lagos",
                employment_status="FullTime", monthly_income_ngn=600000.00
            ),
            loan_amount_requested_ngn=500000.00,
            loan_purpose="PersonalUse",
            requested_loan_tenor_months=12,
            submitted_documents=[
                DocumentProof(document_type_name="Payslip July", document_category="IncomeProof", file_url=HttpUrl("http://example.com/payslip.pdf")),
                DocumentProof(document_type_name="National ID Front", document_category="Identification", file_url=HttpUrl("http://example.com/national_id.jpg")),
                DocumentProof(document_type_name="6M Bank Statement", document_category="BankStatement", file_url=HttpUrl("http://example.com/statement.pdf"))
            ]
        )
        test_app_id = test_app_data.application_id

        print(f"\nTesting with Application ID: {test_app_id}")
        assessment_result = await start_credit_analysis_workflow_async(test_app_id, test_app_data)

        print("\n--- Final Assessment Result from Agent Workflow ---")
        print(json.dumps(assessment_result, indent=2, default=str)) # Use default=str for datetime/date

        # Validate if it can be parsed by LoanAssessmentOutput
        try:
            parsed_output = LoanAssessmentOutput(**assessment_result)
            print("\nSuccessfully parsed agent output into LoanAssessmentOutput schema.")
            # print(parsed_output.model_dump_json(indent=2))
        except Exception as e:
            print(f"\nError parsing agent output into LoanAssessmentOutput schema: {e}")

    # asyncio.run(test_credit_analyst_workflow())
    print("Credit Analyst Agent logic (agent.py). Contains workflow to analyze loan applications using tools (mocked execution).")
