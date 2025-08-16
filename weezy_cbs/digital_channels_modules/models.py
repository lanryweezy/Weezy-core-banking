# Database models for Digital Channels Modules
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLAlchemyEnum, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

from weezy_cbs.database import Base # Use the shared Base

class ChannelTypeEnum(enum.Enum):
    INTERNET_BANKING = "INTERNET_BANKING"
    MOBILE_BANKING_APP = "MOBILE_BANKING_APP"
    USSD = "USSD"
    WHATSAPP_BOT = "WHATSAPP_BOT"
    TELEGRAM_BOT = "TELEGRAM_BOT"
    FACEBOOK_MESSENGER_BOT = "FACEBOOK_MESSENGER_BOT"
    AGENT_PORTAL = "AGENT_PORTAL"
    KIOSK = "KIOSK"
    SMS_BANKING = "SMS_BANKING"

class DigitalUserProfile(Base):
    __tablename__ = "digital_user_profiles"
    id = Column(Integer, primary_key=True, index=True)

    # Link to the main Customer record in customer_identity_management.customers
    # Ensure the Customer model in 'customer_identity_management' has:
    # digital_profile = relationship("DigitalUserProfile", uselist=False, back_populates="customer", cascade="all, delete-orphan")
    customer_id = Column(Integer, ForeignKey("customers.id", name="fk_digitaluser_customer"), unique=True, nullable=False, index=True)
    # customer = relationship("Customer", back_populates="digital_profile") # Relationship defined in Customer model

    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)

    security_question_1 = Column(String(255), nullable=True)
    security_answer_1_hashed = Column(String(128), nullable=True)
    # Add more security questions if needed, or a separate related table for dynamic questions.

    is_active = Column(Boolean, default=True, index=True)
    is_verified_email = Column(Boolean, default=False) # If username is email or separate email verification
    is_verified_phone = Column(Boolean, default=False) # If phone is used for login or 2FA

    last_login_channel = Column(SQLAlchemyEnum(ChannelTypeEnum), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)

    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    preferences_json = Column(Text, nullable=True) # For language, theme, preferred_account_display etc.
    notification_settings_json = Column(Text, nullable=True) # e.g., {"sms_alerts_transaction": true, "email_statements_monthly": false}

    transaction_pin_hashed = Column(String(128), nullable=True) # Hashed PIN for USSD, quick actions
    is_transaction_pin_set = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    registered_devices = relationship("RegisteredDevice", back_populates="digital_user_profile", cascade="all, delete-orphan")
    session_logs = relationship("SessionLog", back_populates="digital_user_profile", cascade="all, delete-orphan")
    ussd_sessions = relationship("USSDSession", back_populates="digital_user_profile", cascade="all, delete-orphan")
    chatbot_interaction_logs = relationship("ChatbotInteractionLog", back_populates="digital_user_profile", cascade="all, delete-orphan")


class RegisteredDevice(Base):
    __tablename__ = "registered_devices"
    id = Column(Integer, primary_key=True, index=True)
    digital_user_profile_id = Column(Integer, ForeignKey("digital_user_profiles.id", name="fk_device_digitaluser"), nullable=False)

    device_identifier = Column(String(255), nullable=False, index=True)
    device_name = Column(String(100), nullable=True)
    device_os = Column(String(50), nullable=True)
    app_version = Column(String(20), nullable=True)

    is_trusted = Column(Boolean, default=False)
    status = Column(String(20), default="PENDING_VERIFICATION", index=True) # PENDING_VERIFICATION, ACTIVE, BLOCKED, INACTIVE

    last_login_from_device_at = Column(DateTime(timezone=True), nullable=True)
    registration_date = Column(DateTime(timezone=True), server_default=func.now())
    push_notification_token = Column(String(512), nullable=True, unique=True) # Ensure this is unique if one token per device globally

    digital_user_profile = relationship("DigitalUserProfile", back_populates="registered_devices")
    __table_args__ = (UniqueConstraint('digital_user_profile_id', 'device_identifier', name='uq_user_device_identifier'),)


class SessionLog(Base):
    __tablename__ = "session_logs"
    id = Column(Integer, primary_key=True, index=True)
    digital_user_profile_id = Column(Integer, ForeignKey("digital_user_profiles.id", name="fk_sessionlog_digitaluser"), nullable=False, index=True)

    channel = Column(SQLAlchemyEnum(ChannelTypeEnum), nullable=False, index=True)
    registered_device_id = Column(Integer, ForeignKey("registered_devices.id", name="fk_sessionlog_device"), nullable=True)

    login_time = Column(DateTime(timezone=True), server_default=func.now())
    logout_time = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    session_token_jti = Column(String(100), unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    digital_user_profile = relationship("DigitalUserProfile", back_populates="session_logs")
    device = relationship("RegisteredDevice")

class USSDSession(Base):
    __tablename__ = "ussd_sessions"
    id = Column(String(100), primary_key=True, index=True)
    phone_number = Column(String(15), nullable=False, index=True)
    digital_user_profile_id = Column(Integer, ForeignKey("digital_user_profiles.id", name="fk_ussdsession_digitaluser"), nullable=True, index=True)

    current_menu_code = Column(String(50), nullable=True)
    session_data_json = Column(Text, nullable=True)

    last_interaction_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    language_code = Column(String(5), default="en")
    status = Column(String(20), default="ACTIVE", index=True) # ACTIVE, COMPLETED, TIMED_OUT, CANCELLED

    digital_user_profile = relationship("DigitalUserProfile", back_populates="ussd_sessions")

class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id = Column(Integer, primary_key=True, index=True)
    # Link to customer if the notification is related to a specific customer, even if they don't have a digital profile yet.
    customer_id = Column(Integer, ForeignKey("customers.id", name="fk_notification_customer"), nullable=True, index=True)
    digital_user_profile_id = Column(Integer, ForeignKey("digital_user_profiles.id", name="fk_notification_digitaluser"), nullable=True, index=True) # For profile-specific notifications

    channel_type = Column(SQLAlchemyEnum(ChannelTypeEnum), nullable=False, index=True)
    recipient_identifier = Column(String(255), nullable=False, index=True)

    message_type = Column(String(50), nullable=True, index=True)
    subject = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)

    status = Column(String(20), default="PENDING", index=True)
    failure_reason = Column(Text, nullable=True)
    external_message_id = Column(String(100), nullable=True, index=True)

    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Link to a transaction or event if the notification is for a specific one
    # financial_transaction_id = Column(Integer, ForeignKey("financial_transactions.id"), nullable=True, index=True)
    reference_id = Column(String(50), nullable=True, index=True) # Generic reference

    # customer = relationship("Customer", back_populates="notifications") # Define in Customer
    digital_user_profile = relationship("DigitalUserProfile") # One-way for now, or add back_populates if needed


class ChatbotInteractionLog(Base):
    __tablename__ = "chatbot_interaction_logs"
    id = Column(Integer, primary_key=True, index=True)
    digital_user_profile_id = Column(Integer, ForeignKey("digital_user_profiles.id", name="fk_chatlog_digitaluser"), nullable=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", name="fk_chatlog_customer"), nullable=True, index=True)

    session_id = Column(String(100), index=True, nullable=False)
    channel = Column(SQLAlchemyEnum(ChannelTypeEnum), nullable=False, index=True)

    user_message = Column(Text, nullable=True)
    bot_response = Column(Text, nullable=True)
    intent_detected = Column(String(100), nullable=True)
    entities_extracted_json = Column(Text, nullable=True)
    confidence_score = Column(String(20), nullable=True) # Storing as string if it can be varied format from provider

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    feedback_rating = Column(Integer, nullable=True)
    is_escalated = Column(Boolean, default=False)

    digital_user_profile = relationship("DigitalUserProfile", back_populates="chatbot_interaction_logs")
    # customer = relationship("Customer", back_populates="chatbot_logs") # Define in Customer

# Relationships to be defined in the Customer model (customer_identity_management.models.Customer):
# from sqlalchemy.orm import relationship
# digital_profile = relationship("DigitalUserProfile", uselist=False, back_populates="customer", cascade="all, delete-orphan")
# notifications = relationship("NotificationLog", back_populates="customer") # If NotificationLog has a back_populates to customer
# chatbot_logs = relationship("ChatbotInteractionLog", back_populates="customer") # If ChatbotInteractionLog has a back_populates to customer
# ussd_sessions = relationship("USSDSession", back_populates="customer") # If USSDSession links to customer and has back_populates
# Make sure the foreign key names (e.g., fk_digitaluser_customer) are consistent if you define them explicitly in relationships too.
# The cascade="all, delete-orphan" on digital_profile ensures that if a Customer is deleted, their DigitalUserProfile and related channel data (like devices) are also deleted.
# Other relationships might not need cascade delete from the Customer side (e.g., logs might be kept or archived).
