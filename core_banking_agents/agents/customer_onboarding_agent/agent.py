# LangChain/CrewAI agent logic for Customer Onboarding

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .schemas import OnboardingRequest, VerificationStepResult, VerificationStatus, DocumentType, AccountTier
from .tools import nin_bvn_verification_tool, ocr_tool, face_match_tool, aml_screening_tool, document_validation_tool

from crewai import Agent, Task, Crew, Process
from langchain_community.llms.fake import FakeListLLM

logger = logging.getLogger(__name__)
# Ensure logger is configured, e.g. by basicConfig in main or if run directly
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- LLM Configuration (Mocked for CrewAI) ---
# This list needs to be carefully constructed. Each string represents an LLM call's output.
# For a task using a tool: the FakeListLLM response should be the *JSON string representation of that tool's output*.
# The final_assessment_task's response is the *final consolidated JSON string*.

MOCK_BVN_NIN_TOOL_OUTPUT_STR = json.dumps({
    "bvn_verification": {"status": "Verified", "bvn_status": "Verified", "bvn_details": {"message": "BVN mock verified", "matched_data": {"firstName": "CrewTest", "lastName": "TierTwo", "dateOfBirth": "1995-02-10"}}},
    "nin_verification": {"status": "Verified", "nin_status": "Verified", "nin_details": {"message": "NIN mock verified"}}
})
MOCK_ID_OCR_TOOL_OUTPUT_STR = json.dumps({"status": "Success", "extracted_data": {"first_name": "CrewTest", "last_name": "TierTwo", "nin": "34343434344", "date_of_birth": "1995-02-10", "document_type": "NationalID"}})
MOCK_ID_VALIDATION_TOOL_OUTPUT_STR = json.dumps({"validation_status": "Valid", "checks_passed": ["Mock ID format check passed", "Name on ID matches applicant data."], "validation_issues": []})

MOCK_UTILITY_OCR_TOOL_OUTPUT_STR = json.dumps({"status": "Success", "extracted_data": {"address": "2 Crew Avenue, Lagos", "document_type": "UtilityBill", "bill_date": "2023-10-01"}})
MOCK_UTILITY_VALIDATION_TOOL_OUTPUT_STR = json.dumps({"validation_status": "Valid", "checks_passed": ["Mock Utility Bill address matches", "Utility bill date is recent."], "validation_issues": []})

MOCK_FACE_MATCH_TOOL_OUTPUT_STR = json.dumps({"status": "Success", "is_match": True, "match_score": 0.92, "confidence": "High", "message": "Face match successful."})
MOCK_AML_TOOL_OUTPUT_STR = json.dumps({"status": "Clear", "risk_level": "Low", "details": {"message": "AML mock clear", "screened_lists": ["Global Sanctions", "PEP"]}})

# This is the crucial part: the final assessment task's expected output, which consolidates all previous (mocked) task outputs.
# The LLM for the final_assessment_task is expected to generate this based on the string outputs of context_tasks.
MOCK_FINAL_ASSESSMENT_JSON_STR = json.dumps({
    "overall_status": "Approve", "approved_tier": "Tier2",
    "summary_message": "CrewAI mock approval for CrewTest TierTwo. All checks passed via mocked tool outputs.",
    "bvn_nin_result": json.loads(MOCK_BVN_NIN_TOOL_OUTPUT_STR),
    "id_processing_result": {"ocr": json.loads(MOCK_ID_OCR_TOOL_OUTPUT_STR), "validation": json.loads(MOCK_ID_VALIDATION_TOOL_OUTPUT_STR)},
    "utility_bill_processing_result": {"ocr": json.loads(MOCK_UTILITY_OCR_TOOL_OUTPUT_STR), "validation": json.loads(MOCK_UTILITY_VALIDATION_TOOL_OUTPUT_STR)},
    "face_match_result": json.loads(MOCK_FACE_MATCH_TOOL_OUTPUT_STR),
    "aml_result": json.loads(MOCK_AML_TOOL_OUTPUT_STR)
})

# Sequence of responses for FakeListLLM. One response per task that "runs".
# The response for a task that calls a tool should be the tool's output as a JSON string.
# The response for the final consolidation task is the MOCK_FINAL_ASSESSMENT_JSON_STR.
# This order must match the order of tasks if all are executed.
# If tasks are conditional, this list needs dynamic adjustment or a more sophisticated FakeListLLM.
mock_llm_responses_for_onboarding_crew_tier2 = [ # Assuming all tasks run for Tier 2
    MOCK_BVN_NIN_TOOL_OUTPUT_STR,
    MOCK_ID_OCR_TOOL_OUTPUT_STR,
    MOCK_ID_VALIDATION_TOOL_OUTPUT_STR,
    MOCK_UTILITY_OCR_TOOL_OUTPUT_STR,
    MOCK_UTILITY_VALIDATION_TOOL_OUTPUT_STR,
    MOCK_FACE_MATCH_TOOL_OUTPUT_STR,
    MOCK_AML_TOOL_OUTPUT_STR,
    MOCK_FINAL_ASSESSMENT_JSON_STR      # Output of final_assessment_task (synthesized by LLM)
]
# For Tier 1, utility bill tasks might be skipped.
mock_llm_responses_for_onboarding_crew_tier1 = [
    MOCK_BVN_NIN_TOOL_OUTPUT_STR,
    MOCK_ID_OCR_TOOL_OUTPUT_STR,
    MOCK_ID_VALIDATION_TOOL_OUTPUT_STR,
    # Skip Utility Bill OCR & Validation
    MOCK_FACE_MATCH_TOOL_OUTPUT_STR,
    MOCK_AML_TOOL_OUTPUT_STR,
    # Slightly different final assessment for Tier 1 (no utility bill part)
    json.dumps({
        "overall_status": "Approve", "approved_tier": "Tier1",
        "summary_message": "CrewAI mock approval for Tier1. Checks passed.",
        "bvn_nin_result": json.loads(MOCK_BVN_NIN_TOOL_OUTPUT_STR),
        "id_processing_result": {"ocr": json.loads(MOCK_ID_OCR_TOOL_OUTPUT_STR), "validation": json.loads(MOCK_ID_VALIDATION_TOOL_OUTPUT_STR)},
        "utility_bill_processing_result": None, # Explicitly None for Tier 1
        "face_match_result": json.loads(MOCK_FACE_MATCH_TOOL_OUTPUT_STR),
        "aml_result": json.loads(MOCK_AML_TOOL_OUTPUT_STR)
    })
]


# --- Agent Definition ---
onboarding_tools = [
    nin_bvn_verification_tool, ocr_tool, document_validation_tool,
    face_match_tool, aml_screening_tool,
]

# LLM instance will be created dynamically in start_onboarding_process based on tier
customer_onboarding_specialist_agent_template = Agent( # Template, LLM will be set dynamically
    role="Customer Onboarding Specialist AI",
    goal=(
        "Efficiently and accurately manage the entire customer KYC process, "
        "from initial data collection and document submission to multi-step verification (BVN, NIN, ID OCR & Validation, Face Match, AML), "
        "and final decisioning for account opening, adhering to Nigerian banking regulations (CBN tiers)."
    ),
    backstory=(
        "An advanced AI agent designed to streamline customer onboarding for a modern Nigerian bank. "
        "It leverages a suite of specialized tools to perform verifications, assess risk, and ensure compliance. "
        "It aims to provide a seamless experience for applicants while maintaining strict regulatory adherence."
    ),
    tools=onboarding_tools,
    # llm will be set dynamically
    verbose=1,
    allow_delegation=False,
)

# --- Task Definitions ---
def create_onboarding_tasks(onboarding_request_dict: Dict[str, Any], documents_list_dict: List[Dict[str,Any]]) -> List[Task]:
    tasks: List[Task] = []

    applicant_details_for_tasks = {
        "bvn": onboarding_request_dict.get("bvn"), "nin": onboarding_request_dict.get("nin"),
        "first_name": onboarding_request_dict.get("first_name"), "last_name": onboarding_request_dict.get("last_name"),
        "date_of_birth": onboarding_request_dict.get("date_of_birth"),
        "phone_number": onboarding_request_dict.get("phone_number"),
        "country": onboarding_request_dict.get("country", "NG"),
        "street_address": onboarding_request_dict.get("street_address")
    }
    applicant_details_json_str = json.dumps(applicant_details_for_tasks)


    # Task 1: BVN/NIN Verification
    bvn_nin_task = Task(
        description=f"Verify the customer's BVN and/or NIN using details from the applicant data: {applicant_details_json_str}. Use the NINBVNVerificationTool.",
        expected_output="A JSON string detailing BVN and NIN verification results (e.g., {\"bvn_verification\": {\"status\": \"Verified\", ...}, \"nin_verification\": {\"status\": \"Mismatch\", ...}}). This output will be the direct JSON string result from the NINBVNVerificationTool.",
        agent=customer_onboarding_specialist_agent_template, # Agent instance passed here
    )
    tasks.append(bvn_nin_task)

    id_document_dict = next((doc for doc in documents_list_dict if doc["type_name"] in ["NationalID", "DriversLicense", "Passport"]), None)
    id_doc_ocr_task: Optional[Task] = None
    id_doc_validation_task: Optional[Task] = None

    if id_document_dict:
        id_doc_ocr_task = Task(
            description=f"Process the customer's ID document ({id_document_dict['type_name']}) available at URL '{id_document_dict['url']}' using OCRTool. Extract key information.",
            expected_output="A JSON string with OCR results for the ID document (status, extracted_data). This output will be the direct JSON string result from the OCRTool.",
            agent=customer_onboarding_specialist_agent_template,
            context_tasks=[bvn_nin_task]
        )
        tasks.append(id_doc_ocr_task)

        id_doc_validation_task = Task(
            description=f"""\
            Validate the processed ID document ({id_document_dict['type_name']}) from URL '{id_document_dict['url']}'.
            Use its OCR results (which is the string output of the ID OCR task) and the applicant's data: {applicant_details_json_str}.
            The OCR result (JSON string from previous task) needs to be parsed to get 'extracted_data'.
            Use DocumentValidationTool.
            """,
            expected_output="A JSON string with validation status ('Valid', 'Suspicious', 'Invalid'), checks passed, and issues found. This output will be the direct JSON string result from the DocumentValidationTool.",
            agent=customer_onboarding_specialist_agent_template,
            context_tasks=[id_doc_ocr_task]
        )
        tasks.append(id_doc_validation_task)

    utility_bill_doc_dict = next((doc for doc in documents_list_dict if doc["type_name"] == "UtilityBill"), None)
    utility_bill_ocr_task: Optional[Task] = None
    utility_bill_validation_task: Optional[Task] = None

    if utility_bill_doc_dict and onboarding_request_dict.get("requested_account_tier", {}).get("tier") in ["Tier2", "Tier3"]:
        utility_bill_ocr_task = Task(
            description=f"Process the customer's utility bill ({utility_bill_doc_dict['type_name']}) at URL '{utility_bill_doc_dict['url']}' using OCRTool. Extract address and biller details.",
            expected_output="A JSON string with OCR results for the utility bill (status, extracted_data). This output will be the direct JSON string result from the OCRTool.",
            agent=customer_onboarding_specialist_agent_template,
            # Ensure this task can run after BVN/NIN or ID checks, not strictly dependent on ID validation if parallelizable
            context_tasks=[id_doc_validation_task] if id_doc_validation_task else [bvn_nin_task]
        )
        tasks.append(utility_bill_ocr_task)

        utility_bill_validation_task = Task(
            description=f"""\
            Validate the processed utility bill ({utility_bill_doc_dict['type_name']}) from URL '{utility_bill_doc_dict['url']}'.
            Use its OCR results (string output of previous task) and the applicant's address details from: {applicant_details_json_str}.
            The OCR result (JSON string from previous task) needs to be parsed to get 'extracted_data'.
            Use DocumentValidationTool.
            """,
            expected_output="A JSON string with validation status, checks passed, and issues. This output will be the direct JSON string result from the DocumentValidationTool.",
            agent=customer_onboarding_specialist_agent_template,
            context_tasks=[utility_bill_ocr_task]
        )
        tasks.append(utility_bill_validation_task)

    selfie_doc_dict = next((doc for doc in documents_list_dict if doc["type_name"] == "Selfie"), None)
    if selfie_doc_dict and id_document_dict:
        face_match_task = Task(
            description=f"Perform a face match: selfie ({selfie_doc_dict['url']}) vs ID photo (from ID document: {id_document_dict['url']}). Use FaceMatchTool.",
            expected_output="A JSON string with face match results (status, is_match, match_score, confidence). This output will be the direct JSON string result from the FaceMatchTool.",
            agent=customer_onboarding_specialist_agent_template,
            context_tasks=[id_doc_validation_task] if id_doc_validation_task else ([id_doc_ocr_task] if id_doc_ocr_task else [])
        )
        tasks.append(face_match_task)

    aml_task = Task(
        description=f"Perform AML screening for applicant using details from {applicant_details_json_str}. Use AMLScreeningTool.",
        expected_output="A JSON string with AML screening results (status, risk_level, details). This output will be the direct JSON string result from the AMLScreeningTool.",
        agent=customer_onboarding_specialist_agent_template,
        context_tasks=[bvn_nin_task]
    )
    tasks.append(aml_task)

    # Build context for final assessment based on which tasks were actually added
    final_assessment_context_tasks = [t for t in [
        bvn_nin_task, id_doc_ocr_task, id_doc_validation_task,
        utility_bill_ocr_task, utility_bill_validation_task,
        face_match_task, aml_task
    ] if t is not None]

    final_assessment_task = Task(
        description=f"""\
        Consolidate all verification results from previous tasks.
        The applicant's initial data was: {applicant_details_json_str}.
        The requested tier was: {onboarding_request_dict.get("requested_account_tier", {}).get("tier")}.
        Assess overall KYC status. Determine the achievable account tier.
        Provide a final recommendation: 'Approve', 'Reject', or 'RequiresManualIntervention'.
        If 'Approve', specify the approved tier. If 'Reject' or 'RequiresManualIntervention', provide clear reasons.
        The output MUST be a single JSON string that includes: 'overall_status', 'approved_tier' (if applicable),
        'summary_message', and nested objects for each verification step's result
        (e.g., 'bvn_nin_result', 'id_processing_result': {{'ocr': ..., 'validation': ...}}, etc.),
        similar to MOCK_FINAL_ASSESSMENT_JSON_STR example.
        """,
        expected_output="A single JSON string summarizing the final assessment, including overall_status, approved_tier, summary_message, and detailed results for each verification type, similar to MOCK_FINAL_ASSESSMENT_JSON_STR.",
        agent=customer_onboarding_specialist_agent_template,
        context_tasks=final_assessment_context_tasks
    )
    tasks.append(final_assessment_task)

    return tasks

# --- Main Workflow Function ---
async def start_onboarding_process(onboarding_id: str, request: OnboardingRequest) -> Dict[str, Any]:
    """
    Initiates and manages the customer onboarding workflow using CrewAI.
    Uses FakeListLLM and mocked tools.
    """
    logger.info(f"Agent Log: Starting CrewAI onboarding process for ID: {onboarding_id}, Customer: {request.first_name} {request.last_name}, Tier: {request.requested_account_tier.tier}")

    onboarding_request_dict = request.model_dump(mode='json')
    documents_list_dict = [doc.model_dump(mode='json') for doc in request.documents]

    # Select mock LLM responses based on tier (affects if utility bill tasks run)
    active_llm_responses = []
    if request.requested_account_tier.tier in ["Tier2", "Tier3"] and any(d['type_name'] == 'UtilityBill' for d in documents_list_dict) :
        active_llm_responses = mock_llm_responses_for_onboarding_crew_tier2
        logger.debug("Using Tier 2/3 LLM responses (all tasks expected).")
    else: # Tier 1 or Tier 2/3 without utility bill submitted (or utility tasks are skipped)
        # This needs to match the number of tasks that will actually run and call LLM
        # For Tier 1: BVN/NIN, ID OCR, ID Val, Face, AML, Final = 6 responses.
        # MOCK_FINAL_ASSESSMENT_JSON_STR_TIER1 needs to be defined if final output differs.
        # For simplicity, assume Tier1 also uses 8 responses, but some are "skipped" by task logic.
        # This is a limitation of simple FakeListLLM; a more dynamic mock or actual LLM is better.
        # For now, use Tier1 responses if it's simpler and has fewer steps.
        active_llm_responses = mock_llm_responses_for_onboarding_crew_tier1 # Assumes fewer steps
        logger.debug("Using Tier 1 (or equivalent) LLM responses.")

    # Create a new LLM instance for this specific run with the correct responses
    current_llm = FakeListLLM(responses=active_llm_responses)
    customer_onboarding_specialist_agent_template.llm = current_llm # Assign to the agent template for this run

    defined_tasks = create_onboarding_tasks(onboarding_request_dict, documents_list_dict)

    if not defined_tasks:
        logger.error(f"Agent Log: No tasks defined for {onboarding_id} based on input. Aborting.")
        return { "status": "RequiresManualIntervention", "message": "Agent could not define tasks.", "last_updated_at": datetime.utcnow(), "verification_steps": [] }

    onboarding_crew = Crew(
        agents=[customer_onboarding_specialist_agent_template], tasks=defined_tasks, # Use the agent with updated LLM
        process=Process.sequential, verbose=1,
    )

    crew_inputs = { 'onboarding_request_json': request.model_dump_json() }

    logger.info(f"Agent Log: Kicking off CrewAI for {onboarding_id} with {len(defined_tasks)} tasks. LLM responses queued: {len(active_llm_responses)}")

    crew_result_str: Optional[str] = None
    try:
        crew_result_str = onboarding_crew.kickoff(inputs=crew_inputs)
        logger.info(f"Agent Log: CrewAI processing completed for {onboarding_id}. Raw output from final task: {crew_result_str[:1000]}...")
    except Exception as e:
        logger.error(f"Agent Log: CrewAI kickoff failed for {onboarding_id}: {e}", exc_info=True)
        crew_result_str = json.dumps({
            "application_id": onboarding_id, "overall_status": "RequiresManualIntervention",
            "summary_message": f"Agent workflow execution error: {str(e)}", "assessment_timestamp": datetime.utcnow().isoformat()
        })

    if crew_result_str is None:
        logger.error(f"Agent Log: CrewAI kickoff returned None for {onboarding_id}.")
        crew_result_str = json.dumps({
            "application_id": onboarding_id, "overall_status": "RequiresManualIntervention",
            "summary_message": "Agent workflow returned no result.", "assessment_timestamp": datetime.utcnow().isoformat()
        })

    # --- Process final_assessment (from CrewAI's final task) to build the update_payload for FastAPI ---
    final_assessment: Dict[str, Any] = {}
    try:
        final_assessment = json.loads(crew_result_str)
    except Exception as e: # Catch JSONDecodeError and TypeError (if crew_result_str is None)
        logger.error(f"Agent Log: Error decoding/processing final assessment JSON for {onboarding_id}: {crew_result_str}. Error: {e}", exc_info=True)
        final_assessment = { # Default error structure
            "application_id": onboarding_id, "overall_status": "RequiresManualIntervention",
            "summary_message": f"Malformed or missing agent JSON result. Content: {str(crew_result_str)[:200]}..."
        }

    updated_verification_steps: List[Dict[str, Any]] = []
    # Helper to safely extract and form status dict from various tool output structures
    def _parse_tool_output_to_status_dict(step_name: str, tool_output_dict: Optional[Dict[str, Any]],
                                        status_key_in_tool:str = "status",
                                        message_key_in_tool:str = "message",
                                        details_root_key_in_tool:Optional[str] = None) -> Dict[str,Any]:
        if not isinstance(tool_output_dict, dict):
            logger.warning(f"Tool output for {step_name} is not a dict: {tool_output_dict}")
            return {"status": "Error", "message": f"Invalid tool output structure for {step_name}."}

        status_val = tool_output_dict.get(status_key_in_tool, "Error")
        message_val = tool_output_dict.get(message_key_in_tool)

        details_val = tool_output_dict # Default to full tool output as details
        if details_root_key_in_tool and details_root_key_in_tool in tool_output_dict:
            details_val = tool_output_dict[details_root_key_in_tool]

        # Specific known tool output structures:
        if step_name == "BVNVerification": # nin_bvn_verification_tool
            status_val = tool_output_dict.get("bvn_status", "Error")
            details_val = tool_output_dict.get("bvn_details", tool_output_dict)
            message_val = details_val.get("message") if isinstance(details_val, dict) else None
        elif step_name == "NINVerification": # nin_bvn_verification_tool
            status_val = tool_output_dict.get("nin_status", "Error")
            details_val = tool_output_dict.get("nin_details", tool_output_dict)
            message_val = details_val.get("message") if isinstance(details_val, dict) else None
        elif step_name == "IDDocumentCheck_OCR" or step_name == "UtilityBill_OCR": # ocr_tool
             message_val = tool_output_dict.get("error_message") if status_val == "Failed" else "OCR successful."
             details_val = tool_output_dict.get("extracted_data", tool_output_dict)
        elif step_name == "IDDocumentCheck_Validation" or step_name == "UtilityBill_Validation": # document_validation_tool
            status_val = tool_output_dict.get("validation_status", "Error")
            message_val = f"Issues: {tool_output_dict.get('validation_issues')}" if tool_output_dict.get('validation_issues') else "Validation checks passed."
            details_val = tool_output_dict # Full tool output
        elif step_name == "FaceMatch": # face_match_tool
            status_val = "Verified" if tool_output_dict.get("is_match") else ("Failed" if tool_output_dict.get("status")=="Success" else tool_output_dict.get("status", "Error"))
            message_val = tool_output_dict.get("message")
        elif step_name == "AMLScreening": # aml_screening_tool
            status_val = "Verified" if tool_output_dict.get("status") == "Clear" else ("Failed" if tool_output_dict.get("status") == "Hit" else tool_output_dict.get("status", "Error"))
            message_val = tool_output_dict.get("details", {}).get("message")
            details_val = tool_output_dict.get("details", tool_output_dict)

        return {"status": status_val, "message": message_val, "details": details_val}

    # Populate updated_verification_steps based on final_assessment structure
    fa_bvn_nin = final_assessment.get("bvn_nin_result", {})
    updated_verification_steps.append({"step_name": "BVNVerification", "status": _parse_tool_output_to_status_dict("BVNVerification", fa_bvn_nin.get("bvn_verification"))})
    updated_verification_steps.append({"step_name": "NINVerification", "status": _parse_tool_output_to_status_dict("NINVerification", fa_bvn_nin.get("nin_verification"))})

    fa_id_proc = final_assessment.get("id_processing_result", {})
    id_ocr_status = _parse_tool_output_to_status_dict("IDDocumentCheck_OCR", fa_id_proc.get("ocr"))
    id_val_status = _parse_tool_output_to_status_dict("IDDocumentCheck_Validation", fa_id_proc.get("validation"))
    # Consolidate ID check status
    id_final_status: VerificationStatus = "Error" # type: ignore
    id_final_msg = "ID processing error."
    if id_val_status.get("status") == "Valid" and id_ocr_status.get("status") == "Success": id_final_status = "Verified" # type: ignore
    elif id_val_status.get("status") in ["Suspicious", "Invalid"]: id_final_status = "RequiresManualReview" if id_val_status.get("status") == "Suspicious" else "Failed" # type: ignore
    elif id_ocr_status.get("status") == "Failed": id_final_status = "Failed" # type: ignore
    if id_val.get("validation_issues"): id_final_msg = f"ID Validation: {id_val.get('validation_status')}. Issues: {id_val.get('validation_issues')}"
    elif id_ocr.get("status") == "Failed": id_final_msg = f"ID OCR Failed: {id_ocr.get('error_message', 'Unknown OCR error')}"
    elif id_final_status == "Verified": id_final_msg = "ID document processed and validated."
    updated_verification_steps.append({"step_name": "IDDocumentCheck", "status": {"status": id_final_status, "message": id_final_msg, "details": fa_id_proc}})

    updated_verification_steps.append({"step_name": "FaceMatch", "status": _parse_tool_output_to_status_dict("FaceMatch", final_assessment.get("face_match_result"))})
    updated_verification_steps.append({"step_name": "AMLScreening", "status": _parse_tool_output_to_status_dict("AMLScreening", final_assessment.get("aml_result"))})

    addr_ver_payload: Dict[str, Any] = {"step_name": "AddressVerification", "status": {"status": "NotApplicable"}}
    fa_util_proc = final_assessment.get("utility_bill_processing_result")
    if fa_util_proc and isinstance(fa_util_proc, dict) and fa_util_proc.get("ocr"):
        util_ocr_status = _parse_tool_output_to_status_dict("UtilityBill_OCR", fa_util_proc.get("ocr"))
        util_val_status = _parse_tool_output_to_status_dict("UtilityBill_Validation", fa_util_proc.get("validation"))
        util_final_status: VerificationStatus = "Error" # type: ignore
        util_final_msg = "Utility bill processing error."
        if util_val_status.get("status") == "Valid" and util_ocr_status.get("status") == "Success": util_final_status = "Verified" # type: ignore
        # ... (similar consolidation logic as ID check) ...
        addr_ver_payload["status"] = {"status": util_final_status, "message": util_final_msg, "details": fa_util_proc}
    elif request.requested_account_tier.tier in ["Tier2", "Tier3"] and not any(doc.type_name == "UtilityBill" for doc in request.documents):
        addr_ver_payload["status"] = {"status": "Pending", "message": "Utility bill required for Tier 2/3 but not provided."}
    updated_verification_steps.append(addr_ver_payload)

    overall_status_str = final_assessment.get("overall_status", "RequiresManualIntervention")
    valid_overall_statuses = get_args(OnboardingProcess.__annotations__['status'])
    if overall_status_str not in valid_overall_statuses:
        logger.warning(f"Agent returned invalid overall_status '{overall_status_str}'. Defaulting to RequiresManualIntervention.")
        overall_status_str = "RequiresManualIntervention"

    achieved_tier_data = final_assessment.get("approved_tier")
    achieved_tier_obj = None
    if overall_status_str in ["Approve", "Completed"] and achieved_tier_data:
         achieved_tier_obj = AccountTier(tier=achieved_tier_data) if isinstance(achieved_tier_data, str) else AccountTier(**achieved_tier_data)

    update_payload = {
        "status": overall_status_str, "message": final_assessment.get("summary_message", "Processing complete."),
        "last_updated_at": datetime.utcnow(),
        "achieved_tier": achieved_tier_obj.model_dump() if achieved_tier_obj else None,
        "verification_steps": updated_verification_steps,
        "customer_id": f"CUST-{onboarding_id.split('-')[-1]}" if overall_status_str in ["Approve", "Completed"] and achieved_tier_obj else None
    }
    return update_payload


async def get_onboarding_status_from_agent(onboarding_id: str) -> Dict[str, Any]:
    logger.info(f"Agent Log: Fetching status for onboarding ID: {onboarding_id} (mocked, no active polling)")
    return { "message": "Status check from agent: Process is assumed to be handled by the initial call.", "last_updated_at": datetime.utcnow()}


if __name__ == "__main__":
    import asyncio
    from typing import get_args

    async def test_run():
        if not logger.handlers:
            logging.basicConfig(level=logging.DEBUG)
            logger.info("Test run logger configured.")

        mock_documents_tier2 = [
            DocumentType(type_name="NationalID", url=HttpUrl("http://example.com/id_crew_user.jpg")),
            DocumentType(type_name="Selfie", url=HttpUrl("http://example.com/selfie_crew_user.jpg")),
            DocumentType(type_name="UtilityBill", url=HttpUrl("http://example.com/bill_crew_user.pdf"))
        ]
        mock_request_data_tier2 = OnboardingRequest(
            first_name="CrewTest", last_name="TierTwo", date_of_birth="1995-02-10",
            phone_number="08022334455", email_address="crew.test.t2@example.com",
            bvn="12121212122", nin="34343434344", country="NG", street_address="2 Crew Avenue, Lagos",
            requested_account_tier={"tier": "Tier2"}, documents=mock_documents_tier2
        )
        onboarding_id_test_t2 = "ONB-CREWAI-T2-001"

        print(f"\n--- Simulating start_onboarding_process (CrewAI kickoff) for {onboarding_id_test_t2} (Tier 2) ---")
        update_payload_t2 = await start_onboarding_process(onboarding_id_test_t2, mock_request_data_tier2)
        print(f"Update payload from agent for {onboarding_id_test_t2}:")
        print(json.dumps(update_payload_t2, indent=2, default=str))

        valid_statuses = get_args(OnboardingProcess.__annotations__['status'])
        if update_payload_t2["status"] not in valid_statuses:
            print(f"ERROR: Payload status '{update_payload_t2['status']}' is not a valid OnboardingProcess status: {valid_statuses}")

        valid_step_statuses = get_args(VerificationStatus.__annotations__["status"])
        for step in update_payload_t2.get("verification_steps", []):
            step_status_val = step.get("status", {}).get("status")
            if step_status_val not in valid_step_statuses:
                 print(f"ERROR: Step '{step.get('step_name')}' has invalid status '{step_status_val}'. Valid: {valid_step_statuses}")

    # Important: To run this test effectively, you need to uncomment the `asyncio.run(test_run())` line.
    # For automated agent runs, it's kept commented.
    # asyncio.run(test_run())
    print("\nCustomer Onboarding Agent logic (agent.py) with CrewAI structure (actual kickoff enabled, using FakeListLLM and mocked tools).")
