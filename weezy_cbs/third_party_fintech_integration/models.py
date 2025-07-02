# Database models for Third-Party & Fintech Integration Module
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLAlchemyEnum, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

# from weezy_cbs.database import Base
Base = declarative_base() # Local Base for now

import enum

class ThirdPartyServiceEnum(enum.Enum):
    CREDIT_BUREAU_CRC = "CREDIT_BUREAU_CRC"
    CREDIT_BUREAU_FIRSTCENTRAL = "CREDIT_BUREAU_FIRSTCENTRAL"
    NIMC_NIN_VERIFICATION = "NIMC_NIN_VERIFICATION" # If separate from NIBSS BVN/NIN
    BILL_AGGREGATOR_X = "BILL_AGGREGATOR_X" # e.g. specific bill payment aggregator
    EXTERNAL_LOAN_ORIGINATOR_Y = "EXTERNAL_LOAN_ORIGINATOR_Y"
    BAAS_PARTNER_Z = "BAAS_PARTNER_Z" # For Banking-as-a-Service client integrations
    # Add more specific third-party services

# Reusing APILog related enums from payments_integration_layer conceptually
# If they are in a shared module, import from there. For now, redefining for clarity.
class TPAPILogDirectionEnum(enum.Enum):
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"

class TPAPILogStatusEnum(enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"

class ThirdPartyAPILog(Base): # Log of API calls to/from these third parties
    __tablename__ = "third_party_api_logs"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(SQLAlchemyEnum(ThirdPartyServiceEnum), nullable=False, index=True)
    # Link to a more specific record if needed, e.g. a specific credit report request
    # internal_request_reference = Column(String, index=True, nullable=True)
    external_call_reference = Column(String, index=True, nullable=True) # Ref ID from the third party

    endpoint_url = Column(String, nullable=False)
    http_method = Column(String(10), nullable=False)
    direction = Column(SQLAlchemyEnum(TPAPILogDirectionEnum), nullable=False)

    request_headers = Column(Text, nullable=True)
    request_payload = Column(Text, nullable=True)
    response_status_code = Column(Integer, nullable=True)
    response_headers = Column(Text, nullable=True)
    response_payload = Column(Text, nullable=True) # Can be large (e.g. credit report XML/JSON)

    status = Column(SQLAlchemyEnum(TPAPILogStatusEnum), nullable=False)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class ThirdPartyConfig(Base): # Configuration for connecting to third-party services
    __tablename__ = "third_party_configs"
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(SQLAlchemyEnum(ThirdPartyServiceEnum), nullable=False, unique=True)

    api_base_url = Column(String, nullable=False)
    # Credentials (store encrypted or use a secrets manager)
    # username_encrypted = Column(String, nullable=True)
    # password_encrypted = Column(String, nullable=True)
    # api_key_encrypted = Column(String, nullable=True)
    # client_certificate_path = Column(String, nullable=True) # Path to cert file if mTLS needed

    # Other config params as JSON
    # additional_config_json = Column(Text, nullable=True) # e.g. {"timeout_seconds": 60, "retry_attempts": 3}

    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())

# --- Specific Integration Models (Examples) ---

class CreditBureauReport(Base): # Storing summary or reference to credit reports
    __tablename__ = "credit_bureau_reports"
    id = Column(Integer, primary_key=True, index=True)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    # loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=True, index=True)
    bvn_queried = Column(String(11), nullable=False, index=True)

    bureau_name = Column(SQLAlchemyEnum(ThirdPartyServiceEnum), nullable=False) # CREDIT_BUREAU_CRC, etc.
    report_reference_external = Column(String, unique=True, nullable=False) # Report ID from bureau

    report_date = Column(DateTime(timezone=True), nullable=False)
    credit_score = Column(Integer, nullable=True)
    # summary_data_json = Column(Text, nullable=True) # Key data points from the report
    # full_report_path_or_lob = Column(Text, nullable=True) # Path to stored report file or LOB if storing full report

    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    # requested_by_user_id = Column(Integer, ForeignKey("users.id"))

class ExternalLoanApplication(Base): # For loans originated by partners
    __tablename__ = "external_loan_applications"
    id = Column(Integer, primary_key=True, index=True)
    originator_name = Column(SQLAlchemyEnum(ThirdPartyServiceEnum), nullable=False) # e.g. EXTERNAL_LOAN_ORIGINATOR_Y
    originator_reference_id = Column(String, nullable=False, index=True) # Unique ID from the loan originator

    # Mirrored/subset of data from LoanApplication model, plus originator specific fields
    # requested_amount = Column(Numeric(precision=18, scale=2))
    # customer_bvn = Column(String(11))
    # ... other customer and loan details received from originator ...

    # raw_payload_received_json = Column(Text) # Store the full payload from originator
    status_at_originator = Column(String, nullable=True) # Status on originator's system

    # internal_loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=True, unique=True) # Link to our internal loan app
    # internal_status = Column(String) # Our bank's status for this application (e.g. PENDING_REVIEW, APPROVED, REJECTED)

    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

# BaaS (Banking-as-a-Service) Partner API Call Log (if bank exposes APIs to fintechs)
# This could be part of APIManagementConfig in core_infrastructure if that's for inbound calls.
# If this module handles specific BaaS partner logic, then a log here might be relevant.
# class BaaSPartnerAPICall(Base):
#    __tablename__ = "baas_partner_api_calls"
#    id = Column(Integer, primary_key=True)
#    partner_id = Column(String, ForeignKey("baas_partners.partner_code")) # Link to a BaaS partner definition table
#    endpoint_called = Column(String)
#    request_payload_json = Column(Text)
#    response_payload_json = Column(Text)
#    timestamp = Column(DateTime(timezone=True), server_default=func.now())
#    status_code = Column(Integer)

# This module is primarily about enabling communication with external non-payment systems.
# Key aspects:
# - Securely storing credentials/configs for these third parties.
# - Logging all API interactions for audit and debugging.
# - Adapting data between internal CBS formats and third-party API formats.
# - Handling webhooks/callbacks from these third parties.
# The actual business logic using data from these integrations (e.g., using credit score in loan decisioning)
# would reside in the respective core modules (e.g., LoanManagementModule).
