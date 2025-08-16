# Database models for Payments Integration Layer (if any)
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLAlchemyEnum, ForeignKey, Boolean
from sqlalchemy.sql import func
from weezy_cbs.database import Base # Use the shared Base

import enum

# Assuming CurrencyEnum will be shared, for now define locally or import if available
# from weezy_cbs.accounts_ledger_management.models import CurrencyEnum as SharedCurrencyEnum
class CurrencyEnum(enum.Enum):
    NGN = "NGN"
    USD = "USD"
    # Add other relevant currencies

class PaymentGatewayEnum(enum.Enum):
    PAYSTACK = "PAYSTACK"
    FLUTTERWAVE = "FLUTTERWAVE"
    MONNIFY = "MONNIFY"
    REMITA = "REMITA"
    INTERSWITCH_WEB = "INTERSWITCH_WEB"
    NIBSS_EBILLSPAY = "NIBSS_EBILLSPAY"
    NQR = "NQR"
    # Add others

class APILogDirectionEnum(enum.Enum):
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"

class APILogStatusEnum(enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"

class PaymentAPILog(Base):
    __tablename__ = "payment_api_logs"

    id = Column(Integer, primary_key=True, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True, index=True)
    external_reference = Column(String(100), index=True, nullable=True)
    internal_reference = Column(String(100), index=True, nullable=True)

    gateway = Column(SQLAlchemyEnum(PaymentGatewayEnum), nullable=False, index=True)
    endpoint_url = Column(String(512), nullable=False)
    http_method = Column(String(10), nullable=False)

    direction = Column(SQLAlchemyEnum(APILogDirectionEnum), nullable=False)

    request_headers = Column(Text, nullable=True)
    request_payload = Column(Text, nullable=True)

    response_status_code = Column(Integer, nullable=True)
    response_headers = Column(Text, nullable=True)
    response_payload = Column(Text, nullable=True)

    status = Column(SQLAlchemyEnum(APILogStatusEnum), nullable=False)
    error_message = Column(Text, nullable=True)

    duration_ms = Column(Integer, nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PaymentAPILog(id={self.id}, gateway='{self.gateway.value}', status='{self.status.value}')>"

class PaymentGatewayConfig(Base):
    __tablename__ = "payment_gateway_configs"
    id = Column(Integer, primary_key=True, index=True)
    gateway = Column(SQLAlchemyEnum(PaymentGatewayEnum), nullable=False, unique=True)

    api_key_encrypted = Column(String(512), nullable=True)
    secret_key_encrypted = Column(String(512), nullable=True)
    public_key_encrypted = Column(String(512), nullable=True)
    webhook_secret_key_encrypted = Column(String(512), nullable=True) # For verifying incoming webhooks

    base_url = Column(String(255), nullable=False)
    merchant_id = Column(String(100), nullable=True)
    additional_headers_json = Column(Text, nullable=True) # JSON: {"X-Custom-Header": "value"}

    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<PaymentGatewayConfig(gateway='{self.gateway.value}', active={self.is_active})>"

class WebhookEventLog(Base):
    __tablename__ = "webhook_event_logs"
    id = Column(Integer, primary_key=True, index=True)
    gateway = Column(SQLAlchemyEnum(PaymentGatewayEnum), nullable=False, index=True)
    event_type = Column(String(100), index=True)
    event_id_external = Column(String(100), index=True, nullable=True)

    payload_received = Column(Text, nullable=False)
    headers_received = Column(Text, nullable=True)

    processing_status = Column(String(30), default="PENDING", index=True)
    processing_notes = Column(Text, nullable=True)

    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True, index=True)

    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<WebhookEventLog(id={self.id}, gateway='{self.gateway.value}', event='{self.event_type}')>"

class PaymentLink(Base):
    __tablename__ = "payment_links"
    id = Column(Integer, primary_key=True, index=True)
    link_reference = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    account_to_credit_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)

    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    description = Column(String(255), nullable=True)

    is_reusable = Column(Boolean, default=False)
    max_usage_count = Column(Integer, nullable=True)
    current_usage_count = Column(Integer, default=0)

    status = Column(String(20), default="ACTIVE", index=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # financial_transaction_ids_json = Column(Text, nullable=True) # Storing multiple FT IDs if link is reusable

    customer = relationship("Customer") # Add back_populates in Customer model
    account_to_credit = relationship("Account") # Add back_populates in Account model

    def __repr__(self):
        return f"<PaymentLink(ref='{self.link_reference}', amount='{self.amount} {self.currency.value}')>"
