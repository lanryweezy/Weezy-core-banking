# FastAPI app for Customer Support Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from typing import Dict, Any, List
import logging
from datetime import datetime
import asyncio # For mock background task sleep
import random # For mock background task sleep duration

from .schemas import (
    CustomerQueryInput, SupportResponseOutput, QueryChannel, SupportResponseStatus,
    TicketCreationRequest, TicketCreationResponse, ChatMessage
)
# Import agent interaction logic
from .agent import process_customer_query_async
# Placeholder: from .agent import create_support_ticket_async # If ticket creation was also agent-driven

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Stores (Mock Databases) ---
MOCK_QUERIES_DB: Dict[str, CustomerQueryInput] = {} # query_id -> CustomerQueryInput
MOCK_QUERY_RESPONSES_DB: Dict[str, SupportResponseOutput] = {} # query_id -> SupportResponseOutput
MOCK_CONVERSATIONS_DB: Dict[str, List[ChatMessage]] = {} # conversation_id -> List[ChatMessage]
MOCK_TICKETS_DB: Dict[str, TicketCreationRequest] = {} # ticket_id -> TicketCreationRequest

app = FastAPI(
    title="Customer Support Agent API (Agent Integrated - Mocked)",
    description="Handles customer queries, provides assistance, and manages support tickets via an AI Agent.",
    version="0.1.1", # Incremented version
    contact={
        "name": "Core Banking AI Customer Experience Team",
        "email": "ai-support@examplebank.ng",
    },
)

# --- Background Task Runner ---
async def run_query_processing_background(query_input: CustomerQueryInput, initial_response: SupportResponseOutput):
    """
    Wrapper to run the customer support agent workflow in the background
    and update the mock results store with the detailed response.
    """
    query_id = query_input.query_id
    logger.info(f"Background task started for query processing: {query_id}")
    try:
        # Call the agent's workflow function
        # This function returns a dictionary aligning with SupportResponseOutput fields
        agent_response_dict = await process_customer_query_async(query_input)

        if query_id:
            try:
                # Create/Update the SupportResponseOutput object from the agent's dictionary result
                # Ensure all necessary fields from agent_response_dict are used.
                # Pydantic model will use its defaults for response_id, timestamp if not in agent_response_dict.

                # Ensure required fields for SupportResponseOutput are present or use initial values
                agent_response_dict["query_id"] = agent_response_dict.get("query_id", query_id)
                agent_response_dict["conversation_id"] = agent_response_dict.get("conversation_id", query_input.conversation_id)

                final_support_response = SupportResponseOutput(**agent_response_dict)
                MOCK_QUERY_RESPONSES_DB[query_id] = final_support_response

                logger.info(f"Background task completed for query {query_id}. Agent response status: {final_support_response.status}")

                # If agent escalated and created a ticket, log it in MOCK_TICKETS_DB
                if final_support_response.status == "EscalatedToHuman" and final_support_response.escalation_ticket_id:
                    if final_support_response.escalation_ticket_id not in MOCK_TICKETS_DB:
                        MOCK_TICKETS_DB[final_support_response.escalation_ticket_id] = TicketCreationRequest(
                            ticket_id=final_support_response.escalation_ticket_id,
                            customer_id=query_input.customer_id,
                            query_id=query_id,
                            subject=f"Escalated: {query_input.query_text[:50]}...",
                            description=f"Original Query: {query_input.query_text}\nAgent Response: {final_support_response.response_text}",
                            priority="Medium", # Default, agent might suggest priority
                            channel_of_complaint=query_input.channel,
                            category="EscalatedByAI"
                        )
                        logger.info(f"Mock ticket {final_support_response.escalation_ticket_id} created for escalated query {query_id}.")

                # Update conversation history with agent's response
                if final_support_response.conversation_id:
                    if final_support_response.conversation_id not in MOCK_CONVERSATIONS_DB:
                        MOCK_CONVERSATIONS_DB[final_support_response.conversation_id] = []
                    MOCK_CONVERSATIONS_DB[final_support_response.conversation_id].append(ChatMessage(
                        conversation_id=final_support_response.conversation_id, role="Agent",
                        text=final_support_response.response_text, timestamp=final_support_response.timestamp
                    ))


            except Exception as e:
                logger.error(f"Error parsing agent response for query {query_id}: {e}. Data: {agent_response_dict}", exc_info=True)
                if query_id in MOCK_QUERY_RESPONSES_DB:
                    current_response = MOCK_QUERY_RESPONSES_DB[query_id]
                    current_response.status = "Processing" # Revert to a generic pending or error status
                    current_response.response_text = f"Error processing your query after agent analysis: {str(e)}. Please try again or contact human support."
                    current_response.timestamp = datetime.utcnow()
        else:
            logger.error(f"Query ID missing in agent response processing for customer {query_input.customer_id}")

    except Exception as e:
        logger.error(f"Critical error in query processing background task for query {query_id}: {e}", exc_info=True)
        if query_id in MOCK_QUERY_RESPONSES_DB:
            response_entry = MOCK_QUERY_RESPONSES_DB[query_id]
            response_entry.status = "Processing" # type: ignore
            response_entry.response_text = f"A critical error occurred while our AI tried to process your query: {str(e)}. Please contact human support."
            response_entry.timestamp = datetime.utcnow()


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Customer Support Agent."""
    logger.info("Customer Support Agent root endpoint accessed.")
    return {"message": "Customer Support Agent is running. Agent integration active (mocked). See /docs."}

@app.post("/support/queries", response_model=SupportResponseOutput, status_code=status.HTTP_202_ACCEPTED, tags=["Support Queries"])
async def submit_customer_query_endpoint( # Renamed
    query_input: CustomerQueryInput,
    background_tasks: BackgroundTasks
):
    """
    Submits a customer query for processing by the AI Customer Support Agent.
    """
    q_id = query_input.query_id
    logger.info(f"API: Received customer query: ID {q_id}, Customer {query_input.customer_id}, Channel {query_input.channel}")

    if q_id in MOCK_QUERY_RESPONSES_DB and MOCK_QUERY_RESPONSES_DB[q_id].status not in ["Received", "Processing"]:
        logger.warning(f"Query ID {q_id} already handled. Returning existing/latest status: {MOCK_QUERY_RESPONSES_DB[q_id].status}")
        return MOCK_QUERY_RESPONSES_DB[q_id]

    MOCK_QUERIES_DB[q_id] = query_input

    conv_id = query_input.conversation_id or f"CONV-{query_input.customer_id}-{int(datetime.utcnow().timestamp())}"
    if not query_input.conversation_id: # If no conv_id provided, assign one for this interaction
        query_input.conversation_id = conv_id # Update the input object that might be passed to agent

    if conv_id not in MOCK_CONVERSATIONS_DB:
        MOCK_CONVERSATIONS_DB[conv_id] = []
    MOCK_CONVERSATIONS_DB[conv_id].append(ChatMessage(
        conversation_id=conv_id, role="User", text=query_input.query_text, timestamp=query_input.timestamp
    ))

    initial_response = SupportResponseOutput(
        query_id=q_id,
        conversation_id=conv_id,
        response_text="Your query has been received. Our AI support agent is looking into it...",
        status="Received" # type: ignore
    )
    MOCK_QUERY_RESPONSES_DB[q_id] = initial_response

    background_tasks.add_task(run_query_processing_background, query_input, initial_response)
    logger.info(f"API: Customer query {q_id} accepted. Support agent workflow scheduled.")

    return initial_response

@app.get("/support/queries/{query_id}/response", response_model=SupportResponseOutput, tags=["Support Queries"])
async def get_query_response_endpoint(query_id: str): # Renamed
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
async def get_conversation_history_endpoint(conversation_id: str): # Renamed
    """
    Retrieves the message history for a given conversation ID.
    """
    logger.info(f"API: Fetching history for conversation ID: {conversation_id}")
    history = MOCK_CONVERSATIONS_DB.get(conversation_id)
    if history is None:
        logger.warning(f"Conversation ID {conversation_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation ID {conversation_id} not found.")
    return history


@app.post("/support/tickets", response_model=TicketCreationResponse, status_code=status.HTTP_201_CREATED, tags=["Support Tickets"])
async def create_support_ticket_endpoint( # Renamed
    ticket_input: TicketCreationRequest
):
    """
    Logs a new support ticket. Can be used for issues escalated by an agent or system.
    """
    t_id = ticket_input.ticket_id
    logger.info(f"API: Received request to create support ticket: ID {t_id} for customer {ticket_input.customer_id}")

    if t_id in MOCK_TICKETS_DB:
        logger.warning(f"Ticket with ID {t_id} already exists.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Support ticket with ID {t_id} already exists.")

    MOCK_TICKETS_DB[t_id] = ticket_input

    # Placeholder: If ticket creation itself needs agent processing (e.g., categorization, auto-assignment)
    # background_tasks.add_task(create_support_ticket_async, ticket_input.model_dump())

    logger.info(f"API: Support ticket {t_id} created successfully.")
    return TicketCreationResponse(
        ticket_id=t_id,
        customer_id=ticket_input.customer_id,
        subject=ticket_input.subject,
        status="Created" # type: ignore
    )

@app.get("/support/tickets/{ticket_id}", response_model=TicketCreationRequest, tags=["Support Tickets"])
async def get_support_ticket_endpoint(ticket_id: str): # Renamed
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
    logger.info("Customer Support Agent FastAPI application (Agent Integrated - Mocked). To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.customer_support_agent.main:app --reload --port 8006`")
    pass
