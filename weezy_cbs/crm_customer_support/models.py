# Database models for CRM & Customer Support
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLAlchemyEnum, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

from weezy_cbs.database import Base # Use the shared Base

class TicketStatusEnum(enum.Enum):
    OPEN = "OPEN"; PENDING_CUSTOMER = "PENDING_CUSTOMER"; PENDING_AGENT = "PENDING_AGENT"
    IN_PROGRESS = "IN_PROGRESS"; RESOLVED = "RESOLVED"; CLOSED = "CLOSED"; REOPENED = "REOPENED"

class TicketPriorityEnum(enum.Enum):
    LOW = "LOW"; MEDIUM = "MEDIUM"; HIGH = "HIGH"; URGENT = "URGENT"

class TicketCategoryEnum(enum.Enum):
    ACCOUNT_INQUIRY = "ACCOUNT_INQUIRY"; TRANSACTION_DISPUTE = "TRANSACTION_DISPUTE"
    CARD_ISSUE = "CARD_ISSUE"; LOAN_APPLICATION_QUERY = "LOAN_APPLICATION_QUERY"
    TECHNICAL_SUPPORT = "TECHNICAL_SUPPORT"; GENERAL_FEEDBACK = "GENERAL_FEEDBACK"
    COMPLAINT = "COMPLAINT"; FEATURE_REQUEST = "FEATURE_REQUEST"; OTHER = "OTHER"

class TicketChannelEnum(enum.Enum):
    PHONE_CALL = "PHONE_CALL"; EMAIL = "EMAIL"; WEB_FORM = "WEB_FORM"
    IN_APP_CHAT = "IN_APP_CHAT"; BRANCH_VISIT = "BRANCH_VISIT"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"; CHATBOT_ESCALATION = "CHATBOT_ESCALATION"; INTERNAL = "INTERNAL"

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(20), unique=True, index=True, nullable=False)

    # --- Links to other modules ---
    # Ensure Customer model has: support_tickets = relationship("SupportTicket", back_populates="customer")
    customer_id = Column(Integer, ForeignKey("customers.id", name="fk_ticket_customer"), nullable=False, index=True)
    # Ensure DigitalUserProfile model has: support_tickets = relationship("SupportTicket", back_populates="digital_user_profile")
    digital_user_profile_id = Column(Integer, ForeignKey("digital_user_profiles.id", name="fk_ticket_digitaluser"), nullable=True, index=True)
    # Ensure User model (core_infra) has: assigned_tickets = relationship("SupportTicket", foreign_keys="[SupportTicket.assigned_to_user_id]", back_populates="assigned_agent")
    assigned_to_user_id = Column(Integer, ForeignKey("users.id", name="fk_ticket_assignedagent"), nullable=True, index=True)

    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    status = Column(SQLAlchemyEnum(TicketStatusEnum), default=TicketStatusEnum.OPEN, nullable=False, index=True)
    priority = Column(SQLAlchemyEnum(TicketPriorityEnum), default=TicketPriorityEnum.MEDIUM, nullable=False, index=True)
    category = Column(SQLAlchemyEnum(TicketCategoryEnum), nullable=True, index=True)
    channel_of_origin = Column(SQLAlchemyEnum(TicketChannelEnum), nullable=True)

    resolution_details = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    sla_due_date = Column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships defined via back_populates from other models or here if one-way needed
    # customer = relationship("Customer", back_populates="support_tickets") # If Customer model is directly importable & defines inverse
    # digital_user_profile = relationship("DigitalUserProfile", back_populates="support_tickets") # If DigitalUserProfile model is directly importable
    # assigned_agent = relationship("User", foreign_keys=[assigned_to_user_id]) # If User model is directly importable

    updates = relationship("TicketUpdate", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketUpdate.created_at")


class TicketUpdate(Base):
    __tablename__ = "ticket_updates"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", name="fk_update_ticket", ondelete="CASCADE"), nullable=False, index=True)

    # --- Links to other modules for who made the update ---
    # Ensure User model (core_infra) has: ticket_updates_made = relationship("TicketUpdate", foreign_keys="[TicketUpdate.agent_user_id]", back_populates="agent_user")
    agent_user_id = Column(Integer, ForeignKey("users.id", name="fk_update_agentuser"), nullable=True)
    # If customer replies via authenticated channel, digital_user_profile_id on ticket can be used for context.
    # If via unauthenticated (e.g. direct email reply), might not link to a digital profile here directly.
    # For simplicity, we assume agent_user_id or it's a system/customer reply not directly linked to a specific digital_user_profile on the update itself.

    update_text = Column(Text, nullable=False)
    is_internal_note = Column(Boolean, default=False, nullable=False)
    attachments_json = Column(Text, nullable=True) # JSON array of strings: [{"filename": "doc.pdf", "url": "...", "size": 1024}]

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("SupportTicket", back_populates="updates")
    # agent_user = relationship("User", foreign_keys=[agent_user_id]) # If User model is directly importable


class CustomerNote(Base):
    __tablename__ = "customer_notes"
    id = Column(Integer, primary_key=True, index=True)
    # Ensure Customer model has: customer_notes = relationship("CustomerNote", back_populates="customer")
    customer_id = Column(Integer, ForeignKey("customers.id", name="fk_note_customer"), nullable=False, index=True)
    # Ensure User model (core_infra) has: customer_notes_created = relationship("CustomerNote", foreign_keys="[CustomerNote.agent_user_id]", back_populates="agent_user")
    agent_user_id = Column(Integer, ForeignKey("users.id", name="fk_note_agentuser"), nullable=False)

    note_text = Column(Text, nullable=False)
    category = Column(String(50), nullable=True, index=True) # e.g., "Follow-up", "Feedback", "InteractionLog"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # customer = relationship("Customer", back_populates="customer_notes")
    # agent_user = relationship("User", foreign_keys=[agent_user_id])


class CampaignStatusEnum(enum.Enum):
    DRAFT = "DRAFT"; SCHEDULED = "SCHEDULED"; ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"; COMPLETED = "COMPLETED"; ARCHIVED = "ARCHIVED"; FAILED = "FAILED"

class CampaignChannelEnum(enum.Enum):
    EMAIL = "EMAIL"; SMS = "SMS"; PUSH_NOTIFICATION = "PUSH_NOTIFICATION"
    IN_APP_MESSAGE = "IN_APP_MESSAGE"

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    campaign_name = Column(String(150), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    status = Column(SQLAlchemyEnum(CampaignStatusEnum), default=CampaignStatusEnum.DRAFT, nullable=False, index=True)
    campaign_channel = Column(SQLAlchemyEnum(CampaignChannelEnum), nullable=False)

    target_audience_rules_json = Column(Text, nullable=True)

    message_template_name = Column(String(100), nullable=True)
    message_subject = Column(String(255), nullable=True)
    message_body_content = Column(Text, nullable=True)

    start_date = Column(DateTime(timezone=True), nullable=True, index=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Ensure User model (core_infra) has: campaigns_created = relationship("Campaign", foreign_keys="[Campaign.created_by_user_id]", back_populates="created_by_user")
    created_by_user_id = Column(Integer, ForeignKey("users.id", name="fk_campaign_createdby"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    logs = relationship("CampaignLog", back_populates="campaign", cascade="all, delete-orphan")

class CampaignLogEntryStatusEnum(enum.Enum):
    PENDING_SEND = "PENDING_SEND"; TARGETED = "TARGETED"; SENT = "SENT"; DELIVERED = "DELIVERED" # Added TARGETED
    OPENED = "OPENED"; CLICKED = "CLICKED"; CONVERTED = "CONVERTED"
    FAILED = "FAILED"; UNSUBSCRIBED = "UNSUBSCRIBED"; BOUNCED = "BOUNCED"

class CampaignLog(Base):
    __tablename__ = "campaign_logs"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", name="fk_camplog_campaign", ondelete="CASCADE"), nullable=False, index=True)
    # Ensure Customer model has: campaign_logs = relationship("CampaignLog", back_populates="customer")
    customer_id = Column(Integer, ForeignKey("customers.id", name="fk_camplog_customer"), nullable=False, index=True)

    status = Column(SQLAlchemyEnum(CampaignLogEntryStatusEnum), default=CampaignLogEntryStatusEnum.TARGETED, nullable=False, index=True)
    recipient_identifier = Column(String(255), nullable=False)

    processed_at = Column(DateTime(timezone=True), server_default=func.now()) # When this log entry was created/targeted
    sent_at = Column(DateTime(timezone=True), nullable=True)
    interacted_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    external_message_id = Column(String(100), nullable=True, index=True)

    campaign = relationship("Campaign", back_populates="logs")
    # customer = relationship("Customer", back_populates="campaign_logs")
    __table_args__ = (UniqueConstraint('campaign_id', 'customer_id', name='uq_campaign_customer'),)


class FAQItem(Base):
    __tablename__ = "faq_items"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    question = Column(Text, nullable=False, unique=True) # Question should be unique
    answer = Column(Text, nullable=False)
    tags_json = Column(Text, nullable=True) # JSON array of strings
    is_published = Column(Boolean, default=True, nullable=False, index=True)
    view_count = Column(Integer, default=0, nullable=False)

    # Ensure User model (core_infra) has relevant relationships if tracking creators/updaters
    created_by_user_id = Column(Integer, ForeignKey("users.id", name="fk_faq_createdby"), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id", name="fk_faq_updatedby"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    # updated_by_user = relationship("User", foreign_keys=[updated_by_user_id])

# Notes on Relationships:
# - Foreign Keys: Defined with `name` for explicit constraint naming.
# - `ondelete="CASCADE"` is used on `TicketUpdate.ticket_id` and `CampaignLog.campaign_id`
#   meaning if a ticket or campaign is deleted, its updates/logs are also deleted.
# - `back_populates` is crucial for bi-directional relationships. The string value must match
#   the relationship name on the other side of the pair.
# - For relationships to models in other modules (Customer, User, DigitalUserProfile),
#   the corresponding `relationship` definition must exist in those other models' files,
#   and they must also use `back_populates` pointing back to the relationship name here.
#   Example for Customer model:
#   from weezy_cbs.crm_customer_support.models import SupportTicket # (Adjust import based on actual structure)
#   support_tickets = relationship("SupportTicket", back_populates="customer")
#   This assumes a shared SQLAlchemy `Base` or careful handling of metadata across modules.
#   If `Base` is not shared, string-based relationship definitions might be needed initially,
#   and then resolved using `orm.configure_mappers()`.
#   For this project, we assume `Base` will be centralized eventually.
#   The FKs like "customers.id" work if table names are globally unique and `Base` knows about them.
#   If schemas are used (e.g. "customer_identity.customers"), that needs to be in FK string.
#   For now, direct table names are assumed.
