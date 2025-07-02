# LangChain/CrewAI agent logic for Customer Onboarding

from typing import Dict, Any, List
from datetime import datetime
import json # For parsing expected outputs if they are JSON strings

# Assuming schemas are in the same directory
from .schemas import OnboardingRequest, VerificationStepResult, VerificationStatus, DocumentType
# Import the defined tools
from .tools import nin_bvn_verification_tool, ocr_tool, face_match_tool, aml_screening_tool # Added aml_screening_tool

from crewai import Agent, Task, Crew, Process
# from langchain_openai import ChatOpenAI # Actual LLM
from langchain_community.llms.fake import FakeListLLM # Using FakeListLLM for mocking CrewAI execution

# --- LLM Configuration (Mocked for now) ---
def get_customer_onboarding_llm(expected_responses: List[str]):
    # In a real scenario, load API keys from config (e.g., core_settings.OPENAI_API_KEY)
    # return ChatOpenAI(model_name="gpt-4-turbo", temperature=0.1)
    # For testing without actual LLM calls, use FakeListLLM
    # Each response in the list corresponds to an expected LLM call by the agent/tasks.
    # The content of these responses should be what the LLM would ideally return to fulfill the task's expected_output.
    return FakeListLLM(responses=expected_responses)


# --- Agent Definition ---
# Note: Tools are instantiated when creating the agent or tasks.
# For CrewAI, tools are typically passed to the Agent constructor.

onboarding_tools = [nin_bvn_verification_tool, ocr_tool, face_match_tool, aml_screening_tool] # Added aml_screening_tool

# This is a placeholder for expected LLM outputs if we were to run the full crew.
# The number of responses should match the number of times the LLM is invoked by the agent across all tasks.
# For now, we'll mock the task outputs directly instead of mocking the LLM responses that produce them.
# llm = get_customer_onboarding_llm(expected_responses=["Mock LLM response for task 1", "Mock for task 2", ...])

customer_onboarding_specialist = Agent(
    role="Customer Onboarding Specialist AI",
    goal=(
        "Efficiently and accurately manage the entire customer KYC process, "
        "from initial data collection and document submission to multi-step verification (BVN, NIN, ID, Face Match), "
        "and final decisioning for account opening, adhering to Nigerian banking regulations (CBN tiers)."
    ),
    backstory=(
        "An advanced AI agent designed to streamline customer onboarding for a modern Nigerian bank. "
        "It leverages a suite of specialized tools to perform verifications, assess risk, and ensure compliance. "
        "It aims to provide a seamless experience for applicants while maintaining strict regulatory adherence."
    ),
    tools=onboarding_tools,
    llm=FakeListLLM(responses=["Okay, I will start the BVN/NIN verification.", "Processing ID document.", "Processing utility bill.", "Performing face match.", "AML screening complete.", "Finalizing assessment."]), # Provide enough mock responses for the agent's internal thoughts/tool selections
    verbose=True,
    allow_delegation=False,
)

# --- Task Definitions ---
def create_onboarding_tasks(onboarding_request_data: Dict[str, Any], documents: List[DocumentType]) -> List[Task]:
    tasks = []
    # Convert dict to OnboardingRequest Pydantic model for easier access if needed, or use dict directly.
    # For context in tasks, it's often easier to pass simple dicts or strings.
    context = {
        "bvn": onboarding_request_data.get("bvn"),
        "nin": onboarding_request_data.get("nin"),
        "first_name": onboarding_request_data.get("first_name"),
        "last_name": onboarding_request_data.get("last_name"),
        "date_of_birth": onboarding_request_data.get("date_of_birth"),
        "phone_number": onboarding_request_data.get("phone_number"),
        "documents": [doc.model_dump() for doc in documents] # Pass document info
    }

    # Task 1: BVN/NIN Verification
    bvn_nin_task = Task(
        description=f"""\
        Verify the customer's BVN and/or NIN using the provided details.
        Input Context: {json.dumps(context)}
        Use the NINBVNVerificationTool.
        Focus on matching provided details (first name, last name, DOB, phone) with official records.
        """,
        expected_output="""\
        A JSON string detailing BVN and NIN verification results.
        Example: {
            "bvn_verification": {"status": "Verified", "details": {"message": "BVN details match.", "matched_data": {...}}},
            "nin_verification": {"status": "Mismatch", "details": {"message": "NIN details mismatch.", "mismatches": ["DOB mismatch"], "nin_record_summary": {...}}}
        }""",
        agent=customer_onboarding_specialist,
        tools=[nin_bvn_verification_tool] # Explicitly list tools for the task if different from agent's default
    )
    tasks.append(bvn_nin_task)

    # Task 2: ID Document Processing
    id_document = next((doc for doc in documents if doc.type_name in ["NationalID", "DriversLicense", "Passport"]), None)
    if id_document:
        id_doc_task = Task(
            description=f"""\
            Process the customer's ID document using OCR.
            Document URL: {id_document.url}, Document Type: {id_document.type_name}
            Use the OCRTool.
            Extract key information from the document.
            """,
            expected_output=f"""\
            A JSON string with OCR results for the ID document.
            Example: {{
                "document_type": "{id_document.type_name}", "status": "Success",
                "extracted_data": {{"surname": "...", "first_name": "...", "nin": "...", "date_of_birth": "..."}}
            }}""",
            agent=customer_onboarding_specialist,
            tools=[ocr_tool],
            context={"document_url": id_document.url, "document_type": id_document.type_name} # Provide specific context if needed
        )
        tasks.append(id_doc_task)

    # Task 3: Utility Bill Processing (if applicable, e.g., for Tier 2/3 address verification)
    utility_bill_doc = next((doc for doc in documents if doc.type_name == "UtilityBill"), None)
    if utility_bill_doc and onboarding_request_data.get("requested_account_tier", {}).get("tier") in ["Tier2", "Tier3"]:
        utility_bill_task = Task(
            description=f"""\
            Process the customer's utility bill using OCR for address verification.
            Document URL: {utility_bill_doc.url}, Document Type: {utility_bill_doc.type_name}
            Use the OCRTool.
            Extract address information and biller details.
            """,
            expected_output=f"""\
            A JSON string with OCR results for the utility bill.
            Example: {{
                "document_type": "{utility_bill_doc.type_name}", "status": "Success",
                "extracted_data": {{"account_name": "...", "address": "...", "biller": "..."}}
            }}""",
            agent=customer_onboarding_specialist,
            tools=[ocr_tool]
        )
        tasks.append(utility_bill_task)

    # Task 4: Face Match
    selfie_doc = next((doc for doc in documents if doc.type_name == "Selfie"), None)
    # Assume ID photo URL comes from OCR result of ID document or is passed explicitly
    # For mock, we'll need to ensure id_photo_url is available in context if this task runs
    if selfie_doc and id_document: # Simplified: assumes id_document was processed
        face_match_task = Task(
            description=f"""\
            Perform a face match between the customer's selfie and their ID photo.
            Selfie URL: {selfie_doc.url}
            ID Photo URL (assumed to be from processed ID document): {id_document.url} (placeholder, real URL would be from OCR'd ID image)
            Use the FaceMatchTool.
            """,
            expected_output="""\
            A JSON string with face match results.
            Example: {"status": "Success", "is_match": true, "match_score": 0.92, "confidence": "High"}""",
            agent=customer_onboarding_specialist,
            tools=[face_match_tool]
        )
        tasks.append(face_match_task)

    # Task 5: AML Screening
    aml_task = Task(
        description=f"""\
        Perform AML screening for the applicant using their full name, date of birth, and nationality.
        Applicant Full Name: {onboarding_request_data.get('first_name', '')} {onboarding_request_data.get('middle_name', '') if onboarding_request_data.get('middle_name') else ''} {onboarding_request_data.get('last_name', '')}
        Date of Birth: {onboarding_request_data.get('date_of_birth')}
        Nationality: {onboarding_request_data.get('country', 'NG')}
        Use the AMLScreeningTool.
        """,
        expected_output="""\
        A JSON string with AML screening results.
        Example: {"status": "Clear", "risk_level": "Low", "details": {"screened_lists": ["Mock Sanctions", ...], "message": "Applicant clear."}}
        Example on hit: {"status": "Hit", "risk_level": "High", "details": {"hit_details": {"matched_name": "...", "list_name": "...", "reason": "..."}}}
        """,
        agent=customer_onboarding_specialist,
        tools=[aml_screening_tool]
    )
    tasks.append(aml_task)

    # Task 6: Final Assessment & Tier Assignment
    final_assessment_task = Task(
        description="""\
        Consolidate all verification results (BVN/NIN, ID OCR, Utility Bill OCR, Face Match, AML).
        Assess overall KYC status. Determine the achievable account tier based on verified information.
        Provide a final recommendation: 'Approve', 'Reject', or 'RequiresManualReview'.
        If 'Approve', specify the approved tier. If 'Reject' or 'RequiresManualReview', provide clear reasons.
        """,
        expected_output="""\
        A JSON string summarizing the final assessment.
        Example: {
            "overall_status": "Approve", "approved_tier": "Tier1",
            "summary_message": "All verifications successful. Approved for Tier 1 account.",
            "bvn_nin_result": {/* from previous task */},
            "id_ocr_result": {/* ... */},
            "face_match_result": {/* ... */},
            "aml_result": {/* ... */}
        }""",
        agent=customer_onboarding_specialist,
        # This task might not use tools directly but relies on context from previous tasks.
        # context = previous_task_outputs would be implicitly managed by CrewAI
    )
    tasks.append(final_assessment_task)

    return tasks

# --- Main Workflow Function ---
async def start_onboarding_process(onboarding_id: str, request: OnboardingRequest) -> Dict[str, Any]:
    """
    Initiates and manages the customer onboarding workflow using CrewAI.
    """
    print(f"Agent Log: Starting CrewAI onboarding process for ID: {onboarding_id}, Customer: {request.first_name} {request.last_name}")

    onboarding_crew_inputs = request.model_dump()
    onboarding_crew_inputs['onboarding_id'] = onboarding_id

    # Create tasks based on the request (e.g., which documents were provided)
    defined_tasks = create_onboarding_tasks(onboarding_crew_inputs, request.documents)

    if not defined_tasks:
        print(f"Agent Log: No tasks defined for {onboarding_id}. Aborting.")
        return {
            "status": "RequiresManualIntervention", # type: ignore
            "message": "Agent could not define tasks based on input. Please review.",
            "last_updated_at": datetime.utcnow(),
            "verification_steps": []
        }

    onboarding_crew = Crew(
        agents=[customer_onboarding_specialist],
        tasks=defined_tasks,
        process=Process.sequential,
        verbose=2,
        # memory=True # Enable memory for the crew if needed for context passing across complex tasks
    )

    # --- MOCKING CREW EXECUTION ---
    # In a real scenario, you'd run: crew_result = onboarding_crew.kickoff(inputs=onboarding_crew_inputs)
    # For now, we'll construct a mock result based on the tasks.
    print(f"Agent Log: Simulating CrewAI kickoff for {onboarding_id} with {len(defined_tasks)} tasks.")

    # This is a highly simplified mock of the final task's output.
    # A real CrewAI execution would populate this based on actual tool calls and LLM processing.
    mock_final_assessment_output = {
        "overall_status": "Approve", # Possible: "Approve", "Reject", "RequiresManualReview"
        "approved_tier": request.requested_account_tier.tier, # Defaulting to requested, real logic would determine this
        "summary_message": f"Mock approval for {request.first_name}. All checks passed (simulated).",
        "bvn_nin_result": {"bvn_verification": {"status": "Verified"}, "nin_verification": {"status": "Verified"}}, # Mock
        "id_ocr_result": {"status": "Success", "extracted_data": {"first_name": request.first_name}}, # Mock
        "face_match_result": {"status": "Success", "is_match": True, "match_score": 0.9}, # Mock
        "aml_result": {"aml_status": "Clear", "risk_rating": "Low"}, # Mock
        # Utility bill result would be here if applicable
    }
    crew_result_str = json.dumps(mock_final_assessment_output) # CrewAI tasks often return strings

    print(f"Agent Log: Mock CrewAI processing complete for {onboarding_id}.")
    # --- END MOCKING CREW EXECUTION ---

    # Process the crew_result to update the OnboardingProcess structure
    try:
        final_assessment = json.loads(crew_result_str) # Assuming the final task returns a JSON string
    except json.JSONDecodeError:
        print(f"Agent Log: Error decoding final assessment JSON for {onboarding_id}.")
        final_assessment = {"overall_status": "RequiresManualIntervention", "summary_message": "Error processing agent results."}


    # Update verification steps based on (mocked) individual task results if available in final_assessment
    updated_verification_steps: List[Dict[str, Any]] = [] # Will hold dicts to be parsed by Pydantic

    # BVN/NIN
    bvn_res = final_assessment.get("bvn_nin_result", {}).get("bvn_verification", {})
    nin_res = final_assessment.get("bvn_nin_result", {}).get("nin_verification", {})
    updated_verification_steps.append({
        "step_name": "BVNVerification",
        "status": {"status": bvn_res.get("status", "Error"), "message": bvn_res.get("details", {}).get("message"), "details": bvn_res.get("details")}
    })
    updated_verification_steps.append({
        "step_name": "NINVerification",
        "status": {"status": nin_res.get("status", "Error"), "message": nin_res.get("details", {}).get("message"), "details": nin_res.get("details")}
    })

    # ID Document
    id_ocr_res = final_assessment.get("id_ocr_result", {})
    updated_verification_steps.append({
        "step_name": "IDDocumentCheck",
        "status": {"status": id_ocr_res.get("status", "Error"), "message": id_ocr_res.get("error_message"), "details": id_ocr_res.get("extracted_data")}
    })

    # Face Match
    face_match_res = final_assessment.get("face_match_result", {})
    updated_verification_steps.append({
        "step_name": "FaceMatch",
        "status": {"status": face_match_res.get("status", "Error"), "message": face_match_res.get("message"), "details": face_match_res}
    })

    # AML Screening
    aml_res = final_assessment.get("aml_result", {})
    updated_verification_steps.append({
        "step_name": "AMLScreening",
        "status": {"status": aml_res.get("aml_status", "Error"), "message": aml_res.get("message"), "details": aml_res}
    })

    # Utility Bill (if processed)
    util_ocr_res = final_assessment.get("utility_bill_ocr_result", {}) # Assuming it might be nested if run
    if util_ocr_res:
         updated_verification_steps.append({
            "step_name": "AddressVerification", # Assuming utility bill is for address
            "status": {"status": util_ocr_res.get("status", "Error"), "message": util_ocr_res.get("error_message"), "details": util_ocr_res.get("extracted_data")}
        })
    else: # Ensure AddressVerification step is present even if not run or N/A
        addr_ver_step = next((s for s in request.documents if s.type_name == "UtilityBill"), None) # Check if it was expected
        if addr_ver_step or request.requested_account_tier.tier in ["Tier2", "Tier3"]:
            updated_verification_steps.append({"step_name": "AddressVerification", "status": {"status": "NotStarted"}})
        else:
            updated_verification_steps.append({"step_name": "AddressVerification", "status": {"status": "NotApplicable"}})


    overall_onboarding_status = final_assessment.get("overall_status", "RequiresManualIntervention")
    achieved_tier_val = final_assessment.get("approved_tier") if overall_onboarding_status == "Approve" else None


    # This is the payload that main.py will use to update the OnboardingProcess object
    update_payload = {
        "status": overall_onboarding_status,
        "message": final_assessment.get("summary_message", "Processing complete. Review details."),
        "last_updated_at": datetime.utcnow(),
        "achieved_tier": {"tier": achieved_tier_val} if achieved_tier_val else None,
        "verification_steps": updated_verification_steps,
        "customer_id": f"CUST-{onboarding_id.split('-')[-1]}" if overall_onboarding_status == "Approve" else None # Mock customer ID
    }
    return update_payload


async def get_onboarding_status_from_agent(onboarding_id: str) -> Dict[str, Any]:
    """
    Retrieves the current status of the onboarding process. (Mocked)
    In a real system, this would query where the agent/crew stores its state.
    """
    print(f"Agent Log: Fetching status for onboarding ID: {onboarding_id} (mocked, no active polling)")
    return { # This function is less relevant if start_onboarding_process returns the final state for the background task
        "message": "Status check from agent: Process is assumed to be handled by the initial call. Query DB for actual status.",
        "last_updated_at": datetime.utcnow()
    }


if __name__ == "__main__":
    import asyncio
    import json

    async def test_run():
        mock_documents = [
            DocumentType(type_name="NationalID", url=HttpUrl("http://example.com/id.jpg")),
            DocumentType(type_name="Selfie", url=HttpUrl("http://example.com/selfie.jpg")),
            # DocumentType(type_name="UtilityBill", url=HttpUrl("http://example.com/bill.pdf"))
        ]
        mock_request_data = OnboardingRequest(
            first_name="Test", last_name="User", date_of_birth="2000-01-01",
            phone_number="08011223344", email_address="test.user@example.com",
            bvn="11223344556", nin="88776655443",
            requested_account_tier={"tier": "Tier1"}, documents=mock_documents
        )
        onboarding_id_test = "ONB-CREWTEST01"

        print(f"\n--- Simulating start_onboarding_process (CrewAI) for {onboarding_id_test} ---")
        update_payload = await start_onboarding_process(onboarding_id_test, mock_request_data)
        print(f"Update payload from agent for {onboarding_id_test}:")
        print(json.dumps(update_payload, indent=2, default=str))

    asyncio.run(test_run())
    print("\nCustomer Onboarding Agent logic (agent.py) with CrewAI structure (mocked execution).")
