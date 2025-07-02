# API Endpoints for CRM & Customer Support Module
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from . import services, schemas, models
# from weezy_cbs.database import get_db
# from weezy_cbs.auth.dependencies import get_current_active_user, get_current_active_support_agent, get_current_active_admin_user

# Placeholder get_db and auth
def get_db_placeholder(): yield None
get_db = get_db_placeholder
def get_current_active_user_placeholder(): return {"id": 1, "customer_id": 101, "username": "customer_user"} # Generic customer
get_current_active_user = get_current_active_user_placeholder
def get_current_active_support_agent_placeholder(): return {"id": 201, "username": "agent007", "role": "support_agent"}
get_current_active_support_agent = get_current_active_support_agent_placeholder
def get_current_active_admin_user_placeholder(): return {"id": 301, "username": "crm_admin", "role": "admin"}
get_current_active_admin_user = get_current_active_admin_user_placeholder


router = APIRouter(
    prefix="/crm-support",
    tags=["CRM & Customer Support"],
    responses={404: {"description": "Not found"}},
)

# --- Support Ticket Endpoints (Customer & Agent/Admin) ---
@router.post("/tickets", response_model=schemas.SupportTicketResponse, status_code=status.HTTP_201_CREATED)
def create_new_support_ticket(
    ticket_in: schemas.SupportTicketCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user) # Can be customer or agent creating on behalf
):
    """Create a new support ticket."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = current_user.get("customer_id") # If user is a customer
    user_id_creator = current_user.get("id") if not customer_id else None # If staff created it

    # If reporter details are not in payload but user is customer, populate from customer profile
    if customer_id and not ticket_in.reporter_name:
        # customer_profile = services.get_customer_profile(db, customer_id) # Fetch from CustomerIdentity
        # if customer_profile:
        #     ticket_in.reporter_name = customer_profile.full_name
        #     ticket_in.reporter_email = customer_profile.email
        #     ticket_in.reporter_phone = customer_profile.phone_number
        pass # Placeholder for populating reporter details

    try:
        ticket = services.create_support_ticket(db, ticket_in, customer_id, user_id_creator)
        return ticket
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create ticket: {str(e)}")

@router.get("/tickets/my-tickets", response_model=schemas.PaginatedSupportTicketResponse)
def get_my_support_tickets( # For authenticated customer
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """Get support tickets logged by the authenticated customer."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    customer_id = current_user.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=403, detail="User is not a customer.")

    tickets = services.get_tickets_for_customer(db, customer_id, skip, limit)
    total = db.query(func.count(models.SupportTicket.id)).filter(models.SupportTicket.customer_id == customer_id).scalar_one_or_none() or 0
    return schemas.PaginatedSupportTicketResponse(items=tickets, total=total, page=(skip//limit)+1, size=len(tickets))


@router.get("/tickets/agent-queue", response_model=schemas.PaginatedSupportTicketResponse) # Agent view
def get_agent_ticket_queue(
    status: Optional[models.TicketStatusEnum] = Query(None, description="Filter by status (e.g. OPEN, PENDING_AGENT_RESPONSE)"),
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_agent: dict = Depends(get_current_active_support_agent)
):
    """Get tickets assigned to or in the queue for the authenticated support agent."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    agent_id = current_agent.get("id")
    tickets = services.get_tickets_assigned_to_agent(db, agent_id, status, skip, limit)

    query = db.query(func.count(models.SupportTicket.id)).filter(models.SupportTicket.assigned_to_user_id == agent_id)
    if status: query = query.filter(models.SupportTicket.status == status)
    else: query = query.filter(models.SupportTicket.status.notin_([models.TicketStatusEnum.RESOLVED, models.TicketStatusEnum.CLOSED]))
    total = query.scalar_one_or_none() or 0

    return schemas.PaginatedSupportTicketResponse(items=tickets, total=total, page=(skip//limit)+1, size=len(tickets))


@router.get("/tickets/{ticket_id}", response_model=schemas.SupportTicketDetailResponse)
def get_ticket_details_with_comments(
    ticket_id: int,
    db: Session = Depends(get_db)
    # auth: User = Depends(get_user_who_can_view_ticket) # Customer owner or agent/admin
):
    """Get full details of a support ticket, including comments and attachments."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    ticket = services.get_support_ticket(db, ticket_id=ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    # TODO: Add authorization: only ticket owner or authorized staff can view.

    # Manually load comments and attachments for the response schema if not eager loaded by service
    comments = db.query(models.TicketComment).filter(models.TicketComment.ticket_id == ticket_id).order_by(models.TicketComment.created_at.asc()).all()
    attachments = db.query(models.TicketAttachment).filter(models.TicketAttachment.ticket_id == ticket_id).all()

    ticket_data = schemas.SupportTicketResponse.from_orm(ticket).dict()
    ticket_data["comments"] = [schemas.TicketCommentResponse.from_orm(c) for c in comments]
    ticket_data["attachments"] = [schemas.TicketAttachmentResponse.from_orm(a) for a in attachments]

    return schemas.SupportTicketDetailResponse(**ticket_data)


@router.patch("/tickets/{ticket_id}", response_model=schemas.SupportTicketResponse) # Agent/Admin updating ticket
def update_ticket_by_agent(
    ticket_id: int,
    update_in: schemas.SupportTicketUpdateRequest,
    db: Session = Depends(get_db),
    current_agent: dict = Depends(get_current_active_support_agent)
):
    """Update status, priority, assignment, or add resolution notes to a ticket. (Agent/Admin operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    agent_id = current_agent.get("id")
    try:
        # Check if ticket is assigned to this agent or if agent has rights to update any ticket
        return services.update_support_ticket(db, ticket_id, update_in, agent_id)
    except services.NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except services.InvalidOperationException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tickets/{ticket_id}/comments", response_model=schemas.TicketCommentResponse)
def add_comment_to_ticket(
    ticket_id: int,
    comment_in: schemas.TicketCommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user) # Can be customer or agent
):
    """Add a comment to a support ticket. Can be by customer or support agent."""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")

    commenter_id = current_user.get("id")
    commenter_type = "AGENT" if current_user.get("role") == "support_agent" else "CUSTOMER" # Simplified
    commenter_name = current_user.get("username") # Or full name

    # TODO: Authorization: if customer, ensure they own the ticket. If agent, ensure assigned or has rights.

    try:
        return services.add_ticket_comment(db, comment_in, ticket_id, commenter_id, commenter_type, commenter_name)
    except services.NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- Ticket Attachment Endpoints (Conceptual - file upload is separate) ---
@router.post("/tickets/{ticket_id}/attachments", response_model=schemas.TicketAttachmentResponse)
async def add_attachment_to_ticket_metadata(
    ticket_id: int,
    # file: UploadFile = File(...), # Actual file upload
    attachment_meta_in: schemas.TicketAttachmentCreateRequest, # Client sends this AFTER uploading file to S3/etc.
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Record metadata for a file attached to a support ticket.
    Assumes file is already uploaded to a storage service and `file_url` is provided.
    """
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # file_url = await services.save_ticket_attachment_file(file) # This service would save to S3 etc.
    # attachment_meta_in.file_url = file_url
    # attachment_meta_in.file_name = file.filename
    # attachment_meta_in.file_type = file.content_type

    uploader_id = current_user.get("id")
    uploader_type = "AGENT" if current_user.get("role") == "support_agent" else "CUSTOMER"

    try:
        return services.add_ticket_attachment(db, attachment_meta_in, ticket_id, uploader_id, uploader_type)
    except services.NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- Customer Interaction Log Endpoints (Agent/System) ---
@router.post("/customers/{customer_id}/interactions", response_model=schemas.CustomerInteractionLogResponse)
def log_new_customer_interaction(
    customer_id: int,
    log_in: schemas.CustomerInteractionLogCreateRequest,
    db: Session = Depends(get_db),
    current_agent: dict = Depends(get_current_active_support_agent) # Or any staff role
):
    """Log a new interaction with a customer (e.g., phone call, email). (Staff operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    staff_user_id = current_agent.get("id")
    try:
        return services.log_customer_interaction(db, log_in, customer_id, staff_user_id)
    except services.NotFoundException as e: # If customer_id not found
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/customers/{customer_id}/interactions", response_model=schemas.PaginatedCustomerInteractionLogResponse)
def get_customer_interaction_history(
    customer_id: int,
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_agent: dict = Depends(get_current_active_support_agent) # Or any staff with CRM access
):
    """Get interaction history for a specific customer. (Staff operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    # Add authorization check if agent can view this customer's interactions
    interactions = services.get_interactions_for_customer(db, customer_id, skip, limit)
    total = db.query(func.count(models.CustomerInteractionLog.id)).filter(models.CustomerInteractionLog.customer_id == customer_id).scalar_one_or_none() or 0
    return schemas.PaginatedCustomerInteractionLogResponse(items=interactions, total=total, page=(skip//limit)+1, size=len(interactions))

# --- Marketing Campaign Endpoints (Admin/Marketing User) ---
@router.post("/marketing-campaigns", response_model=schemas.MarketingCampaignResponse, status_code=status.HTTP_201_CREATED)
def create_new_marketing_campaign_config(
    campaign_in: schemas.MarketingCampaignCreateRequest,
    db: Session = Depends(get_db),
    current_admin_or_mkt: dict = Depends(get_current_active_admin_user) # Or marketing role
):
    """Define a new marketing campaign. (Admin/Marketing operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    user_id = current_admin_or_mkt.get("id")
    return services.create_marketing_campaign(db, campaign_in, user_id)

@router.post("/marketing-campaigns/{campaign_id}/launch", status_code=status.HTTP_202_ACCEPTED)
async def launch_active_marketing_campaign( # Making it async for potential background task
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_admin_or_mkt: dict = Depends(get_current_active_admin_user)
):
    """Launch an active marketing campaign. This will identify target audience and queue communications. (Admin/Marketing operation)"""
    if db is None: raise HTTPException(status_code=503, detail="Database not configured for API.")
    try:
        # services.launch_marketing_campaign(db, campaign_id) # Synchronous version
        background_tasks.add_task(services.launch_marketing_campaign, db, campaign_id)
        return {"message": "Marketing campaign launch process initiated."}
    except services.NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except services.InvalidOperationException as e: # e.g. campaign not in DRAFT status
        raise HTTPException(status_code=400, detail=str(e))

# TODO: Endpoints for TicketCategory CRUD (Admin), managing campaign audience logs (Reporting).

# Import func for count queries if not already at top
from sqlalchemy import func
