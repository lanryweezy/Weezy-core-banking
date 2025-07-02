# API Endpoints for Customer & Identity Management using FastAPI
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from . import services, schemas, models
# Assuming a get_db dependency is defined in weezy_cbs.database
# from weezy_cbs.database import get_db
# For now, let's define a placeholder get_db.
# This should be properly set up with SQLAlchemy session management.
def get_db_placeholder():
    # This is a placeholder. In a real FastAPI app, this would yield a SQLAlchemy Session.
    # from weezy_cbs.database import SessionLocal
    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()
    yield None # Returning None will cause errors if services.py actually uses the db session.

get_db = get_db_placeholder # Assign placeholder

router = APIRouter(
    prefix="/customer-identity",
    tags=["Customer & Identity Management"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_new_customer(
    customer_in: schemas.CustomerCreate,
    db: Session = Depends(get_db) # Replace get_db with actual dependency
):
    """
    Onboard a new customer (Retail or SME).
    - Validates input data.
    - Creates customer record.
    - Initiates basic KYC checks if applicable (e.g., Tier 1 defaults).
    """
    try:
        # This is where you would use a real db session
        # For testing without full DB setup, service calls will fail or use mocks
        if db is None:
             raise HTTPException(status_code=503, detail="Database not configured for API.")
        customer = services.create_customer(db=db, customer_in=customer_in)
        return customer
    except services.DuplicateEntryException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e: # For Pydantic validation errors if not caught by FastAPI
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during customer creation.")


@router.get("/{customer_id}", response_model=schemas.CustomerResponse)
def read_customer_by_id(customer_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a customer's details by their unique ID.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    db_customer = services.get_customer(db, customer_id=customer_id)
    if db_customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return db_customer

@router.get("/", response_model=schemas.PaginatedCustomerResponse)
def read_all_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    phone_number: Optional[str] = Query(None),
    bvn: Optional[str] = Query(None),
    nin: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of customers with pagination and optional filters.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # This is a simplified filter. A more robust solution might involve a filter builder.
    if phone_number:
        customer = services.get_customer_by_phone(db, phone_number)
        items = [customer] if customer else []
        total = 1 if customer else 0
    elif bvn:
        customer = services.get_customer_by_bvn(db, bvn)
        items = [customer] if customer else []
        total = 1 if customer else 0
    elif nin:
        customer = services.get_customer_by_nin(db, nin)
        items = [customer] if customer else []
        total = 1 if customer else 0
    else:
        items = services.get_customers(db, skip=skip, limit=limit)
        total = db.query(models.Customer).count() # Get total count for pagination

    return schemas.PaginatedCustomerResponse(
        items=[schemas.CustomerResponse.from_orm(item) for item in items], # Ensure items are converted
        total=total,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=len(items)
    )

@router.put("/{customer_id}", response_model=schemas.CustomerResponse)
def update_existing_customer(
    customer_id: int,
    customer_in: schemas.CustomerUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing customer's information.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    updated_customer = services.update_customer(db, customer_id=customer_id, customer_in=customer_in)
    if updated_customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return updated_customer

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_customer_account(customer_id: int, db: Session = Depends(get_db)):
    """
    Deactivate a customer's account (logical delete).
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    if not services.delete_customer(db, customer_id=customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return

@router.post("/{customer_id}/verify-bvn", response_model=schemas.BVNVerificationResponse)
def verify_customer_bvn(
    customer_id: int,
    bvn_data: schemas.BVNVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify customer's BVN using NIBSS integration (or mock).
    Updates customer's KYC status upon successful verification.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        response = services.verify_bvn_with_nibss(db, customer_id=customer_id, bvn_details=bvn_data)
        if not response.is_valid:
            # Even if NIBSS says invalid, it's not a 404 on our customer
            # It's a successful call that returned a negative verification
            return response
        return response
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.ExternalServiceException as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

@router.post("/{customer_id}/verify-nin", response_model=schemas.NINVerificationResponse)
def verify_customer_nin(
    customer_id: int,
    nin_data: schemas.NINVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify customer's NIN using NIMC integration (or mock).
    Updates customer's KYC status upon successful verification.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        response = services.verify_nin_with_nimc(db, customer_id=customer_id, nin_details=nin_data)
        return response
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.ExternalServiceException as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{customer_id}/profile360", response_model=schemas.CustomerProfileResponse)
def get_customer_360_view(customer_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a comprehensive 360° profile of the customer.
    Includes KYC status, account details (summary), transaction history (summary), etc.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    profile = services.get_customer_360_profile(db, customer_id=customer_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return profile

@router.post("/{customer_id}/documents", response_model=schemas.CustomerDocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_customer_document_reference(
    customer_id: int,
    document_in: schemas.CustomerDocumentBase, # Note: customer_id is path param, so not in body
    db: Session = Depends(get_db)
):
    """
    Upload a reference to a customer's document (e.g., ID card, utility bill).
    The actual file upload to storage (like S3) should happen client-side or via a dedicated upload service; this endpoint saves the metadata and URL.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    doc_create_schema = schemas.CustomerDocumentCreate(customer_id=customer_id, **document_in.dict())
    try:
        document = services.add_customer_document(db, document_in=doc_create_schema)
        return document
    except services.NotFoundException as e: # If customer_id for the document is not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{customer_id}/documents", response_model=List[schemas.CustomerDocumentResponse])
def list_customer_documents(customer_id: int, db: Session = Depends(get_db)):
    """
    List all documents uploaded for a customer.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        documents = services.get_customer_documents(db, customer_id=customer_id)
        return documents
    except services.NotFoundException as e: # If customer_id itself is not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/{customer_id}/kyc-status", response_model=schemas.CustomerResponse)
def update_customer_kyc_details(
    customer_id: int,
    kyc_update: schemas.KYCStatusUpdate,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_active_admin_user) # TODO: Add Authentication for admin actions
):
    """
    Manually update KYC status flags or account tier for a customer.
    Typically an admin-only operation.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        customer = services.update_kyc_status(db, customer_id, kyc_update)
        return customer
    except services.NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e: # Catch other potential errors from service layer
        # Log e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error updating KYC status: {str(e)}")

# TODO: Add endpoints for Multi-tiered accounts (Tier 1, 2, 3 per CBN) management if not covered by kyc-status
# TODO: Add specific AML check endpoints or integrate AML checks into relevant operations.
# TODO: Add endpoints for managing SME specific data if different from retail.
