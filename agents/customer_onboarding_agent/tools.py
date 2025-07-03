# Conceptual tools for the Customer Onboarding AI Agent
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session # For type hinting if db session is passed to tools

# Import relevant schemas from CBS modules
# These imports assume the weezy_cbs package is correctly in PYTHONPATH
from weezy_cbs.customer_identity_management import schemas as cim_schemas
from weezy_cbs.customer_identity_management import services as cim_services
# from weezy_cbs.customer_identity_management.services import NotFoundException, DuplicateEntryException, ExternalServiceException # If using custom exceptions

# Conceptual: For AI services like OCR
from weezy_cbs.ai_automation_layer import schemas as ai_schemas
# from weezy_cbs.ai_automation_layer.services import DocumentParsingAIService # Example if we had such a service

# For OTP, if needed during onboarding flow by the agent
# from weezy_cbs.digital_channels_modules import schemas as dc_schemas
# from weezy_cbs.digital_channels_modules.services import digital_user_profile_service as dc_profile_service

# --- Tool Definitions ---

def verify_bvn_tool(
    db: Session,
    bvn: str,
    phone_number: Optional[str] = None,
    # first_name: Optional[str] = None, # NIBSS might use these for stricter matching
    # last_name: Optional[str] = None,
    # date_of_birth: Optional[str] = None # as YYYY-MM-DD string
    customer_id_for_logging: Optional[int] = None, # If we have a preliminary customer record
    triggering_user_id: str = "AI_ONBOARDING_AGENT"
) -> cim_schemas.BVNVerificationResponse:
    """
    Tool to verify BVN using the Customer Identity Management service.
    This tool wraps the actual service call.
    Customer_id is needed by the service to link verification to a customer.
    If customer doesn't exist yet, this tool might be part of a pre-check,
    or the service needs to handle BVN verification without an existing customer_id.

    For this agent, we assume it might be called before a customer record is created,
    or to verify against an existing preliminary record.
    The `cim_services.verify_bvn` expects a `customer_id`. This implies the agent
    might need to create a shell customer record first or the service needs adaptation.

    Let's assume for now the agent calls this AFTER a preliminary customer shell is made,
    or the service is adapted. For mock purposes, we'll proceed.
    If customer_id_for_logging is None, it means it's a pre-check.
    """
    print(f"TOOL: Verifying BVN {bvn} for customer ID {customer_id_for_logging or 'N/A'}")

    if not customer_id_for_logging:
        # This case is problematic for the current `cim_services.verify_bvn` which needs customer_id.
        # Simulating a direct NIBSS check without updating a customer record.
        print(f"TOOL_INFO: BVN pre-check for {bvn}. No customer record to update yet.")
        # Mock response for pre-check:
        if "INVALID" in bvn:
            return cim_schemas.BVNVerificationResponse(is_valid=False, message="BVN not found (mock pre-check).", bvn_data=None)

        mock_bvn_data = {
            "bvn": bvn, "firstName": "MockFirstName", "lastName": "MockLastName",
            "dateOfBirth": "1990-01-01", "phoneNumber": phone_number or "08012345678"
        }
        return cim_schemas.BVNVerificationResponse(is_valid=True, message="BVN seems valid (mock pre-check).", bvn_data=mock_bvn_data)

    bvn_req_schema = cim_schemas.BVNVerificationRequest(bvn=bvn, phone_number=phone_number)
    try:
        # This service call updates the customer record directly.
        response = cim_services.verify_bvn(
            db=db,
            customer_id=customer_id_for_logging,
            bvn_verification_request=bvn_req_schema,
            verified_by_user_id=triggering_user_id
        )
        return response
    except cim_services.NotFoundException: # If customer_id not found
         return cim_schemas.BVNVerificationResponse(is_valid=False, message=f"Customer ID {customer_id_for_logging} not found for BVN verification.", bvn_data=None)
    except cim_services.ExternalServiceException as e:
        return cim_schemas.BVNVerificationResponse(is_valid=False, message=f"BVN service error: {str(e)}", bvn_data=None)
    except Exception as e: # Catch-all for other unexpected errors
        print(f"TOOL_ERROR: Unexpected error in verify_bvn_tool: {e}")
        return cim_schemas.BVNVerificationResponse(is_valid=False, message=f"Unexpected tool error: {str(e)}", bvn_data=None)


def verify_nin_tool(
    db: Session,
    nin: str,
    customer_id_for_logging: Optional[int] = None,
    triggering_user_id: str = "AI_ONBOARDING_AGENT"
) -> cim_schemas.NINVerificationResponse:
    """Tool to verify NIN using the Customer Identity Management service."""
    print(f"TOOL: Verifying NIN {nin} for customer ID {customer_id_for_logging or 'N/A'}")

    if not customer_id_for_logging:
        print(f"TOOL_INFO: NIN pre-check for {nin}. No customer record to update yet.")
        if "INVALID" in nin:
            return cim_schemas.NINVerificationResponse(is_valid=False, message="NIN not found (mock pre-check).", nin_data=None)
        mock_nin_data = {"nin": nin, "firstname": "MockNINFirst", "surname": "MockNINSLast", "birthdate": "1990-01-01"}
        return cim_schemas.NINVerificationResponse(is_valid=True, message="NIN seems valid (mock pre-check).", nin_data=mock_nin_data)

    nin_req_schema = cim_schemas.NINVerificationRequest(nin=nin)
    try:
        response = cim_services.verify_nin(
            db=db,
            customer_id=customer_id_for_logging,
            nin_verification_request=nin_req_schema,
            verified_by_user_id=triggering_user_id
        )
        return response
    except cim_services.NotFoundException:
         return cim_schemas.NINVerificationResponse(is_valid=False, message=f"Customer ID {customer_id_for_logging} not found for NIN verification.", nin_data=None)
    except cim_services.ExternalServiceException as e:
        return cim_schemas.NINVerificationResponse(is_valid=False, message=f"NIN service error: {str(e)}", nin_data=None)
    except Exception as e:
        print(f"TOOL_ERROR: Unexpected error in verify_nin_tool: {e}")
        return cim_schemas.NINVerificationResponse(is_valid=False, message=f"Unexpected tool error: {str(e)}", nin_data=None)


def parse_document_with_ocr_tool(
    db: Session, # db might be needed if OCR service logs to AITaskLog
    document_url: str,
    document_type: str, # e.g., "ID_CARD", "PASSPORT", "UTILITY_BILL"
    ocr_model_name: Optional[str] = None, # From agent config
    triggering_user_id: str = "AI_ONBOARDING_AGENT"
) -> Dict[str, Any]:
    """
    Tool to parse a document using a conceptual OCR service.
    This would call an AIModelMetadata of type OCR_DOCUMENT_PARSING.
    For now, it returns mock data.
    """
    print(f"TOOL: Parsing document '{document_type}' from URL: {document_url} using OCR model: {ocr_model_name or 'default_ocr'}")

    # Conceptual: Call to ai_automation_layer.services.DocumentParsingAIService.parse_document(url, type)
    # That service would create an AITaskLog, invoke the model (internal/external), and return results.

    # Mock OCR results based on document type
    mock_parsed_data = {"document_type_provided": document_type, "ocr_confidence": 0.90}
    if document_type.upper() in ["ID_CARD", "PASSPORT", "DRIVERS_LICENSE", "NIN_SLIP"]:
        mock_parsed_data.update({
            "first_name": "MockOCRFirstName",
            "last_name": "MockOCRLastName",
            "date_of_birth": "1992-03-15",
            "document_number": f"DOC{random.randint(10000,99999)}",
            "gender": "FEMALE",
            "expiry_date": "2028-10-20"
        })
    elif document_type.upper() == "UTILITY_BILL":
        mock_parsed_data.update({
            "address_full": "123 Mock OCR Street, Ikeja, Lagos",
            "name_on_bill": "MockOCRFirstName MockOCRLastName",
            "issue_date": "2024-01-05"
        })
    else:
        mock_parsed_data["error"] = "Unsupported document type for mock OCR"
        mock_parsed_data["ocr_confidence"] = 0.30

    # Simulate logging this OCR task via AITaskLogService (conceptual)
    # from weezy_cbs.ai_automation_layer.services import ai_task_log_service
    # task_log_create = ai_schemas.AITaskLogCreate(
    #     model_metadata_id= ... # find OCR model ID from ocr_model_name
    #     task_name="OCR_DOCUMENT_PARSE",
    #     related_entity_type="OnboardingDocument", related_entity_id=document_url, # Or a temp ID
    #     input_data_summary_json={"document_url": document_url, "document_type": document_type},
    # )
    # log_entry = ai_task_log_service.create_task_log(db, task_log_create)
    # ai_task_log_service.update_task_log_finish(db, log_entry.id, status=ai_models.AITaskStatusEnum.SUCCESS, output_summary=mock_parsed_data)

    return mock_parsed_data


def create_customer_tool(
    db: Session,
    customer_data: cim_schemas.CustomerCreate,
    triggering_user_id: str = "AI_ONBOARDING_AGENT"
) -> cim_schemas.CustomerResponse:
    """Tool to create a new customer profile using Customer Identity Management service."""
    print(f"TOOL: Creating customer profile for phone: {customer_data.phone_number}")
    try:
        customer = cim_services.create_customer(db=db, customer_in=customer_data, created_by_user_id=triggering_user_id)
        return customer # Already a Pydantic model from service if using from_orm
    except cim_services.DuplicateEntryException as e:
        # Agent needs to handle this, maybe by fetching existing customer
        raise # Re-raise for agent to catch and decide
    except cim_services.InvalidInputException as e:
        raise
    except Exception as e:
        print(f"TOOL_ERROR: Unexpected error in create_customer_tool: {e}")
        # Convert to a known exception type or let agent handle generic error
        raise Exception(f"Failed to create customer due to tool error: {str(e)}")


def store_document_reference_tool(
    db: Session,
    doc_data: cim_schemas.CustomerDocumentCreate,
    triggering_user_id: str = "AI_ONBOARDING_AGENT"
) -> cim_schemas.CustomerDocumentResponse:
    """Tool to store document metadata and URL using Customer Identity Management service."""
    print(f"TOOL: Storing document reference for customer ID {doc_data.customer_id}, type: {doc_data.document_type}")
    try:
        document = cim_services.add_customer_document(db=db, document_in=doc_data, uploaded_by_user_id=triggering_user_id)
        return document
    except cim_services.NotFoundException as e: # If customer_id for the document is not found
        raise
    except Exception as e:
        print(f"TOOL_ERROR: Unexpected error in store_document_reference_tool: {e}")
        raise Exception(f"Failed to store document reference due to tool error: {str(e)}")

# Example of how a tool might use another AI service (conceptual)
# def verify_face_match_tool(db: Session, image1_url: str, image2_url: str) -> Dict[str, Any]:
#     """Calls a FaceMatch AI service."""
#     # from weezy_cbs.ai_automation_layer.services import face_match_ai_service
#     # request = ai_schemas.FaceMatchRequest(image_url1=image1_url, image_url2=image2_url)
#     # response = face_match_ai_service.compare_faces(db, request) # This service would log its own AITask
#     # return response.dict()
#     mock_response = {"is_match": random.choice([True, False]), "confidence": random.uniform(0.7, 0.99)}
#     print(f"TOOL: Face match between {image1_url} and {image2_url} -> {mock_response}")
#     return mock_response
