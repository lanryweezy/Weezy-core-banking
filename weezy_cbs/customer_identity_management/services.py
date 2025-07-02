# Service layer for Customer & Identity Management
from sqlalchemy.orm import Session
from . import models, schemas
from .models import AccountTier # Ensure direct access for enum comparison if needed
# from weezy_cbs.shared import exceptions # Assuming a shared exceptions module
# from weezy_cbs.integrations import nibss, nimc # Assuming integration modules

# Placeholder for shared exceptions
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


# --- Customer Services ---
def create_customer(db: Session, customer_in: schemas.CustomerCreate) -> models.Customer:
    """
    Creates a new customer.
    """
    # Check for existing customer by phone or email (if provided)
    if customer_in.email and db.query(models.Customer).filter(models.Customer.email == customer_in.email).first():
        raise DuplicateEntryException(f"Customer with email {customer_in.email} already exists.")
    if db.query(models.Customer).filter(models.Customer.phone_number == customer_in.phone_number).first():
        raise DuplicateEntryException(f"Customer with phone number {customer_in.phone_number} already exists.")

    db_customer = models.Customer(**customer_in.dict(exclude_unset=True)) # Use exclude_unset for partial models if applicable

    # Set default tier based on CBN guidelines (simplified)
    # Tier 1: Basic info, no strict ID verification needed at creation for some limits
    # Tier 2 & 3 would require more upfront or post-creation verification
    db_customer.account_tier = customer_in.account_tier or AccountTier.TIER1

    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    # TODO: Add KYC Audit Log entry for customer creation
    return db_customer

def get_customer(db: Session, customer_id: int) -> Optional[models.Customer]:
    """
    Retrieves a customer by their ID.
    """
    return db.query(models.Customer).filter(models.Customer.id == customer_id).first()

def get_customer_by_bvn(db: Session, bvn: str) -> Optional[models.Customer]:
    """
    Retrieves a customer by their BVN.
    """
    return db.query(models.Customer).filter(models.Customer.bvn == bvn).first()

def get_customer_by_nin(db: Session, nin: str) -> Optional[models.Customer]:
    """
    Retrieves a customer by their NIN.
    """
    return db.query(models.Customer).filter(models.Customer.nin == nin).first()

def get_customer_by_phone(db: Session, phone_number: str) -> Optional[models.Customer]:
    """
    Retrieves a customer by their phone number.
    """
    return db.query(models.Customer).filter(models.Customer.phone_number == phone_number).first()


def get_customers(db: Session, skip: int = 0, limit: int = 100) -> List[models.Customer]:
    """
    Retrieves a list of customers with pagination.
    """
    return db.query(models.Customer).offset(skip).limit(limit).all()

def update_customer(db: Session, customer_id: int, customer_in: schemas.CustomerUpdate) -> Optional[models.Customer]:
    """
    Updates an existing customer's details.
    """
    db_customer = get_customer(db, customer_id)
    if not db_customer:
        return None # Or raise NotFoundException

    update_data = customer_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_customer, key, value)

    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    # TODO: Add KYC Audit Log entry for customer update
    return db_customer

def delete_customer(db: Session, customer_id: int) -> bool:
    """
    Deletes a customer (logically or physically, depending on policy).
    For now, logical delete by setting is_active to False.
    """
    db_customer = get_customer(db, customer_id)
    if not db_customer:
        return False # Or raise NotFoundException

    db_customer.is_active = False
    # Potentially anonymize or clear sensitive data based on regulations
    db.add(db_customer)
    db.commit()
    # TODO: Add KYC Audit Log entry for customer deactivation
    return True

# --- KYC/AML Services ---
def verify_bvn_with_nibss(db: Session, customer_id: int, bvn_details: schemas.BVNVerificationRequest) -> schemas.BVNVerificationResponse:
    """
    Verifies BVN with NIBSS (mocked). Updates customer profile on success.
    """
    customer = get_customer(db, customer_id)
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found.")

    # Mock NIBSS call
    # In real scenario: result = nibss.verify_bvn(bvn_details.bvn, ...)
    mock_nibss_response = {"valid": True, "data": {"first_name": "MockFirstName", "last_name": "MockLastName", "phone_number": customer.phone_number, "date_of_birth": "1990-01-01"}}

    if mock_nibss_response["valid"]:
        # TODO: Add more sophisticated matching logic (e.g., name similarity, DOB match)
        customer.bvn = bvn_details.bvn
        customer.is_verified_bvn = True
        # Potentially update customer's name/DOB if NIBSS data is deemed more authoritative and matches closely
        db.commit()
        db.refresh(customer)
        # TODO: Add KYC Audit Log
        return schemas.BVNVerificationResponse(is_valid=True, message="BVN verified successfully.", bvn_data=mock_nibss_response["data"])
    else:
        # TODO: Add KYC Audit Log for failed attempt
        return schemas.BVNVerificationResponse(is_valid=False, message="BVN verification failed with NIBSS.", bvn_data=None)

def verify_nin_with_nimc(db: Session, customer_id: int, nin_details: schemas.NINVerificationRequest) -> schemas.NINVerificationResponse:
    """
    Verifies NIN with NIMC (mocked). Updates customer profile on success.
    """
    customer = get_customer(db, customer_id)
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found.")

    # Mock NIMC call
    # In real scenario: result = nimc.verify_nin(nin_details.nin, ...)
    mock_nimc_response = {"valid": True, "data": {"first_name": "MockFirstName", "last_name": "MockLastName", "photo_id": "base64string..."}}

    if mock_nimc_response["valid"]:
        customer.nin = nin_details.nin
        customer.is_verified_nin = True
        db.commit()
        db.refresh(customer)
        # TODO: Add KYC Audit Log
        return schemas.NINVerificationResponse(is_valid=True, message="NIN verified successfully.", nin_data=mock_nimc_response["data"])
    else:
        # TODO: Add KYC Audit Log for failed attempt
        return schemas.NINVerificationResponse(is_valid=False, message="NIN verification failed with NIMC.", nin_data=None)

def update_kyc_status(db: Session, customer_id: int, kyc_update: schemas.KYCStatusUpdate) -> models.Customer:
    """
    Manually updates KYC statuses and potentially account tier.
    Primarily for admin use or after offline verification.
    """
    customer = get_customer(db, customer_id)
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found.")

    changed_fields = []
    if kyc_update.is_verified_bvn is not None and customer.is_verified_bvn != kyc_update.is_verified_bvn:
        customer.is_verified_bvn = kyc_update.is_verified_bvn
        changed_fields.append("is_verified_bvn")

    if kyc_update.is_verified_nin is not None and customer.is_verified_nin != kyc_update.is_verified_nin:
        customer.is_verified_nin = kyc_update.is_verified_nin
        changed_fields.append("is_verified_nin")

    if kyc_update.is_verified_identity_document is not None and customer.is_verified_identity_document != kyc_update.is_verified_identity_document:
        customer.is_verified_identity_document = kyc_update.is_verified_identity_document
        changed_fields.append("is_verified_identity_document")

    if kyc_update.is_verified_address is not None and customer.is_verified_address != kyc_update.is_verified_address:
        customer.is_verified_address = kyc_update.is_verified_address
        changed_fields.append("is_verified_address")

    if kyc_update.account_tier is not None:
        # Logic to ensure tier upgrade/downgrade is valid based on current KYC status
        # E.g., cannot upgrade to Tier 3 without full verification
        can_change_tier = True # Add actual logic here
        if can_change_tier and customer.account_tier != AccountTier(kyc_update.account_tier.value): # Compare model enum with schema enum value
            customer.account_tier = AccountTier(kyc_update.account_tier.value)
            changed_fields.append("account_tier")
        elif not can_change_tier:
            # Potentially raise an error or return a message
            pass

    if changed_fields:
        db.commit()
        db.refresh(customer)
        # TODO: Add KYC Audit Log for each changed field or a summary
        # log_kyc_event(db, customer_id, event_type="MANUAL_KYC_UPDATE", details=f"Fields changed: {', '.join(changed_fields)}. Notes: {kyc_update.notes}")

    return customer

# --- Customer Document Services ---
def add_customer_document(db: Session, document_in: schemas.CustomerDocumentCreate) -> models.CustomerDocument:
    """
    Adds a document reference for a customer.
    Actual file upload should be handled separately (e.g., to S3, then pass URL here).
    """
    customer = get_customer(db, document_in.customer_id)
    if not customer:
        raise NotFoundException(f"Customer with ID {document_in.customer_id} not found for document upload.")

    db_document = models.CustomerDocument(**document_in.dict())
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    # TODO: Add KYC Audit Log
    # log_kyc_event(db, document_in.customer_id, event_type="DOCUMENT_UPLOADED", details=f"Type: {document_in.document_type}")
    return db_document

def get_customer_documents(db: Session, customer_id: int) -> List[models.CustomerDocument]:
    """
    Retrieves all documents for a given customer.
    """
    customer = get_customer(db, customer_id)
    if not customer:
        raise NotFoundException(f"Customer with ID {customer_id} not found.")
    # This assumes the relationship 'documents' is set up on the Customer model
    # return customer.documents
    # If not, query directly:
    return db.query(models.CustomerDocument).filter(models.CustomerDocument.customer_id == customer_id).all()

def verify_customer_document(db: Session, document_id: int, is_verified: bool) -> Optional[models.CustomerDocument]:
    """
    Marks a customer document as verified or unverified.
    """
    db_document = db.query(models.CustomerDocument).filter(models.CustomerDocument.id == document_id).first()
    if not db_document:
        return None # Or raise NotFoundException

    db_document.is_verified = is_verified
    db_document.verified_at = datetime.utcnow() if is_verified else None
    db.commit()
    db.refresh(db_document)
    # TODO: Add KYC Audit Log
    # event_detail = "VERIFIED" if is_verified else "UNVERIFIED"
    # log_kyc_event(db, db_document.customer_id, event_type=f"DOCUMENT_{event_detail}", details=f"Doc ID: {document_id}, Type: {db_document.document_type}")

    # Potentially trigger update_kyc_status if this verification completes a requirement for a tier upgrade
    # Example: if db_document.document_type == 'UTILITY_BILL' and is_verified:
    #    update_kyc_status(db, db_document.customer_id, schemas.KYCStatusUpdate(is_verified_address=True))
    return db_document

# --- Customer 360 Profile ---
def get_customer_360_profile(db: Session, customer_id: int) -> Optional[schemas.CustomerProfileResponse]:
    """
    Constructs a 360-degree profile of the customer.
    This would involve fetching data from multiple services/models.
    """
    customer = get_customer(db, customer_id)
    if not customer:
        return None

    documents = get_customer_documents(db, customer_id)
    # accounts_data = accounts_ledger_service.get_accounts_for_customer(db, customer_id) # Example call

    # Convert SQLAlchemy models to Pydantic schemas for response
    customer_response_data = schemas.CustomerResponse.from_orm(customer)
    documents_response_data = [schemas.CustomerDocumentResponse.from_orm(doc) for doc in documents]

    profile_data = customer_response_data.dict()
    profile_data["documents"] = documents_response_data
    # profile_data["accounts"] = [schemas.AccountResponse.from_orm(acc).dict() for acc in accounts_data]

    return schemas.CustomerProfileResponse(**profile_data)


# --- KYC Audit Log Service (Helper) ---
def log_kyc_event(db: Session, customer_id: int, event_type: str, details: Optional[str] = None, changed_by_user_id: Optional[int] = None):
    """
    Logs a KYC related event for audit purposes.
    """
    log_entry = models.KYCAuditLog(
        customer_id=customer_id,
        event_type=event_type,
        details=details,
        changed_by_user_id=changed_by_user_id
    )
    db.add(log_entry)
    db.commit()
    # No refresh needed unless you need the ID of the log entry immediately
    return log_entry
