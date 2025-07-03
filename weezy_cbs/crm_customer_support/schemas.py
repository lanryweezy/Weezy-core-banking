from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from .models import (
    TicketStatusEnum, TicketPriorityEnum, TicketCategoryEnum, TicketChannelEnum,
    CampaignStatusEnum, CampaignChannelEnum, CampaignLogEntryStatusEnum
)

# --- SupportTicket Schemas ---
class SupportTicketBase(BaseModel):
    subject: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    priority: TicketPriorityEnum = TicketPriorityEnum.MEDIUM
    category: Optional[TicketCategoryEnum] = None
    channel_of_origin: Optional[TicketChannelEnum] = None # Usually set by system based on endpoint

class SupportTicketCreate(SupportTicketBase):
    customer_id: int # Must be linked to an existing customer
    # If submitted by an authenticated digital user:
    digital_user_profile_id: Optional[int] = None
    # If submitted via unauthenticated channel (e.g. public web form, email to support@)
    # these might be captured, though customer_id should ideally be found/created first.
    reporter_name: Optional[str] = Field(None, max_length=150)
    reporter_email: Optional[EmailStr] = None
    reporter_phone: Optional[str] = Field(None, max_length=20)


class SupportTicketUpdateSchema(BaseModel): # For agent updates
    subject: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=10) # To append or clarify
    status: Optional[TicketStatusEnum] = None
    priority: Optional[TicketPriorityEnum] = None
    category: Optional[TicketCategoryEnum] = None
    assigned_to_user_id: Optional[int] = None # Agent ID
    resolution_details: Optional[str] = None
    sla_due_date: Optional[datetime] = None

class TicketUpdateCreate(BaseModel):
    update_text: str = Field(..., min_length=1)
    is_internal_note: bool = False
    # agent_user_id will be taken from the authenticated agent making the call
    # attachments_json: Optional[List[Dict[str, Any]]] = None # e.g. [{"filename": "...", "url": "..."}]

    # @validator('attachments_json', pre=True)
    # def parse_attachments_json_string(cls, value):
    #     if isinstance(value, str):
    #         try: return json.loads(value)
    #         except json.JSONDecodeError: raise ValueError("Invalid JSON for attachments")
    #     return value

class TicketUpdateResponse(TicketUpdateCreate):
    id: int
    ticket_id: int
    agent_user_id: Optional[int] = None # ID of agent who made the update
    # commenter_name: Optional[str] = None # Could be agent name or "Customer"
    created_at: datetime
    attachments_json: Optional[List[Dict[str, Any]]] = None # Parsed back to dict/list

    class Config:
        orm_mode = True
        # use_enum_values = True # Not needed here

    @validator('attachments_json', pre=True, always=True)
    def parse_db_attachments_json_string(cls, value):
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: return None # Or raise error
        return value


class SupportTicketResponse(SupportTicketBase):
    id: int
    ticket_number: str
    customer_id: int
    digital_user_profile_id: Optional[int] = None
    assigned_to_user_id: Optional[int] = None
    status: TicketStatusEnum
    resolution_details: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    sla_due_date: Optional[datetime] = None

    # Potentially include names for better display, fetched via joins in service
    # customer_name: Optional[str] = None
    # assigned_agent_name: Optional[str] = None

    updates: List[TicketUpdateResponse] = []

    class Config:
        orm_mode = True
        use_enum_values = True # Ensure enums are returned as their string values


# --- CustomerNote Schemas ---
class CustomerNoteBase(BaseModel):
    note_text: str = Field(..., min_length=5)
    category: Optional[str] = Field(None, max_length=50)

class CustomerNoteCreate(CustomerNoteBase):
    customer_id: int
    # agent_user_id is taken from authenticated agent

class CustomerNoteResponse(CustomerNoteBase):
    id: int
    customer_id: int
    agent_user_id: int
    # agent_username: Optional[str] = None # Added by service
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- Campaign Schemas ---
class CampaignBase(BaseModel):
    campaign_name: str = Field(..., min_length=3, max_length=150)
    description: Optional[str] = None
    campaign_channel: CampaignChannelEnum
    target_audience_rules_json: Optional[Dict[str, Any]] = None
    message_template_name: Optional[str] = Field(None, max_length=100)
    message_subject: Optional[str] = Field(None, max_length=255) # For email
    message_body_content: Optional[str] = None # Actual content or template structure
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @validator('target_audience_rules_json', pre=True)
    def parse_rules_json(cls, value):
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: raise ValueError("Invalid JSON for target_audience_rules_json")
        return value

class CampaignCreate(CampaignBase):
    status: CampaignStatusEnum = CampaignStatusEnum.DRAFT # Default on create
    # created_by_user_id is from authenticated user

class CampaignUpdateSchema(BaseModel): # Partial updates
    campaign_name: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = None
    status: Optional[CampaignStatusEnum] = None
    campaign_channel: Optional[CampaignChannelEnum] = None
    target_audience_rules_json: Optional[Dict[str, Any]] = None
    message_template_name: Optional[str] = Field(None, max_length=100)
    message_subject: Optional[str] = Field(None, max_length=255)
    message_body_content: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @validator('target_audience_rules_json', pre=True)
    def parse_update_rules_json(cls, value): # Duplicate validator for update schema
        if value is None: return None
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: raise ValueError("Invalid JSON for target_audience_rules_json")
        return value

class CampaignResponse(CampaignBase):
    id: int
    status: CampaignStatusEnum
    created_by_user_id: int
    # created_by_username: Optional[str] = None # Added by service
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True


# --- CampaignLog Schemas ---
class CampaignLogResponse(BaseModel):
    id: int
    campaign_id: int
    customer_id: int
    # customer_name: Optional[str] = None # Added by service
    status: CampaignLogEntryStatusEnum
    recipient_identifier: str
    processed_at: datetime
    sent_at: Optional[datetime] = None
    interacted_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    external_message_id: Optional[str] = None

    class Config:
        orm_mode = True
        use_enum_values = True

# --- FAQItem Schemas ---
class FAQItemBase(BaseModel):
    category: str = Field(..., max_length=100)
    question: str = Field(..., min_length=10)
    answer: str = Field(..., min_length=10)
    tags_json: Optional[List[str]] = None # Will be stored as JSON string
    is_published: bool = True

    @validator('tags_json', pre=True)
    def parse_tags_json(cls, value):
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: raise ValueError("Invalid JSON for tags_json")
        if isinstance(value, list): # Already a list
            return value
        return None


class FAQItemCreate(FAQItemBase):
    # created_by_user_id from authenticated user
    pass

class FAQItemUpdateSchema(BaseModel): # Partial updates
    category: Optional[str] = Field(None, max_length=100)
    question: Optional[str] = Field(None, min_length=10)
    answer: Optional[str] = Field(None, min_length=10)
    tags_json: Optional[List[str]] = None
    is_published: Optional[bool] = None
    # updated_by_user_id from authenticated user

    @validator('tags_json', pre=True)
    def parse_update_tags_json(cls, value): # Duplicate validator for update schema
        if value is None: return None
        if isinstance(value, str):
            try: return json.loads(value)
            except json.JSONDecodeError: raise ValueError("Invalid JSON for tags_json")
        if isinstance(value, list):
            return value
        return None


class FAQItemResponse(FAQItemBase):
    id: int
    view_count: int
    created_by_user_id: Optional[int] = None
    updated_by_user_id: Optional[int] = None
    # created_by_username: Optional[str] = None # Added by service
    # updated_by_username: Optional[str] = None # Added by service
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- Paginated Responses ---
class PaginatedSupportTicketResponse(BaseModel):
    items: List[SupportTicketResponse] # Or a minimal version
    total: int
    page: int
    size: int

class PaginatedCustomerNoteResponse(BaseModel):
    items: List[CustomerNoteResponse]
    total: int
    page: int
    size: int

class PaginatedCampaignResponse(BaseModel):
    items: List[CampaignResponse]
    total: int
    page: int
    size: int

class PaginatedCampaignLogResponse(BaseModel):
    items: List[CampaignLogResponse]
    total: int
    page: int
    size: int

class PaginatedFAQItemResponse(BaseModel):
    items: List[FAQItemResponse]
    total: int
    page: int
    size: int
