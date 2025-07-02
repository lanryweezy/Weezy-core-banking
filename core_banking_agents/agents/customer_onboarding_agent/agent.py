# LangChain/CrewAI agent logic for Customer Onboarding

from typing import Dict, Any, List, Optional
from datetime import datetime
import json # For parsing expected outputs if they are JSON strings

# Assuming schemas are in the same directory
from .schemas import OnboardingRequest, VerificationStepResult, VerificationStatus, DocumentType, AccountTier
# Import the defined tools
from .tools import nin_bvn_verification_tool, ocr_tool, face_match_tool, aml_screening_tool, document_validation_tool

from crewai import Agent, Task, Crew, Process
from langchain_community.llms.fake import FakeListLLM # Using FakeListLLM for mocking CrewAI execution
# from langchain_openai import ChatOpenAI
# from ..core.config import core_settings # For OPENAI_API_KEY if needed

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- LLM Configuration (Mocked for CrewAI) ---
# The number of responses should be enough for the agent's internal processing for each task.
# Each response corresponds to an LLM call.
# The content of these responses should be what the LLM would ideally return
# to select the right tool or synthesize information based on task description.
# We need enough "thoughts" or "tool selections" for all tasks in a sequence.
# For N tasks, it might be N or N*2 responses.
# Example: BVN/NIN -> ID OCR -> ID Validate -> FaceMatch -> AML -> Final Assess (6 main steps)
# Plus maybe a few for thinking/chaining.
mock_llm_responses = [
    "I need to verify BVN and NIN. I will use the NINBVNVerificationTool.", # BVN/NIN Task
    "Okay, BVN/NIN verification done. Now, I need to process the ID document. I'll use OCRTool.", # ID OCR Task
    "ID document OCR complete. Now I need to validate it. I'll use DocumentValidationTool.", # ID Validation Task
    "ID validation complete. If there's a utility bill for Tier 2/3, I'll process that too.", # Utility Bill OCR (conditional)
    "Utility bill OCR complete. Now validating it.", # Utility Bill Validation (conditional)
    "Document processing done. Now, I need to perform face match. I'll use FaceMatchTool.", # Face Match Task
    "Face match done. Next, AML screening. I'll use AMLScreeningTool.", # AML Task
    "All checks performed. Now I will consolidate all results and provide a final assessment." # Final Assessment Task
] * 2 # Multiply if more detailed thought process is simulated by CrewAI verbosity

llm = FakeListLLM(responses=mock_llm_responses)

# --- Agent Definition ---
onboarding_tools = [
    nin_bvn_verification_tool,
    ocr_tool,
    document_validation_tool,
    face_match_tool,
    aml_screening_tool,
]

customer_onboarding_specialist = Agent(
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
    llm=llm,
    verbose=True, # Set to 1 or 2 for more details during CrewAI execution
    allow_delegation=False, # This agent will execute its tasks directly using its tools
)

# --- Task Definitions ---
def create_onboarding_tasks(onboarding_request_dict: Dict[str, Any], documents_list_dict: List[Dict[str,Any]]) -> List[Task]:
    tasks: List[Task] = []

    # Context for tasks, making it easier to interpolate into descriptions
    # CrewAI tasks primarily get their dynamic inputs via string interpolation in descriptions
    # or via a shared 'inputs' dictionary passed to crew.kickoff().
    # For more complex data, tasks can also write to a shared "scratchpad" or "context" object if the agent/crew is configured for memory.
    # Here, we pass key identifiers as JSON strings in the description.

    applicant_initial_data_json = json.dumps({
        "bvn": onboarding_request_dict.get("bvn"), "nin": onboarding_request_dict.get("nin"),
        "first_name": onboarding_request_dict.get("first_name"), "last_name": onboarding_request_dict.get("last_name"),
        "date_of_birth": onboarding_request_dict.get("date_of_birth"), "phone_number": onboarding_request_dict.get("phone_number"),
        "country": onboarding_request_dict.get("country", "NG"),
        "street_address": onboarding_request_dict.get("street_address")
    })

    # Task 1: BVN/NIN Verification
    bvn_nin_task = Task(
        description=f"Verify the customer's BVN and/NIN using details from the applicant data: {applicant_initial_data_json}. Use the NINBVNVerificationTool.",
        expected_output="A JSON string detailing BVN and NIN verification results (e.g., {\"bvn_verification\": {\"status\": \"Verified\", ...}, \"nin_verification\": {\"status\": \"Mismatch\", ...}}).",
        agent=customer_onboarding_specialist,
    )
    tasks.append(bvn_nin_task)

    # Document Processing Tasks (OCR followed by Validation)
    id_document_dict = next((doc for doc in documents_list_dict if doc["type_name"] in ["NationalID", "DriversLicense", "Passport"]), None)
    id_doc_ocr_task: Optional[Task] = None
    id_doc_validation_task: Optional[Task] = None

    if id_document_dict:
        id_doc_ocr_task = Task(
            description=f"Process the customer's ID document ({id_document_dict['type_name']}) available at URL '{id_document_dict['url']}' using OCRTool. Extract key information.",
            expected_output="A JSON string with OCR results for the ID document (status, extracted_data).",
            agent=customer_onboarding_specialist,
            context_tasks=[bvn_nin_task] # Can run after BVN/NIN
        )
        tasks.append(id_doc_ocr_task)

        id_doc_validation_task = Task(
            description=f"Validate the processed ID document ({id_document_dict['type_name']}) from URL '{id_document_dict['url']}'. Use its OCR results (from the previous task's output) and the applicant's initial data ({applicant_initial_data_json}) for cross-referencing. Use DocumentValidationTool.",
            expected_output="A JSON string with validation status ('Valid', 'Suspicious', 'Invalid'), checks passed, and issues found.",
            agent=customer_onboarding_specialist,
            context_tasks=[id_doc_ocr_task] # Depends on the output of id_doc_ocr_task
        )
        tasks.append(id_doc_validation_task)

    utility_bill_doc_dict = next((doc for doc in documents_list_dict if doc["type_name"] == "UtilityBill"), None)
    utility_bill_ocr_task: Optional[Task] = None
    utility_bill_validation_task: Optional[Task] = None

    if utility_bill_doc_dict and onboarding_request_dict.get("requested_account_tier", {}).get("tier") in ["Tier2", "Tier3"]:
        utility_bill_ocr_task = Task(
            description=f"Process the customer's utility bill ({utility_bill_doc_dict['type_name']}) at URL '{utility_bill_doc_dict['url']}' using OCRTool. Extract address and biller details.",
            expected_output="A JSON string with OCR results for the utility bill (status, extracted_data).",
            agent=customer_onboarding_specialist,
            context_tasks=[bvn_nin_task] # Can run after BVN/NIN
        )
        tasks.append(utility_bill_ocr_task)

        utility_bill_validation_task = Task(
            description=f"Validate the processed utility bill ({utility_bill_doc_dict['type_name']}) from URL '{utility_bill_doc_dict['url']}'. Use its OCR results and the applicant's address data from ({applicant_initial_data_json}) for consistency. Use DocumentValidationTool.",
            expected_output="A JSON string with validation status, checks passed, and issues.",
            agent=customer_onboarding_specialist,
            context_tasks=[utility_bill_ocr_task]
        )
        tasks.append(utility_bill_validation_task)

    # Face Match Task
    selfie_doc_dict = next((doc for doc in documents_list_dict if doc["type_name"] == "Selfie"), None)
    if selfie_doc_dict and id_document_dict:
        face_match_task = Task(
            description=f"Perform a face match between customer's selfie (URL: {selfie_doc_dict['url']}) and their ID photo (from ID document: {id_document_dict['url']}). Use FaceMatchTool.", # Tool needs to handle getting photo from ID URL if not directly provided
            expected_output="A JSON string with face match results (status, is_match, match_score, confidence).",
            agent=customer_onboarding_specialist,
            context_tasks=[id_doc_ocr_task] if id_doc_ocr_task else [] # Might depend on ID OCR if photo URL is extracted there
        )
        tasks.append(face_match_task)

    # AML Screening Task
    aml_task = Task(
        description=f"Perform AML screening for applicant using details from {applicant_initial_data_json}. Use AMLScreeningTool.",
        expected_output="A JSON string with AML screening results (status, risk_level, details).",
        agent=customer_onboarding_specialist,
        # This can run in parallel with some document checks, or after BVN/NIN
        context_tasks=[bvn_nin_task]
    )
    tasks.append(aml_task)

    # Final Assessment Task - Gathers all previous results
    # Context for this task will be the outputs of all preceding tasks.
    # CrewAI handles passing this context implicitly if tasks are sequential or correctly linked.
    all_prior_tasks = [t for t in tasks if t is not aml_task] # Example: all tasks created so far
    all_prior_tasks.append(aml_task) # Ensure AML is also part of context for final assessment

    final_assessment_task = Task(
        description=f"""\
        Consolidate all verification results from previous tasks (BVN/NIN, ID Document OCR & Validation,
        Utility Bill OCR & Validation (if performed), Face Match, AML Screening).
        The applicant's initial data was: {applicant_initial_data_json}.
        The requested tier was: {onboarding_request_dict.get("requested_account_tier", {}).get("tier")}.
        Assess overall KYC status. Determine the achievable account tier based on verified information and CBN guidelines.
        Provide a final recommendation: 'Approve', 'Reject', or 'RequiresManualIntervention'.
        If 'Approve', specify the approved tier. If 'Reject' or 'RequiresManualIntervention', provide clear reasons.
        The output MUST be a single JSON string that includes: 'overall_status', 'approved_tier' (if applicable),
        'summary_message', and nested objects for each verification step's result
        (e.g., 'bvn_nin_result', 'id_processing_result': {{'ocr': ..., 'validation': ...}}, 'face_match_result', 'aml_result', etc.).
        """,
        expected_output="A single JSON string summarizing the final assessment, including overall_status, approved_tier, summary_message, and detailed results for each verification type.",
        agent=customer_onboarding_specialist,
        # No specific tools for this task, it's about synthesis by the LLM based on prior task outputs.
        context_tasks=all_prior_tasks # Depends on all previous tasks
    )
    tasks.append(final_assessment_task)

    return tasks

# --- Main Workflow Function ---
async def start_onboarding_process(onboarding_id: str, request: OnboardingRequest) -> Dict[str, Any]:
    """
    Initiates and manages the customer onboarding workflow using CrewAI.
    """
    logger.info(f"Agent Log: Starting CrewAI onboarding process for ID: {onboarding_id}, Customer: {request.first_name} {request.last_name}")

    # Convert Pydantic models to dicts for CrewAI task creation and inputs
    onboarding_request_dict = request.model_dump(mode='json') # mode='json' ensures HttpUrl etc. are strings
    documents_list_dict = [doc.model_dump(mode='json') for doc in request.documents]

    defined_tasks = create_onboarding_tasks(onboarding_request_dict, documents_list_dict)

    if not defined_tasks:
        logger.error(f"Agent Log: No tasks defined for {onboarding_id} based on input. Aborting.")
        return {
            "status": "RequiresManualIntervention", "message": "Agent could not define tasks. Critical input missing.",
            "last_updated_at": datetime.utcnow(), "verification_steps": []
        }

    onboarding_crew = Crew(
        agents=[customer_onboarding_specialist], tasks=defined_tasks,
        process=Process.sequential, verbose=1, # Verbose 1 for less output than 2
    )

    # Inputs for the first task(s) can be passed to kickoff.
    # Subsequent tasks use context from previous tasks.
    # The descriptions of tasks already interpolate necessary specific data.
    # `applicant_initial_data_json` is a good candidate for a general input.
    crew_inputs = {'applicant_initial_data_json': json.dumps(onboarding_request_dict)}


    logger.info(f"Agent Log: Kicking off CrewAI for {onboarding_id} with {len(defined_tasks)} tasks. Inputs: {list(crew_inputs.keys())}")

    # --- ACTUAL CREWAI EXECUTION (Commented out for pure mock, uncomment for FakeListLLM test) ---
    # try:
    #     crew_result_str = onboarding_crew.kickoff(inputs=crew_inputs)
    #     logger.info(f"Agent Log: CrewAI processing completed for {onboarding_id}. Raw output from final task: {crew_result_str[:500]}...")
    # except Exception as e:
    #     logger.error(f"Agent Log: CrewAI kickoff failed for {onboarding_id}: {e}", exc_info=True)
    #     crew_result_str = json.dumps({
    #         "overall_status": "RequiresManualIntervention",
    #         "summary_message": f"Agent workflow execution error: {str(e)}"
    #     })
    # --- END ACTUAL CREWAI EXECUTION ---


    # --- MOCKING CREW EXECUTION & TASK OUTPUTS (for when kickoff is commented) ---
    # This simulates the final task's output by directly calling tools, as before,
    # but now the task definitions and agent structure are in place.
    if True: # Keep this block for controlled mocking until LLM is fully active
        logger.warning(f"Agent Log: Using MOCKED CrewAI execution path for {onboarding_id}.")
        mock_bvn_nin_output = nin_bvn_verification_tool.run(onboarding_request_dict) # Pass relevant fields

        id_document = next((doc for doc in request.documents if doc.type_name in ["NationalID", "DriversLicense", "Passport"]), None)
        mock_id_ocr_output = {}
        mock_id_validation_output = {}
        if id_document:
            mock_id_ocr_output = ocr_tool.run({"document_url": id_document.url, "document_type": id_document.type_name})
            if mock_id_ocr_output.get("status") == "Success":
                mock_id_validation_output = document_validation_tool.run({
                    "document_url": id_document.url, "document_type": id_document.type_name,
                    "ocr_extracted_data": mock_id_ocr_output.get("extracted_data", {}),
                    "applicant_data": onboarding_request_dict
                })

        mock_utility_ocr_output = {}
        mock_utility_validation_output = {}
        utility_bill_doc = next((doc for doc in request.documents if doc.type_name == "UtilityBill"), None)
        if utility_bill_doc and request.requested_account_tier.tier in ["Tier2", "Tier3"]:
            mock_utility_ocr_output = ocr_tool.run({"document_url": utility_bill_doc.url, "document_type": utility_bill_doc.type_name})
            if mock_utility_ocr_output.get("status") == "Success":
                mock_utility_validation_output = document_validation_tool.run({
                    "document_url": utility_bill_doc.url, "document_type": utility_bill_doc.type_name,
                    "ocr_extracted_data": mock_utility_ocr_output.get("extracted_data", {}),
                    "applicant_data": onboarding_request_dict
                })

        mock_face_match_output = {}
        selfie_doc = next((doc for doc in request.documents if doc.type_name == "Selfie"), None)
        if selfie_doc and id_document:
            mock_face_match_output = face_match_tool.run({"selfie_url": selfie_doc.url, "id_photo_url": id_document.url})

        applicant_full_name = f"{request.first_name} {request.middle_name or ''} {request.last_name}".replace("  ", " ").strip()
        mock_aml_output = aml_screening_tool.run({
            "full_name": applicant_full_name, "date_of_birth": request.date_of_birth, "nationality": request.country
        })

        mock_final_assessment_payload = {
            "overall_status": "Approve", "approved_tier": request.requested_account_tier.tier,
            "summary_message": f"Mock approval for {request.first_name} via direct tool calls.",
            "bvn_nin_result": mock_bvn_nin_output,
            "id_processing_result": {"ocr": mock_id_ocr_output, "validation": mock_id_validation_output},
            "utility_bill_processing_result": {"ocr": mock_utility_ocr_output, "validation": mock_utility_validation_output} if utility_bill_doc and request.requested_account_tier.tier in ["Tier2", "Tier3"] else None,
            "face_match_result": mock_face_match_output, "aml_result": mock_aml_output
        }
        # Simplified overall status logic for mock
        if any(res.get("status") == "Error" or res.get("validation_status") == "Error" for res_list in [mock_bvn_nin_output.values(), [mock_id_ocr_output, mock_id_validation_output], [mock_utility_ocr_output, mock_utility_validation_output], [mock_face_match_output], [mock_aml_output]] for res in res_list if isinstance(res,dict)) \
           or any(s == "Failed" for s in [mock_bvn_nin_output.get("bvn_status"), mock_bvn_nin_output.get("nin_status"), mock_id_validation_output.get("validation_status")]) \
           or (mock_face_match_output and not mock_face_match_output.get("is_match", True)) \
           or mock_aml_output.get("status") == "Hit":
            mock_final_assessment_payload["overall_status"] = "RequiresManualReview"
            mock_final_assessment_payload["summary_message"] = "One or more checks require review or failed (direct tool mock)."
            if mock_aml_output.get("status") == "Hit": mock_final_assessment_payload["overall_status"] = "Rejected"
            mock_final_assessment_payload["approved_tier"] = None
        crew_result_str = json.dumps(mock_final_assessment_payload)
    # --- END MOCKING CREW EXECUTION ---

    try:
        final_assessment = json.loads(crew_result_str)
    except json.JSONDecodeError as e:
        logger.error(f"Agent Log: Error decoding final assessment JSON for {onboarding_id}: {crew_result_str}, Error: {e}", exc_info=True)
        final_assessment = {"overall_status": "RequiresManualIntervention", "summary_message": f"Malformed agent JSON result: {str(e)}"}

    # --- Process final_assessment to build the update_payload for FastAPI ---
    # (This parsing logic remains largely the same as before, ensuring it correctly interprets the final_assessment structure)
    updated_verification_steps: List[Dict[str, Any]] = []

    bvn_res = final_assessment.get("bvn_nin_result", {}).get("bvn_verification", {}) # Direct from tool output
    updated_verification_steps.append({
        "step_name": "BVNVerification",
        "status": {"status": bvn_res.get("bvn_status", bvn_res.get("status", "Error")), "message": bvn_res.get("bvn_details", {}).get("message"), "details": bvn_res.get("bvn_details")}
    })
    nin_res = final_assessment.get("bvn_nin_result", {}).get("nin_verification", {}) # Direct from tool output
    updated_verification_steps.append({
        "step_name": "NINVerification",
        "status": {"status": nin_res.get("nin_status", nin_res.get("status", "Error")), "message": nin_res.get("nin_details", {}).get("message"), "details": nin_res.get("nin_details")}
    })

    id_proc_res = final_assessment.get("id_processing_result", {})
    id_ocr = id_proc_res.get("ocr", {})
    id_val = id_proc_res.get("validation", {})
    id_status_val: VerificationStatus = "Error" # type: ignore
    id_msg = "ID processing error."
    if id_val.get("validation_status") == "Valid" and id_ocr.get("status") == "Success": id_status_val = "Verified" # type: ignore
    elif id_val.get("validation_status") == "Suspicious": id_status_val = "RequiresManualReview" # type: ignore
    elif id_val.get("validation_status") == "Invalid" or id_ocr.get("status") == "Failed": id_status_val = "Failed" # type: ignore

    if id_val.get("validation_issues"): id_msg = f"ID Validation: {id_val.get('validation_status')}. Issues: {id_val.get('validation_issues')}"
    elif id_ocr.get("status") == "Failed": id_msg = f"ID OCR Failed: {id_ocr.get('error_message', 'Unknown OCR error')}"
    elif id_status_val == "Verified": id_msg = "ID document processed and validated."
    else: id_msg = f"ID check status: OCR '{id_ocr.get('status')}', Validation '{id_val.get('validation_status')}'."

    updated_verification_steps.append({
        "step_name": "IDDocumentCheck",
        "status": {"status": id_status_val, "message": id_msg, "details": {"ocr": id_ocr, "validation": id_val}}
    })

    fm_res = final_assessment.get("face_match_result", {})
    fm_status_val: VerificationStatus = "Error" # type: ignore
    if fm_res.get("status") == "Success": fm_status_val = "Verified" if fm_res.get("is_match") else "Failed" # type: ignore
    elif fm_res.get("status") == "Failed": fm_status_val = "Failed" # type: ignore
    updated_verification_steps.append({
        "step_name": "FaceMatch",
        "status": {"status": fm_status_val, "message": fm_res.get("message"), "details": fm_res}
    })

    aml_s_res = final_assessment.get("aml_result", {})
    aml_status_val: VerificationStatus = "Error" # type: ignore
    if aml_s_res.get("status") == "Clear": aml_status_val = "Verified" # type: ignore
    elif aml_s_res.get("status") == "Hit": aml_status_val = "Failed" # type: ignore # Or RequiresManualReview
    updated_verification_steps.append({
        "step_name": "AMLScreening",
        "status": {"status": aml_status_val, "message": aml_s_res.get("details", {}).get("message"), "details": aml_s_res}
    })

    addr_ver_step_payload: Dict[str, Any] = {"step_name": "AddressVerification", "status": {"status": "NotApplicable"}}
    util_proc_res = final_assessment.get("utility_bill_processing_result")

    if util_proc_res and util_proc_res.get("ocr"):
        util_ocr = util_proc_res.get("ocr", {})
        util_val = util_proc_res.get("validation", {})
        addr_status_val: VerificationStatus = "Error" # type: ignore
        addr_msg = "Address verification error."
        if util_val.get("validation_status") == "Valid" and util_ocr.get("status") == "Success": addr_status_val = "Verified" # type: ignore
        elif util_val.get("validation_status") == "Suspicious": addr_status_val = "RequiresManualReview" # type: ignore
        elif util_val.get("validation_status") == "Invalid" or util_ocr.get("status") == "Failed": addr_status_val = "Failed" # type: ignore

        if util_val.get("validation_issues"): addr_msg = f"Utility Bill Validation: {util_val.get('validation_status')}. Issues: {util_val.get('validation_issues')}"
        elif util_ocr.get("status") == "Failed": addr_msg = f"Utility Bill OCR Failed: {util_ocr.get('error_message', 'Unknown OCR error')}"
        elif addr_status_val == "Verified": addr_msg = "Address verified via utility bill."
        else: addr_msg = f"Utility Bill check status: OCR '{util_ocr.get('status')}', Validation '{util_val.get('validation_status')}'."

        addr_ver_step_payload["status"] = {"status": addr_status_val, "message": addr_msg, "details": {"ocr": util_ocr, "validation": util_val}}
    elif request.requested_account_tier.tier in ["Tier2", "Tier3"] and not any(doc.type_name == "UtilityBill" for doc in request.documents):
         addr_ver_step_payload["status"] = {"status": "Pending", "message":"Utility bill required for Tier 2/3 but not provided."}
    updated_verification_steps.append(addr_ver_step_payload)

    overall_status_str = final_assessment.get("overall_status", "RequiresManualIntervention")
    # Ensure overall_status_str is a valid literal for OnboardingProcess.status
    valid_overall_statuses = get_args(OnboardingProcess.__annotations__['status']) # Get Literal values
    if overall_status_str not in valid_overall_statuses:
        logger.warning(f"Agent returned invalid overall_status '{overall_status_str}'. Defaulting to RequiresManualIntervention.")
        overall_status_str = "RequiresManualIntervention"


    achieved_tier_data = final_assessment.get("approved_tier")
    achieved_tier_obj = None
    if overall_status_str == "Approve" and achieved_tier_data: # Should be "Approve" not "Approved" for schema
         achieved_tier_obj = AccountTier(tier=achieved_tier_data) if isinstance(achieved_tier_data, str) else AccountTier(**achieved_tier_data)
    elif overall_status_str == "Completed" and achieved_tier_data: # if using "Completed" for successful onboarding
         achieved_tier_obj = AccountTier(tier=achieved_tier_data) if isinstance(achieved_tier_data, str) else AccountTier(**achieved_tier_data)


    update_payload = {
        "status": overall_status_str, #This needs to match OnboardingProcess status literal
        "message": final_assessment.get("summary_message", "Processing complete."),
        "last_updated_at": datetime.utcnow(),
        "achieved_tier": achieved_tier_obj.model_dump() if achieved_tier_obj else None,
        "verification_steps": updated_verification_steps,
        "customer_id": f"CUST-{onboarding_id.split('-')[-1]}" if overall_status_str in ["Approve", "Completed"] and achieved_tier_obj else None
    }
    return update_payload


async def get_onboarding_status_from_agent(onboarding_id: str) -> Dict[str, Any]:
    """
    Retrieves the current status of the onboarding process. (Mocked)
    In a real system, this would query where the agent/crew stores its state.
    """
    logger.info(f"Agent Log: Fetching status for onboarding ID: {onboarding_id} (mocked, no active polling)")
    return {
        "message": "Status check from agent: Process is assumed to be handled by the initial call. Query DB for actual status.",
        "last_updated_at": datetime.utcnow()
    }


if __name__ == "__main__":
    import asyncio
    from typing import get_args # For OnboardingProcess status literal

    async def test_run():
        mock_documents = [
            DocumentType(type_name="NationalID", url=HttpUrl("http://example.com/id.jpg")),
            DocumentType(type_name="Selfie", url=HttpUrl("http://example.com/selfie.jpg")),
            DocumentType(type_name="UtilityBill", url=HttpUrl("http://example.com/bill.pdf"))
        ]
        mock_request_data = OnboardingRequest(
            first_name="CrewTest", last_name="User", date_of_birth="1995-02-10", # String DOB
            phone_number="08022334455", email_address="crew.test@example.com",
            bvn="12121212121", nin="34343434343", country="NG", street_address="1 Crew Street",
            requested_account_tier={"tier": "Tier2"}, documents=mock_documents
        )
        onboarding_id_test = "ONB-CREWAI001"

        print(f"\n--- Simulating start_onboarding_process (CrewAI structure) for {onboarding_id_test} ---")
        update_payload = await start_onboarding_process(onboarding_id_test, mock_request_data)
        print(f"Update payload from agent for {onboarding_id_test}:")
        print(json.dumps(update_payload, indent=2, default=str)) # Use default=str for datetime

        # Validate the main status
        valid_statuses = get_args(OnboardingProcess.__annotations__['status'])
        if update_payload["status"] not in valid_statuses:
            print(f"ERROR: Payload status '{update_payload['status']}' is not a valid OnboardingProcess status: {valid_statuses}")

        # Validate verification step statuses
        valid_step_statuses = get_args(VerificationStatus.__annotations__["status"])
        for step in update_payload.get("verification_steps", []):
            if step["status"]["status"] not in valid_step_statuses:
                 print(f"ERROR: Step '{step['step_name']}' has invalid status '{step['status']['status']}'. Valid: {valid_step_statuses}")


    asyncio.run(test_run())
    print("\nCustomer Onboarding Agent logic (agent.py) with CrewAI structure (mocked execution of tools, not full Crew kickoff).")
