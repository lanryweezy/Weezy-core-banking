# FastAPI app for Credit Analyst Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from typing import Dict, Any
import logging
from datetime import datetime

from .schemas import (
    LoanApplicationInput, LoanAssessmentOutput, LoanApplicationStatusResponse,
    LoanDecisionType
)
# Placeholder for agent interaction logic
# from .agent import start_credit_analysis_workflow_async, get_loan_assessment_from_workflow

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Store (Mock Database for Loan Applications and Assessments) ---
MOCK_LOAN_APPLICATIONS_DB: Dict[str, LoanAssessmentOutput] = {} # Stores application_id -> LoanAssessmentOutput

app = FastAPI(
    title="Credit Analyst Agent API",
    description="Assesses loan applications, providing decisions and risk analysis.",
    version="0.1.0",
    contact={
        "name": "Core Banking AI Team",
        "email": "ai-devs@examplebank.ng",
    },
)

# --- Background Task Runner (Placeholder) ---
# async def run_credit_analysis_background(application_id: str, application_input: LoanApplicationInput):
#     logger.info(f"Background task started for credit analysis: {application_id}")
#     # agent_assessment = await start_credit_analysis_workflow_async(application_id, application_input.model_dump())
#     # MOCK_LOAN_APPLICATIONS_DB[application_id] = LoanAssessmentOutput(**agent_assessment) # Assuming agent returns full assessment
#     # logger.info(f"Background task completed for {application_id}. Assessment: {agent_assessment.get('decision')}")
#     # Simulate agent processing and update:
#     import time, random
#     await asyncio.sleep(random.randint(5,15)) # Simulate processing time

#     # This is a very basic mock update. Real agent would provide detailed assessment.
#     if application_id in MOCK_LOAN_APPLICATIONS_DB:
#         current_assessment = MOCK_LOAN_APPLICATIONS_DB[application_id]
#         current_assessment.decision = random.choice(["Approved", "Rejected", "ConditionalApproval"]) # type: ignore
#         current_assessment.decision_reason = f"Mock agent decision: {current_assessment.decision}"
#         current_assessment.assessment_timestamp = datetime.utcnow()
#         if current_assessment.decision == "Approved":
#             current_assessment.approved_loan_amount_ngn = application_input.loan_amount_requested_ngn * random.uniform(0.8, 1.0)
#         logger.info(f"Background task (mock) updated assessment for {application_id} to {current_assessment.decision}")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Credit Analyst Agent."""
    logger.info("Credit Analyst Agent root endpoint accessed.")
    return {"message": "Credit Analyst Agent is running. See /docs for API details."}

@app.post("/loan-applications/", response_model=LoanApplicationStatusResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Loan Applications"])
async def submit_loan_application(
    application_input: LoanApplicationInput,
    background_tasks: BackgroundTasks # To simulate async agent processing
):
    """
    Submits a new loan application for assessment by the AI Credit Analyst.
    The actual analysis is performed asynchronously.
    """
    app_id = application_input.application_id # Use ID from input or generate one if not provided by client
    logger.info(f"Received loan application submission: ID {app_id} for {application_input.applicant_details.first_name} {application_input.applicant_details.last_name}")

    if app_id in MOCK_LOAN_APPLICATIONS_DB:
        logger.warning(f"Loan application with ID {app_id} already exists.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Loan application with ID {app_id} already exists.")

    # Create an initial assessment record with "PendingReview" status
    initial_assessment = LoanAssessmentOutput(
        application_id=app_id,
        decision="PendingReview", # type: ignore
        decision_reason="Application received and queued for AI credit analysis.",
        # Copy relevant details from input if needed, or let agent populate them fully.
        # For now, agent will be responsible for populating the full assessment.
    )
    MOCK_LOAN_APPLICATIONS_DB[app_id] = initial_assessment

    # TODO: Schedule the actual agent workflow in the background
    # background_tasks.add_task(run_credit_analysis_background, app_id, application_input)
    logger.info(f"Loan application {app_id} accepted and queued for analysis (mock background task).")

    return initial_assessment # Return the initial "PendingReview" state

@app.get("/loan-applications/{application_id}/status", response_model=LoanApplicationStatusResponse, tags=["Loan Applications"])
async def get_loan_application_status(application_id: str):
    """
    Retrieves the current status and assessment details of a loan application.
    """
    logger.info(f"Fetching status for loan application ID: {application_id}")

    assessment = MOCK_LOAN_APPLICATIONS_DB.get(application_id)
    if not assessment:
        logger.warning(f"Loan application with ID {application_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Loan application with ID {application_id} not found.")

    # TODO: In a real system, this might poll an agent/task manager or query a DB updated by the agent.
    # For now, it returns the current state from MOCK_LOAN_APPLICATIONS_DB, which would be
    # updated by the (placeholder) background task.

    logger.info(f"Returning status for loan application {application_id}: Decision {assessment.decision}")
    return assessment

# --- Main block for Uvicorn ---
if __name__ == "__main__":
    logger.info("Credit Analyst Agent FastAPI application. To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.credit_analyst_agent.main:app --reload --port 8003`")
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8003) # For direct run, if main.py is at root of module context
    pass
