# Agent for Customer Onboarding
from . import tools
from . import config
from weezy_cbs.accounts_ledger_management import services as account_services
from weezy_cbs.accounts_ledger_management import schemas as account_schemas

class CustomerOnboardingAgent:
    def __init__(self, agent_id="onboarding_agent_001", memory_storage=None):
        self.agent_id = agent_id
        self.role = "Manages the entire KYC process from registration to verification and account creation."
        # Memory: Stores onboarding progress and identity details for each customer session
        # Example: self.memory = {"session_id_123": {"progress": "bvn_verified", "details": {...}}}
        self.memory = memory_storage if memory_storage is not None else {}

    def _get_session_memory(self, session_id):
        if session_id not in self.memory:
            self.memory[session_id] = {"progress": "started", "data": {}}
        return self.memory[session_id]

    def _update_session_memory(self, session_id, progress_status, data_update=None):
        session = self._get_session_memory(session_id)
        session["progress"] = progress_status
        if data_update:
            session["data"].update(data_update)

    def greet_customer(self, session_id: str) -> str:
        """Greets the customer and initiates the onboarding process."""
        self._get_session_memory(session_id) # Initialize memory if not present
        return "Welcome to Weezy Bank! I'm here to help you open an account. Let's start with your documents."

    def process_documents(self, session_id: str, name: str, phone_number: str, bvn: str = None, nin: str = None, id_card_path: str = None, utility_bill_path: str = None, selfie_path: str = None) -> dict:
        """
        Processes customer documents through various verification steps.
        Inputs:
            session_id: Unique identifier for the onboarding session.
            name: Customer's full name.
            phone_number: Customer's phone number.
            bvn: Bank Verification Number.
            nin: National Identity Number.
            id_card_path: File path to the ID card image.
            utility_bill_path: File path to the utility bill image.
            selfie_path: File path to the selfie image.
        """
        session_memory = self._get_session_memory(session_id)
        session_memory['data']['customer_name'] = name

        # Step 0: Create a customer record
        try:
            customer = tools.customer_services.create_customer(next(tools.get_db()), tools.customer_schemas.CustomerCreate(first_name=name.split(" ")[0], last_name=name.split(" ")[-1], phone_number=phone_number, bvn=bvn, nin=nin))
            self._update_session_memory(session_id, "customer_created", {"customer_id": customer.id})
        except tools.customer_services.DuplicateEntryException as e:
            return {"status": "failed", "message": "Customer with these details already exists.", "details": str(e)}


        # Step 1: BVN/NIN Verification
        if bvn:
            bvn_verification_result = tools.verify_bvn_nin(customer_id=customer.id, bvn=bvn)
            self._update_session_memory(session_id, "bvn_verification_attempted", {"bvn_result": bvn_verification_result})
            if not bvn_verification_result.get("is_valid"):
                return {"status": "failed", "message": "BVN verification failed.", "details": bvn_verification_result}
            # Potentially cross-check name from BVN with provided name
        elif nin:
            nin_verification_result = tools.verify_bvn_nin(customer_id=customer.id, nin=nin)
            self._update_session_memory(session_id, "nin_verification_attempted", {"nin_result": nin_verification_result})
            if not nin_verification_result.get("is_valid"):
                return {"status": "failed", "message": "NIN verification failed.", "details": nin_verification_result}
        else:
            return {"status": "failed", "message": "Either BVN or NIN must be provided."}

        self._update_session_memory(session_id, "identity_verified_初步")

        # Step 2: Document OCR (ID Card and Utility Bill)
        parsed_id_data = {}
        if id_card_path:
            parsed_id_data = tools.ocr_document(id_card_path)
            self._update_session_memory(session_id, "id_card_ocr_attempted", {"id_ocr_result": parsed_id_data})
            if parsed_id_data.get("error"):
                 return {"status": "failed", "message": "ID Card OCR failed.", "details": parsed_id_data}
        # Add similar processing for utility_bill_path if needed for address verification etc.

        # Step 3: Face Match (if ID card and selfie are provided)
        if id_card_path and selfie_path: # Assuming OCR from ID card gives a face image or we use the ID card image directly
            # This step is conceptual as ocr_document doesn't specify face extraction.
            # Let's assume id_card_path can be used directly if it's a photo ID.
            face_match_result = tools.verify_face_match(id_card_path, selfie_path)
            self._update_session_memory(session_id, "face_match_attempted", {"face_match_result": face_match_result})
            if not face_match_result.get("match") or face_match_result.get("confidence", 0) < config.MIN_CONFIDENCE_SCORE_FACE_MATCH:
                return {"status": "failed", "message": "Face verification failed or confidence too low.", "details": face_match_result}

        self._update_session_memory(session_id, "documents_processed")

        # Step 4: Flag Anomalies (Simplified - more complex logic can be added)
        # Example: Check if name from ID matches name from BVN/NIN
        # This requires more detailed parsing from OCR and BVN/NIN results.
        # For now, we assume previous steps handle critical failures.

        # Step 5: Auto-create account if all checks pass (Conceptual)
        # This would involve calling another module/service.
        account_creation_status = self._create_customer_account(session_id, session_memory['data'])
        if account_creation_status.get("success"):
            self._update_session_memory(session_id, "account_created", {"account_details": account_creation_status})
            return {"status": "success", "message": "Customer onboarded and account created successfully.", "account_number": account_creation_status.get("account_number")}
        else:
            self._update_session_memory(session_id, "account_creation_failed", {"error_details": account_creation_status})
            return {"status": "failed", "message": "Account creation failed.", "details": account_creation_status.get("message")}

    def _create_customer_account(self, session_id: str, customer_data: dict) -> dict:
        """
        Creates a customer account using the accounts_ledger_management service.
        """
        print(f"Attempting to create account for session {session_id} with data: {customer_data}")
        try:
            account = account_services.create_account(
                db=next(tools.get_db()),
                account_in=account_schemas.AccountCreateRequest(
                    customer_id=customer_data['customer_id'],
                    product_code="SAVINGS_TIER_1" # This should be determined by the agent's logic
                ),
                created_by_user_id="onboarding_agent"
            )
            return {"success": True, "account_number": account.account_number, "message": "Account created successfully."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_onboarding_status(self, session_id: str) -> dict:
        """Returns the current onboarding status for a given session."""
        if session_id in self.memory:
            return self.memory[session_id]
        return {"status": "not_found", "message": "No onboarding session found for this ID."}

