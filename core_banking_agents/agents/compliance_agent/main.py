# FastAPI app for Compliance Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from typing import Dict, Any, List
import logging
from datetime import datetime

from .schemas import (
    ScreeningRequest, ScreeningResponse, ScreeningResult,
    EntityToScreen, ScreeningStatus, ScreeningCheckType
)
# Placeholder for agent interaction logic
# from .agent import start_entity_screening_workflow_async

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Stores (Mock Databases) ---
MOCK_SCREENING_REQUESTS_DB: Dict[str, ScreeningRequest] = {}
MOCK_SCREENING_RESULTS_DB: Dict[str, ScreeningResponse] = {} # request_id -> ScreeningResponse

app = FastAPI(
    title="Compliance Agent API",
    description="Handles AML/KYC screening, regulatory monitoring, and reporting assistance.",
    version="0.1.0",
    contact={
        "name": "Core Banking Compliance AI Team",
        "email": "ai-compliance@examplebank.ng",
    },
)

# --- Background Task Runner (Placeholder) ---
# async def run_screening_background(request: ScreeningRequest, initial_response: ScreeningResponse):
#     logger.info(f"Background task started for screening request: {request.request_id}")
#     # agent_results = await start_entity_screening_workflow_async(request.model_dump())
#     # Process agent_results and update MOCK_SCREENING_RESULTS_DB[request.request_id]
#     # For now, simulate some processing and update.
#     import time, random
#     await asyncio.sleep(random.randint(3,10))

#     updated_results_per_entity = []
#     all_clear = True
#     for entity_result in initial_response.results_per_entity:
#         mock_status: ScreeningStatus = random.choice(["Clear", "PotentialHit", "Error"]) # type: ignore
#         entity_result.screening_status = mock_status
#         entity_result.last_checked_at = datetime.utcnow()
#         if mock_status == "Clear":
#             entity_result.summary_message = "Screening complete. No adverse findings."
#             entity_result.overall_risk_rating = "Low" # type: ignore
#         elif mock_status == "PotentialHit":
#             all_clear = False
#             entity_result.summary_message = "Potential hit found. Requires manual review."
#             entity_result.overall_risk_rating = "Medium" # type: ignore
#             # Add mock hit details
#             # entity_result.hits = [ScreeningHitDetails(...)]
#         else: # Error
#             all_clear = False
#             entity_result.summary_message = "Error during screening process for this entity."
#             entity_result.errors = ["Simulated screening service unavailable."]

#         updated_results_per_entity.append(entity_result)

#     initial_response.results_per_entity = updated_results_per_entity
#     initial_response.overall_status = "Completed" if all_clear else "PartiallyCompleted" # type: ignore
#     initial_response.response_timestamp = datetime.utcnow()
#     MOCK_SCREENING_RESULTS_DB[request.request_id] = initial_response
#     logger.info(f"Background task (mock) completed for screening request {request.request_id}. Overall status: {initial_response.overall_status}")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Compliance Agent."""
    logger.info("Compliance Agent root endpoint accessed.")
    return {"message": "Compliance Agent is running. See /docs for API details."}

@app.post("/screening/entities", response_model=ScreeningResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Screening"])
async def request_entity_screening(
    request_input: ScreeningRequest,
    background_tasks: BackgroundTasks
):
    """
    Submits one or more entities for compliance screening (e.g., Sanctions, PEP).
    The AI Compliance Agent performs screening asynchronously.
    This endpoint acknowledges receipt and returns an initial 'Pending' status for each entity.
    """
    req_id = request_input.request_id
    logger.info(f"API: Received entity screening request: ID {req_id} for {len(request_input.entities_to_screen)} entities. Checks: {request_input.checks_to_perform}")

    if req_id in MOCK_SCREENING_RESULTS_DB:
        logger.warning(f"Screening request with ID {req_id} already exists or is being processed.")
        # Can choose to return existing or raise error. For now, let's return existing if completed.
        if MOCK_SCREENING_RESULTS_DB[req_id].overall_status == "Completed":
            return MOCK_SCREENING_RESULTS_DB[req_id]
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Screening request ID {req_id} already exists and is pending or failed.")

    MOCK_SCREENING_REQUESTS_DB[req_id] = request_input

    # Prepare initial response with pending status for each entity
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

    # TODO: Schedule the actual agent workflow in the background
    # background_tasks.add_task(run_screening_background, request_input, initial_screening_response)
    logger.info(f"API: Screening request {req_id} accepted. Compliance agent workflow scheduled (mock background task).")

    return initial_screening_response

@app.get("/screening/results/{request_id}", response_model=ScreeningResponse, tags=["Screening"])
async def get_screening_results(request_id: str):
    """
    Retrieves the results of a previously submitted entity screening request.
    Poll this endpoint for updates.
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
    logger.info("Compliance Agent FastAPI application. To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.compliance_agent.main:app --reload --port 8005`")
    pass
