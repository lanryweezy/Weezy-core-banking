# Main logic for the Customer Onboarding AI Agent
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session # For type hinting if db session is passed around
from datetime import datetime

# Agent specific config and tools
from . import config as agent_config
from . import tools as agent_tools

# CBS Schemas
from weezy_cbs.customer_identity_management import schemas as cim_schemas
# CBS Services (especially for logging AI tasks)
from weezy_cbs.ai_automation_layer import services as ai_services
from weezy_cbs.ai_automation_layer import models as ai_models # For AITaskStatusEnum

class CustomerOnboardingAIAgent:
    def __init__(self, db: Session): # Agent might need DB session to pass to tools
        self.db = db
        self.agent_name = agent_config.AGENT_CONFIG_NAME
        # In a real agent framework (CrewAI, LangGraph), this setup would be more complex,
        # potentially loading LLM, tools, memory, etc.

        # Initialize services needed by the agent or its tools
        # For now, tools call services directly. If agent orchestrates more, it might hold service instances.
        self.ai_task_logger = ai_services.ai_task_log_service # For logging agent's main task

    def _log_agent_task_start(self, input_summary: Dict) -> models.AITaskLog:
        log_create_schema = ai_schemas.AITaskLogCreate(
            task_name=f"{self.agent_name}_Flow",
            input_data_summary_json=input_summary,
            # model_metadata_id could be an ID for this agent's config/definition if stored in AIModelMetadata
            status=ai_models.AITaskStatusEnum.PROCESSING # Mark as processing right away
        )
        log_entry = self.ai_task_logger.create_task_log(self.db, log_create_schema)
        # self.ai_task_logger.update_task_log_start(self.db, log_entry.id) # Already set to PROCESSING
        return log_entry

    def _log_agent_task_finish(self, log_entry: models.AITaskLog, status: ai_models.AITaskStatusEnum, output_summary: Dict, error_msg: Optional[str] = None):
        self.ai_task_logger.update_task_log_finish(
            self.db, log_entry.id, status,
            output_summary=output_summary,
            error_msg=error_msg
        )

    def run_onboarding_flow(
        self,
        initial_customer_details: Dict[str, Any], # e.g., {"first_name": "John", "last_name": "Doe", "phone_number": "080..."}
        documents_provided: List[Dict[str, str]], # e.g., [{"document_type": "NIN_SLIP", "document_url": "s3://.../nin.jpg"}]
        bvn_to_verify: Optional[str] = None,
        nin_to_verify: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates the customer onboarding process.
        1. Logs start of task.
        2. Verifies BVN/NIN if provided.
        3. Processes documents using OCR.
        4. Cross-references/validates data.
        5. Attempts to create customer profile.
        6. Stores document references.
        7. Logs end of task.
        Returns a summary of the outcome.
        """
        task_input_summary = {
            "initial_customer_details": initial_customer_details,
            "documents_provided_count": len(documents_provided),
            "bvn_provided": bool(bvn_to_verify),
            "nin_provided": bool(nin_to_verify)
        }
        main_task_log = self._log_agent_task_start(task_input_summary)

        onboarding_status = "PENDING"
        onboarding_issues = []
        created_customer_id: Optional[int] = None
        final_customer_data: Optional[cim_schemas.CustomerResponse] = None

        try:
            # --- Step 1: BVN/NIN Verification (if provided) ---
            bvn_data: Optional[Dict[str, Any]] = None
            if bvn_to_verify:
                print(f"AGENT: Verifying BVN: {bvn_to_verify}")
                bvn_result = agent_tools.verify_bvn_tool(
                    self.db, bvn=bvn_to_verify,
                    phone_number=initial_customer_details.get("phone_number"),
                    # customer_id_for_logging=None, # Pre-check, no customer_id yet
                    triggering_user_id=self.agent_name
                )
                if not bvn_result.is_valid:
                    onboarding_issues.append(f"BVN verification failed: {bvn_result.message}")
                    # Potentially halt onboarding or proceed with lower tier based on policy
                else:
                    bvn_data = bvn_result.bvn_data
                    print(f"AGENT: BVN data retrieved: {bvn_data}")
                    # TODO: Cross-reference bvn_data with initial_customer_details
                    # e.g., if initial_customer_details['first_name'] != bvn_data['firstName'] -> add issue/flag

            nin_data: Optional[Dict[str, Any]] = None
            if nin_to_verify:
                print(f"AGENT: Verifying NIN: {nin_to_verify}")
                nin_result = agent_tools.verify_nin_tool(
                    self.db, nin=nin_to_verify,
                    # customer_id_for_logging=None,
                    triggering_user_id=self.agent_name
                )
                if not nin_result.is_valid:
                    onboarding_issues.append(f"NIN verification failed: {nin_result.message}")
                else:
                    nin_data = nin_result.nin_data
                    print(f"AGENT: NIN data retrieved: {nin_data}")
                    # TODO: Cross-reference nin_data

            # --- Step 2: Document Processing (OCR) ---
            parsed_documents_data: List[Dict[str, Any]] = []
            for doc_info in documents_provided:
                print(f"AGENT: Processing document: {doc_info['document_type']} from {doc_info['document_url']}")
                ocr_result = agent_tools.parse_document_with_ocr_tool(
                    self.db,
                    document_url=doc_info["document_url"],
                    document_type=doc_info["document_type"],
                    ocr_model_name=agent_config.DEFAULT_OCR_MODEL_NAME,
                    triggering_user_id=self.agent_name
                )
                parsed_documents_data.append({**doc_info, "ocr_data": ocr_result})
                if ocr_result.get("error"):
                    onboarding_issues.append(f"OCR failed for {doc_info['document_type']}: {ocr_result.get('error')}")
                # TODO: Cross-reference OCR data with initial_details, BVN/NIN data.
                # Example: If ID card OCR name doesn't match BVN name within a threshold.

            # --- Step 3: Assemble Customer Creation Data ---
            # This logic would merge data from initial_details, BVN, NIN, OCR, and apply rules.
            # For simplicity, we'll primarily use initial_customer_details and augment if BVN/NIN verified.

            customer_create_payload = initial_customer_details.copy()
            if bvn_data and bvn_data.get("bvn"): customer_create_payload["bvn"] = bvn_data["bvn"]
            if nin_data and nin_data.get("nin"): customer_create_payload["nin"] = nin_data["nin"]

            # Ensure all mandatory fields for the target tier are present
            # This is a simplified check; real tier determination is complex.
            customer_create_schema = cim_schemas.CustomerCreate(**customer_create_payload) # Validate payload structure

            # --- Step 4: Create Customer Profile ---
            if not onboarding_issues: # Proceed only if no major verification/OCR issues so far (configurable policy)
                print(f"AGENT: Attempting to create customer profile.")
                try:
                    created_customer_orm = agent_tools.create_customer_tool(
                        self.db, customer_data=customer_create_schema, triggering_user_id=self.agent_name
                    )
                    created_customer_id = created_customer_orm.id
                    # Convert ORM object to Pydantic schema for consistent data structure
                    final_customer_data = cim_schemas.CustomerResponse.from_orm(created_customer_orm)
                    onboarding_status = "CUSTOMER_PROFILE_CREATED"
                    print(f"AGENT: Customer profile created with ID: {created_customer_id}")

                    # --- Step 5: Store Document References ---
                    for doc_data_with_ocr in parsed_documents_data:
                        if not doc_data_with_ocr.get("ocr_data", {}).get("error"): # Only store if OCR was okayish
                            doc_create_schema = cim_schemas.CustomerDocumentCreate(
                                customer_id=created_customer_id,
                                document_type=doc_data_with_ocr["document_type"],
                                document_url=doc_data_with_ocr["document_url"],
                                # Populate other fields from OCR data if available and mapped
                                document_number=doc_data_with_ocr.get("ocr_data", {}).get("document_number"),
                                # expiry_date= ...
                            )
                            agent_tools.store_document_reference_tool(
                                self.db, doc_data=doc_create_schema, triggering_user_id=self.agent_name
                            )
                            print(f"AGENT: Stored document reference for {doc_data_with_ocr['document_type']}")
                    onboarding_status = "COMPLETED_SUCCESSFULLY"

                except Exception as e: # Catch errors from create_customer_tool or store_document_reference_tool
                    onboarding_issues.append(f"Customer profile/document creation failed: {str(e)}")
                    onboarding_status = "FAILED_PROFILE_CREATION"
            else:
                onboarding_status = "FAILED_PRE_CHECKS"
                print(f"AGENT: Onboarding halted due to pre-check issues: {onboarding_issues}")


            # --- Finalize ---
            if onboarding_status == "COMPLETED_SUCCESSFULLY":
                self._log_agent_task_finish(main_task_log, ai_models.AITaskStatusEnum.SUCCESS,
                                            {"status": onboarding_status, "customer_id": created_customer_id, "issues": onboarding_issues})
                return {"status": onboarding_status, "message": "Customer onboarded successfully.", "customer_id": created_customer_id, "customer_data": final_customer_data.dict() if final_customer_data else None}
            else:
                self._log_agent_task_finish(main_task_log, ai_models.AITaskStatusEnum.FAILED,
                                            {"status": onboarding_status, "issues": onboarding_issues})
                return {"status": onboarding_status, "message": "Customer onboarding failed.", "issues": onboarding_issues}

        except Exception as e:
            # Catch any unexpected error during the flow
            print(f"AGENT_ERROR: Unhandled exception in onboarding flow: {e}")
            onboarding_issues.append(f"System error: {str(e)}")
            self._log_agent_task_finish(main_task_log, ai_models.AITaskStatusEnum.FAILED,
                                        {"status": "SYSTEM_ERROR", "issues": onboarding_issues}, error_msg=str(e))
            return {"status": "SYSTEM_ERROR", "message": "An unexpected system error occurred during onboarding.", "issues": onboarding_issues}


if __name__ == '__main__':
    # This is a conceptual test/example of how to run the agent.
    # It requires a mock DB session and for all imported services/schemas to be available.

    # Mock DB session (replace with actual session setup for testing)
    class MockDBSession:
        def add(self, obj): print(f"MockDB: Add {obj}")
        def commit(self): print("MockDB: Commit")
        def refresh(self, obj): print(f"MockDB: Refresh {obj}")
        def query(self, *args): # Extremely simplified query mock
            class MockQuery:
                def filter(self, *criterion): return self
                def first(self): return None # Default to not found for existence checks
                def count(self): return 0
                def all(self): return []
                def options(self, *args): return self
                def offset(self, val): return self
                def limit(self, val): return self
                def order_by(self, val): return self
            return MockQuery()

    mock_db = MockDBSession()

    print("--- Conceptual Test of Customer Onboarding Agent ---")
    agent = CustomerOnboardingAIAgent(db=mock_db) # type: ignore

    sample_customer_details = {
        "first_name": "Test", "last_name": "User", "phone_number": "08012345670",
        "email": "test.user@example.com", "date_of_birth": "1995-05-10",
        "customer_type": "INDIVIDUAL", # This should match the enum value or schema type
        # Ensure all required fields for CustomerCreate schema are here or defaulted
        "nationality": "NG",
        # "account_tier": "TIER_1" # This is usually determined by service, not direct input here
    }
    sample_documents = [
        {"document_type": "NIN_SLIP", "document_url": "file://path/to/nin_slip.jpg"},
        {"document_type": "UTILITY_BILL", "document_url": "file://path/to/utility_bill.pdf"}
    ]

    result = agent.run_onboarding_flow(
        initial_customer_details=sample_customer_details,
        documents_provided=sample_documents,
        bvn_to_verify="12345678901", # Valid mock BVN
        # nin_to_verify="19876543210"
    )

    print("\n--- Onboarding Result ---")
    print(json.dumps(result, indent=2, default=str))

    print("\n--- Test with failing BVN ---")
    result_fail_bvn = agent.run_onboarding_flow(
        initial_customer_details=sample_customer_details,
        documents_provided=sample_documents,
        bvn_to_verify="INVALID12345",
    )
    print(json.dumps(result_fail_bvn, indent=2, default=str))
```
