# Database models for Payments Integration Layer (if any)
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLAlchemyEnum, ForeignKey, Boolean
from sqlalchemy.sql import func
# from weezy_cbs.database import Base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base() # Local Base for now

import enum

class PaymentGatewayEnum(enum.Enum):
    PAYSTACK = "PAYSTACK"
    FLUTTERWAVE = "FLUTTERWAVE"
    MONNIFY = "MONNIFY"
    REMITA = "REMITA"
    INTERSWITCH = "INTERSWITCH_WEB" # For WebPay, Quickteller etc.
    NIBSS_EBILLSPAY = "NIBSS_EBILLSPAY"
    NQR = "NQR" # NIBSS QR
    # Add others like specific Telco airtime aggregators (VeedezPay was an example)

class APILogDirectionEnum(enum.Enum):
    OUTGOING = "OUTGOING" # Request sent from our system
    INCOMING = "INCOMING" # Request received by our system (e.g. webhook callback)

class APILogStatusEnum(enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING" # For async responses

# Log of API calls made to/from external payment services
class PaymentAPILog(Base):
    __tablename__ = "payment_api_logs"

    id = Column(Integer, primary_key=True, index=True)
    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, index=True) # Link to master FT if applicable
    external_reference = Column(String, index=True, nullable=True) # Reference from the external gateway
    internal_reference = Column(String, index=True, nullable=True) # Our internal reference for the call

    gateway = Column(SQLAlchemyEnum(PaymentGatewayEnum), nullable=False, index=True)
    endpoint_url = Column(String, nullable=False)
    http_method = Column(String(10), nullable=False) # GET, POST, PUT etc.

    direction = Column(SQLAlchemyEnum(APILogDirectionEnum), nullable=False) # OUTGOING or INCOMING (webhook)

    request_headers = Column(Text, nullable=True) # Store sanitized headers
    request_payload = Column(Text, nullable=True) # Store sanitized payload

    response_status_code = Column(Integer, nullable=True)
    response_headers = Column(Text, nullable=True) # Store sanitized headers
    response_payload = Column(Text, nullable=True) # Store sanitized payload

    status = Column(SQLAlchemyEnum(APILogStatusEnum), nullable=False)
    error_message = Column(Text, nullable=True) # If call failed

    duration_ms = Column(Integer, nullable=True) # How long the call took

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PaymentAPILog(id={self.id}, gateway='{self.gateway.value}', status='{self.status.value}')>"

class PaymentGatewayConfig(Base):
    __tablename__ = "payment_gateway_configs"
    id = Column(Integer, primary_key=True, index=True)
    gateway = Column(SQLAlchemyEnum(PaymentGatewayEnum), nullable=False, unique=True)

    # Store encrypted credentials or references to a secure vault
    api_key_encrypted = Column(String, nullable=True)
    secret_key_encrypted = Column(String, nullable=True)
    public_key_encrypted = Column(String, nullable=True) # For gateways like Flutterwave

    base_url = Column(String, nullable=False)
    # Other specific config fields like merchant_id, callback_url_template etc.
    merchant_id = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<PaymentGatewayConfig(gateway='{self.gateway.value}', active={self.is_active})>"

class WebhookEventLog(Base): # For incoming webhook events from payment gateways
    __tablename__ = "webhook_event_logs"
    id = Column(Integer, primary_key=True, index=True)
    gateway = Column(SQLAlchemyEnum(PaymentGatewayEnum), nullable=False, index=True)
    event_type = Column(String, index=True) # e.g., 'charge.success', 'transfer.failed' (gateway specific)
    event_id_external = Column(String, index=True, nullable=True) # Event ID from the gateway

    payload_received = Column(Text) # Full JSON payload
    headers_received = Column(Text) # Relevant headers (e.g., for signature verification)

    processing_status = Column(String, default="PENDING") # PENDING, PROCESSED, FAILED_VALIDATION, ERROR_PROCESSING
    processing_notes = Column(Text, nullable=True)

    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, index=True) # If successfully linked to an FT

    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<WebhookEventLog(id={self.id}, gateway='{self.gateway.value}', event='{self.event_type}')>"

# PaymentLink Management (if the bank generates its own payment links)
class PaymentLink(Base):
    __tablename__ = "payment_links"
    id = Column(Integer, primary_key=True, index=True)
    link_reference = Column(String, unique=True, index=True, nullable=False) # Unique, shareable part of the URL
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True) # If generated by a specific customer/merchant
    # account_to_credit_id = Column(Integer, ForeignKey("accounts.id"), nullable=False) # Account that receives funds

    amount = Column(Numeric(precision=18, scale=2), nullable=False) # Fixed amount for the link
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    description = Column(String, nullable=True)

    is_reusable = Column(Boolean, default=False) # If false, can only be paid once
    max_usage_count = Column(Integer, nullable=True) # If reusable, how many times
    current_usage_count = Column(Integer, default=0)

    status = Column(String, default="ACTIVE") # ACTIVE, INACTIVE, PAID (if not reusable), EXPIRED
    expiry_date = Column(DateTime(timezone=True), nullable=True)

    # Callback URL for this specific link if different from global config
    # custom_callback_url = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # financial_transaction_ids = Column(Text, nullable=True) # Store JSON array of successful FT IDs if multiple payments allowed

    def __repr__(self):
        return f"<PaymentLink(ref='{self.link_reference}', amount='{self.amount} {self.currency.value}')>"

# This module primarily defines how to interact with external services.
# Models here are mostly for logging, configuration, or managing artifacts like payment links.
# The core logic resides in 'services.py' which would contain clients for each gateway.
