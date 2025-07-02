# FastAPI app for Customer Support Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from typing import Dict, Any, List
import logging
from datetime import datetime
import asyncio # For mock background task

from .schemas import (
    CustomerQueryInput, SupportResponseOutput, QueryChannel, SupportResponseStatus,
    TicketCreationRequest, TicketCreationResponse, ChatMessage
)
# Placeholder for agent interaction logic
# from .agent import process_customer_query_async, create_support_ticket_async

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Stores (Mock Databases) ---
MOCK_QUERIES_DB: Dict[str, CustomerQueryInput] = {} # query_id -> CustomerQueryInput
MOCK_QUERY_RESPONSES_DB: Dict[str, SupportResponseOutput] = {} # query_id -> SupportResponseOutput
MOCK_CONVERSATIONS_DB: Dict[str, List[ChatMessage]] = {} # conversation_id -> List[ChatMessage]
MOCK_TICKETS_DB: Dict[str, TicketCreationRequest] = {} # ticket_id -> TicketCreationRequest

app = FastAPI(
    title="Customer Support Agent API",
    description="Handles customer queries, provides assistance, and manages support tickets via an AI Agent.",
    version="0.1.0",
    contact={
        "name": "Core Banking AI Customer Experience Team",
        "email": "ai-support@examplebank.ng",
    },
)

# --- Background Task Runner (Placeholder) ---
# async def run_query_processing_background(query: CustomerQueryInput, initial_response: SupportResponseOutput):
#     logger.info(f"Background task started for query processing: {query.query_id}")
#     # agent_response_data = await process_customer_query_async(query.model_dump())
#     # MOCK_QUERY_RESPONSES_DB[query.query_id] = SupportResponseOutput(**agent_response_data)
#     # logger.info(f"Background task completed for query {query.query_id}. Agent response status: {agent_response_data.get('status')}")
#     # Simulate agent processing:
#     await asyncio.sleep(random.randint(2,5))

#     mock_agent_resp_text = f"Mock AI response to: '{query.query_text[:30]}...'. Check knowledge base for password reset."
#     mock_status: SupportResponseStatus = random.choice(["InformationProvided", "Resolved", "EscalatedToHuman"]) # type: ignore

#     updated_response = MOCK_QUERY_RESPONSES_DB.get(query.query_id, initial_response) # Get current or initial
#     updated_response.response_text = mock_agent_resp_text
#     updated_response.status = mock_status
#     updated_response.timestamp = datetime.utcnow()
#     if mock_status == "EscalatedToHuman":
#         # Simulate creating a ticket if escalated
#         mock_ticket_id = f"TCKT-ESC-{query.query_id[-5:]}"
#         updated_response.escalation_ticket_id = mock_ticket_id
#         # Log a mock ticket
#         MOCK_TICKETS_DB[mock_ticket_id] = TicketCreationRequest(
#             ticket_id=mock_ticket_id, customer_id=query.customer_id, query_id=query.query_id,
#             subject=f"Escalated: {query.query_text[:50]}", description=query.query_text, priority="Medium",
#             channel_of_complaint=query.channel
#         )

#     MOCK_QUERY_RESPONSES_DB[query.query_id] = updated_response
#     logger.info(f"Background task (mock) completed for query {query.query_id}. Status: {mock_status}")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Customer Support Agent."""
    logger.info("Customer Support Agent root endpoint accessed.")
    return {"message": "Customer Support Agent is running. See /docs for API details."}

@app.post("/support/queries", response_model=SupportResponseOutput, status_code=status.HTTP_202_ACCEPTED, tags=["Support Queries"])
async def submit_customer_query(
    query_input: CustomerQueryInput,
    background_tasks: BackgroundTasks
):
    """
    Submits a customer query for processing by the AI Customer Support Agent.
    The agent will attempt to understand the query, find solutions, and respond.
    Complex queries may be escalated or logged as tickets.
    """
    q_id = query_input.query_id
    logger.info(f"API: Received customer query: ID {q_id}, Customer {query_input.customer_id}, Channel {query_input.channel}")

    if q_id in MOCK_QUERY_RESPONSES_DB and MOCK_QUERY_RESPONSES_DB[q_id].status not in ["Received", "Processing"]:
        logger.warning(f"Query ID {q_id} already processed or being processed. Returning existing/latest status.")
        return MOCK_QUERY_RESPONSES_DB[q_id]

    MOCK_QUERIES_DB[q_id] = query_input

    # Log message to conversation history if conversation_id is present
    if query_input.conversation_id:
        if query_input.conversation_id not in MOCK_CONVERSATIONS_DB:
            MOCK_CONVERSATIONS_DB[query_input.conversation_id] = []
        MOCK_CONVERSATIONS_DB[query_input.conversation_id].append(ChatMessage(
            conversation_id=query_input.conversation_id, role="User", text=query_input.query_text, timestamp=query_input.timestamp
        ))

    initial_response = SupportResponseOutput(
        query_id=q_id,
        conversation_id=query_input.conversation_id,
        response_text="Your query has been received and is being processed by our AI support agent. Please wait a moment.",
        status="Received" # type: ignore
    )
    MOCK_QUERY_RESPONSES_DB[q_id] = initial_response

    # TODO: Schedule the actual agent workflow in the background
    # background_tasks.add_task(run_query_processing_background, query_input, initial_response)
    logger.info(f"API: Customer query {q_id} accepted. Support agent workflow scheduled (mock background task).")

    return initial_response

@app.get("/support/queries/{query_id}/response", response_model=SupportResponseOutput, tags=["Support Queries"])
async def get_query_response(query_id: str):
    """
    Retrieves the latest response or status for a previously submitted customer query.
    """
    logger.info(f"API: Fetching response for query ID: {query_id}")

    response = MOCK_QUERY_RESPONSES_DB.get(query_id)
    if not response:
        logger.warning(f"Response for query ID {query_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Response for query ID {query_id} not found.")

    logger.info(f"API: Returning response for query {query_id}. Status: {response.status}")
    return response

@app.get("/support/conversations/{conversation_id}", response_model=List[ChatMessage], tags=["Support Queries"])
async def get_conversation_history(conversation_id: str):
    """
    Retrieves the message history for a given conversation ID.
    """
    logger.info(f"API: Fetching history for conversation ID: {conversation_id}")
    history = MOCK_CONVERSATIONS_DB.get(conversation_id)
    if history is None: # Allow empty list if conversation exists but no messages yet
        logger.warning(f"Conversation ID {conversation_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation ID {conversation_id} not found.")
    return history


@app.post("/support/tickets", response_model=TicketCreationResponse, status_code=status.HTTP_201_CREATED, tags=["Support Tickets"])
async def create_support_ticket(
    ticket_input: TicketCreationRequest
    # background_tasks: BackgroundTasks # If ticket creation also involves agent work
):
    """
    Logs a new support ticket. This might be used for issues escalated by an agent
    or directly by a system/user if the AI cannot resolve a query.
    """
    t_id = ticket_input.ticket_id
    logger.info(f"API: Received request to create support ticket: ID {t_id} for customer {ticket_input.customer_id}")

    if t_id in MOCK_TICKETS_DB:
        logger.warning(f"Ticket with ID {t_id} already exists.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Support ticket with ID {t_id} already exists.")

    MOCK_TICKETS_DB[t_id] = ticket_input

    # TODO: Potentially trigger agent task for ticket categorization or initial data gathering if needed.
    # background_tasks.add_task(process_new_ticket_background, ticket_input)

    logger.info(f"API: Support ticket {t_id} created successfully.")
    return TicketCreationResponse(
        ticket_id=t_id,
        customer_id=ticket_input.customer_id,
        subject=ticket_input.subject,
        status="Created" # type: ignore
    )

@app.get("/support/tickets/{ticket_id}", response_model=TicketCreationRequest, tags=["Support Tickets"]) # Assuming we return the input for now
async def get_support_ticket(ticket_id: str):
    """
    Retrieves details of a specific support ticket.
    """
    logger.info(f"API: Fetching details for support ticket ID: {ticket_id}")
    ticket = MOCK_TICKETS_DB.get(ticket_id)
    if not ticket:
        logger.warning(f"Support ticket ID {ticket_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Support ticket ID {ticket_id} not found.")
    return ticket


# --- Main block for Uvicorn ---
if __name__ == "__main__":
    logger.info("Customer Support Agent FastAPI application. To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.customer_support_agent.main:app --reload --port 8006`")
    pass
