# FastAPI app for Compliance Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from typing import Dict, Any, List
import logging
from datetime import datetime
import asyncio # For mock background task sleep

from .schemas import (
    ScreeningRequest, ScreeningResponse, ScreeningResult,
    EntityToScreen, ScreeningCheckType, ScreeningStatus, RiskRating # Added RiskRating
)
# Import agent interaction logic
from .agent import start_entity_screening_workflow_async

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Stores (Mock Databases) ---
MOCK_SCREENING_REQUESTS_DB: Dict[str, ScreeningRequest] = {}
MOCK_SCREENING_RESULTS_DB: Dict[str, ScreeningResponse] = {} # request_id -> ScreeningResponse

app = FastAPI(
    title="Compliance Agent API (Agent Integrated - Mocked)",
    description="Handles AML/KYC screening, regulatory monitoring, and reporting assistance via an AI Agent.",
    version="0.1.1", # Incremented version
    contact={
        "name": "Core Banking Compliance AI Team",
        "email": "ai-compliance@examplebank.ng",
    },
)

# --- Background Task Runner ---
async def run_screening_background(request: ScreeningRequest, initial_response_obj: ScreeningResponse):
    """
    Wrapper to run the compliance screening agent workflow in the background
    and update the mock results store with detailed results.
    """
    request_id = request.request_id
    logger.info(f"Background task started for screening request: {request_id}")
    try:
        # Call the agent's workflow function
        # This function returns a list of dictionaries, each conforming to ScreeningResult structure
        agent_entity_results_list = await start_entity_screening_workflow_async(request)

        if request_id in MOCK_SCREENING_RESULTS_DB:
            # Update the existing ScreeningResponse object
            current_screening_response = MOCK_SCREENING_RESULTS_DB[request_id]

            parsed_entity_results: List[ScreeningResult] = []
            all_completed_successfully = True
            any_hits = False

            for result_dict in agent_entity_results_list:
                try:
                    # Ensure last_checked_at is set, Pydantic default_factory might not run if dict is passed
                    if "last_checked_at" not in result_dict or result_dict["last_checked_at"] is None:
                         result_dict["last_checked_at"] = datetime.utcnow()
                    else: # Ensure it's a datetime object if already present as string
                         if isinstance(result_dict["last_checked_at"], str):
                            result_dict["last_checked_at"] = datetime.fromisoformat(result_dict["last_checked_at"].replace("Z", "+00:00"))


                    entity_res = ScreeningResult(**result_dict)
                    parsed_entity_results.append(entity_res)
                    if entity_res.screening_status == "Error":
                        all_completed_successfully = False
                    if entity_res.screening_status in ["ConfirmedHit", "PotentialHit"]:
                        any_hits = True
                except Exception as e:
                    logger.error(f"Error parsing agent result for an entity in request {request_id}: {e}. Data: {result_dict}", exc_info=True)
                    # Add a placeholder error result for this entity
                    # Find corresponding entity_id from initial_response_obj if possible, or use a generic one
                    original_entity_id = result_dict.get("entity_id", "UNKNOWN_ENTITY")
                    original_input_name = result_dict.get("input_name", "Unknown Name")
                    parsed_entity_results.append(ScreeningResult(
                        entity_id=original_entity_id, input_name=original_input_name,
                        screening_status="Error", summary_message=f"Failed to parse agent result: {str(e)}",
                        last_checked_at=datetime.utcnow()
                    ))
                    all_completed_successfully = False

            current_screening_response.results_per_entity = parsed_entity_results
            current_screening_response.response_timestamp = datetime.utcnow()

            if not all_completed_successfully and any_hits:
                 current_screening_response.overall_status = "PartiallyCompleted" # type: ignore
            elif not all_completed_successfully:
                 current_screening_response.overall_status = "Failed" # type: ignore
            else:
                 current_screening_response.overall_status = "Completed" # type: ignore

            MOCK_SCREENING_RESULTS_DB[request_id] = current_screening_response # Store updated response
            logger.info(f"Background task completed for screening request {request_id}. Overall status: {current_screening_response.overall_status}")
        else:
            logger.warning(f"Screening request ID {request_id} not found in DB for update after agent processing.")

    except Exception as e:
        logger.error(f"Critical error in screening background task for request {request_id}: {e}", exc_info=True)
        if request_id in MOCK_SCREENING_RESULTS_DB:
            response_entry = MOCK_SCREENING_RESULTS_DB[request_id]
            response_entry.overall_status = "Failed" # type: ignore
            # Mark all individual entity results as error too
            for er_idx in range(len(response_entry.results_per_entity)):
                 response_entry.results_per_entity[er_idx].screening_status = "Error" # type: ignore
                 response_entry.results_per_entity[er_idx].summary_message = f"Agent workflow failed critically: {str(e)}"
                 response_entry.results_per_entity[er_idx].last_checked_at = datetime.utcnow()

            response_entry.response_timestamp = datetime.utcnow()


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Compliance Agent."""
    logger.info("Compliance Agent root endpoint accessed.")
    return {"message": "Compliance Agent is running. Agent integration active (mocked). See /docs."}

@app.post("/screening/entities", response_model=ScreeningResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Screening"])
async def request_entity_screening_endpoint( # Renamed to avoid conflict with schema name
    request_input: ScreeningRequest,
    background_tasks: BackgroundTasks
):
    """
    Submits one or more entities for compliance screening (e.g., Sanctions, PEP).
    The AI Compliance Agent performs screening asynchronously.
    """
    req_id = request_input.request_id
    logger.info(f"API: Received entity screening request: ID {req_id} for {len(request_input.entities_to_screen)} entities. Checks: {request_input.checks_to_perform}")

    if req_id in MOCK_SCREENING_RESULTS_DB and MOCK_SCREENING_RESULTS_DB[req_id].overall_status == "Completed":
        logger.warning(f"Screening request ID {req_id} already completed. Returning existing result.")
        return MOCK_SCREENING_RESULTS_DB[req_id]
    elif req_id in MOCK_SCREENING_RESULTS_DB: # Pending or other non-completed status
        logger.warning(f"Screening request ID {req_id} already submitted and is being processed or failed. Returning current status.")
        return MOCK_SCREENING_RESULTS_DB[req_id]
        # Or: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Screening request ID {req_id} already exists.")


    MOCK_SCREENING_REQUESTS_DB[req_id] = request_input

    initial_entity_results: List[ScreeningResult] = []
    for entity in request_input.entities_to_screen:
        initial_entity_results.append(
            ScreeningResult(
                entity_id=entity.entity_id,
                input_name=entity.name,
                screening_status="Pending",
                summary_message="Screening queued for processing by AI Compliance Agent."
            )
        )

    initial_screening_response = ScreeningResponse(
        request_id=req_id,
        overall_status="Pending",
        results_per_entity=initial_entity_results
    )
    MOCK_SCREENING_RESULTS_DB[req_id] = initial_screening_response

    background_tasks.add_task(run_screening_background, request_input, initial_screening_response)
    logger.info(f"API: Screening request {req_id} accepted. Compliance agent workflow scheduled.")

    return initial_screening_response

@app.get("/screening/results/{request_id}", response_model=ScreeningResponse, tags=["Screening"])
async def get_screening_results_endpoint(request_id: str): # Renamed
    """
    Retrieves the results of a previously submitted entity screening request.
    """
    logger.info(f"API: Fetching screening results for request ID: {request_id}")

    result = MOCK_SCREENING_RESULTS_DB.get(request_id)
    if not result:
        logger.warning(f"Screening results for request ID {request_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Screening results for request ID {request_id} not found.")

    logger.info(f"API: Returning screening results for {request_id}. Overall Status: {result.overall_status}")
    return result

# --- Main block for Uvicorn ---
if __name__ == "__main__":
    logger.info("Compliance Agent FastAPI application (Agent Integrated - Mocked). To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.compliance_agent.main:app --reload --port 8005`")
    pass
