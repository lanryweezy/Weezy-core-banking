# Database models for Digital Channels Modules (Shared or Common)
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

# from weezy_cbs.database import Base
Base = declarative_base() # Local Base for now

import enum

class DigitalUserChannelPreference(Base): # User preferences for digital channels
    __tablename__ = "digital_user_channel_preferences"
    id = Column(Integer, primary_key=True, index=True)
    # customer_id = Column(Integer, ForeignKey("customers.id"), unique=True, nullable=False, index=True) # Link to the main customer record

    # Example preferences:
    # preferred_notification_channel = Column(String, default="SMS") # SMS, EMAIL, PUSH_APP
    # receive_promotional_emails = Column(Boolean, default=True)
    # default_login_channel = Column(String, nullable=True) # e.g. "MOBILE_APP"

    # Security settings specific to digital channels
    # two_fa_enabled_channels_json = Column(Text, nullable=True) # JSON: {"MOBILE_APP": true, "WEB_BANKING": false}
    # last_channel_activity_json = Column(Text, nullable=True) # JSON: {"MOBILE_APP": "2023-10-27T10:00:00Z", ...}

    # customer = relationship("Customer")

class DigitalChannelSession(Base): # Active sessions across digital channels
    __tablename__ = "digital_channel_sessions"
    id = Column(String, primary_key=True, index=True) # Session ID (e.g. JWT ID or custom session token)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True) # Link to the User (could be customer acting as user or staff)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True) # If session is for a customer

    channel_type = Column(String, nullable=False) # "WEB_BANKING", "MOBILE_APP", "USSD_SESSION", "CHATBOT"
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    device_id = Column(String, nullable=True, index=True) # For mobile apps

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    is_active = Column(Boolean, default=True) # Can be marked false on logout or expiry

    # user = relationship("User")
    # customer = relationship("Customer")

class RegisteredDevice(Base): # For mobile banking app device registration
    __tablename__ = "registered_devices"
    id = Column(Integer, primary_key=True, index=True)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    device_id_unique = Column(String, unique=True, nullable=False, index=True) # Unique identifier from the device
    device_name = Column(String, nullable=True) # User-friendly name for the device, e.g. "John's iPhone"
    device_os = Column(String, nullable=True) # e.g. "iOS 15.1", "Android 12"
    app_version = Column(String, nullable=True)

    fcm_token_or_push_id = Column(String, nullable=True, index=True) # For push notifications

    is_trusted = Column(Boolean, default=False) # User can mark device as trusted for less friction
    last_login_from_device = Column(DateTime(timezone=True), nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())

    # customer = relationship("Customer")

# Models for specific channels (Internet Banking, Mobile Banking, USSD, Agent Dashboard, Chatbot)
# would typically reside within their respective sub-modules if they have distinct data needs.
# For example:
# - internet_banking/models.py might have `WebUserProfile` if web specific profile data is stored.
# - ussd_banking/models.py might have `USSDMenuState` or `USSDUserSession` for tracking user progress through menus.
# - chatbot_integration/models.py might have `ChatConversationLog`.

# This top-level models.py is for shared entities or if the structure is flatter.
# For now, keeping it simple with potentially shared models.

# Example: A log for notifications sent via various channels
class NotificationLog(Base):
    __tablename__ = "digital_channel_notification_logs"
    id = Column(Integer, primary_key=True, index=True)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    channel_sent_via = Column(String, nullable=False) # SMS, EMAIL, PUSH_NOTIFICATION_APP
    recipient_identifier = Column(String, nullable=False) # Phone number, email address, device push token

    message_type = Column(String, nullable=True) # TRANSACTION_ALERT, OTP, PROMO, PASSWORD_RESET
    message_content_template_id = Column(String, nullable=True) # Reference to a template
    # message_content_actual = Column(Text) # The actual message sent (be careful with PII)

    status = Column(String, default="SENT") # SENT, DELIVERED, FAILED, READ (if trackable)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    # external_provider_ref_id = Column(String, nullable=True) # Ref from Twilio, Mandrill etc.
    error_message = Column(Text, nullable=True) # If sending failed

# If there's a unified "Digital User" concept separate from "Customer" (e.g. for login credentials)
# class DigitalUser(Base):
#     __tablename__ = "digital_users"
#     id = Column(Integer, primary_key=True)
#     customer_id = Column(Integer, ForeignKey("customers.id"), unique=True, nullable=False)
#     digital_username = Column(String, unique=True, index=True, nullable=False)
#     hashed_password = Column(String, nullable=False) # For web/mobile login
#     # Security questions, preferred 2FA method etc.
#     is_active = Column(Boolean, default=True) # Digital channel access status
#     # ... other fields related to digital channel access management

# The sub-modules (internet_banking, mobile_banking, etc.) would primarily contain API endpoints (routers)
# and services that call upon the core CBS modules (accounts, transactions, etc.)
# and potentially these shared digital channel models.
