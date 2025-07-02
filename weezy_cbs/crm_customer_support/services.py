# Service layer for CRM & Customer Support Module
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from . import models, schemas
from .models import TicketStatusEnum, TicketPriorityEnum, TicketChannelEnum # Direct enum access
import uuid
from datetime import datetime

# Placeholder for other service integrations & data sources
# from weezy_cbs.customer_identity_management.services import get_customer_by_id, get_customer_by_email_or_phone
# from weezy_cbs.core_infrastructure_config_engine.services import get_user # For support agents
# from weezy_cbs.integrations import email_service, sms_service # For notifications
# from weezy_cbs.shared import exceptions

class NotFoundException(Exception): pass
class InvalidOperationException(Exception): pass

def _generate_ticket_reference(prefix="WZYSPT"):
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

# --- Support Ticket Services ---
def create_support_ticket(db: Session, ticket_in: schemas.SupportTicketCreateRequest, customer_id: Optional[int] = None, user_id_creator: Optional[int] = None) -> models.SupportTicket:
    # If customer_id is not provided, try to find customer by reporter_email or reporter_phone
    # if not customer_id and (ticket_in.reporter_email or ticket_in.reporter_phone):
    #     customer = get_customer_by_email_or_phone(db, email=ticket_in.reporter_email, phone=ticket_in.reporter_phone)
    #     if customer: customer_id = customer.id

    ticket_ref = _generate_ticket_reference()
    db_ticket = models.SupportTicket(
        ticket_reference=ticket_ref,
        customer_id=customer_id, # May be None if reporter not a known customer
        # created_by_user_id = user_id_creator, # If logged by staff
        **ticket_in.dict()
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)

    # TODO: Send acknowledgement notification to reporter
    # if ticket_in.reporter_email:
    #    email_service.send_email(ticket_in.reporter_email, "Support Ticket Created: " + ticket_ref, f"Your ticket '{ticket_in.subject}' has been received...")

    # TODO: Assign to a default queue/agent based on category/channel
    return db_ticket

def get_support_ticket(db: Session, ticket_id: Optional[int] = None, reference: Optional[str] = None) -> Optional[models.SupportTicket]:
    if ticket_id:
        # return db.query(models.SupportTicket).options(joinedload(models.SupportTicket.comments), joinedload(models.SupportTicket.attachments)).filter(models.SupportTicket.id == ticket_id).first()
        return db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first() # Simpler for now
    if reference:
        return db.query(models.SupportTicket).filter(models.SupportTicket.ticket_reference == reference).first()
    return None

def update_support_ticket(db: Session, ticket_id: int, update_in: schemas.SupportTicketUpdateRequest, agent_user_id: int) -> models.SupportTicket:
    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).with_for_update().first()
    if not ticket:
        raise NotFoundException(f"Support ticket {ticket_id} not found.")

    # Store old status for audit/notification if it changes
    # old_status = ticket.status
    update_data = update_in.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(ticket, key, value)

    # If status changed to RESOLVED or CLOSED, set corresponding dates
    if update_in.status and update_in.status in [TicketStatusEnum.RESOLVED, TicketStatusEnum.CLOSED]:
        if update_in.status == TicketStatusEnum.RESOLVED and not ticket.resolved_at:
            ticket.resolved_at = datetime.utcnow()
        if update_in.status == TicketStatusEnum.CLOSED and not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()
            if not ticket.resolved_at: ticket.resolved_at = datetime.utcnow() # Close also implies resolved

    # ticket.last_updated_by_user_id = agent_user_id
    ticket.updated_at = datetime.utcnow() # Ensure updated_at is set

    db.commit()
    db.refresh(ticket)

    # TODO: If status changed, notify customer/reporter.
    # if old_status != ticket.status:
    #    notify_customer_of_ticket_update(db, ticket, old_status)
    return ticket

def get_tickets_for_customer(db: Session, customer_id: int, skip: int = 0, limit: int = 20) -> List[models.SupportTicket]:
    return db.query(models.SupportTicket).filter(models.SupportTicket.customer_id == customer_id).order_by(models.SupportTicket.updated_at.desc()).offset(skip).limit(limit).all()

def get_tickets_assigned_to_agent(db: Session, agent_user_id: int, status: Optional[TicketStatusEnum] = None, skip: int = 0, limit: int = 20) -> List[models.SupportTicket]:
    query = db.query(models.SupportTicket).filter(models.SupportTicket.assigned_to_user_id == agent_user_id)
    if status:
        query = query.filter(models.SupportTicket.status == status)
    else: # Default to non-closed tickets
        query = query.filter(models.SupportTicket.status.notin_([TicketStatusEnum.RESOLVED, TicketStatusEnum.CLOSED]))
    return query.order_by(models.SupportTicket.priority.desc(), models.SupportTicket.updated_at.asc()).offset(skip).limit(limit).all()


# --- Ticket Comment Services ---
def add_ticket_comment(db: Session, comment_in: schemas.TicketCommentCreateRequest, ticket_id: int, commenter_id: int, commenter_type: str, commenter_name: Optional[str]=None) -> models.TicketComment:
    ticket = get_support_ticket(db, ticket_id=ticket_id)
    if not ticket:
        raise NotFoundException(f"Ticket {ticket_id} not found for adding comment.")

    db_comment = models.TicketComment(
        ticket_id=ticket_id,
        commenter_type=commenter_type.upper(), # AGENT, CUSTOMER, SYSTEM
        commenter_name=commenter_name, # Can be agent's name or customer's name
        **comment_in.dict()
    )
    if commenter_type.upper() == "AGENT":
        # db_comment.user_id = commenter_id
        pass # In a real app, set user_id
    elif commenter_type.upper() == "CUSTOMER":
        # db_comment.customer_id = commenter_id
        pass # In a real app, set customer_id

    db.add(db_comment)

    # Update ticket's updated_at timestamp and potentially status (e.g., if customer replied, move to PENDING_AGENT_RESPONSE)
    ticket.updated_at = datetime.utcnow()
    # if commenter_type.upper() == "CUSTOMER" and ticket.status == TicketStatusEnum.PENDING_CUSTOMER_RESPONSE:
    #     ticket.status = TicketStatusEnum.PENDING_AGENT_RESPONSE
    # elif commenter_type.upper() == "AGENT" and ticket.status == TicketStatusEnum.PENDING_AGENT_RESPONSE:
    #     # If agent is replying to customer, maybe it becomes PENDING_CUSTOMER_RESPONSE again, or stays PENDING_AGENT if more work needed
    #     pass

    db.commit()
    db.refresh(db_comment)
    db.refresh(ticket) # To get updated 'updated_at'

    # TODO: Notify relevant parties about the new comment
    # if commenter_type.upper() == "AGENT" and not comment_in.is_internal_note:
    #     notify_customer_of_new_comment(db, ticket, db_comment)
    # elif commenter_type.upper() == "CUSTOMER" and ticket.assigned_to_user_id:
    #     notify_agent_of_new_comment(db, ticket, db_comment)
    return db_comment

# --- Ticket Attachment Services (Conceptual: file storage is external) ---
def add_ticket_attachment(db: Session, attachment_in: schemas.TicketAttachmentCreateRequest, ticket_id: int, uploader_id: int, uploader_type: str) -> models.TicketAttachment:
    # Verify ticket exists
    # ...
    db_attachment = models.TicketAttachment(
        ticket_id=ticket_id,
        # uploaded_by_user_id = uploader_id if uploader_type == "AGENT" else None,
        # uploaded_by_customer_id = uploader_id if uploader_type == "CUSTOMER" else None,
        **attachment_in.dict()
    )
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment

# --- Customer Interaction Log Services ---
def log_customer_interaction(db: Session, log_in: schemas.CustomerInteractionLogCreateRequest, customer_id: int, user_id_staff: Optional[int] = None) -> models.CustomerInteractionLog:
    # customer = get_customer_by_id(db, customer_id)
    # if not customer: raise NotFoundException("Customer not found for interaction logging.")

    db_log = models.CustomerInteractionLog(
        customer_id=customer_id,
        # user_id=user_id_staff,
        **log_in.dict()
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_interactions_for_customer(db: Session, customer_id: int, skip: int = 0, limit: int = 20) -> List[models.CustomerInteractionLog]:
    return db.query(models.CustomerInteractionLog).filter(models.CustomerInteractionLog.customer_id == customer_id).order_by(models.CustomerInteractionLog.interacted_at.desc()).offset(skip).limit(limit).all()

# --- Marketing Campaign Services (Admin/Marketing User) ---
def create_marketing_campaign(db: Session, campaign_in: schemas.MarketingCampaignCreateRequest, created_by_user_id: int) -> models.MarketingCampaign:
    db_campaign = models.MarketingCampaign(
        # created_by_user_id=created_by_user_id,
        **campaign_in.dict()
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign

def launch_marketing_campaign(db: Session, campaign_id: int):
    campaign = db.query(models.MarketingCampaign).filter(models.MarketingCampaign.id == campaign_id).with_for_update().first()
    if not campaign: raise NotFoundException("Campaign not found.")
    if campaign.status != "DRAFT": raise InvalidOperationException("Campaign not in DRAFT status.")

    # 1. Identify target audience based on campaign.target_segment_criteria_json
    # target_customers = find_customers_matching_criteria(db, json.loads(campaign.target_segment_criteria_json))
    target_customers_mock = [{"id": 1, "email": "cust1@example.com", "phone": "0801"}, {"id": 2, "email": "cust2@example.com", "phone": "0802"}] # Mock

    # 2. For each target customer, log in CampaignAudienceLog and send communication
    for cust_data in target_customers_mock:
        audience_log = models.CampaignAudienceLog(
            campaign_id=campaign.id,
            customer_id=cust_data["id"],
            status="TARGETED"
        )
        db.add(audience_log)
        # try:
            # message_content = render_template(campaign.template_id, customer_data=cust_data)
            # if campaign.communication_channel == "EMAIL":
            #     email_service.send_email(cust_data["email"], campaign.campaign_name, message_content)
            # elif campaign.communication_channel == "SMS":
            #     sms_service.send_sms(cust_data["phone"], message_content)
            # audience_log.status = "SENT"
            # audience_log.sent_at = datetime.utcnow()
        # except Exception as e:
            # audience_log.status = "FAILED_SEND"
            # Log error
            pass

    campaign.status = "ACTIVE" # Or "SENDING_IN_PROGRESS" if async
    db.commit()
    # Potentially return status of launch (e.g. number of messages queued)

# --- Ticket Category Services (Admin) ---
def create_ticket_category(db: Session, category_in: schemas.TicketCategoryCreateRequest) -> models.TicketCategory:
    db_category = models.TicketCategory(**category_in.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def get_ticket_categories(db: Session) -> List[models.TicketCategory]:
    return db.query(models.TicketCategory).order_by(models.TicketCategory.name).all()

# This module's services would be called by:
# - Digital Channel APIs (e.g., when a customer submits a support request via mobile app).
# - Internal Admin/Agent dashboards for managing tickets, campaigns.
# - Automated processes (e.g., for escalating overdue tickets, sending campaign messages).
# It requires integration with notification services (Email, SMS, Push) and potentially customer identity for context.

# Import any necessary helper for pagination or specific model queries
from sqlalchemy.orm import joinedload # For eager loading related data if needed.
# Example: db.query(models.SupportTicket).options(joinedload(models.SupportTicket.customer)).filter(...)
# This helps avoid N+1 query problems when accessing related objects like ticket.customer.name.
# For now, most queries are simple. Complex responses (like SupportTicketDetailResponse) would benefit from this.
