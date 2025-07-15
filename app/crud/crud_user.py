from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json # For handling JSON string in kyc_doc_references

from app.models.user import User
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.utils.security import get_password_hash

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def create_db_user(db: Session, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)

    # Handle kyc_doc_references (Pydantic schema has Dict, model has String)
    kyc_docs_str = None
    if user.kyc_doc_references:
        try:
            kyc_docs_str = json.dumps(user.kyc_doc_references)
        except TypeError:
            # Handle or log error if kyc_doc_references is not JSON serializable
            pass # Or raise HTTPException

    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone_number=user.phone_number,
        date_of_birth=user.date_of_birth,
        address=user.address,
        bvn=user.bvn,
        nin=user.nin,
        kyc_doc_references=kyc_docs_str, # Store as JSON string
        account_tier=user.account_tier,
        is_sme_customer=user.is_sme_customer,
        # status will default to PENDING as per model
        # kyc_status will default to NOT_INITIATED as per model
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_db_user(db: Session, db_user: User, user_in: UserUpdate) -> User:
    user_data = user_in.model_dump(exclude_unset=True) # Use model_dump for Pydantic v2+

    if "password" in user_data and user_data["password"]: # Should be handled by a separate endpoint ideally
        hashed_password = get_password_hash(user_data["password"])
        db_user.hashed_password = hashed_password
        del user_data["password"] # Don't try to set it directly unless User model has a setter

    if "kyc_doc_references" in user_data and user_data["kyc_doc_references"]:
        try:
            db_user.kyc_doc_references = json.dumps(user_data["kyc_doc_references"])
        except TypeError:
            pass # or handle error
        del user_data["kyc_doc_references"]


    for field, value in user_data.items():
        setattr(db_user, field, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Placeholder for get_users (with pagination, filtering)
# def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
#     return db.query(User).offset(skip).limit(limit).all()
