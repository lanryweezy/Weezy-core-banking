# API Endpoints for Customer & Identity Management using FastAPI
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body # Added Body
from sqlalchemy.orm import Session
from typing import List, Optional

from . import services, schemas, models
# Assuming a get_db dependency is defined in weezy_cbs.database
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_user, get_current_active_admin_user # For auth

# For now, let's define a placeholder get_db.
# This should be properly set up with SQLAlchemy session management.
def get_db_placeholder():
    # This is a placeholder. In a real FastAPI app, this would yield a SQLAlchemy Session.
    # from weezy_cbs.database import SessionLocal # Assuming SessionLocal is defined in database.py
    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()
    # For mock purposes where services might not use db:
    yield None # Returning None will cause errors if services.py actually uses the db session.

get_db = get_db_placeholder # Assign placeholder

# Placeholder for current user (replace with actual auth dependency)
def get_current_user_placeholder():
    return {"id": "user_SYSTEM", "username": "system", "roles": ["admin"]} # Mock admin user

router = APIRouter(
    prefix="/customer-identity", # Consistent with original
    tags=["Customer & Identity Management"],
    responses={404: {"description": "Not found"}},
)

@router.post("/customers", response_model=schemas.CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_new_customer(
    customer_in: schemas.CustomerCreate,
    db: Session = Depends(get_db), # Replace get_db with actual dependency
    # current_user: dict = Depends(get_current_user_placeholder) # Example auth
):
    """
    Onboard a new customer (Individual, SME, or Corporate).
    - Validates input data based on customer type.
    - Creates customer record with an initial account tier.
    - Initiates basic KYC checks (e.g., Tier 1 defaults).
    """
    # user_id_performing_action = current_user.get("id") # For audit logging
    user_id_performing_action = "API_USER" # Placeholder
    try:
        if db is None and False: # Set to True to enforce DB for testing, services are mocked for now
             raise HTTPException(status_code=503, detail="Database (db) session not available for API.")
        customer = services.create_customer(db=db, customer_in=customer_in, created_by_user_id=user_id_performing_action)
        return customer
    except services.DuplicateEntryException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.InvalidInputException as e: # For validation errors from service layer
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e: # Catch other ValueErrors (e.g. Pydantic if not caught by FastAPI, or custom)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log the exception e (e.g., import logging; logging.exception("Customer creation error"))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/customers/{customer_id}", response_model=schemas.CustomerResponse)
def read_customer_by_id(customer_id: int, db: Session = Depends(get_db)):
    """Retrieve a customer's details by their unique internal ID."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database (db) session not available.")
    db_customer = services.get_customer(db, customer_id=customer_id)
    if db_customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return db_customer

@router.get("/customers", response_model=schemas.PaginatedCustomerResponse)
def read_all_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100), # Adjusted default limit
    phone_number: Optional[str] = Query(None, description="Search by phone number"),
    bvn: Optional[str] = Query(None, description="Search by BVN"),
    nin: Optional[str] = Query(None, description="Search by NIN"),
    email: Optional[str] = Query(None, description="Search by email"),
    db: Session = Depends(get_db)
):
    """Retrieve a list of customers with pagination and optional filters."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database (db) session not available.")
    # Refined filter logic
    items = []
    total = 0
    # In a real app, use a more dynamic query builder in services.py
    if phone_number:
        customer = services.get_customer_by_phone(db, phone_number)
        if customer: items = [customer]; total = 1
    elif bvn:
        customer = services.get_customer_by_bvn(db, bvn)
        if customer: items = [customer]; total = 1
    elif nin:
        customer = services.get_customer_by_nin(db, nin)
        if customer: items = [customer]; total = 1
    elif email: # Add email search if service supports it
        # customer = services.get_customer_by_email(db, email) # Assuming this service exists
        # if customer: items = [customer]; total = 1
        pass # Placeholder for email search
    else:
        items = services.get_customers(db, skip=skip, limit=limit)
        # total = db.query(models.Customer).count() # Get total count for pagination (requires real DB session)
        total = len(items) if items else 0 # Mock total for now if no DB

    return schemas.PaginatedCustomerResponse(
        items=[schemas.CustomerResponse.from_orm(item) for item in items if item], # Ensure items are converted and not None
        total=total,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(items)
    )

@router.put("/customers/{customer_id}", response_model=schemas.CustomerResponse)
def update_existing_customer_details(
    customer_id: int,
    customer_in: schemas.CustomerUpdate,
    db: Session = Depends(get_db),
    # current_user: dict = Depends(get_current_user_placeholder) # For audit
):
    """Update an existing customer's information."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database (db) session not available.")
    # user_id_performing_action = current_user.get("id")
    user_id_performing_action = "API_USER_UPDATE" # Placeholder
    try:
        updated_customer = services.update_customer_details(db, customer_id=customer_id, customer_in=customer_in, updated_by_user_id=user_id_performing_action)
        return updated_customer
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.DuplicateEntryException as e: # If trying to update email/phone to an existing one
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/customers/{customer_id}/verify-bvn", response_model=schemas.BVNVerificationResponse)
def trigger_customer_bvn_verification(
    customer_id: int,
    bvn_data: schemas.BVNVerificationRequest, # Contains BVN and optionally phone for NIBSS matching
    db: Session = Depends(get_db),
    # current_user: dict = Depends(get_current_user_placeholder) # For audit
):
    """
    Verify customer's BVN using NIBSS integration (mocked).
    Updates customer's KYC status and BVN field upon successful verification.
    """
    if db is None and False: raise HTTPException(status_code=503, detail="Database (db) session not available.")
    # user_id_performing_action = current_user.get("id")
    user_id_performing_action = "API_BVN_VERIFIER" # Placeholder
    try:
        response = services.verify_bvn(db, customer_id=customer_id, bvn_verification_request=bvn_data, verified_by_user_id=user_id_performing_action)
        # Service now directly returns the BVNVerificationResponse schema
        return response
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.ExternalServiceException as e: # If NIBSS call itself fails
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"BVN service error: {str(e)}")

@router.post("/customers/{customer_id}/verify-nin", response_model=schemas.NINVerificationResponse)
def trigger_customer_nin_verification(
    customer_id: int,
    nin_data: schemas.NINVerificationRequest,
    db: Session = Depends(get_db),
    # current_user: dict = Depends(get_current_user_placeholder)
):
    """
    Verify customer's NIN using NIMC integration (mocked).
    Updates customer's KYC status and NIN field upon successful verification.
    """
    if db is None and False: raise HTTPException(status_code=503, detail="Database (db) session not available.")
    # user_id_performing_action = current_user.get("id")
    user_id_performing_action = "API_NIN_VERIFIER" # Placeholder
    try:
        response = services.verify_nin(db, customer_id=customer_id, nin_verification_request=nin_data, verified_by_user_id=user_id_performing_action)
        return response
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.ExternalServiceException as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"NIN service error: {str(e)}")

@router.get("/customers/{customer_id}/profile", response_model=schemas.CustomerProfileResponse) # Changed from profile360
def get_customer_full_profile(customer_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a comprehensive profile of the customer, including documents and linked account summaries.
    """
    if db is None and False: raise HTTPException(status_code=503, detail="Database (db) session not available.")
    profile = services.get_customer_360_profile(db, customer_id=customer_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer profile not found")
    return profile

@router.post("/customers/{customer_id}/documents", response_model=schemas.CustomerDocumentResponse, status_code=status.HTTP_201_CREATED)
def add_customer_document_reference( # Renamed from upload_...
    customer_id: int,
    document_in: schemas.CustomerDocumentCreate, # customer_id is now in body, aligns with schema
    db: Session = Depends(get_db),
    # current_user: dict = Depends(get_current_user_placeholder)
):
    """
    Add a reference to a customer's document (e.g., ID card, utility bill).
    The document_in schema should contain `customer_id`.
    Actual file upload to storage (like S3) should happen client-side or via a dedicated upload service;
    this endpoint saves the metadata and URL.
    """
    if db is None and False: raise HTTPException(status_code=503, detail="Database (db) session not available.")
    if customer_id != document_in.customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path customer_id does not match customer_id in request body.")

    # user_id_performing_action = current_user.get("id")
    user_id_performing_action = "API_DOC_UPLOADER" # Placeholder
    try:
        document = services.add_customer_document(db, document_in=document_in, uploaded_by_user_id=user_id_performing_action)
        return document
    except services.NotFoundException as e: # If customer_id for the document is not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/customers/{customer_id}/documents", response_model=List[schemas.CustomerDocumentResponse])
def list_all_customer_documents(customer_id: int, db: Session = Depends(get_db)): # Renamed
    """List all document references for a specific customer."""
    if db is None and False: raise HTTPException(status_code=503, detail="Database (db) session not available.")
    # No try-except for NotFoundException here, as services.get_customer_documents might not raise it for an empty list.
    # If customer must exist for this endpoint, add a services.get_customer(db, customer_id) check first.
    documents = services.get_customer_documents(db, customer_id=customer_id)
    if not documents and not services.get_customer(db, customer_id): # Check if customer exists if no docs found
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer with ID {customer_id} not found.")
    return documents

@router.patch("/documents/{document_id}/verify", response_model=schemas.CustomerDocumentResponse)
def verify_or_reject_customer_document(
    document_id: int,
    is_verified: bool = Body(..., embed=True),
    verification_meta: Optional[Dict[str, Any]] = Body(None, embed=True),
    db: Session = Depends(get_db),
    # current_admin_or_compliance: dict = Depends(get_current_user_placeholder) # Admin/Compliance role
):
    """Mark a customer document as verified or unverified. (Admin/Compliance operation)"""
    if db is None and False: raise HTTPException(status_code=503, detail="Database (db) session not available.")
    # user_id_performing_action = current_admin_or_compliance.get("id")
    user_id_performing_action = "API_DOC_VERIFIER" # Placeholder
    try:
        return services.verify_customer_document(db, document_id, is_verified, verification_meta, verified_by_user_id=user_id_performing_action)
    except services.NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/customers/{customer_id}/kyc-status", response_model=schemas.CustomerResponse)
def update_customer_overall_kyc_status( # Renamed from update_customer_kyc_details
    customer_id: int,
    kyc_update: schemas.KYCStatusUpdateRequest, # Updated schema name
    db: Session = Depends(get_db),
    # current_admin_or_compliance: dict = Depends(get_current_user_placeholder) # Admin/Compliance role
):
    """
    Manually update KYC status flags (e.g., verification status, PEP status) or account tier for a customer.
    Requires a reason/note for the update. (Admin/Compliance operation)
    """
    if db is None and False: raise HTTPException(status_code=503, detail="Database (db) session not available.")
    # user_id_performing_action = current_admin_or_compliance.get("id")
    user_id_performing_action = "API_KYC_UPDATER" # Placeholder
    try:
        customer = services.update_customer_kyc_status(db, customer_id, kyc_update, updated_by_user_id=user_id_performing_action)
        return customer # Returns the updated customer object
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.InvalidInputException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e: # Catch other potential errors from service layer
        # Log e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error updating KYC status: {str(e)}")

# Removed deactivate_customer_account (DELETE /customers/{customer_id})
# Deactivation is a complex process, often tied to account closure rules (zero balance, no active loans etc.)
# It should be a specific service call, e.g., services.request_customer_deactivation() which then updates is_active.
# For now, is_active can be managed via the PUT /customers/{customer_id} if CustomerUpdate schema allows it,
# or via the PATCH /customers/{customer_id}/kyc-status if it's considered a KYC/status aspect.
# The current CustomerUpdate schema does not include is_active, which is good.
# A dedicated endpoint for activation/deactivation with proper checks would be better.

# Note: The placeholder `get_db` and auth dependencies need to be replaced with actual implementations.
# The `db is None and False:` check is a temporary measure to allow testing with mocked services
# without a live DB connection. Set to `db is None:` to enforce DB session.
# Import `func` if doing counts directly in API: from sqlalchemy import func
# Import `date` from datetime for date type hints
from datetime import date
