# FastAPI app for Credit Analyst Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from typing import Dict, Any
import logging
from datetime import datetime
import asyncio # For the mock background task sleep

from .schemas import (
    LoanApplicationInput, LoanAssessmentOutput, LoanApplicationStatusResponse,
    LoanDecisionType # Ensure this is imported if used directly
)
# Import agent interaction logic
from .agent import start_credit_analysis_workflow_async
# Placeholder: from .agent import get_loan_assessment_from_workflow # If we had a separate getter

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Store (Mock Database for Loan Applications and Assessments) ---
MOCK_LOAN_APPLICATIONS_DB: Dict[str, LoanAssessmentOutput] = {} # Stores application_id -> LoanAssessmentOutput

app = FastAPI(
    title="Credit Analyst Agent API (Agent Integrated - Mocked)",
    description="Assesses loan applications, providing decisions and risk analysis via an AI Agent.",
    version="0.1.1", # Incremented version
    contact={
        "name": "Core Banking AI Team",
        "email": "ai-devs@examplebank.ng",
    },
)

# --- Background Task Runner ---
async def run_credit_analysis_background(application_id: str, application_input: LoanApplicationInput):
    logger.info(f"Background task started for credit analysis: {application_id}")
    try:
        # Call the agent's workflow function
        agent_assessment_dict = await start_credit_analysis_workflow_async(application_id, application_input)

        # Validate and update the MOCK_LOAN_APPLICATIONS_DB with the detailed assessment
        # The agent_assessment_dict should align with LoanAssessmentOutput fields
        if application_id in MOCK_LOAN_APPLICATIONS_DB:
            try:
                # Create a new LoanAssessmentOutput object from the agent's dictionary result
                # This ensures that the data stored matches the schema.
                updated_assessment = LoanAssessmentOutput(**agent_assessment_dict)
                MOCK_LOAN_APPLICATIONS_DB[application_id] = updated_assessment
                logger.info(f"Background task completed for {application_id}. Assessment decision: {updated_assessment.decision}")
            except Exception as e: # Catch Pydantic validation errors or others
                logger.error(f"Error parsing agent assessment for {application_id}: {e}. Data: {agent_assessment_dict}", exc_info=True)
                # Update status to reflect error during agent processing or data parsing
                current_assessment = MOCK_LOAN_APPLICATIONS_DB[application_id]
                current_assessment.decision = "PendingReview" # type: ignore # Or a new "ErrorInProcessing" status
                current_assessment.decision_reason = f"Error processing agent's analysis result: {str(e)}"
                current_assessment.assessment_timestamp = datetime.utcnow()
        else:
            logger.warning(f"Application ID {application_id} not found in DB after agent processing (should not happen).")

    except Exception as e:
        logger.error(f"Critical error in credit analysis background task for {application_id}: {e}", exc_info=True)
        if application_id in MOCK_LOAN_APPLICATIONS_DB:
            assessment = MOCK_LOAN_APPLICATIONS_DB[application_id]
            assessment.decision = "PendingReview" # type: ignore # Or a specific error status
            assessment.decision_reason = f"Agent workflow failed critically: {str(e)}"
            assessment.assessment_timestamp = datetime.utcnow()


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Credit Analyst Agent."""
    logger.info("Credit Analyst Agent root endpoint accessed.")
    return {"message": "Credit Analyst Agent is running. Agent integration active (mocked). See /docs for API details."}

@app.post("/loan-applications/", response_model=LoanApplicationStatusResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Loan Applications"])
async def submit_loan_application(
    application_input: LoanApplicationInput,
    background_tasks: BackgroundTasks
):
    """
    Submits a new loan application for assessment by the AI Credit Analyst.
    The actual analysis is performed asynchronously by the agent.
    """
    app_id = application_input.application_id
    logger.info(f"API: Received loan application submission: ID {app_id} for {application_input.applicant_details.first_name} {application_input.applicant_details.last_name}")

    if app_id in MOCK_LOAN_APPLICATIONS_DB:
        logger.warning(f"Loan application with ID {app_id} already exists.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Loan application with ID {app_id} already exists.")

    # Create an initial assessment record with "PendingReview" status
    # The agent workflow will provide the full, detailed assessment later.
    initial_assessment = LoanAssessmentOutput(
        application_id=app_id,
        # assessment_id is auto-generated
        decision="PendingReview", # type: ignore
        decision_reason="Application received and queued for AI credit analysis.",
        # Other fields will be populated by the agent's background task.
    )
    MOCK_LOAN_APPLICATIONS_DB[app_id] = initial_assessment

    # Schedule the agent workflow to run in the background
    background_tasks.add_task(run_credit_analysis_background, app_id, application_input)
    logger.info(f"API: Loan application {app_id} accepted. Credit analysis agent workflow scheduled in background.")

    return initial_assessment # Return the initial "PendingReview" state

@app.get("/loan-applications/{application_id}/status", response_model=LoanApplicationStatusResponse, tags=["Loan Applications"])
async def get_loan_application_status(application_id: str):
    """
    Retrieves the current status and assessment details of a loan application.
    The assessment is updated asynchronously by the AI agent.
    """
    logger.info(f"API: Fetching status for loan application ID: {application_id}")

    assessment = MOCK_LOAN_APPLICATIONS_DB.get(application_id)
    if not assessment:
        logger.warning(f"Loan application with ID {application_id} not found in MOCK_DB.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Loan application with ID {application_id} not found.")

    logger.info(f"API: Returning status for loan application {application_id}. Current Decision: {assessment.decision}, Reason: {assessment.decision_reason}")
    return assessment

# --- Main block for Uvicorn ---
if __name__ == "__main__":
    logger.info("Credit Analyst Agent FastAPI application (Agent Integrated - Mocked). To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.credit_analyst_agent.main:app --reload --port 8003`")
    pass
