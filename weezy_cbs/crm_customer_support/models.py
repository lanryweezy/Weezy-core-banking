# Database models for CRM & Customer Support Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

# from weezy_cbs.database import Base
Base = declarative_base() # Local Base for now

import enum

class TicketStatusEnum(enum.Enum):
    OPEN = "OPEN"
    PENDING_CUSTOMER_RESPONSE = "PENDING_CUSTOMER_RESPONSE"
    PENDING_AGENT_RESPONSE = "PENDING_AGENT_RESPONSE" # Or "IN_PROGRESS"
    ON_HOLD = "ON_HOLD" # Waiting for external input or resolution
    RESOLVED = "RESOLVED" # Agent marked as resolved
    CLOSED = "CLOSED"     # Customer confirmed resolution or auto-closed after period
    REOPENED = "REOPENED"

class TicketPriorityEnum(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class TicketChannelEnum(enum.Enum): # Channel through which the ticket was created
    EMAIL = "EMAIL"
    PHONE_CALL = "PHONE_CALL"
    WEB_FORM = "WEB_FORM" # From bank's website contact form
    MOBILE_APP_SUPPORT = "MOBILE_APP_SUPPORT"
    CHAT = "CHAT" # Live chat or chatbot escalation
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    BRANCH_VISIT = "BRANCH_VISIT"
    INTERNAL = "INTERNAL" # Created by staff on behalf of customer or for internal issue

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_reference = Column(String, unique=True, nullable=False, index=True) # Auto-generated

    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True) # If ticket is from a known customer
    # For non-customers or if customer not yet identified:
    reporter_name = Column(String, nullable=True)
    reporter_email = Column(String, nullable=True, index=True)
    reporter_phone = Column(String, nullable=True, index=True)

    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False) # Initial problem description

    status = Column(SQLAlchemyEnum(TicketStatusEnum), default=TicketStatusEnum.OPEN, nullable=False, index=True)
    priority = Column(SQLAlchemyEnum(TicketPriorityEnum), default=TicketPriorityEnum.MEDIUM, nullable=False)
    channel_origin = Column(SQLAlchemyEnum(TicketChannelEnum), nullable=False)

    # category_id = Column(Integer, ForeignKey("ticket_categories.id"), nullable=True) # e.g. "Transaction Dispute", "Card Issue", "Account Inquiry"
    # sub_category_id = Column(Integer, ForeignKey("ticket_sub_categories.id"), nullable=True)

    # assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True) # Support agent
    # assigned_to_team_id = Column(Integer, ForeignKey("support_teams.id"), nullable=True, index=True) # Support team/queue

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # sla_due_date = Column(DateTime(timezone=True), nullable=True) # Service Level Agreement due date for resolution

    # Relationships
    # customer = relationship("Customer")
    # assigned_agent = relationship("User")
    # comments = relationship("TicketComment", back_populates="ticket", order_by="TicketComment.created_at")
    # attachments = relationship("TicketAttachment", back_populates="ticket")

    def __repr__(self):
        return f"<SupportTicket(ref='{self.ticket_reference}', status='{self.status.value}')>"

class TicketComment(Base):
    __tablename__ = "ticket_comments"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False, index=True)

    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Staff member who commented
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True) # If customer commented via portal
    commenter_name = Column(String, nullable=True) # Can be staff name or customer name
    commenter_type = Column(String, default="AGENT") # AGENT, CUSTOMER, SYSTEM

    comment_text = Column(Text, nullable=False)
    is_internal_note = Column(Boolean, default=False) # If true, not visible to customer

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ticket = relationship("SupportTicket", back_populates="comments")

class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False, index=True)
    # comment_id = Column(Integer, ForeignKey("ticket_comments.id"), nullable=True) # If attachment is part of a comment

    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False) # URL to stored file (e.g. S3)
    file_type = Column(String, nullable=True) # MIME type
    file_size_bytes = Column(Integer, nullable=True)

    # uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # uploaded_by_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # ticket = relationship("SupportTicket", back_populates="attachments")

class TicketCategory(Base): # For classifying tickets
    __tablename__ = "ticket_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    # parent_category_id = Column(Integer, ForeignKey("ticket_categories.id"), nullable=True) # For sub-categories

# --- Customer Notes & Logs (General CRM interaction log beyond tickets) ---
class CustomerInteractionLog(Base):
    __tablename__ = "customer_interaction_logs"
    id = Column(Integer, primary_key=True, index=True)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Staff member who logged interaction

    interaction_type = Column(String, nullable=False) # e.g., "PHONE_CALL_INBOUND", "EMAIL_SENT", "MEETING", "PROFILE_UPDATE_REQUEST"
    channel = Column(String, nullable=True) # e.g. "PHONE", "EMAIL", "BRANCH"
    subject = Column(String, nullable=True)
    notes = Column(Text, nullable=False)

    outcome = Column(String, nullable=True) # e.g. "RESOLVED", "NEEDS_FOLLOW_UP", "INFORMATION_PROVIDED"
    # follow_up_date = Column(DateTime(timezone=True), nullable=True)

    interacted_at = Column(DateTime(timezone=True), server_default=func.now())

    # customer = relationship("Customer")
    # user = relationship("User")

# --- Campaign Management (Simplified) ---
class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"
    id = Column(Integer, primary_key=True, index=True)
    campaign_name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    target_segment_criteria_json = Column(Text, nullable=True) # JSON defining customer segment
    communication_channel = Column(String) # e.g., "EMAIL", "SMS", "PUSH_NOTIFICATION_APP"
    # template_id = Column(String, nullable=True) # ID of message template to use

    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="DRAFT") # DRAFT, ACTIVE, COMPLETED, CANCELLED

    # created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CampaignAudienceLog(Base): # Tracks customers targeted by a campaign and their response
    __tablename__ = "campaign_audience_logs"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"), nullable=False, index=True)
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)

    sent_at = Column(DateTime(timezone=True), nullable=True) # When communication was sent
    status = Column(String, default="TARGETED") # TARGETED, SENT, DELIVERED, OPENED, CLICKED, CONVERTED, FAILED_SEND
    # response_details_json = Column(Text, nullable=True) # e.g. clicked_link, conversion_value

    # campaign = relationship("MarketingCampaign")
    # customer = relationship("Customer")

# Dispute Resolution Tracking is often part of SupportTicket, but if more specialized:
# class DisputeCase(Base):
#     __tablename__ = "dispute_cases"
#     id = Column(Integer, primary_key=True)
#     # ticket_id = Column(Integer, ForeignKey("support_tickets.id"), unique=True, nullable=True) # Link to a support ticket
#     # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=False)
#     # ... more fields specific to financial disputes, chargebacks, etc.

# SMS & Email Notifications are often logged in a generic NotificationLog (see digital_channels_modules)
# or specific logs if detailed delivery tracking per provider (Twilio, Mandrill) is needed here.
# For now, assuming a shared NotificationLog is sufficient.

# This module helps manage customer interactions, resolve issues, and run marketing campaigns.
# It relies heavily on customer data from CustomerIdentity and transaction data for context.
