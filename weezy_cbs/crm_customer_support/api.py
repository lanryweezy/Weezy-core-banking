from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from weezy_cbs.database import get_db
from . import schemas, services, models
from .services import (
    support_ticket_service, customer_note_service, faq_item_service, campaign_service
)
# Assuming an authentication dependency from core_infrastructure_config_engine
from weezy_cbs.core_infrastructure_config_engine.api import get_current_active_superuser, get_performing_user_username
from weezy_cbs.core_infrastructure_config_engine.models import User as CoreUser # For type hint

# Main router for CRM & Customer Support
crm_api_router = APIRouter(
    prefix="/crm",
    tags=["CRM & Customer Support"],
    dependencies=[Depends(get_current_active_superuser)] # Most CRM ops require authenticated staff
)

# --- SupportTicket Endpoints ---
tickets_router = APIRouter(prefix="/tickets", tags=["Support Tickets"])

@tickets_router.post("/", response_model=schemas.SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_support_ticket_endpoint(
    ticket_in: schemas.SupportTicketCreate,
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser) # Agent creating ticket or on behalf of customer
):
    # If channel_of_origin isn't provided, and agent is creating, it might be INTERNAL or based on context
    if not ticket_in.channel_of_origin:
        ticket_in.channel_of_origin = models.TicketChannelEnum.INTERNAL

    return support_ticket_service.create_ticket(
        db=db, ticket_in=ticket_in,
        performing_user_id=current_agent.id,
        performing_username=current_agent.username
    )

@tickets_router.get("/{ticket_id}", response_model=schemas.SupportTicketResponse)
async def read_support_ticket_endpoint(ticket_id: int, db: Session = Depends(get_db)):
    db_ticket = support_ticket_service.get_ticket_by_id(db, ticket_id)
    if db_ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support Ticket not found")
    return db_ticket

@tickets_router.get("/number/{ticket_number}", response_model=schemas.SupportTicketResponse)
async def read_support_ticket_by_number_endpoint(ticket_number: str, db: Session = Depends(get_db)):
    db_ticket = support_ticket_service.get_ticket_by_number(db, ticket_number)
    if db_ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support Ticket not found")
    return db_ticket


@tickets_router.get("/", response_model=schemas.PaginatedSupportTicketResponse)
async def search_support_tickets_endpoint(
    status: Optional[models.TicketStatusEnum] = None,
    priority: Optional[models.TicketPriorityEnum] = None,
    category: Optional[models.TicketCategoryEnum] = None,
    assigned_to_user_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    search_term: Optional[str] = None,
    skip: int = 0, limit: int = 20, # Default limit to 20 for tickets
    db: Session = Depends(get_db)
):
    tickets, total = support_ticket_service.search_tickets(
        db, status=status, priority=priority, category=category,
        assigned_to_user_id=assigned_to_user_id, customer_id=customer_id,
        search_term=search_term, skip=skip, limit=limit
    )
    return {"items": tickets, "total": total, "page": (skip // limit) + 1, "size": limit}

@tickets_router.put("/{ticket_id}", response_model=schemas.SupportTicketResponse)
async def update_support_ticket_endpoint(
    ticket_id: int,
    ticket_update_in: schemas.SupportTicketUpdateSchema,
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    updated_ticket = support_ticket_service.update_ticket_details(
        db, ticket_id=ticket_id, update_in=ticket_update_in,
        performing_agent_id=current_agent.id,
        performing_username=current_agent.username
    )
    if updated_ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support Ticket not found")
    return updated_ticket

@tickets_router.post("/{ticket_id}/updates", response_model=schemas.TicketUpdateResponse, status_code=status.HTTP_201_CREATED)
async def add_ticket_update_endpoint(
    ticket_id: int,
    update_in: schemas.TicketUpdateCreate,
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    # performing_username for audit log is current_agent.username
    new_update = support_ticket_service.add_ticket_update(
        db, ticket_id=ticket_id, update_in=update_in,
        author_agent_id=current_agent.id,
        performing_username=current_agent.username
    )
    if not new_update: # Should be handled by HTTPException in service if ticket not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failed to add update or ticket not found.")
    return new_update

# --- CustomerNote Endpoints ---
# Nested under /customers/{customer_id}/notes for clear association
# but also direct /notes/{note_id} for specific note operations by ID.

customer_notes_router = APIRouter(tags=["Customer Notes"])

@customer_notes_router.post("/customers/{customer_id}/notes", response_model=schemas.CustomerNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_note_for_customer_endpoint(
    customer_id: int,
    note_in: schemas.CustomerNoteCreate, # customer_id in body should match path param or be ignored
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    if note_in.customer_id != customer_id: # Ensure consistency
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer ID in path and body mismatch.")
    return customer_note_service.create_customer_note(
        db, note_in=note_in, agent_user_id=current_agent.id, performing_username=current_agent.username
    )

@customer_notes_router.get("/customers/{customer_id}/notes", response_model=schemas.PaginatedCustomerNoteResponse)
async def list_notes_for_customer_endpoint(
    customer_id: int,
    skip: int = 0, limit: int = 20,
    db: Session = Depends(get_db)
):
    notes, total = customer_note_service.get_notes_for_customer(db, customer_id=customer_id, skip=skip, limit=limit)
    return {"items": notes, "total": total, "page": (skip // limit) + 1, "size": limit}

@customer_notes_router.put("/notes/{note_id}", response_model=schemas.CustomerNoteResponse)
async def update_customer_note_endpoint(
    note_id: int,
    note_in: schemas.CustomerNoteBase, # Base schema for update, customer_id not changed here
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    updated_note = customer_note_service.update_customer_note(
        db, note_id=note_id, note_in=note_in, agent_user_id=current_agent.id, performing_username=current_agent.username
    )
    if not updated_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer Note not found.")
    return updated_note

@customer_notes_router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer_note_endpoint(
    note_id: int,
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    if not customer_note_service.delete_customer_note(db, note_id=note_id, agent_user_id=current_agent.id, performing_username=current_agent.username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer Note not found.")
    return None

# --- FAQItem Endpoints ---
# Public router for GET, protected for CUD
faq_public_router = APIRouter(prefix="/faqs", tags=["FAQ (Public)"])
faq_admin_router = APIRouter(prefix="/admin/faqs", tags=["FAQ (Admin)"], dependencies=[Depends(get_current_active_superuser)])

@faq_admin_router.post("/", response_model=schemas.FAQItemResponse, status_code=status.HTTP_201_CREATED)
async def create_faq_item_endpoint(
    faq_in: schemas.FAQItemCreate,
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    return faq_item_service.create_faq_item(
        db, faq_in=faq_in, created_by_user_id=current_agent.id, performing_username=current_agent.username
    )

@faq_public_router.get("/", response_model=schemas.PaginatedFAQItemResponse)
async def search_faq_items_endpoint(
    query: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0, limit: int = 20,
    db: Session = Depends(get_db)
):
    faqs, total = faq_item_service.search_faq_items(db, query=query, category=category, published_only=True, skip=skip, limit=limit)
    return {"items": faqs, "total": total, "page": (skip // limit) + 1, "size": limit}

@faq_public_router.get("/{faq_id}", response_model=schemas.FAQItemResponse)
async def read_faq_item_endpoint(faq_id: int, db: Session = Depends(get_db)):
    db_faq = faq_item_service.get_faq_item_by_id(db, faq_id)
    if not db_faq or not db_faq.is_published: # Only show published FAQs to public
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ Item not found or not published.")
    # Consider incrementing view count here if it's a public view
    # faq_item_service.increment_faq_view_count(db, faq_id) # This might cause write on GET, often handled async
    return db_faq

@faq_public_router.post("/{faq_id}/view", status_code=status.HTTP_204_NO_CONTENT, summary="Increment view count for an FAQ item")
async def increment_faq_view_count_endpoint(faq_id: int, db: Session = Depends(get_db)):
    if not faq_item_service.increment_faq_view_count(db, faq_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ Item not found.")
    return None


@faq_admin_router.put("/{faq_id}", response_model=schemas.FAQItemResponse)
async def update_faq_item_endpoint(
    faq_id: int,
    faq_in: schemas.FAQItemUpdateSchema,
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    updated_faq = faq_item_service.update_faq_item(
        db, faq_id=faq_id, faq_in=faq_in, updated_by_user_id=current_agent.id, performing_username=current_agent.username
    )
    if not updated_faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ Item not found.")
    return updated_faq

@faq_admin_router.delete("/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq_item_endpoint(
    faq_id: int,
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    if not faq_item_service.delete_faq_item(db, faq_id=faq_id, performing_username=current_agent.username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ Item not found.")
    return None

# --- Campaign Endpoints ---
campaigns_router = APIRouter(prefix="/campaigns", tags=["Marketing Campaigns"], dependencies=[Depends(get_current_active_superuser)])

@campaigns_router.post("/", response_model=schemas.CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign_endpoint(
    campaign_in: schemas.CampaignCreate,
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    return campaign_service.create_campaign(
        db, campaign_in=campaign_in, created_by_user_id=current_agent.id, performing_username=current_agent.username
    )

@campaigns_router.get("/", response_model=schemas.PaginatedCampaignResponse)
async def list_campaigns_endpoint(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    campaigns, total = campaign_service.get_campaigns(db, skip=skip, limit=limit)
    return {"items": campaigns, "total": total, "page": (skip // limit) + 1, "size": limit}

@campaigns_router.get("/{campaign_id}", response_model=schemas.CampaignResponse)
async def read_campaign_endpoint(campaign_id: int, db: Session = Depends(get_db)):
    db_campaign = campaign_service.get_campaign_by_id(db, campaign_id)
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    return db_campaign

@campaigns_router.put("/{campaign_id}", response_model=schemas.CampaignResponse)
async def update_campaign_endpoint(
    campaign_id: int,
    campaign_in: schemas.CampaignUpdateSchema,
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    updated_campaign = campaign_service.update_campaign(
        db, campaign_id=campaign_id, campaign_in=campaign_in, performing_username=current_agent.username
    )
    if not updated_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found or cannot be updated.")
    return updated_campaign

@campaigns_router.post("/{campaign_id}/launch", summary="Launch or schedule a campaign")
async def launch_campaign_endpoint(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_agent: CoreUser = Depends(get_current_active_superuser)
):
    if not campaign_service.launch_campaign(db, campaign_id=campaign_id, performing_username=current_agent.username):
        # Service raises HTTPException for specific failures.
        # This is a fallback if service returns False for a reason not raising HTTPEx.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to launch campaign.")
    return {"message": f"Campaign ID {campaign_id} launch process initiated."}


@campaigns_router.get("/{campaign_id}/logs", response_model=schemas.PaginatedCampaignLogResponse)
async def get_campaign_logs_endpoint(
    campaign_id: int,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db)
):
    logs, total = campaign_service.get_campaign_logs(db, campaign_id=campaign_id, skip=skip, limit=limit)
    if not logs and total == 0: # Check if campaign itself exists or just has no logs
        campaign = campaign_service.get_campaign_by_id(db, campaign_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    return {"items": logs, "total": total, "page": (skip // limit) + 1, "size": limit}


# Include all routers into the main CRM API router
crm_api_router.include_router(tickets_router)
crm_api_router.include_router(customer_notes_router) # Includes /customers/{id}/notes and /notes/{id}
crm_api_router.include_router(faq_public_router) # Publicly accessible GETs for FAQs
crm_api_router.include_router(faq_admin_router)  # Admin CUD for FAQs
crm_api_router.include_router(campaigns_router)

# The main app would then do:
# from weezy_cbs.crm_customer_support.api import crm_api_router
# app.include_router(crm_api_router)
