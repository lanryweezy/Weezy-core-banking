# Renaming file to users_router.py to match import in app/api/v1/__init__.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Optional # Optional added

from app.db import get_db
from app.schemas.user_schemas import UserCreate, UserResponse, UserUpdate # UserUpdate was missing
from app.models.user import User as UserModel # UserModel alias to avoid confusion with User schema
from app.crud import crud_user # Import the whole module

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user. This is the initial step for customer onboarding.
    - BVN is typically required.
    - NIN can be optional depending on account tier requirements.
    - Password will be hashed.
    """
    db_user_by_email = crud_user.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    db_user_by_username = crud_user.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    if user.bvn: # Check for existing BVN if provided and expected to be unique
        # This check should ideally be more robust, perhaps a dedicated function in crud_user
        existing_bvn_user = db.query(UserModel).filter(UserModel.bvn == user.bvn).first()
        if existing_bvn_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"BVN {user.bvn} is already registered to another user.")

    if user.nin: # Check for existing NIN if provided and expected to be unique
        existing_nin_user = db.query(UserModel).filter(UserModel.nin == user.nin).first()
        if existing_nin_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"NIN {user.nin} is already registered to another user.")

    created_user = crud_user.create_db_user(db=db, user=user)
    return created_user


@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a user by their ID.
    """
    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    """
    Update an existing user's details.
    Fields like BVN might be restricted from update after initial setting.
    Password updates should ideally be through a dedicated endpoint.
    """
    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent BVN update if it's already set and different (common policy)
    if user_in.bvn and db_user.bvn and db_user.bvn != user_in.bvn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BVN cannot be changed once set.")

    # Check for email/username conflicts if they are being changed
    if user_in.email and user_in.email != db_user.email:
        existing_email_user = crud_user.get_user_by_email(db, email=user_in.email)
        if existing_email_user and existing_email_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New email already registered by another user.")

    # Username updates are often disallowed or restricted. For now, we allow if not taken.
    # if user_in.username and user_in.username != db_user.username:
    #     existing_username_user = crud_user.get_user_by_username(db, username=user_in.username)
    #     if existing_username_user and existing_username_user.id != user_id:
    #         raise HTTPException(status_code=400, detail="New username already taken.")

    updated_user = crud_user.update_db_user(db=db, db_user=db_user, user_in=user_in)
    return updated_user


@router.post("/{user_id}/kyc-documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_kyc_documents(user_id: int, db: Session = Depends(get_db) ): # Add file uploads later: files: List[UploadFile] = File(...)
    """
    Placeholder: Upload KYC documents for a user.
    In a real system, this would handle file uploads (e.g., to S3 or a local store)
    and update `kyc_doc_references` and `kyc_status` on the User model.
    The "Customer Onboarding Agent" would interact heavily here, potentially using OpenRouter for OCR.
    """
    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Simulate updating kyc_status after document submission
    # db_user.kyc_status = "PENDING_VERIFICATION"
    # crud_user.update_db_user(db, db_user, UserUpdate(kyc_status="PENDING_VERIFICATION"))
    # This direct update won't work well with crud_user.update_db_user as it expects UserUpdate.
    # A dedicated service function would be better. For now, just a message.

    # Placeholder for OpenRouter OCR interaction:
    # for file in files:
    #   content = await file.read()
    #   text_from_doc = open_router_ocr_service(content) # Fictional service
    #   # ... store text, update kyc_doc_references ...

    return {"message": f"KYC document submission process initiated for user {user_id}. Actual file handling and OCR via OpenRouter to be implemented."}

@router.put("/{user_id}/verify-bvn-nin", status_code=status.HTTP_200_OK)
async def verify_bvn_nin_for_user(user_id: int, db: Session = Depends(get_db)):
    """
    Placeholder: Simulate BVN/NIN verification for a user.
    Actual integration with NIBSS/CoreID (via an intermediary or direct if allowed) is a major task.
    The "Customer Onboarding Agent" would use OpenRouter or direct APIs for this.
    """
    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not db_user.bvn: #and not db_user.nin: # Or specific check for what needs verification
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User BVN/NIN not provided for verification.")

    # Simulate verification success and update kyc_status
    # This is a simplified update. A proper service layer would handle this state transition.
    # db_user.kyc_status = "VERIFIED" # Or a more granular status
    # db.commit()
    # db.refresh(db_user)

    # Placeholder for actual verification logic (e.g. calling NIBSS via OpenRouter or other means)
    # verification_result = open_router_bvn_nin_verify_service(bvn=db_user.bvn, nin=db_user.nin)
    # if verification_result.is_successful:
    #    db_user.kyc_status = "VERIFIED" ...

    return {"message": f"BVN/NIN verification process simulated for user {user_id}. KYC status would be updated upon successful external verification."}


@router.get("/{user_id}/profile360", response_model=UserResponse) # Should be a more comprehensive response model
def get_user_profile_360(user_id: int, db: Session = Depends(get_db)):
    """
    Placeholder: Retrieve a basic 360-degree profile for the customer.
    This would combine user data, linked account summaries, loan summaries, etc.
    """
    db_user = crud_user.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # For a true 360 profile, you'd query related models (accounts, loans) and aggregate data.
    # This is just returning the basic UserResponse for now.
    # Example:
    # accounts = db.query(AccountModel).filter(AccountModel.user_id == user_id).all()
    # loans = db.query(LoanModel).filter(LoanModel.user_id == user_id).all()
    # return UserProfile360Response(user_info=db_user, accounts_summary=[...], loans_summary=[...])

    return db_user # Returning basic user info for now

# Basic Authentication endpoints (OAuth2 Password Flow) - will be expanded
# These should ideally be in a separate auth_router.py
from fastapi.security import OAuth2PasswordRequestForm
from app.utils.security import verify_password #, create_access_token (add when JWT is fully set up)
from app.schemas.user_schemas import Token

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 compatible token login, get an access token for future requests.
    (Simplified: does not yet return a real JWT, just simulates structure)
    """
    user = crud_user.get_user_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # access_token = create_access_token(
    #     data={"sub": user.username}, expires_delta=access_token_expires
    # )
    # For now, returning a dummy token
    access_token = f"dummy_jwt_for_{user.username}"
    return {"access_token": access_token, "token_type": "bearer"}

# TODO: Implement proper JWT token creation and dependency for secured endpoints.
# from app.api.dependencies import get_current_active_user
# @router.get("/me", response_model=UserResponse)
# async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
#    return current_user
