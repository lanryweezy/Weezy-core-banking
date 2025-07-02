# FastAPI app for Customer Onboarding Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Depends
from typing import Dict, Any
from datetime import datetime
import logging # Added for logging

from .schemas import OnboardingRequest, OnboardingStatusResponse, OnboardingProcess, VerificationStepResult, VerificationStatus
# Import agent interaction logic
from .agent import start_onboarding_process, get_onboarding_status_from_agent

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Store (Mock Database) ---
# In a real application, use a persistent database (e.g., PostgreSQL via SQLAlchemy)
# and a task queue (e.g., Celery with Redis/RabbitMQ broker) for background tasks.
MOCK_ONBOARDING_DB: Dict[str, OnboardingProcess] = {}


# --- Background Task Runner ---
async def run_agent_workflow_background(onboarding_id: str, process: OnboardingProcess, request_data: OnboardingRequest):
    """
    Wrapper to run the agent workflow in the background and update the mock DB.
    Error handling within this background task should ideally update the process status.
    """
    logger.info(f"Background task started for onboarding_id: {onboarding_id}")
    try:
        agent_update_payload = await start_onboarding_process(onboarding_id, request_data)

        # Update the stored process with information from the agent
        if process:
            process.status = agent_update_payload.get("status", process.status) # type: ignore
            process.message = agent_update_payload.get("message", process.message)
            process.last_updated_at = agent_update_payload.get("last_updated_at", datetime.utcnow())

            agent_steps_update = agent_update_payload.get("verification_steps")
            if isinstance(agent_steps_update, list):
                current_steps_map = {step.step_name: step for step in process.verification_steps}
                for agent_step_data in agent_steps_update:
                    if isinstance(agent_step_data, VerificationStepResult):
                        agent_step_obj = agent_step_data
                    elif isinstance(agent_step_data, dict):
                        try:
                            agent_step_obj = VerificationStepResult(**agent_step_data)
                        except Exception as e:
                            logger.error(f"Error parsing agent step data for {onboarding_id}: {e} - Data: {agent_step_data}")
                            continue
                    else:
                        logger.warning(f"Unrecognized agent step data format for {onboarding_id}: {type(agent_step_data)}")
                        continue

                    if agent_step_obj.step_name in current_steps_map:
                        current_steps_map[agent_step_obj.step_name].status = agent_step_obj.status
                        current_steps_map[agent_step_obj.step_name].status.last_updated = datetime.utcnow()
                    else:
                        process.verification_steps.append(agent_step_obj)

            MOCK_ONBOARDING_DB[onboarding_id] = process
            logger.info(f"Background task completed for onboarding_id: {onboarding_id}. DB updated.")
        else:
            logger.warning(f"Background task for {onboarding_id}: Process object not found in DB for update.")
    except Exception as e:
        logger.error(f"Error in background task for onboarding_id {onboarding_id}: {e}", exc_info=True)
        if process:
            process.status = "RequiresManualIntervention" # type: ignore
            process.message = f"An unexpected error occurred during processing: {str(e)}"
            process.last_updated_at = datetime.utcnow()
            MOCK_ONBOARDING_DB[onboarding_id] = process
            logger.info(f"Onboarding process {onboarding_id} status updated to RequiresManualIntervention due to error.")


# --- FastAPI Application ---
app = FastAPI(
    title="Customer Onboarding Agent API",
    description="Handles KYC, verification, and account creation for new bank customers.",
    version="0.1.2", # Incremented version
    contact={
        "name": "Core Banking AI Team",
        "email": "ai-devs@examplebank.ng",
    },
    license_info={
        "name": "Proprietary", # Replace with actual license if applicable
    }
)

# --- API Endpoints ---
@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Customer Onboarding Agent. Provides basic status."""
    logger.info("Root endpoint accessed.")
    return {"message": "Customer Onboarding Agent is running. See /docs for API details."}

@app.post("/onboardings/", response_model=OnboardingStatusResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Onboarding"])
async def initiate_onboarding_endpoint(request: OnboardingRequest, background_tasks: BackgroundTasks):
    """
    Initiates a new customer onboarding process.

    Accepts customer details and document information to start the KYC workflow.
    The actual verification and decisioning process is handled asynchronously
    by the AI agent in the background.
    """
    logger.info(f"Received onboarding request for: {request.first_name} {request.last_name}")

    # Pydantic performs validation on `request` based on `OnboardingRequest` schema.
    # If validation fails, FastAPI automatically returns a 422 Unprocessable Entity error.

    try:
        new_process = OnboardingProcess(
            requested_tier=request.requested_account_tier,
            verification_steps=[
                VerificationStepResult(step_name="BVNVerification"),
                VerificationStepResult(step_name="NINVerification"),
                VerificationStepResult(step_name="IDDocumentCheck"),
                VerificationStepResult(step_name="FaceMatch"),
                VerificationStepResult(step_name="AddressVerification",
                                       status=VerificationStatus(status="NotStarted" if request.requested_account_tier.tier in ["Tier2", "Tier3"] else "NotApplicable")), # type: ignore
                VerificationStepResult(step_name="AMLScreening")
            ]
        )
        MOCK_ONBOARDING_DB[new_process.onboarding_id] = new_process

        # Schedule the agent workflow to run in the background
        background_tasks.add_task(run_agent_workflow_background, new_process.onboarding_id, new_process, request)

        logger.info(f"API: Initiated onboarding: {new_process.onboarding_id} for {request.first_name} {request.last_name}. Background task scheduled.")
        return new_process
    except Exception as e:
        logger.error(f"Failed to initiate onboarding process: {e}", exc_info=True)
        # This is a server-side error during the setup of the process, not client input error.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate onboarding process due to an internal error: {str(e)}"
        )

@app.get("/onboardings/{onboarding_id}/status", response_model=OnboardingStatusResponse, tags=["Onboarding"])
async def get_onboarding_status_endpoint(onboarding_id: str):
    """
    Retrieves the current status of an ongoing customer onboarding process
    using its unique `onboarding_id`.
    """
    logger.info(f"Fetching status for onboarding_id: {onboarding_id}")
    process = MOCK_ONBOARDING_DB.get(onboarding_id)

    if not process:
        logger.warning(f"Onboarding process with id {onboarding_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding process not found.")

    # The MOCK_ONBOARDING_DB is updated by the background task.
    # For a more robust system, this might involve querying a database or task manager.
    # Example of fetching more current status from agent if it had a direct queryable state:
    # try:
    #     agent_status_update = await get_onboarding_status_from_agent(onboarding_id)
    #     if agent_status_update and agent_status_update.get("last_updated_at") > process.last_updated_at:
    #         logger.info(f"Found more recent status from agent for {onboarding_id}. Merging.")
    #         # ... (merge logic) ...
    # except Exception as e:
    #     logger.error(f"Could not poll agent for status update on {onboarding_id}: {e}")

    logger.info(f"API: Fetched status for onboarding: {onboarding_id}. Current status: {process.status}")
    return process

# --- Main block for Uvicorn ---
if __name__ == "__main__":
    # This is for informational purposes; use Uvicorn directly for development/production.
    logger.info("Customer Onboarding Agent FastAPI application. To run, use Uvicorn:")
    logger.info("uvicorn core_banking_agents.agents.customer_onboarding_agent.main:app --reload --port 8001")
    # Example: import uvicorn
    # uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True) # if this file was at root of module.
    # Correct way from project root: uvicorn core_banking_agents.agents.customer_onboarding_agent.main:app --reload --port 8001
    pass
