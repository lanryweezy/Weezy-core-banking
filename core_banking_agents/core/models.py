# SQLAlchemy models for core data structures
# These models define the database table schemas.

from sqlalchemy import Column, String, DateTime, Float, JSON, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # For PostgreSQL UUID type
import uuid # For generating UUIDs if not using PG's gen_random_uuid()
from datetime import datetime
import enum

from .database import Base # Import Base from database.py

class OnboardingStatusEnum(str, enum.Enum):
    INITIATED = "Initiated"
    PENDING_VERIFICATION = "PendingVerification"
    VERIFICATION_FAILED = "VerificationFailed"
    PENDING_ACCOUNT_CREATION = "PendingAccountCreation"
    COMPLETED = "Completed"
    REQUIRES_MANUAL_INTERVENTION = "RequiresManualIntervention"
    CANCELLED = "Cancelled"


class OnboardingAttempt(Base):
    __tablename__ = "onboarding_attempts"

    # Using String for id to be compatible with SQLite and allow manual UUIDs
    # For PostgreSQL, PG_UUID(as_uuid=True) is often preferred for the primary key.
    id = Column(String, primary_key=True, default=lambda: f"ONB-{uuid.uuid4().hex[:12].upper()}")

    # Alternatively, for PostgreSQL specific UUID:
    # id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email_address = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, index=True, nullable=True)
    bvn = Column(String, index=True, nullable=True)
    nin = Column(String, index=True, nullable=True)

    status = Column(SQLAlchemyEnum(OnboardingStatusEnum), default=OnboardingStatusEnum.INITIATED, nullable=False)
    message = Column(String, nullable=True)

    requested_tier = Column(String, nullable=True) # e.g., "Tier1", "Tier2"
    achieved_tier = Column(String, nullable=True)

    # Storing complex verification steps as JSON.
    # For more relational querying on steps, they could be a separate table.
    verification_steps_json = Column(JSON, nullable=True) # Stores List[VerificationStepResult] as JSON

    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # To store the original request or key parts of it if needed for audit or reprocessing
    # request_payload_json = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<OnboardingAttempt(id='{self.id}', name='{self.first_name} {self.last_name}', status='{self.status}')>"


# Example of another core model, e.g., for a User (could be customer or internal staff)
# class User(Base):
#     __tablename__ = "users"
#     id = Column(String, primary_key=True, default=lambda: f"USR-{uuid.uuid4().hex[:10].upper()}")
#     username = Column(String, unique=True, index=True, nullable=False)
#     email = Column(String, unique=True, index=True, nullable=False)
#     hashed_password = Column(String, nullable=False)
#     full_name = Column(String, nullable=True)
#     is_active = Column(Boolean, default=True)
#     is_staff = Column(Boolean, default=False) # For bank staff access control
#     created_at = Column(DateTime, default=datetime.utcnow)

#     # Relationship to onboarding attempts if a user is created from one
#     # onboarding_attempt_id = Column(String, ForeignKey("onboarding_attempts.id"), nullable=True)
#     # onboarding_attempt = relationship("OnboardingAttempt")


if __name__ == "__main__":
    print("Core SQLAlchemy models defined (e.g., OnboardingAttempt).")
    # This file is primarily for defining models.
    # Table creation logic is in database.py's init_db().
