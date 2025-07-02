# Pydantic schemas for CRM & Customer Support Module
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import TicketStatusEnum, TicketPriorityEnum, TicketChannelEnum # Import enums

# --- SupportTicket Schemas ---
class SupportTicketBase(BaseModel):
    # customer_id: Optional[int] = None # If from a known customer
    reporter_name: Optional[str] = None
    reporter_email: Optional[EmailStr] = None
    reporter_phone: Optional[str] = None
    subject: str = Field(..., min_length=5)
    description: str = Field(..., min_length=10)
    priority: TicketPriorityEnum = TicketPriorityEnum.MEDIUM
    channel_origin: TicketChannelEnum
    # category_id: Optional[int] = None

class SupportTicketCreateRequest(SupportTicketBase):
    # Attachments might be handled separately after ticket creation or via multipart form
    pass

class SupportTicketUpdateRequest(BaseModel): # For agent updates
    status: Optional[TicketStatusEnum] = None
    priority: Optional[TicketPriorityEnum] = None
    # assigned_to_user_id: Optional[int] = None
    # assigned_to_team_id: Optional[int] = None
    # category_id: Optional[int] = None
    # resolution_notes: Optional[str] = None # If marking as resolved

class SupportTicketResponse(SupportTicketBase):
    id: int
    ticket_reference: str
    status: TicketStatusEnum
    # assigned_to_user_id: Optional[int] = None
    # assigned_to_agent_name: Optional[str] = None # Denormalized for display
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    # sla_due_date: Optional[datetime] = None

    class Config:
        orm_mode = True
        use_enum_values = True

# --- TicketComment Schemas ---
class TicketCommentBase(BaseModel):
    comment_text: str = Field(..., min_length=1)
    is_internal_note: bool = False

class TicketCommentCreateRequest(TicketCommentBase):
    # ticket_id: int # Usually from path parameter
    # commenter_type: str # AGENT or CUSTOMER (system sets based on who is calling)
    # commenter_id: int # user_id or customer_id
    pass

class TicketCommentResponse(TicketCommentBase):
    id: int
    ticket_id: int
    # user_id: Optional[int] = None
    # customer_id: Optional[int] = None
    commenter_name: Optional[str] = None
    commenter_type: str
    created_at: datetime

    class Config:
        orm_mode = True

# --- TicketAttachment Schemas ---
# File upload itself is usually handled by FastAPI's UploadFile.
# This schema is for recording the metadata after upload.
class TicketAttachmentCreateRequest(BaseModel):
    # ticket_id: int # From path
    # comment_id: Optional[int] = None # If linked to a specific comment
    file_name: str
    file_url: str # URL after successful upload to storage (e.g. S3)
    file_type: Optional[str] = None # MIME type
    file_size_bytes: Optional[int] = None

class TicketAttachmentResponse(TicketAttachmentCreateRequest):
    id: int
    uploaded_at: datetime
    # uploaded_by_user_id: Optional[int] = None # Or customer_id

    class Config:
        orm_mode = True

class SupportTicketDetailResponse(SupportTicketResponse): # For viewing a single ticket with details
    comments: List[TicketCommentResponse] = []
    attachments: List[TicketAttachmentResponse] = []
    # customer_details: Optional[Dict[str, Any]] = None # Basic info about the customer if linked

# --- TicketCategory Schemas (Admin/Setup) ---
class TicketCategoryBase(BaseModel):
    name: str = Field(..., min_length=3)
    description: Optional[str] = None
    # parent_category_id: Optional[int] = None

class TicketCategoryCreateRequest(TicketCategoryBase):
    pass

class TicketCategoryResponse(TicketCategoryBase):
    id: int
    class Config:
        orm_mode = True

# --- CustomerInteractionLog Schemas ---
class CustomerInteractionLogBase(BaseModel):
    # customer_id: int # Usually from path or known context
    interaction_type: str # e.g., "PHONE_CALL_INBOUND", "EMAIL_SENT"
    channel: Optional[str] = None
    subject: Optional[str] = None
    notes: str = Field(..., min_length=5)
    outcome: Optional[str] = None
    # follow_up_date: Optional[datetime] = None

class CustomerInteractionLogCreateRequest(CustomerInteractionLogBase):
    # user_id: int # Staff member logging this, from auth context
    pass

class CustomerInteractionLogResponse(CustomerInteractionLogBase):
    id: int
    customer_id: int
    # user_id: Optional[int] = None
    # staff_name_logged_by: Optional[str] = None
    interacted_at: datetime

    class Config:
        orm_mode = True

# --- MarketingCampaign Schemas (Admin/Marketing User) ---
class MarketingCampaignBase(BaseModel):
    campaign_name: str = Field(..., min_length=5)
    description: Optional[str] = None
    target_segment_criteria_json: Optional[Dict[str, Any]] = Field({}, description="JSON defining customer segment")
    communication_channel: str # EMAIL, SMS, PUSH_NOTIFICATION_APP
    # template_id: Optional[str] = None
    start_date: datetime
    end_date: datetime
    status: str = "DRAFT" # DRAFT, ACTIVE, COMPLETED, CANCELLED

class MarketingCampaignCreateRequest(MarketingCampaignBase):
    pass

class MarketingCampaignResponse(MarketingCampaignBase):
    id: int
    # created_by_user_id: Optional[int] = None
    created_at: datetime
    class Config:
        orm_mode = True

# --- CampaignAudienceLog Schemas (Primarily for internal tracking/reporting) ---
class CampaignAudienceLogResponse(BaseModel):
    id: int
    campaign_id: int
    # customer_id: int
    sent_at: Optional[datetime] = None
    status: str
    # response_details_json: Optional[Dict[str, Any]] = None
    class Config:
        orm_mode = True

# --- Paginated Responses ---
class PaginatedSupportTicketResponse(BaseModel):
    items: List[SupportTicketResponse] # Or SupportTicketDetailResponse if including comments/attachments in list view
    total: int
    page: int
    size: int

class PaginatedCustomerInteractionLogResponse(BaseModel):
    items: List[CustomerInteractionLogResponse]
    total: int
    page: int
    size: int

class PaginatedMarketingCampaignResponse(BaseModel):
    items: List[MarketingCampaignResponse]
    total: int
    page: int
    size: int
