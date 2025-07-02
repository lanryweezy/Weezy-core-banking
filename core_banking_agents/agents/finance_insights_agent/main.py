# FastAPI app for Finance Insights Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from typing import Dict, Any, List
import logging
from datetime import datetime
import asyncio # For mock background task sleep
import random  # For mock background task sleep

from .schemas import InsightsRequest, InsightsReport
# Import agent interaction logic
from .agent import generate_financial_insights_async

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Store (Mock Database for Insights Reports) ---
MOCK_INSIGHTS_REPORTS_DB: Dict[str, InsightsReport] = {} # report_id -> InsightsReport

app = FastAPI(
    title="Finance Insights Agent API (Agent Integrated - Mocked)",
    description="Provides financial analytics, forecasts, and personalized insights to customers or bank staff via an AI Agent.",
    version="0.1.0",
    contact={
        "name": "Core Banking AI Insights Team",
        "email": "ai-insights@examplebank.ng",
    },
)

# --- Background Task Runner ---
async def run_insights_generation_background(request_input: InsightsRequest, initial_report_id: str):
    """
    Wrapper to run the finance insights agent workflow in the background
    and update the mock results store with the detailed report.
    """
    logger.info(f"Background task started for insights generation: Request ID {request_input.request_id}, Report ID {initial_report_id}")
    try:
        # Call the agent's workflow function
        # This function returns a dictionary aligning with InsightsReport fields
        agent_report_dict = await generate_financial_insights_async(request_input)

        if initial_report_id: # Should always be true from how it's called
            try:
                # Create/Update the InsightsReport object from the agent's dictionary result
                # The agent_report_dict should already include report_id, request_id, etc.
                # generated_at will be handled by Pydantic if not precisely set by agent.
                final_insights_report = InsightsReport(**agent_report_dict)
                MOCK_INSIGHTS_REPORTS_DB[initial_report_id] = final_insights_report

                logger.info(f"Background task completed for Report ID {initial_report_id}. Summary: {final_insights_report.summary[:100] if final_insights_report.summary else 'N/A'}")
            except Exception as e:
                logger.error(f"Error parsing agent report for Report ID {initial_report_id}: {e}. Data: {agent_report_dict}", exc_info=True)
                if initial_report_id in MOCK_INSIGHTS_REPORTS_DB: # Update existing entry with error
                    current_report = MOCK_INSIGHTS_REPORTS_DB[initial_report_id]
                    # current_report.status = "Error" # Assuming InsightsReport has a status field, which it doesn't currently.
                    current_report.summary = f"Error processing insights report: {str(e)}"
                    current_report.generated_at = datetime.utcnow() # Update timestamp
                # else: Could create a new error report entry if initial was lost

    except Exception as e:
        logger.error(f"Critical error in insights generation background task for Report ID {initial_report_id}: {e}", exc_info=True)
        if initial_report_id in MOCK_INSIGHTS_REPORTS_DB:
            report_entry = MOCK_INSIGHTS_REPORTS_DB[initial_report_id]
            report_entry.summary = f"Agent workflow failed critically: {str(e)}"
            # report_entry.status = "Error"
            report_entry.generated_at = datetime.utcnow()


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Finance Insights Agent."""
    logger.info("Finance Insights Agent root endpoint accessed.")
    return {"message": "Finance Insights Agent is running. Agent integration active (mocked). See /docs."}

@app.post("/insights/generate", response_model=InsightsReport, status_code=status.HTTP_202_ACCEPTED, tags=["Financial Insights"])
async def generate_insights_endpoint( # Renamed
    request_input: InsightsRequest,
    background_tasks: BackgroundTasks
):
    """
    Submits a request to generate financial insights for a customer or segment.
    The AI Finance Insights Agent performs analysis asynchronously.
    This endpoint acknowledges receipt and returns an initial 'Pending' state for the report.
    """
    req_id = request_input.request_id or f"INSREQ-{datetime.utcnow().timestamp()}" # Ensure there's a request_id
    if not request_input.request_id: request_input.request_id = req_id

    # Generate a report ID for tracking this specific generation request
    # The agent's output will also contain a report_id, which should match this one or be used.
    # For this flow, the agent's returned dict *is* the report, and its report_id is used.
    # So, we'll let the agent's workflow determine the final report_id.
    # The initial_report returned here is just an ack.

    # Create an initial placeholder report. The agent will generate the full one.
    # We need a report_id to track it. Let the agent's output define it.
    # For the immediate response, we can create a temporary report_id or use the request_id.

    # Let's generate the report_id here and pass it to the agent or ensure agent uses request_id for its report_id.
    # The agent's `generate_financial_insights_async` already creates a report_id like "FINREP-<req_id_suffix>"
    # So, the `initial_report_id_for_tracking` will be what the agent eventually generates.
    # The initial response here is just a placeholder.

    # This is a bit tricky: agent generates report_id. We need one for tracking the response.
    # Let's assume the POST response can be minimal and the GET /insights/{report_id} uses the agent-generated ID.
    # Or, we make the agent use the request_id as part of its report_id.
    # The agent's `generate_financial_insights_async` currently makes a report_id like `FINREP-{request_id.split('-')[-1]}`.
    # This means we need the request_id to construct the eventual report_id for polling.

    initial_report_id = f"FINREP-{req_id.split('-')[-1]}" if req_id else f"FINREP-TEMP-{datetime.utcnow().timestamp()}"


    logger.info(f"API: Received insights generation request: ID {req_id}. Will generate Report ID (approx): {initial_report_id}")

    if initial_report_id in MOCK_INSIGHTS_REPORTS_DB: # Check if this report_id was somehow already processed
        # This check is a bit weak if report_id generation isn't strictly unique before agent run.
        # A better approach might be to always generate a unique task_id for background processing.
        logger.warning(f"Insights report for request ID {req_id} (report ID {initial_report_id}) may already exist or be processing.")
        # return MOCK_INSIGHTS_REPORTS_DB[initial_report_id] # Return existing if needed

    # Placeholder response. The actual content will be filled by the background task.
    # The `report_id` in this initial response should be the one clients poll.
    initial_report_placeholder = InsightsReport(
        report_id=initial_report_id,
        request_id=req_id,
        customer_id=request_input.customer_id,
        segment_id=request_input.segment_id,
        summary="Financial insights generation is pending.",
        # status="Pending" # If InsightsReport schema had a status field
    )
    MOCK_INSIGHTS_REPORTS_DB[initial_report_id] = initial_report_placeholder

    background_tasks.add_task(run_insights_generation_background, request_input, initial_report_id)
    logger.info(f"API: Insights generation for request {req_id} (Report ID: {initial_report_id}) accepted. Agent workflow scheduled.")

    return initial_report_placeholder

@app.get("/insights/{report_id}", response_model=InsightsReport, tags=["Financial Insights"])
async def get_insights_report_endpoint(report_id: str): # Renamed
    """
    Retrieves a generated financial insights report using its report ID.
    Poll this endpoint for updates after submitting an insights generation request.
    """
    logger.info(f"API: Fetching insights report for Report ID: {report_id}")

    report = MOCK_INSIGHTS_REPORTS_DB.get(report_id)
    if not report:
        logger.warning(f"Insights report with ID {report_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Insights report with ID {report_id} not found.")

    logger.info(f"API: Returning report for ID {report_id}. Summary: {report.summary[:100] if report.summary else 'N/A'}")
    return report

# --- Main block for Uvicorn ---
if __name__ == "__main__":
    logger.info("Finance Insights Agent FastAPI application (Agent Integrated - Mocked). To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.finance_insights_agent.main:app --reload --port 8007`") # Assuming port 8007
    pass
