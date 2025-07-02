# LangChain/CrewAI agent logic for Customer Onboarding

from typing import Dict, Any, List
from datetime import datetime
import json # For parsing expected outputs if they are JSON strings

# Assuming schemas are in the same directory
from .schemas import OnboardingRequest, VerificationStepResult, VerificationStatus, DocumentType
# Import the defined tools
from .tools import nin_bvn_verification_tool, ocr_tool, face_match_tool, aml_screening_tool, document_validation_tool

from crewai import Agent, Task, Crew, Process
from langchain_community.llms.fake import FakeListLLM # Using FakeListLLM for mocking CrewAI execution

# --- LLM Configuration (Mocked for now) ---
def get_customer_onboarding_llm():
    # For testing without actual LLM calls, use FakeListLLM
    # Each response in the list corresponds to an expected LLM call by the agent/tasks.
    return FakeListLLM(responses=[
        "Okay, I will start the BVN/NIN verification.",
        "Processing ID document (OCR).",
        "Validating ID document.",
        "Processing utility bill (OCR).",
        "Validating utility bill.",
        "Performing face match.",
        "AML screening complete.",
        "Finalizing assessment and compiling results."
    ])

# --- Agent Definition ---
onboarding_tools = [
    nin_bvn_verification_tool,
    ocr_tool,
    face_match_tool,
    aml_screening_tool,
    document_validation_tool
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
    llm=get_customer_onboarding_llm(),
    verbose=True,
    allow_delegation=False,
)

# --- Task Definitions ---
def create_onboarding_tasks(onboarding_request_data: Dict[str, Any], documents: List[DocumentType]) -> List[Task]:
    tasks: List[Task] = []

    # Prepare context data once
    applicant_full_name = f"{onboarding_request_data.get('first_name', '')} {onboarding_request_data.get('middle_name', '') if onboarding_request_data.get('middle_name') else ''} {onboarding_request_data.get('last_name', '')}".strip()
    applicant_dob = onboarding_request_data.get('date_of_birth')
    applicant_nationality = onboarding_request_data.get('country', 'NG')

    # Simplified applicant data for DocumentValidationTool context from the main request
    applicant_context_for_validation = {
        "first_name": onboarding_request_data.get("first_name"),
        "last_name": onboarding_request_data.get("last_name"),
        "date_of_birth": applicant_dob,
        "street_address": onboarding_request_data.get("street_address")
    }
    # Make sure this context is JSON serializable if passed directly in task inputs
    applicant_context_for_validation_json = json.dumps(applicant_context_for_validation)


    # Task 1: BVN/NIN Verification
    bvn_nin_task = Task(
        description=f"""\
        Verify the customer's BVN and/or NIN.
        Details: First Name: {onboarding_request_data.get('first_name')}, Last Name: {onboarding_request_data.get('last_name')},
        DOB: {applicant_dob}, Phone: {onboarding_request_data.get('phone_number')},
        BVN: {onboarding_request_data.get('bvn')}, NIN: {onboarding_request_data.get('nin')}.
        Use the NINBVNVerificationTool.
        """,
        expected_output="JSON string detailing BVN and NIN verification results (e.g., {\"bvn_verification\": ..., \"nin_verification\": ...}).",
        agent=customer_onboarding_specialist,
        tools=[nin_bvn_verification_tool]
    )
    tasks.append(bvn_nin_task)

    # --- Document Processing Tasks (OCR followed by Validation) ---
    id_document = next((doc for doc in documents if doc.type_name in ["NationalID", "DriversLicense", "Passport"]), None)
    id_doc_ocr_task: Optional[Task] = None
    id_doc_validation_task: Optional[Task] = None

    if id_document:
        id_doc_ocr_task = Task(
            description=f"Process ID document ({id_document.type_name} at {id_document.url}) using OCRTool. Extract key information.",
            expected_output="JSON string with OCR results (status, extracted_data).",
            agent=customer_onboarding_specialist,
            tools=[ocr_tool]
        )
        tasks.append(id_doc_ocr_task)

        id_doc_validation_task = Task(
            description=f"""\
            Validate the processed ID document ({id_document.type_name} from {id_document.url}).
            Use its OCR results (from previous task output) and applicant data for cross-referencing.
            Applicant Data for cross-ref: {applicant_context_for_validation_json}
            Use DocumentValidationTool.
            """,
            expected_output="JSON string with validation status ('Valid', 'Suspicious', 'Invalid'), checks passed, and issues found.",
            agent=customer_onboarding_specialist,
            tools=[document_validation_tool],
            context_tasks=[id_doc_ocr_task] # Depends on OCR task
        )
        tasks.append(id_doc_validation_task)

    utility_bill_doc = next((doc for doc in documents if doc.type_name == "UtilityBill"), None)
    utility_bill_ocr_task: Optional[Task] = None
    utility_bill_validation_task: Optional[Task] = None

    if utility_bill_doc and onboarding_request_data.get("requested_account_tier", {}).get("tier") in ["Tier2", "Tier3"]:
        utility_bill_ocr_task = Task(
            description=f"Process utility bill ({utility_bill_doc.type_name} at {utility_bill_doc.url}) using OCRTool. Extract address and biller details.",
            expected_output="JSON string with OCR results (status, extracted_data).",
            agent=customer_onboarding_specialist,
            tools=[ocr_tool]
        )
        tasks.append(utility_bill_ocr_task)

        utility_bill_validation_task = Task(
            description=f"""\
            Validate the processed utility bill ({utility_bill_doc.type_name} from {utility_bill_doc.url}).
            Use its OCR results and applicant data for address consistency.
            Applicant Data for cross-ref: {applicant_context_for_validation_json}
            Use DocumentValidationTool.
            """,
            expected_output="JSON string with validation status, checks passed, and issues.",
            agent=customer_onboarding_specialist,
            tools=[document_validation_tool],
            context_tasks=[utility_bill_ocr_task] # Depends on utility bill OCR
        )
        tasks.append(utility_bill_validation_task)

    # Face Match Task
    selfie_doc = next((doc for doc in documents if doc.type_name == "Selfie"), None)
    if selfie_doc and id_document:
        face_match_task = Task(
            description=f"Perform face match: selfie ({selfie_doc.url}) vs ID photo (from ID document: {id_document.url}). Use FaceMatchTool.",
            expected_output="JSON string with face match results (status, is_match, match_score, confidence).",
            agent=customer_onboarding_specialist,
            tools=[face_match_tool],
            # Context might be needed if ID photo URL is dynamically extracted, but tool takes direct URLs.
            context_tasks=[id_doc_ocr_task] if id_doc_ocr_task else []
        )
        tasks.append(face_match_task)

    # AML Screening Task
    aml_task = Task(
        description=f"Perform AML screening for '{applicant_full_name}' (DOB: {applicant_dob}, Nat: {applicant_nationality}). Use AMLScreeningTool.",
        expected_output="JSON string with AML results (status, risk_level, details).",
        agent=customer_onboarding_specialist,
        tools=[aml_screening_tool]
    )
    tasks.append(aml_task)

    # Final Assessment Task
    context_for_final_assessment = [t for t in tasks if t is not aml_task] # Gather all preceding tasks for context
    final_assessment_task = Task(
        description="Consolidate ALL verification results (BVN/NIN, ID OCR & Validation, Utility Bill OCR & Validation (if any), Face Match, AML). Assess overall KYC status. Determine achievable account tier. Provide final recommendation ('Approve', 'Reject', 'RequiresManualReview') with reasons and conditions.",
        expected_output="JSON string summarizing the final assessment (overall_status, approved_tier, summary_message, and nested results for each verification type).",
        agent=customer_onboarding_specialist,
        context_tasks=context_for_final_assessment
    )
    tasks.append(final_assessment_task)

    return tasks

# --- Main Workflow Function ---
async def start_onboarding_process(onboarding_id: str, request: OnboardingRequest) -> Dict[str, Any]:
    """
    Initiates and manages the customer onboarding workflow using CrewAI.
    """
    logger.info(f"Agent Log: Starting CrewAI onboarding process for ID: {onboarding_id}, Customer: {request.first_name} {request.last_name}")

    onboarding_crew_inputs = {"full_onboarding_request_json": request.model_dump_json()}
    defined_tasks = create_onboarding_tasks(request.model_dump(), request.documents)

    if not defined_tasks:
        logger.error(f"Agent Log: No tasks defined for {onboarding_id}. Aborting.")
        return {
            "status": "RequiresManualIntervention", "message": "Agent could not define tasks based on input.",
            "last_updated_at": datetime.utcnow(), "verification_steps": []
        }

    onboarding_crew = Crew(
        agents=[customer_onboarding_specialist], tasks=defined_tasks,
        process=Process.sequential, verbose=2,
    )

    # --- MOCKING CREW EXECUTION & TASK OUTPUTS ---
    logger.info(f"Agent Log: Simulating CrewAI kickoff for {onboarding_id} with {len(defined_tasks)} tasks.")

    # Simulate outputs that would be produced by each tool if called by the tasks.
    # The final_assessment_task is expected to consolidate these.
    mock_bvn_nin_output = nin_bvn_verification_tool.run({
        "bvn": request.bvn, "nin": request.nin, "first_name": request.first_name,
        "last_name": request.last_name, "date_of_birth": request.date_of_birth, "phone_number": request.phone_number
    })

    id_document = next((doc for doc in request.documents if doc.type_name in ["NationalID", "DriversLicense", "Passport"]), None)
    mock_id_ocr_output = {}
    mock_id_validation_output = {}
    if id_document:
        mock_id_ocr_output = ocr_tool.run({"document_url": id_document.url, "document_type": id_document.type_name})
        if mock_id_ocr_output.get("status") == "Success":
            mock_id_validation_output = document_validation_tool.run({
                "document_url": id_document.url, "document_type": id_document.type_name,
                "ocr_extracted_data": mock_id_ocr_output.get("extracted_data", {}),
                "applicant_data": request.model_dump() # Pass full request for applicant data context
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
                "applicant_data": request.model_dump()
            })

    mock_face_match_output = {}
    selfie_doc = next((doc for doc in request.documents if doc.type_name == "Selfie"), None)
    if selfie_doc and id_document: # Assuming ID photo would come from id_document
        mock_face_match_output = face_match_tool.run({"selfie_url": selfie_doc.url, "id_photo_url": id_document.url}) # Simplified: tool might need to extract photo from ID

    applicant_full_name = f"{request.first_name} {request.middle_name or ''} {request.last_name}".replace("  ", " ").strip()
    mock_aml_output = aml_screening_tool.run({
        "full_name": applicant_full_name,
        "date_of_birth": request.date_of_birth,
        "nationality": request.country
    })

    # Construct the expected output of the final_assessment_task based on these tool runs
    mock_final_assessment_payload = {
        "overall_status": "Approve", # This would be determined by LLM based on all inputs
        "approved_tier": request.requested_account_tier.tier,
        "summary_message": f"Mock approval for {request.first_name}. All checks passed (simulated with DocumentValidationTool).",
        "bvn_nin_result": mock_bvn_nin_output,
        "id_processing_result": {"ocr": mock_id_ocr_output, "validation": mock_id_validation_output},
        "utility_bill_processing_result": {"ocr": mock_utility_ocr_output, "validation": mock_utility_validation_output} if utility_bill_doc and request.requested_account_tier.tier in ["Tier2", "Tier3"] else None,
        "face_match_result": mock_face_match_output,
        "aml_result": mock_aml_output
    }
    # Simulate overall status determination logic (very simplified)
    if (mock_bvn_nin_output.get("bvn_status") not in ["Verified", "NotProvided"] or \
        mock_bvn_nin_output.get("nin_status") not in ["Verified", "NotProvided"] or \
        mock_id_validation_output.get("validation_status") not in ["Valid", None] or \
        (mock_utility_validation_output and mock_utility_validation_output.get("validation_status") not in ["Valid", None]) or \
        not mock_face_match_output.get("is_match", False) or \
        mock_aml_output.get("status") == "Hit"):
        mock_final_assessment_payload["overall_status"] = "RequiresManualReview"
        mock_final_assessment_payload["summary_message"] = "One or more verification checks require manual review or failed."
        if mock_aml_output.get("status") == "Hit":
             mock_final_assessment_payload["overall_status"] = "Rejected" # Usually an AML hit is a reject
             mock_final_assessment_payload["summary_message"] = "AML screening resulted in a hit."
        mock_final_assessment_payload["approved_tier"] = None


    crew_result_str = json.dumps(mock_final_assessment_payload)
    logger.info(f"Agent Log: Mock CrewAI processing complete for {onboarding_id}. Final payload (simulated from last task): {crew_result_str[:500]}...")
    # --- END MOCKING CREW EXECUTION ---

    try:
        final_assessment = json.loads(crew_result_str)
    except json.JSONDecodeError:
        logger.error(f"Agent Log: Error decoding final assessment JSON for {onboarding_id}: {crew_result_str}")
        final_assessment = {"overall_status": "RequiresManualIntervention", "summary_message": "Error processing agent results."}

    # --- Process final_assessment to build the update_payload for FastAPI ---
    updated_verification_steps: List[Dict[str, Any]] = []

    bvn_res = final_assessment.get("bvn_nin_result", {}).get("bvn_verification", {})
    updated_verification_steps.append({
        "step_name": "BVNVerification",
        "status": {"status": bvn_res.get("status", "Error"), "message": bvn_res.get("bvn_details", {}).get("message"), "details": bvn_res.get("bvn_details")}
    })
    nin_res = final_assessment.get("bvn_nin_result", {}).get("nin_verification", {})
    updated_verification_steps.append({
        "step_name": "NINVerification",
        "status": {"status": nin_res.get("status", "Error"), "message": nin_res.get("nin_details", {}).get("message"), "details": nin_res.get("nin_details")}
    })

    id_proc_res = final_assessment.get("id_processing_result", {})
    id_ocr = id_proc_res.get("ocr", {})
    id_val = id_proc_res.get("validation", {})
    id_status_val = "Error"
    id_msg = "ID processing error."
    if id_val.get("validation_status") == "Valid": id_status_val = "Verified"
    elif id_val.get("validation_status") in ["Suspicious", "Invalid"]: id_status_val = "RequiresManualReview" if id_val.get("validation_status") == "Suspicious" else "Failed"
    elif id_ocr.get("status") == "Failed": id_status_val = "Failed"
    if id_val.get("validation_issues"): id_msg = f"ID Validation: {id_val.get('validation_status')}, Issues: {id_val.get('validation_issues')}"
    elif id_ocr.get("status") == "Failed": id_msg = f"ID OCR Failed: {id_ocr.get('error_message', 'Unknown OCR error')}"
    elif id_status_val == "Verified": id_msg = "ID document processed and validated."
    updated_verification_steps.append({
        "step_name": "IDDocumentCheck",
        "status": {"status": id_status_val, "message": id_msg, "details": {"ocr": id_ocr, "validation": id_val}}
    })

    fm_res = final_assessment.get("face_match_result", {})
    fm_status_val = "Error"
    if fm_res.get("status") == "Success": fm_status_val = "Verified" if fm_res.get("is_match") else "Failed"
    elif fm_res.get("status") == "Failed": fm_status_val = "Failed"
    updated_verification_steps.append({
        "step_name": "FaceMatch",
        "status": {"status": fm_status_val, "message": fm_res.get("message"), "details": fm_res}
    })

    aml_s_res = final_assessment.get("aml_result", {})
    aml_status_val = "Error"
    if aml_s_res.get("status") == "Clear": aml_status_val = "Verified"
    elif aml_s_res.get("status") == "Hit": aml_status_val = "Failed" # Or RequiresManualReview
    updated_verification_steps.append({
        "step_name": "AMLScreening",
        "status": {"status": aml_status_val, "message": aml_s_res.get("details", {}).get("message"), "details": aml_s_res}
    })

    addr_ver_step_payload = {"step_name": "AddressVerification", "status": {"status": "NotApplicable"}}
    util_proc_res = final_assessment.get("utility_bill_processing_result")
    if util_proc_res and util_proc_res.get("ocr"):
        util_ocr = util_proc_res.get("ocr", {})
        util_val = util_proc_res.get("validation", {})
        addr_status_val = "Error"
        addr_msg = "Address verification error."
        if util_val.get("validation_status") == "Valid": addr_status_val = "Verified"
        elif util_val.get("validation_status") in ["Suspicious", "Invalid"]: addr_status_val = "RequiresManualReview" if util_val.get("validation_status") == "Suspicious" else "Failed"
        elif util_ocr.get("status") == "Failed": addr_status_val = "Failed"
        if util_val.get("validation_issues"): addr_msg = f"Utility Bill Validation: {util_val.get('validation_status')}, Issues: {util_val.get('validation_issues')}"
        elif util_ocr.get("status") == "Failed": addr_msg = f"Utility Bill OCR Failed: {util_ocr.get('error_message', 'Unknown OCR error')}"
        elif addr_status_val == "Verified": addr_msg = "Address verified via utility bill."
        addr_ver_step_payload["status"] = {"status": addr_status_val, "message": addr_msg, "details": {"ocr": util_ocr, "validation": util_val}}
    elif request.requested_account_tier.tier in ["Tier2", "Tier3"] and not any(doc.type_name == "UtilityBill" for doc in request.documents):
         addr_ver_step_payload["status"] = {"status": "Pending", "message":"Utility bill required for Tier 2/3 but not provided."}
    updated_verification_steps.append(addr_ver_step_payload)

    overall_status = final_assessment.get("overall_status", "RequiresManualIntervention")
    achieved_tier_val = final_assessment.get("approved_tier") if overall_status == "Approve" else None

    update_payload = {
        "status": overall_status,
        "message": final_assessment.get("summary_message", "Processing complete."),
        "last_updated_at": datetime.utcnow(),
        "achieved_tier": {"tier": achieved_tier_val} if achieved_tier_val else None,
        "verification_steps": updated_verification_steps,
        "customer_id": f"CUST-{onboarding_id.split('-')[-1]}" if overall_status == "Approve" else None
    }
    return update_payload

async def get_onboarding_status_from_agent(onboarding_id: str) -> Dict[str, Any]:
