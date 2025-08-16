# Pydantic schemas for Customer Support Agent

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import uuid

# --- Enums and Helper Models ---
QueryChannel = Literal["Chat", "Email", "PhoneCallSummary", "SocialMedia", "InApp"]
SupportResponseStatus = Literal[
    "Received", "Processing", "InformationProvided", "Resolved",
    "EscalatedToHuman", "PendingCustomerReply", "Closed"
]
SentimentLabel = Literal["Positive", "Neutral", "Negative", "Mixed"]

class ChatMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: f"MSG-{uuid.uuid4().hex[:8].upper()}")
    conversation_id: str
    role: Literal["User", "Agent", "System"]
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None # e.g., attachments, read status

class ConversationHistory(BaseModel):
    messages: List[ChatMessage] = []
    # Could add summary, sentiment trend, etc.

# --- Request Models ---
class CustomerQueryInput(BaseModel):
    query_id: str = Field(default_factory=lambda: f"QRY-{uuid.uuid4().hex[:10].upper()}")
    customer_id: str = Field(..., example="CUST-SPT-001")
    channel: QueryChannel = Field(..., example="Chat")
    query_text: str = Field(..., min_length=5, example="I forgot my internet banking password, how can I reset it?")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    conversation_id: Optional[str] = Field(None, example="CONV-CHAT-CUST001-1678886400") # To link related queries
    # previous_messages_context: Optional[List[ChatMessage]] = Field(None, description="Brief context if continuing a conversation.")

    # Optional metadata
    language: Optional[str] = Field("en", example="en") # ISO 639-1 language code
    device_info: Optional[Dict[str, Any]] = Field(None, example={"os": "Android 12", "app_version": "3.5.1"})

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "CUST-SPT-007", "channel": "InApp",
                "query_text": "My NIP transfer of N5000 to account 0123456789 (GTB) failed but I was debited. What's the status?",
                "conversation_id": "CONV-INAPP-CUST007-123",
                "language": "en"
            }
        }

class TicketCreationRequest(BaseModel):
    ticket_id: str = Field(default_factory=lambda: f"TCKT-{uuid.uuid4().hex[:10].upper()}")
    customer_id: str
    query_id: Optional[str] = Field(None, description="Link to the original query if this ticket is an escalation.")
    subject: str = Field(..., example="Failed NIP Transfer - Reversal Request")
    description: str = Field(..., example="Customer reported a failed NIP transfer on [Date] for [Amount] to [Beneficiary]. Debit occurred but value not received. Please investigate for reversal.")
    priority: Literal["Low", "Medium", "High", "Urgent"] = "Medium"
    channel_of_complaint: QueryChannel = "Chat" # Or where the complaint originated
    category: Optional[str] = Field(None, example="TransactionDisputes") # e.g., AccountIssues, CardIssues, etc.

# --- Response Models ---
class SuggestedSolution(BaseModel): # Re-defined for Support context, can be shared if identical
    source: str = Field(..., example="KnowledgeBaseArticle_#KB123")
    confidence: Optional[float] = Field(None, ge=0, le=1, example=0.90)
    solution_summary: str = Field(..., example="Guide customer through password reset link on website.")
    # full_solution_steps: Optional[List[str]] = None

class SupportResponseOutput(BaseModel):
    query_id: str # From the input query
    response_id: str = Field(default_factory=lambda: f"RSP-{uuid.uuid4().hex[:10].upper()}")
    conversation_id: Optional[str] = None # Link back to the conversation

    response_text: str = Field(..., example="To reset your password, please visit [link] and follow the instructions...")
    status: SupportResponseStatus = Field(..., example="InformationProvided")

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Optional fields based on agent's processing
    sentiment_of_query: Optional[SentimentLabel] = Field(None, example="Negative")
    intent_detected: Optional[str] = Field(None, example="PasswordResetInquiry")
    suggested_solutions_considered: Optional[List[SuggestedSolution]] = None

    escalation_ticket_id: Optional[str] = Field(None, description="Ticket ID if escalated to human agent.")
    next_expected_action: Optional[str] = Field(None, example="Customer to try password reset steps.")

    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "QRY-ABC123XYZ", "response_id": "RSP-DEF456UVW", "conversation_id": "CONV-CHAT-CUST001-123",
                "response_text": "I understand your NIP transfer failed. Typically, NIBSS processes auto-reversals for failed but debited NIP transactions within 24 hours. Could you please confirm if it's been up to 24 hours?",
                "status": "InformationProvided", "timestamp": "2023-10-30T15:00:00Z",
                "sentiment_of_query": "Negative", "intent_detected": "FailedTransactionInquiry"
            }
        }

class TicketCreationResponse(BaseModel):
    ticket_id: str # From the input or generated
    customer_id: str
    subject: str
    status: Literal["Created", "PendingAssignment", "FailedToCreate"] = "Created"
    message: str = "Support ticket created successfully."
    created_at: datetime = Field(default_factory=datetime.utcnow)


if __name__ == "__main__":
    import json
    print("--- CustomerQueryInput Schema ---")
    print(json.dumps(CustomerQueryInput.model_json_schema(), indent=2))
    print("\n--- SupportResponseOutput Schema ---")
    print(json.dumps(SupportResponseOutput.model_json_schema(), indent=2))
    print("\n--- TicketCreationRequest Schema ---")
    print(json.dumps(TicketCreationRequest.model_json_schema(), indent=2))
    print("\n--- TicketCreationResponse Schema ---")
    print(json.dumps(TicketCreationResponse.model_json_schema(), indent=2))

    # Example Instantiation
    # try:
    #     query_data = CustomerQueryInput.Config.json_schema_extra["example"]
    #     query_input = CustomerQueryInput(**query_data)
    #     print("\nValid CustomerQueryInput instance:\n", query_input.model_dump_json(indent=2))

    #     response_data = SupportResponseOutput.Config.json_schema_extra["example"]
    #     support_response = SupportResponseOutput(**response_data)
    #     print("\nValid SupportResponseOutput instance:\n", support_response.model_dump_json(indent=2))
    # except Exception as e:
    #     print("\nError during schema instantiation example:", e)
    pass
