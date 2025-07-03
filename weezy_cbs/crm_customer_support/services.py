import json
from typing import List, Optional, Type, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, or_, and_
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import uuid # For generating unique ticket numbers

from . import models, schemas
from weezy_cbs.core_infrastructure_config_engine.services import AuditLogService
# For type hinting and potential direct lookups (use with caution to avoid tight coupling)
# from weezy_cbs.customer_identity_management.models import Customer as CIMCustomer
# from weezy_cbs.core_infrastructure_config_engine.models import User as CoreUser
# from weezy_cbs.digital_channels_modules.models import DigitalUserProfile


# --- Helper for Ticket Number Generation ---
def generate_ticket_number() -> str:
    # Simple example: HD-YYYYMMDD-UUID_SHORT
    date_str = datetime.utcnow().strftime("%Y%m%d")
    uuid_short = str(uuid.uuid4()).split('-')[0][:4].upper()
    return f"HD-{date_str}-{uuid_short}"

# --- Base CRM Service (if needed) ---
class BaseCRMService:
    def _audit_log(self, db: Session, action: str, entity_type: str, entity_id: Any, summary: str = "", performing_user: str = "SYSTEM"):
        AuditLogService.create_audit_log_entry(
            db,
            username_performing_action=performing_user,
            action_type=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            summary=summary
        )

# --- SupportTicket Service ---
class SupportTicketService(BaseCRMService):
    def _get_ticket_query(self, db: Session):
        return db.query(models.SupportTicket).options(
            selectinload(models.SupportTicket.updates).joinedload(models.TicketUpdate.agent_user_id) # Example of loading related agent for updates
            # selectinload(models.SupportTicket.customer), # If you have Customer relationship defined and want to load it
            # selectinload(models.SupportTicket.assigned_agent) # If you have User relationship for assigned_agent
        )

    def create_ticket(self, db: Session, ticket_in: schemas.SupportTicketCreate, performing_user_id: Optional[int] = None, performing_username: str = "SYSTEM") -> models.SupportTicket:
        # Validate customer_id (ensure customer exists)
        # customer = db.query(CIMCustomer).filter(CIMCustomer.id == ticket_in.customer_id).first()
        # if not customer:
        #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer with ID {ticket_in.customer_id} not found.")

        # Validate digital_user_profile_id if provided
        # if ticket_in.digital_user_profile_id:
        #     profile = db.query(DigitalUserProfile).filter(DigitalUserProfile.id == ticket_in.digital_user_profile_id, DigitalUserProfile.customer_id == ticket_in.customer_id).first()
        #     if not profile:
        #         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Digital user profile ID does not match customer ID or not found.")

        ticket_number = generate_ticket_number()
        while db.query(models.SupportTicket).filter(models.SupportTicket.ticket_number == ticket_number).first():
            ticket_number = generate_ticket_number() # Ensure uniqueness

        db_ticket = models.SupportTicket(
            ticket_number=ticket_number,
            customer_id=ticket_in.customer_id,
            digital_user_profile_id=ticket_in.digital_user_profile_id,
            subject=ticket_in.subject,
            description=ticket_in.description,
            priority=ticket_in.priority,
            category=ticket_in.category,
            channel_of_origin=ticket_in.channel_of_origin or models.TicketChannelEnum.INTERNAL, # Default if not specified
            status=models.TicketStatusEnum.OPEN # Initial status
        )
        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)

        # Initial description as first update if needed (or handled by client)
        # self.add_ticket_update(db, ticket_id=db_ticket.id, update_in=schemas.TicketUpdateCreate(update_text=ticket_in.description), author_user_id=performing_user_id, author_username=performing_username, is_initial_desc=True)

        self._audit_log(db, "TICKET_CREATE", "SupportTicket", db_ticket.id, f"Ticket {ticket_number} created.", performing_username)
        return db_ticket

    def get_ticket_by_id(self, db: Session, ticket_id: int) -> Optional[models.SupportTicket]:
        return self._get_ticket_query(db).filter(models.SupportTicket.id == ticket_id).first()

    def get_ticket_by_number(self, db: Session, ticket_number: str) -> Optional[models.SupportTicket]:
        return self._get_ticket_query(db).filter(models.SupportTicket.ticket_number == ticket_number).first()

    def get_tickets_for_customer(self, db: Session, customer_id: int, skip: int = 0, limit: int = 100) -> Tuple[List[models.SupportTicket], int]:
        query = self._get_ticket_query(db).filter(models.SupportTicket.customer_id == customer_id)
        total = query.count()
        tickets = query.order_by(models.SupportTicket.updated_at.desc()).offset(skip).limit(limit).all()
        return tickets, total

    def search_tickets(
        self, db: Session,
        status: Optional[models.TicketStatusEnum] = None,
        priority: Optional[models.TicketPriorityEnum] = None,
        category: Optional[models.TicketCategoryEnum] = None,
        assigned_to_user_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        search_term: Optional[str] = None, # Search in subject/description
        skip: int = 0, limit: int = 100
    ) -> Tuple[List[models.SupportTicket], int]:
        query = self._get_ticket_query(db)
        if status: query = query.filter(models.SupportTicket.status == status)
        if priority: query = query.filter(models.SupportTicket.priority == priority)
        if category: query = query.filter(models.SupportTicket.category == category)
        if assigned_to_user_id: query = query.filter(models.SupportTicket.assigned_to_user_id == assigned_to_user_id)
        if customer_id: query = query.filter(models.SupportTicket.customer_id == customer_id)
        if search_term:
            query = query.filter(
                or_(
                    models.SupportTicket.subject.ilike(f"%{search_term}%"),
                    models.SupportTicket.description.ilike(f"%{search_term}%"),
                    models.SupportTicket.ticket_number.ilike(f"%{search_term}%")
                )
            )

        total = query.count()
        tickets = query.order_by(models.SupportTicket.updated_at.desc()).offset(skip).limit(limit).all()
        return tickets, total

    def update_ticket_details(self, db: Session, ticket_id: int, update_in: schemas.SupportTicketUpdateSchema, performing_agent_id: int, performing_username: str) -> Optional[models.SupportTicket]:
        db_ticket = self.get_ticket_by_id(db, ticket_id)
        if not db_ticket:
            return None

        update_data = update_in.dict(exclude_unset=True)
        changed_fields = []

        for field, value in update_data.items():
            if hasattr(db_ticket, field) and getattr(db_ticket, field) != value:
                setattr(db_ticket, field, value)
                changed_fields.append(field)

        if not changed_fields: # No actual changes
            return db_ticket

        # Handle status changes specifically for timestamps
        if "status" in changed_fields:
            if db_ticket.status == models.TicketStatusEnum.RESOLVED and not db_ticket.resolved_at:
                db_ticket.resolved_at = datetime.utcnow()
            elif db_ticket.status == models.TicketStatusEnum.CLOSED and not db_ticket.closed_at:
                db_ticket.closed_at = datetime.utcnow()
                if not db_ticket.resolved_at: # If closed directly from non-resolved
                    db_ticket.resolved_at = datetime.utcnow()

        db_ticket.updated_at = datetime.utcnow() # Explicitly update timestamp
        db.commit()
        db.refresh(db_ticket)

        summary = f"Ticket {db_ticket.ticket_number} details updated by agent {performing_username}. Changes: {', '.join(changed_fields)}."
        self._audit_log(db, "TICKET_UPDATE_DETAILS", "SupportTicket", db_ticket.id, summary, performing_username)
        return db_ticket

    def add_ticket_update(self, db: Session, ticket_id: int, update_in: schemas.TicketUpdateCreate,
                          author_agent_id: Optional[int] = None, # Agent adding the update
                          performing_username: str = "SYSTEM" # Username for audit log
                          ) -> Optional[models.TicketUpdate]:
        db_ticket = self.get_ticket_by_id(db, ticket_id)
        if not db_ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

        # Validate agent_user_id if provided
        # if author_agent_id:
        #     agent = db.query(CoreUser).filter(CoreUser.id == author_agent_id).first()
        #     if not agent:
        #         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent user with ID {author_agent_id} not found.")


        db_update = models.TicketUpdate(
            ticket_id=ticket_id,
            update_text=update_in.update_text,
            is_internal_note=update_in.is_internal_note,
            agent_user_id=author_agent_id,
            # attachments_json = json.dumps(update_in.attachments_json) if update_in.attachments_json else None
        )
        db.add(db_update)

        # Update ticket's main updated_at timestamp
        db_ticket.updated_at = datetime.utcnow()
        # If an agent adds a non-internal note, and ticket was PENDING_AGENT, it might change status
        if author_agent_id and not update_in.is_internal_note and db_ticket.status == models.TicketStatusEnum.PENDING_AGENT:
            db_ticket.status = models.TicketStatusEnum.PENDING_CUSTOMER # Or IN_PROGRESS if agent is working on it

        db.commit()
        db.refresh(db_update)
        db.refresh(db_ticket) # Refresh ticket to get updated 'updated_at'

        action_summary = "internal note added" if update_in.is_internal_note else "reply added"
        self._audit_log(db, "TICKET_ADD_UPDATE", "SupportTicket", db_ticket.id, f"Ticket {db_ticket.ticket_number}: {action_summary} by {performing_username}.", performing_username)
        return db_update

# --- CustomerNote Service ---
class CustomerNoteService(BaseCRMService):
    def create_customer_note(self, db: Session, note_in: schemas.CustomerNoteCreate, agent_user_id: int, performing_username: str) -> models.CustomerNote:
        # Validate customer_id and agent_user_id
        # ... (similar checks as in create_ticket) ...

        db_note = models.CustomerNote(
            **note_in.dict(),
            agent_user_id=agent_user_id
        )
        db.add(db_note)
        db.commit()
        db.refresh(db_note)
        self._audit_log(db, "CUSTOMER_NOTE_CREATE", "CustomerNote", db_note.id, f"Note created for customer ID {note_in.customer_id}.", performing_username)
        return db_note

    def get_notes_for_customer(self, db: Session, customer_id: int, skip: int = 0, limit: int = 100) -> Tuple[List[models.CustomerNote], int]:
        query = db.query(models.CustomerNote).filter(models.CustomerNote.customer_id == customer_id)
        total = query.count()
        notes = query.order_by(models.CustomerNote.created_at.desc()).offset(skip).limit(limit).all()
        return notes, total

    def get_note_by_id(self, db: Session, note_id: int) -> Optional[models.CustomerNote]:
        return db.query(models.CustomerNote).filter(models.CustomerNote.id == note_id).first()

    def update_customer_note(self, db: Session, note_id: int, note_in: schemas.CustomerNoteBase, agent_user_id: int, performing_username: str) -> Optional[models.CustomerNote]:
        db_note = self.get_note_by_id(db, note_id)
        if not db_note: return None
        # Optional: Check if agent_user_id matches db_note.agent_user_id for permission

        db_note.note_text = note_in.note_text
        db_note.category = note_in.category
        db_note.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_note)
        self._audit_log(db, "CUSTOMER_NOTE_UPDATE", "CustomerNote", db_note.id, f"Note ID {db_note.id} updated.", performing_username)
        return db_note

    def delete_customer_note(self, db: Session, note_id: int, agent_user_id: int, performing_username: str) -> bool:
        db_note = self.get_note_by_id(db, note_id)
        if not db_note: return False
        # Optional: Check ownership or permissions

        customer_id = db_note.customer_id # For audit log
        db.delete(db_note)
        db.commit()
        self._audit_log(db, "CUSTOMER_NOTE_DELETE", "CustomerNote", note_id, f"Note ID {note_id} for customer ID {customer_id} deleted.", performing_username)
        return True


# --- FAQItem Service ---
class FAQItemService(BaseCRMService):
    def create_faq_item(self, db: Session, faq_in: schemas.FAQItemCreate, created_by_user_id: int, performing_username: str) -> models.FAQItem:
        db_faq = models.FAQItem(
            **faq_in.dict(exclude_unset=True, exclude={"tags_json"}), # Pydantic handles tags_json conversion
            tags_json=json.dumps(faq_in.tags_json) if faq_in.tags_json else None,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=created_by_user_id
        )
        db.add(db_faq)
        db.commit()
        db.refresh(db_faq)
        self._audit_log(db, "FAQ_CREATE", "FAQItem", db_faq.id, f"FAQ '{db_faq.question[:30]}...' created.", performing_username)
        return db_faq

    def get_faq_item_by_id(self, db: Session, faq_id: int) -> Optional[models.FAQItem]:
        return db.query(models.FAQItem).filter(models.FAQItem.id == faq_id).first()

    def update_faq_item(self, db: Session, faq_id: int, faq_in: schemas.FAQItemUpdateSchema, updated_by_user_id: int, performing_username: str) -> Optional[models.FAQItem]:
        db_faq = self.get_faq_item_by_id(db, faq_id)
        if not db_faq: return None

        update_data = faq_in.dict(exclude_unset=True)
        if "tags_json" in update_data and update_data["tags_json"] is not None:
            db_faq.tags_json = json.dumps(update_data.pop("tags_json"))

        for field, value in update_data.items():
            setattr(db_faq, field, value)

        db_faq.updated_by_user_id = updated_by_user_id
        db_faq.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_faq)
        self._audit_log(db, "FAQ_UPDATE", "FAQItem", db_faq.id, f"FAQ ID {db_faq.id} updated.", performing_username)
        return db_faq

    def delete_faq_item(self, db: Session, faq_id: int, performing_username: str) -> bool:
        db_faq = self.get_faq_item_by_id(db, faq_id)
        if not db_faq: return False
        db.delete(db_faq)
        db.commit()
        self._audit_log(db, "FAQ_DELETE", "FAQItem", faq_id, f"FAQ ID {faq_id} deleted.", performing_username)
        return True

    def search_faq_items(self, db: Session, query: Optional[str] = None, category: Optional[str] = None, published_only: bool = True, skip: int = 0, limit: int = 100) -> Tuple[List[models.FAQItem], int]:
        q = db.query(models.FAQItem)
        if published_only:
            q = q.filter(models.FAQItem.is_published == True)
        if category:
            q = q.filter(models.FAQItem.category.ilike(f"%{category}%"))
        if query:
            # Basic search in question, answer, and tags (if stored as searchable text or after JSON parsing in DB if supported)
            # For JSON search, specific DB functions are needed (e.g., for PostgreSQL jsonb_path_exists or @@)
            # Simple ilike on tags_json might work if tags are simple strings without too much JSON noise.
            search_filter = or_(
                models.FAQItem.question.ilike(f"%{query}%"),
                models.FAQItem.answer.ilike(f"%{query}%"),
                models.FAQItem.tags_json.ilike(f"%{query}%")
            )
            q = q.filter(search_filter)

        total = q.count()
        faqs = q.order_by(models.FAQItem.category, models.FAQItem.question).offset(skip).limit(limit).all()
        return faqs, total

    def increment_faq_view_count(self, db: Session, faq_id: int) -> Optional[models.FAQItem]:
        db_faq = self.get_faq_item_by_id(db, faq_id)
        if db_faq:
            db_faq.view_count = (db_faq.view_count or 0) + 1
            db.commit()
            db.refresh(db_faq)
        return db_faq

# --- Campaign Service (Conceptual for execution) ---
class CampaignService(BaseCRMService):
    def create_campaign(self, db: Session, campaign_in: schemas.CampaignCreate, created_by_user_id: int, performing_username: str) -> models.Campaign:
        db_campaign = models.Campaign(
            **campaign_in.dict(exclude_unset=True, exclude={"target_audience_rules_json"}),
            target_audience_rules_json=json.dumps(campaign_in.target_audience_rules_json) if campaign_in.target_audience_rules_json else None,
            created_by_user_id=created_by_user_id
        )
        db.add(db_campaign)
        db.commit()
        db.refresh(db_campaign)
        self._audit_log(db, "CAMPAIGN_CREATE", "Campaign", db_campaign.id, f"Campaign '{db_campaign.campaign_name}' created.", performing_username)
        return db_campaign

    def get_campaign_by_id(self, db: Session, campaign_id: int) -> Optional[models.Campaign]:
        return db.query(models.Campaign).options(selectinload(models.Campaign.logs)).filter(models.Campaign.id == campaign_id).first()

    def update_campaign(self, db: Session, campaign_id: int, campaign_in: schemas.CampaignUpdateSchema, performing_username: str) -> Optional[models.Campaign]:
        db_campaign = self.get_campaign_by_id(db, campaign_id)
        if not db_campaign: return None
        if db_campaign.status not in [models.CampaignStatusEnum.DRAFT, models.CampaignStatusEnum.SCHEDULED, models.CampaignStatusEnum.PAUSED]: # Only allow updates in certain states
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campaign in status {db_campaign.status.value} cannot be updated.")

        update_data = campaign_in.dict(exclude_unset=True)
        if "target_audience_rules_json" in update_data and update_data["target_audience_rules_json"] is not None:
            db_campaign.target_audience_rules_json = json.dumps(update_data.pop("target_audience_rules_json"))

        for field, value in update_data.items():
            setattr(db_campaign, field, value)

        db_campaign.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_campaign)
        self._audit_log(db, "CAMPAIGN_UPDATE", "Campaign", db_campaign.id, f"Campaign '{db_campaign.campaign_name}' updated.", performing_username)
        return db_campaign

    def get_campaigns(self, db: Session, skip: int = 0, limit: int = 100) -> Tuple[List[models.Campaign], int]:
        query = db.query(models.Campaign)
        total = query.count()
        campaigns = query.order_by(models.Campaign.created_at.desc()).offset(skip).limit(limit).all()
        return campaigns, total

    def get_campaign_logs(self, db: Session, campaign_id: int, skip: int = 0, limit: int = 100) -> Tuple[List[models.CampaignLog], int]:
        query = db.query(models.CampaignLog).filter(models.CampaignLog.campaign_id == campaign_id)
        total = query.count()
        logs = query.order_by(models.CampaignLog.processed_at.desc()).offset(skip).limit(limit).all()
        return logs, total

    def launch_campaign(self, db: Session, campaign_id: int, performing_username: str) -> bool:
        """
        Conceptual: Changes campaign status to ACTIVE/SCHEDULED.
        Actual execution (finding audience, sending messages) would be a background task.
        """
        db_campaign = self.get_campaign_by_id(db, campaign_id)
        if not db_campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
        if db_campaign.status not in [models.CampaignStatusEnum.DRAFT, models.CampaignStatusEnum.SCHEDULED, models.CampaignStatusEnum.PAUSED]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campaign cannot be launched from status {db_campaign.status.value}.")

        # If scheduled and start_date is future, status becomes SCHEDULED. If start_date is now/past, becomes ACTIVE.
        if db_campaign.start_date and db_campaign.start_date > datetime.utcnow():
            db_campaign.status = models.CampaignStatusEnum.SCHEDULED
        else:
            db_campaign.status = models.CampaignStatusEnum.ACTIVE
            # Placeholder: Trigger background task to process audience and send messages
            # self._process_and_send_campaign_messages(db, db_campaign)
            print(f"SIMULATING: Campaign '{db_campaign.campaign_name}' (ID: {db_campaign.id}) messages would be processed and sent now.")
            # This would involve:
            # 1. Parsing db_campaign.target_audience_rules_json
            # 2. Querying Customer table based on these rules (e.g. using a generic customer search service)
            # 3. For each targeted customer:
            #    a. Create a CampaignLog entry (status PENDING_SEND or TARGETED)
            #    b. (Async) Send message via NotificationService (digital_channels) using campaign_channel and message content.
            #    c. Update CampaignLog status based on send attempt (SENT, FAILED).

        db.commit()
        db.refresh(db_campaign)
        self._audit_log(db, "CAMPAIGN_LAUNCH", "Campaign", db_campaign.id, f"Campaign '{db_campaign.campaign_name}' status set to {db_campaign.status.value}.", performing_username)
        return True


# Instantiate services
support_ticket_service = SupportTicketService()
customer_note_service = CustomerNoteService()
faq_item_service = FAQItemService()
campaign_service = CampaignService()
