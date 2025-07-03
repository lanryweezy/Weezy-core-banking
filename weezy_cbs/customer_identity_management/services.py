# Service layer for Customer & Identity Management
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime
import json # For handling JSON in audit logs

from . import models, schemas
# Enums imported directly from models for use in service logic
from .models import CBNSupportedAccountTier, CustomerTypeEnum, GenderEnum

# from weezy_cbs.shared import exceptions # Assuming a shared exceptions module
# from weezy_cbs.integrations import nibss_client, nimc_client # Conceptual integration clients

# Placeholder for shared exceptions (should be in a shared module)
class NotFoundException(Exception):
    def __init__(self, message="Resource not found"):
        self.message = message
        super().__init__(self.message)

class DuplicateEntryException(Exception):
    def __init__(self, message="Duplicate entry"):
        self.message = message
        super().__init__(self.message)

class ExternalServiceException(Exception):
    def __init__(self, message="External service error"):
        self.message = message
        super().__init__(self.message)

class InvalidInputException(Exception):
    def __init__(self, message="Invalid input provided"):
        self.message = message
        super().__init__(self.message)


def _log_kyc_event_detailed(
    db: Session, customer_id: int, event_type: str,
    details_before: Optional[Dict[str, Any]] = None,
    details_after: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
    changed_by_user_id: Optional[str] = "SYSTEM"
):
    """Enhanced KYC event logger."""
    log_entry = models.KYCAuditLog(
        customer_id=customer_id,
        event_type=event_type,
        details_before_json=json.dumps(details_before, default=str) if details_before else None,
        details_after_json=json.dumps(details_after, default=str) if details_after else None,
        notes=notes,
        changed_by_user_id=changed_by_user_id
    )
    db.add(log_entry)
    # Commit should be handled by the calling function's transaction


# --- Customer Services ---
def create_customer(db: Session, customer_in: schemas.CustomerCreate, created_by_user_id: Optional[str] = "SYSTEM") -> models.Customer:
    """
    Creates a new customer, determines initial account tier.
    """
    # Validate required fields based on customer_type
    if customer_in.customer_type == schemas.CustomerTypeSchema.INDIVIDUAL:
        if not all([customer_in.first_name, customer_in.last_name, customer_in.phone_number]): # DOB also important for Tiers
            raise InvalidInputException("First name, last name, and phone number are required for individual customers.")
    elif customer_in.customer_type in [schemas.CustomerTypeSchema.SME, schemas.CustomerTypeSchema.CORPORATE]:
        if not all([customer_in.company_name, customer_in.phone_number, customer_in.rc_number, customer_in.date_of_incorporation]): # TIN also important
            raise InvalidInputException("Company name, phone, RC number, and incorporation date are required for business customers.")

    # Check for existing customer by phone (primary unique identifier for initial check)
    if db.query(models.Customer).filter(models.Customer.phone_number == customer_in.phone_number).first():
        raise DuplicateEntryException(f"Customer with phone number {customer_in.phone_number} already exists.")
    if customer_in.email and db.query(models.Customer).filter(models.Customer.email == customer_in.email).first():
        raise DuplicateEntryException(f"Customer with email {customer_in.email} already exists.")
    if customer_in.bvn and db.query(models.Customer).filter(models.Customer.bvn == customer_in.bvn).first():
        raise DuplicateEntryException(f"Customer with BVN {customer_in.bvn} already exists.")
    if customer_in.nin and db.query(models.Customer).filter(models.Customer.nin == customer_in.nin).first():
        raise DuplicateEntryException(f"Customer with NIN {customer_in.nin} already exists.")

    # Determine initial account tier based on data provided (simplified logic)
    # A full implementation would check specific documents and verification statuses.
    determined_tier = CBNSupportedAccountTier.TIER_1 # Default
    if customer_in.bvn or customer_in.nin: # Presence of BVN/NIN might allow Tier 2 start, pending verification
        determined_tier = CBNSupportedAccountTier.TIER_2
    # Tier 3 typically requires verified ID and address proof.

    db_customer = models.Customer(
        **customer_in.dict(exclude_unset=True, exclude={'account_tier'}), # Don't use tier from input directly yet
        account_tier=determined_tier # Use determined tier
    )

    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)

    _log_kyc_event_detailed(db, customer_id=db_customer.id, event_type="CUSTOMER_CREATED", details_after=customer_in.dict(), changed_by_user_id=created_by_user_id, notes=f"Initial tier set to {determined_tier.value}")
    db.commit() # Commit log

    return db_customer

def get_customer(db: Session, customer_id: int) -> Optional[models.Customer]:
    return db.query(models.Customer).filter(models.Customer.id == customer_id).first()

def get_customer_by_bvn(db: Session, bvn: str) -> Optional[models.Customer]:
    return db.query(models.Customer).filter(models.Customer.bvn == bvn).first()

def get_customer_by_nin(db: Session, nin: str) -> Optional[models.Customer]:
    return db.query(models.Customer).filter(models.Customer.nin == nin).first()

def get_customer_by_phone(db: Session, phone_number: str) -> Optional[models.Customer]:
    return db.query(models.Customer).filter(models.Customer.phone_number == phone_number).first()

def get_customers(db: Session, skip: int = 0, limit: int = 100) -> List[models.Customer]:
    return db.query(models.Customer).offset(skip).limit(limit).all()

def update_customer_details(db: Session, customer_id: int, customer_in: schemas.CustomerUpdate, updated_by_user_id: str) -> Optional[models.Customer]:
    db_customer = get_customer(db, customer_id)
    if not db_customer:
        raise NotFoundException("Customer not found.")

    # details_before = {k: getattr(db_customer, k, None) for k in customer_in.dict(exclude_unset=True).keys()}
    # For simplicity, capture all relevant fields before update
    details_before = schemas.CustomerResponse.from_orm(db_customer).dict()


    update_data = customer_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_customer, key, value)

    db_customer.updated_at = datetime.utcnow() # Ensure timestamp is updated
    db.add(db_customer) # Not strictly necessary if instance is already in session and modified

    _log_kyc_event_detailed(db, customer_id=db_customer.id, event_type="CUSTOMER_DETAILS_UPDATED", details_before=details_before, details_after=schemas.CustomerResponse.from_orm(db_customer).dict(), changed_by_user_id=updated_by_user_id)
    db.commit()
    db.refresh(db_customer)
    return db_customer

# --- KYC/AML Services ---
def _simulate_external_verification(identifier_value: str, service_name: str, customer_phone: Optional[str]=None) -> Dict[str, Any]:
    """Simulates a call to NIBSS (BVN) or NIMC (NIN)."""
    # print(f"Simulating {service_name} verification for: {identifier_value}")
    if "INVALID" in identifier_value.upper():
        return {"is_valid": False, "message": f"{service_name} not found or invalid.", "data": None}

    # Simulate data returned by NIBSS/NIMC
    first_name = "VerifiedFirstName"
    last_name = "VerifiedLastName"
    dob_str = "1988-08-08"

    if service_name == "NIBSS_BVN":
        # NIBSS might return slightly different names, phone, DOB than provided initially
        return {
            "is_valid": True,
            "message": "BVN details successfully retrieved.",
            "data": {
                "bvn": identifier_value,
                "firstName": first_name, "lastName": last_name, "middleName": "V.",
                "dateOfBirth": dob_str, "phoneNumber": customer_phone or "080VERIFIED123",
                "nationality": "NG", "gender": "Male",
                # "photoIdBase64": "base64_encoded_image_data_bvn..."
            }
        }
    elif service_name == "NIMC_NIN":
        return {
            "is_valid": True,
            "message": "NIN details successfully retrieved.",
            "data": {
                "nin": identifier_value,
                "firstname": first_name, "surname": last_name, "middlename": "N.",
                "birthdate": dob_str, "gender": "M",
                "telephoneno": customer_phone or "090VERIFIED456",
                # "photo": "base64_encoded_image_data_nin..."
            }
        }
    return {"is_valid": False, "message": "Unknown verification service for simulation.", "data": None}


def verify_bvn(db: Session, customer_id: int, bvn_verification_request: schemas.BVNVerificationRequest, verified_by_user_id: str) -> schemas.BVNVerificationResponse:
    customer = get_customer(db, customer_id)
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found.")

    # In real scenario: result_dict = nibss_client.verify_bvn(bvn_verification_request.bvn, phone_number=bvn_verification_request.phone_number, ...)
    simulated_result = _simulate_external_verification(bvn_verification_request.bvn, "NIBSS_BVN", customer.phone_number)

    details_before = {"bvn": customer.bvn, "is_verified_bvn": customer.is_verified_bvn}
    event_notes = f"BVN verification attempt for {bvn_verification_request.bvn}."

    if simulated_result["is_valid"]:
        customer.bvn = bvn_verification_request.bvn # Store the verified BVN
        customer.is_verified_bvn = True
        # Optionally, update customer name/DOB if NIBSS data is considered authoritative and passes matching logic
        # For now, just log the retrieved data.
        event_notes += f" NIBSS Data: {simulated_result['data']}"
        _log_kyc_event_detailed(db, customer_id, "BVN_VERIFIED", details_before, {"bvn": customer.bvn, "is_verified_bvn": customer.is_verified_bvn, "nibss_data": simulated_result['data']}, event_notes, verified_by_user_id)
        db.commit()
        db.refresh(customer)
        return schemas.BVNVerificationResponse(is_valid=True, message="BVN verified successfully and customer profile updated.", bvn_data=simulated_result["data"])
    else:
        _log_kyc_event_detailed(db, customer_id, "BVN_VERIFICATION_FAILED", details_before, details_before, f"{event_notes} Failure: {simulated_result['message']}", verified_by_user_id)
        db.commit() # Commit log even on failure
        return schemas.BVNVerificationResponse(is_valid=False, message=simulated_result["message"], bvn_data=None)

def verify_nin(db: Session, customer_id: int, nin_verification_request: schemas.NINVerificationRequest, verified_by_user_id: str) -> schemas.NINVerificationResponse:
    customer = get_customer(db, customer_id)
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found.")

    # In real scenario: result_dict = nimc_client.verify_nin(nin_verification_request.nin, ...)
    simulated_result = _simulate_external_verification(nin_verification_request.nin, "NIMC_NIN", customer.phone_number)

    details_before = {"nin": customer.nin, "is_verified_nin": customer.is_verified_nin}
    event_notes = f"NIN verification attempt for {nin_verification_request.nin}."

    if simulated_result["is_valid"]:
        customer.nin = nin_verification_request.nin
        customer.is_verified_nin = True
        event_notes += f" NIMC Data: {simulated_result['data']}"
        _log_kyc_event_detailed(db, customer_id, "NIN_VERIFIED", details_before, {"nin": customer.nin, "is_verified_nin": customer.is_verified_nin, "nimc_data": simulated_result['data']}, event_notes, verified_by_user_id)
        db.commit()
        db.refresh(customer)
        return schemas.NINVerificationResponse(is_valid=True, message="NIN verified successfully and customer profile updated.", nin_data=simulated_result["data"])
    else:
        _log_kyc_event_detailed(db, customer_id, "NIN_VERIFICATION_FAILED", details_before, details_before, f"{event_notes} Failure: {simulated_result['message']}", verified_by_user_id)
        db.commit()
        return schemas.NINVerificationResponse(is_valid=False, message=simulated_result["message"], nin_data=None)

def update_customer_kyc_status(db: Session, customer_id: int, kyc_update: schemas.KYCStatusUpdateRequest, updated_by_user_id: str) -> models.Customer:
    customer = get_customer(db, customer_id)
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found.")

    details_before = {
        "is_verified_bvn": customer.is_verified_bvn, "is_verified_nin": customer.is_verified_nin,
        "is_verified_identity_document": customer.is_verified_identity_document,
        "is_verified_address": customer.is_verified_address, "account_tier": customer.account_tier.value,
        "is_pep": customer.is_pep
    }
    changed_fields_log = {}

    if kyc_update.is_verified_bvn is not None and customer.is_verified_bvn != kyc_update.is_verified_bvn:
        customer.is_verified_bvn = kyc_update.is_verified_bvn
        changed_fields_log["is_verified_bvn"] = customer.is_verified_bvn
    # ... similar updates for other verification flags ...
    if kyc_update.is_verified_identity_document is not None: customer.is_verified_identity_document = kyc_update.is_verified_identity_document; changed_fields_log["is_verified_identity_document"] = customer.is_verified_identity_document
    if kyc_update.is_verified_address is not None: customer.is_verified_address = kyc_update.is_verified_address; changed_fields_log["is_verified_address"] = customer.is_verified_address
    if kyc_update.is_pep_status_override is not None: customer.is_pep = kyc_update.is_pep_status_override; changed_fields_log["is_pep"] = customer.is_pep

    if kyc_update.account_tier_override is not None:
        new_tier_model_enum = CBNSupportedAccountTier[kyc_update.account_tier_override.value] # Convert schema enum string to model enum
        if customer.account_tier != new_tier_model_enum:
            # Add logic here: can only upgrade tier if underlying KYC requirements are met.
            # E.g., to move to TIER_3, BVN, NIN, ID, Address must all be verified.
            can_change = True # Placeholder for actual validation logic
            if can_change:
                customer.account_tier = new_tier_model_enum
                changed_fields_log["account_tier"] = customer.account_tier.value
            else:
                raise InvalidInputException(f"Cannot change to tier {new_tier_model_enum.value} due to unmet KYC requirements.")

    if changed_fields_log:
        customer.updated_at = datetime.utcnow()
        _log_kyc_event_detailed(db, customer_id, "MANUAL_KYC_STATUS_UPDATE", details_before, schemas.CustomerResponse.from_orm(customer).dict(), kyc_update.notes, updated_by_user_id)
        db.commit()
        db.refresh(customer)
    return customer

# --- Customer Document Services ---
def add_customer_document(db: Session, document_in: schemas.CustomerDocumentCreate, uploaded_by_user_id: str) -> models.CustomerDocument:
    customer = get_customer(db, document_in.customer_id)
    if not customer:
        raise NotFoundException(f"Customer with ID {document_in.customer_id} not found for document upload.")

    db_document = models.CustomerDocument(**document_in.dict()) # Assumes customer_id is in dict
    db.add(db_document)

    _log_kyc_event_detailed(db, customer_id=document_in.customer_id, event_type="DOCUMENT_UPLOADED", details_after=document_in.dict(), notes=f"Type: {document_in.document_type}", changed_by_user_id=uploaded_by_user_id)
    db.commit()
    db.refresh(db_document)
    return db_document

def get_customer_documents(db: Session, customer_id: int) -> List[models.CustomerDocument]:
    # Eager load customer to avoid N+1 if accessing customer.name etc. (though not strictly needed here)
    # return db.query(models.CustomerDocument).options(joinedload(models.CustomerDocument.customer)).filter(models.CustomerDocument.customer_id == customer_id).all()
    return db.query(models.CustomerDocument).filter(models.CustomerDocument.customer_id == customer_id).all()


def verify_customer_document(db: Session, document_id: int, is_verified: bool, verification_meta: Optional[Dict[str,Any]], verified_by_user_id: str) -> models.CustomerDocument:
    db_document = db.query(models.CustomerDocument).filter(models.CustomerDocument.id == document_id).first()
    if not db_document:
        raise NotFoundException(f"Document with ID {document_id} not found.")

    details_before = {"is_verified": db_document.is_verified, "verified_at": db_document.verified_at, "verification_meta_json": db_document.verification_meta_json}

    db_document.is_verified = is_verified
    db_document.verified_at = datetime.utcnow() if is_verified else None
    db_document.verification_meta_json = json.dumps(verification_meta) if verification_meta else None

    details_after = {"is_verified": db_document.is_verified, "verified_at": db_document.verified_at, "verification_meta_json": db_document.verification_meta_json}
    log_notes = f"Document '{db_document.document_type}' (ID: {db_document.id}) marked as {'VERIFIED' if is_verified else 'UNVERIFIED'}."
    if verification_meta: log_notes += f" Meta: {verification_meta}"

    _log_kyc_event_detailed(db, customer_id=db_document.customer_id, event_type="DOCUMENT_VERIFICATION_STATUS_UPDATED", details_before=details_before, details_after=details_after, notes=log_notes, changed_by_user_id=verified_by_user_id)

    # Potentially trigger update of customer's overall KYC flags (is_verified_identity_document, is_verified_address)
    # and re-evaluate account_tier eligibility based on this document's verification.
    # Example: if db_document.document_type == 'UTILITY_BILL' and is_verified:
    #    update_customer_kyc_status(db, db_document.customer_id, schemas.KYCStatusUpdateRequest(is_verified_address=True, notes="Auto-updated from utility bill verification"), "SYSTEM")

    db.commit()
    db.refresh(db_document)
    return db_document

# --- Customer 360 Profile ---
def get_customer_360_profile(db: Session, customer_id: int) -> Optional[schemas.CustomerProfileResponse]:
    # Use joinedload to eager load related documents to avoid N+1 queries
    customer = db.query(models.Customer).options(joinedload(models.Customer.documents)).filter(models.Customer.id == customer_id).first()
    if not customer:
        return None

    # Fetch summary of linked accounts (conceptual - this would call AccountsLedgerMgmt service)
    # linked_accounts_summary_data = accounts_ledger_service.get_account_summaries_for_customer(db, customer_id)
    mock_linked_accounts_summary = [
        schemas.LinkedAccountSummarySchema(account_number="0123456789", account_type="SAVINGS", currency="NGN", status="ACTIVE"),
        schemas.LinkedAccountSummarySchema(account_number="0987654321", account_type="CURRENT", currency="NGN", status="ACTIVE")
    ] if customer_id % 2 == 0 else [] # Mock some accounts for some customers

    # Convert Customer and its documents to Pydantic schemas
    # Pydantic's from_orm will handle the conversion including nested relationships if schemas are set up correctly.
    customer_profile_response = schemas.CustomerProfileResponse.from_orm(customer)
    # Manually assign if not directly mapped or needs specific logic:
    customer_profile_response.linked_accounts_summary = mock_linked_accounts_summary

    # Example of calculating an overall KYC status (simplified)
    # overall_kyc_level = "INCOMPLETE"
    # if customer.is_verified_bvn and customer.is_verified_nin and customer.is_verified_identity_document and customer.is_verified_address:
    #     overall_kyc_level = "TIER_3_COMPLETE"
    # elif customer.is_verified_bvn or customer.is_verified_nin:
    #     overall_kyc_level = "TIER_2_ELIGIBLE" # Or TIER_1 if that's the base with just phone
    # customer_profile_response.overall_kyc_level_met = overall_kyc_level

    return customer_profile_response

async def get_staff_customer_360_view(db: Session, customer_id: int) -> Optional[schemas.StaffCustomer360Response]:
    """
    Aggregates comprehensive customer information for a staff-facing 360-degree view.
    This is a conceptual implementation and uses mock data for cross-module calls.
    """
    # 1. Fetch Core Customer Details
    # customer_orm = get_customer(db, customer_id) # Uses existing service
    # For mock, let's assume we get a customer object
    customer_orm = db.query(models.Customer).options(
        joinedload(models.Customer.documents),
        # joinedload(models.Customer.kyc_audit_logs).raiseload('*') # Example of controlling load depth
    ).filter(models.Customer.id == customer_id).first()

    if not customer_orm:
        raise NotFoundException(f"Customer with ID {customer_id} not found.")

    full_name = f"{customer_orm.first_name} {customer_orm.last_name}" if customer_orm.customer_type == models.CustomerTypeEnum.INDIVIDUAL else customer_orm.company_name

    # 2. KYC/AML Status & Documents
    overall_kyc_status = "Partially Verified" # Placeholder
    if customer_orm.is_verified_bvn and customer_orm.is_verified_nin and customer_orm.is_verified_identity_document and customer_orm.is_verified_address:
        overall_kyc_status = "Fully Verified"
    elif customer_orm.is_verified_bvn or customer_orm.is_verified_nin:
        overall_kyc_status = "Basic Verification Met"

    key_documents_summary: List[schemas.StaffViewKYCDocumentSummarySchema] = []
    for doc in customer_orm.documents[:3]: # Show max 3 key docs summary
        key_documents_summary.append(schemas.StaffViewKYCDocumentSummarySchema(
            document_type=doc.document_type,
            status="Verified" if doc.is_verified else "Pending" if doc.verified_at is None else "Rejected", # Simplified status
            expiry_date=doc.expiry_date,
            document_url=doc.document_url # In real app, consider if staff should see direct URL
        ))

    # last_kyc_review_date: Conceptual - query KYCAuditLog for latest relevant event
    last_kyc_review = db.query(models.KYCAuditLog.timestamp)\
        .filter(models.KYCAuditLog.customer_id == customer_id)\
        .order_by(models.KYCAuditLog.timestamp.desc())\
        .first()
    last_kyc_review_date_val = last_kyc_review[0].date() if last_kyc_review else None


    # 3. Financial Summary & Linked Accounts (MOCK DATA)
    # Conceptual: Call accounts_ledger_management.services.account_service
    # accounts_data, total_deposit_bal = alm_account_service.get_customer_account_financial_summary(db, customer_id)
    mock_accounts_summary: List[schemas.StaffViewAccountSummarySchema] = [
        schemas.StaffViewAccountSummarySchema(account_id=101, account_number_masked="******7890", account_type="SAVINGS", product_name="Regular Savings", currency="NGN", available_balance=120500.75, ledger_balance=120500.75, status="ACTIVE"),
        schemas.StaffViewAccountSummarySchema(account_id=102, account_number_masked="******1234", account_type="CURRENT", product_name="Business Current", currency="NGN", available_balance=550000.00, ledger_balance=550000.00, status="ACTIVE", lien_amount=50000.00),
        schemas.StaffViewAccountSummarySchema(account_id=103, account_number_masked="******5555", account_type="DOMICILIARY", product_name="USD Domiciliary", currency="USD", available_balance=1500.00, ledger_balance=1500.00, status="ACTIVE"),
    ]
    total_deposit_balance_ngn_equivalent_val = 120500.75 + 550000.00 + (1500.00 * 1400) # Mock conversion

    # 4. Recent Transaction Activity (MOCK DATA)
    # Conceptual: Call transaction_management.services.transaction_service
    # recent_txns_data = tm_transaction_service.get_recent_transactions_for_customer(db, customer_id, limit=5)
    mock_recent_transactions: List[schemas.StaffViewTransactionSummarySchema] = [
        schemas.StaffViewTransactionSummarySchema(transaction_id="TXN001", date=datetime.utcnow()-timedelta(days=1), description="DSTV Subscription", amount=-15000.00, currency="NGN", type_category="BILL_PAYMENT", channel="MOBILE_APP", status="SUCCESSFUL"),
        schemas.StaffViewTransactionSummarySchema(transaction_id="TXN002", date=datetime.utcnow()-timedelta(days=2), description="Salary - ACME Corp", amount=350000.00, currency="NGN", type_category="FUNDS_TRANSFER", channel="NIP", status="SUCCESSFUL"),
    ]

    # 5. Loan Portfolio Summary (MOCK DATA)
    # Conceptual: Call loan_management_module.services.loan_account_service
    # active_loans_data, total_loan_exposure = lms_loan_service.get_customer_loan_summary(db, customer_id)
    mock_active_loans: List[schemas.StaffViewLoanSummarySchema] = []
    total_loan_exposure_ngn_equivalent_val = 0.0
    if customer_id % 3 == 0: # Randomly give some customers a mock loan
        mock_active_loans.append(
            schemas.StaffViewLoanSummarySchema(loan_account_id=201, loan_account_number="LN000123", product_name="Personal Quick Loan", disbursed_amount=200000.00, total_outstanding=150000.00, currency="NGN", status="ACTIVE", next_repayment_date=(datetime.utcnow()+timedelta(days=20)).date(), next_repayment_amount=25000.00, days_past_due=0)
        )
        total_loan_exposure_ngn_equivalent_val = 150000.00

    # 6. CRM & Support Interaction History (MOCK DATA)
    # Conceptual: Call crm_customer_support.services.support_ticket_service and customer_note_service
    # recent_tickets_data = crm_ticket_service.get_tickets_for_customer(db, customer_id, limit=3, sort_by_updated=True)
    # important_notes_data = crm_note_service.get_important_notes_for_customer(db, customer_id, limit=3)
    mock_recent_tickets: List[schemas.StaffViewSupportTicketSummarySchema] = [
        schemas.StaffViewSupportTicketSummarySchema(ticket_id=301, ticket_number="HD-20240115-001", subject="Card Activation Issue", status="PENDING_AGENT", priority="HIGH", created_at=datetime.utcnow()-timedelta(days=3), assigned_agent_name="Support Agent A"),
    ]
    mock_important_notes: List[schemas.StaffViewCustomerNoteSummarySchema] = [
        schemas.StaffViewCustomerNoteSummarySchema(note_id=401, category="Feedback", note_snippet="Customer called to appreciate mobile app...", created_at=datetime.utcnow()-timedelta(days=10), agent_name="Agent B"),
    ]

    # 7. Digital Channel Engagement (MOCK DATA)
    # Conceptual: Call digital_channels_modules.services.digital_user_profile_service
    # digital_profile_data = dc_profile_service.get_profile_summary_by_customer_id(db, customer_id)
    mock_digital_profile: Optional[schemas.StaffViewDigitalProfileSummarySchema] = None
    if customer_orm.email: # Assume digital profile if email exists
        mock_digital_profile = schemas.StaffViewDigitalProfileSummarySchema(
            username=customer_orm.email, status="Active",
            last_login_at=customer_orm.updated_at - timedelta(hours=random.randint(1,72)), # Mock last login
            last_login_channel="MOBILE_APP",
            is_verified_email=True, is_verified_phone=customer_orm.is_verified_bvn # Assume phone verified if BVN verified
        )

    # Assemble response
    response = schemas.StaffCustomer360Response(
        customer_id=customer_orm.id,
        full_name=full_name,
        customer_type=customer_orm.customer_type.value,
        bvn=customer_orm.bvn,
        nin=customer_orm.nin,
        primary_phone=customer_orm.phone_number,
        primary_email=customer_orm.email,
        date_onboarded=customer_orm.created_at.date(),
        relationship_manager_name=None, # Placeholder
        overall_kyc_status=overall_kyc_status,
        account_tier=customer_orm.account_tier.value,
        is_pep=customer_orm.is_pep,
        sanction_status="Clear", # Placeholder
        last_kyc_review_date=last_kyc_review_date_val,
        key_documents=key_documents_summary,
        total_deposit_balance_ngn_equivalent=total_deposit_balance_ngn_equivalent_val,
        total_loan_exposure_ngn_equivalent=total_loan_exposure_ngn_equivalent_val,
        accounts=mock_accounts_summary,
        recent_transactions=mock_recent_transactions,
        active_loans=mock_active_loans,
        recent_support_tickets=mock_recent_tickets,
        important_customer_notes=mock_important_notes,
        digital_profile=mock_digital_profile,
        active_alerts_count=0, # Placeholder
        key_flags=[] # Placeholder
    )
    return response
