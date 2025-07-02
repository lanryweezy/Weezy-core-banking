# FastAPI app for Customer Onboarding Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks, Depends
from typing import Dict, Any
from datetime import datetime
import logging

from .schemas import OnboardingRequest, OnboardingStatusResponse, OnboardingProcess, VerificationStepResult, VerificationStatus, AccountTier
# Import agent interaction logic
from .agent import start_onboarding_process, get_onboarding_status_from_agent

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Store (Mock Database) ---
MOCK_ONBOARDING_DB: Dict[str, OnboardingProcess] = {}


# --- Background Task Runner ---
async def run_agent_workflow_background(onboarding_id: str, process: OnboardingProcess, request_data: OnboardingRequest):
    """
    Wrapper to run the agent workflow in the background and update the mock DB
    with detailed results from the CrewAI process.
    """
    logger.info(f"Background task started for onboarding_id: {onboarding_id}")
    try:
        # This call now returns a more detailed payload from the (mocked) CrewAI execution
        agent_update_payload = await start_onboarding_process(onboarding_id, request_data)

        if process:
            process.status = agent_update_payload.get("status", process.status) # type: ignore
            process.message = agent_update_payload.get("message", process.message)
            process.last_updated_at = agent_update_payload.get("last_updated_at", datetime.utcnow())

            achieved_tier_data = agent_update_payload.get("achieved_tier")
            if achieved_tier_data and isinstance(achieved_tier_data, dict) and "tier" in achieved_tier_data:
                process.achieved_tier = AccountTier(**achieved_tier_data)

            process.customer_id = agent_update_payload.get("customer_id", process.customer_id)

            # Update verification_steps with the detailed results from the agent
            agent_steps_payload = agent_update_payload.get("verification_steps")
            if isinstance(agent_steps_payload, list):
                new_verification_steps = []
                for step_payload in agent_steps_payload:
                    if isinstance(step_payload, dict):
                        try:
                            # Ensure status is also parsed correctly if it's a dict
                            status_payload = step_payload.get("status")
                            if isinstance(status_payload, dict):
                                step_payload["status"] = VerificationStatus(**status_payload)

                            new_verification_steps.append(VerificationStepResult(**step_payload))
                        except Exception as e:
                            logger.error(f"Error parsing verification step payload for {onboarding_id}: {e} - Data: {step_payload}")
                    elif isinstance(step_payload, VerificationStepResult): # if agent already returns Pydantic models
                        new_verification_steps.append(step_payload)
                process.verification_steps = new_verification_steps

            MOCK_ONBOARDING_DB[onboarding_id] = process
            logger.info(f"Background task completed for onboarding_id: {onboarding_id}. DB updated with agent results. Final status: {process.status}")
        else:
            logger.warning(f"Background task for {onboarding_id}: Process object not found in DB for update after agent execution.")
    except Exception as e:
        logger.error(f"Error in background task for onboarding_id {onboarding_id}: {e}", exc_info=True)
        if process:
            process.status = "RequiresManualIntervention" # type: ignore
            process.message = f"An critical error occurred during agent processing: {str(e)}"
            process.last_updated_at = datetime.utcnow()
            # Clear out steps as they might be inconsistent
            # process.verification_steps = [] # Or mark all as error
            for step in process.verification_steps:
                step.status = VerificationStatus(status="Error", message="Agent processing failed")

            MOCK_ONBOARDING_DB[onboarding_id] = process
            logger.info(f"Onboarding process {onboarding_id} status updated to RequiresManualIntervention due to agent error.")


# --- FastAPI Application ---
app = FastAPI(
    title="Customer Onboarding Agent API",
    description="Handles KYC, verification, and account creation for new bank customers using CrewAI.",
    version="0.1.3", # Incremented version
    contact={
        "name": "Core Banking AI Team",
        "email": "ai-devs@examplebank.ng",
    },
    license_info={
        "name": "Proprietary",
    }
)

# --- API Endpoints ---
@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Customer Onboarding Agent. Provides basic status."""
    logger.info("Root endpoint accessed.")
    return {"message": "Customer Onboarding Agent is running. CrewAI integration active (mocked). See /docs for API details."}

@app.post("/onboardings/", response_model=OnboardingStatusResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Onboarding"])
async def initiate_onboarding_endpoint(request: OnboardingRequest, background_tasks: BackgroundTasks):
    """
    Initiates a new customer onboarding process.
    The AI agent handles verification and decisioning asynchronously.
    """
    logger.info(f"Received onboarding request for: {request.first_name} {request.last_name}, Tier: {request.requested_account_tier.tier}")

    try:
        # Initial process state before agent runs
        initial_verification_steps = [
            VerificationStepResult(step_name="BVNVerification"),
            VerificationStepResult(step_name="NINVerification"),
            VerificationStepResult(step_name="IDDocumentCheck"),
            VerificationStepResult(step_name="FaceMatch"),
            VerificationStepResult(
                step_name="AddressVerification",
                status=VerificationStatus(
                    status="NotStarted" if request.requested_account_tier.tier in ["Tier2", "Tier3"] else "NotApplicable" # type: ignore
                )
            ),
            VerificationStepResult(step_name="AMLScreening")
        ]

        new_process = OnboardingProcess(
            requested_tier=request.requested_account_tier,
            verification_steps=initial_verification_steps,
            status="Initiated",
            message="Onboarding initiated. Agent processing scheduled."
        )
        MOCK_ONBOARDING_DB[new_process.onboarding_id] = new_process

        background_tasks.add_task(run_agent_workflow_background, new_process.onboarding_id, new_process, request)

        logger.info(f"API: Initiated onboarding: {new_process.onboarding_id} for {request.first_name} {request.last_name}. Background task scheduled.")
        return new_process
    except Exception as e:
        logger.error(f"Failed to initiate onboarding process: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate onboarding process due to an internal error: {str(e)}"
        )

@app.get("/onboardings/{onboarding_id}/status", response_model=OnboardingStatusResponse, tags=["Onboarding"])
async def get_onboarding_status_endpoint(onboarding_id: str):
    """
    Retrieves the current status of an ongoing customer onboarding process.
    """
    logger.info(f"Fetching status for onboarding_id: {onboarding_id}")
    process = MOCK_ONBOARDING_DB.get(onboarding_id)

    if not process:
        logger.warning(f"Onboarding process with id {onboarding_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding process not found.")

    logger.info(f"API: Fetched status for onboarding: {onboarding_id}. Current status: {process.status}, Message: {process.message}")
    return process

# --- Main block for Uvicorn ---
if __name__ == "__main__":
    logger.info("Customer Onboarding Agent FastAPI application. To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.customer_onboarding_agent.main:app --reload --port 8001`")
    pass
