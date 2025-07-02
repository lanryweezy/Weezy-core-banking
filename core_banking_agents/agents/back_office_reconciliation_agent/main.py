# FastAPI app for Back Office Reconciliation Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from typing import Dict, Any, List
import logging
from datetime import datetime
import asyncio # For mock background task
import random # For mock background task

from .schemas import (
    ReconciliationTaskInput, ReconciliationReportOutput, ReconciliationStatus,
    ReconciliationSummaryStats # Import if used explicitly for construction
)
# Import agent interaction logic
from .agent import start_reconciliation_workflow_async

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Stores (Mock Databases) ---
MOCK_RECON_TASKS_DB: Dict[str, ReconciliationTaskInput] = {} # task_id -> ReconciliationTaskInput
MOCK_RECON_REPORTS_DB: Dict[str, ReconciliationReportOutput] = {} # task_id -> ReconciliationReportOutput

app = FastAPI(
    title="Back Office Reconciliation Agent API (Agent Integrated - Mocked)",
    description="Manages and executes reconciliation tasks via an AI Agent.",
    version="0.1.1", # Incremented version
    contact={
        "name": "Core Banking Operations AI Team",
        "email": "ai-recon@examplebank.ng",
    },
)

# --- Background Task Runner ---
async def run_reconciliation_background(task_input: ReconciliationTaskInput):
    """
    Wrapper to run the back-office reconciliation agent workflow in the background
    and update the mock reports store with the detailed report.
    """
    task_id = task_input.task_id
    logger.info(f"Background task started for reconciliation task: {task_id}")
    try:
        # Call the agent's workflow function
        # This function returns a dictionary aligning with ReconciliationReportOutput fields
        agent_report_dict = await start_reconciliation_workflow_async(task_input)

        if task_id:
            try:
                # Create/Update the ReconciliationReportOutput object from the agent's dictionary result
                # The agent_report_dict should contain all necessary fields, including task_id and report_id.
                # Pydantic will use default_factory for report_id if not in agent_report_dict, but agent should provide it.
                # Ensure dates from agent_report_dict are actual date/datetime objects or valid ISO strings for Pydantic.

                # Convert date strings back to date objects if agent returned strings
                for date_field in ["reconciliation_date_from", "reconciliation_date_to"]:
                    if date_field in agent_report_dict and isinstance(agent_report_dict[date_field], str):
                        agent_report_dict[date_field] = date.fromisoformat(agent_report_dict[date_field])
                if "generation_timestamp" in agent_report_dict and isinstance(agent_report_dict["generation_timestamp"], str):
                     agent_report_dict["generation_timestamp"] = datetime.fromisoformat(agent_report_dict["generation_timestamp"].replace("Z","+00:00"))


                final_report = ReconciliationReportOutput(**agent_report_dict)
                MOCK_RECON_REPORTS_DB[task_id] = final_report # Use task_id as key for report storage

                logger.info(f"Background task completed for task {task_id}. Report Status: {final_report.status}, Message: {final_report.status_message}")
            except Exception as e:
                logger.error(f"Error parsing agent report for task {task_id}: {e}. Data: {agent_report_dict}", exc_info=True)
                if task_id in MOCK_RECON_REPORTS_DB: # Update existing entry with error
                    current_report = MOCK_RECON_REPORTS_DB[task_id]
                    current_report.status = "Failed" # type: ignore
                    current_report.status_message = f"Error processing agent's report result: {str(e)}"
                    current_report.generation_timestamp = datetime.utcnow()
                    current_report.error_log = (current_report.error_log or []) + [f"Parsing agent output error: {str(e)}"]
                # else, could create a new error report entry if initial was lost

    except Exception as e:
        logger.error(f"Critical error in reconciliation background task for task {task_id}: {e}", exc_info=True)
        if task_id in MOCK_RECON_REPORTS_DB:
            report_entry = MOCK_RECON_REPORTS_DB[task_id]
            report_entry.status = "Failed" # type: ignore
            report_entry.status_message = f"Agent workflow failed critically: {str(e)}"
            report_entry.generation_timestamp = datetime.utcnow()
            report_entry.error_log = (report_entry.error_log or []) + [f"Critical agent workflow error: {str(e)}"]


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Back Office Reconciliation Agent."""
    logger.info("Back Office Reconciliation Agent root endpoint accessed.")
    return {"message": "Back Office Reconciliation Agent is running. Agent integration active (mocked). See /docs."}

@app.post("/reconciliation/tasks", response_model=ReconciliationReportOutput, status_code=status.HTTP_202_ACCEPTED, tags=["Reconciliation Tasks"])
async def create_reconciliation_task_endpoint( # Renamed
    task_input: ReconciliationTaskInput,
    background_tasks: BackgroundTasks
):
    """
    Creates and schedules a new back-office reconciliation task.
    The AI agent performs the reconciliation asynchronously.
    """
    task_id = task_input.task_id # Use client-provided or Pydantic default_factory generated ID
    logger.info(f"API: Received request to create reconciliation task: ID {task_id} for dates {task_input.reconciliation_date_from} to {task_input.reconciliation_date_to}")

    if task_id in MOCK_RECON_REPORTS_DB and MOCK_RECON_REPORTS_DB[task_id].status not in ["Pending", "Scheduled"]: # type: ignore
        logger.warning(f"Reconciliation task ID {task_id} already processed or actively running. Returning current report.")
        return MOCK_RECON_REPORTS_DB[task_id]
    elif task_id in MOCK_RECON_TASKS_DB: # If task exists but no report yet, or still pending.
         logger.warning(f"Reconciliation task ID {task_id} already submitted and is pending/scheduled.")
         # Return the initial report if it exists, otherwise raise conflict or re-initiate.
         if task_id in MOCK_RECON_REPORTS_DB:
             return MOCK_RECON_REPORTS_DB[task_id]
         # else: fall through to create initial report and schedule task. This path implies a previous attempt failed before creating initial report.

    MOCK_RECON_TASKS_DB[task_id] = task_input

    initial_report = ReconciliationReportOutput(
        report_id=f"RECREP-{task_id.split('-')[-1]}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}", # Generate a unique report_id
        task_id=task_id,
        reconciliation_date_from=task_input.reconciliation_date_from,
        reconciliation_date_to=task_input.reconciliation_date_to,
        status="Scheduled", # type: ignore
        status_message="Reconciliation task has been scheduled for processing by the AI agent."
    )
    MOCK_RECON_REPORTS_DB[task_id] = initial_report # Store by task_id for easy retrieval

    background_tasks.add_task(run_reconciliation_background, task_input)
    logger.info(f"API: Reconciliation task {task_id} created and scheduled. Report ID: {initial_report.report_id}")

    return initial_report

@app.get("/reconciliation/tasks/{task_id}/report", response_model=ReconciliationReportOutput, tags=["Reconciliation Tasks"])
async def get_reconciliation_task_report_endpoint(task_id: str): # Renamed
    """
    Retrieves the latest report (status and results) for a specific reconciliation task ID.
    """
    logger.info(f"API: Fetching report for reconciliation task ID: {task_id}")

    report = MOCK_RECON_REPORTS_DB.get(task_id) # Reports are stored by task_id
    if not report:
        if task_id in MOCK_RECON_TASKS_DB: # Task was submitted but report not generated yet or error
            logger.warning(f"Report for task ID {task_id} not yet available, task exists. Returning placeholder pending.")
            # This should ideally be the initial_report created during POST.
            # If it's missing, something went wrong or it hasn't been created by POST yet.
            # For robustness, create a minimal pending if truly missing.
            task_details = MOCK_RECON_TASKS_DB[task_id]
            return ReconciliationReportOutput(
                task_id=task_id,
                reconciliation_date_from=task_details.reconciliation_date_from,
                reconciliation_date_to=task_details.reconciliation_date_to,
                status="Pending", # type: ignore
                status_message="Report generation is pending or an initial error occurred."
            )
        logger.warning(f"Reconciliation task/report with ID {task_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reconciliation task/report with ID {task_id} not found.")

    logger.info(f"API: Returning report for task {task_id}. Report ID: {report.report_id}, Status: {report.status}")
    return report

# --- Main block for Uvicorn ---
if __name__ == "__main__":
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Back Office Reconciliation Agent FastAPI application (Agent Integrated - Mocked). To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.back_office_reconciliation_agent.main:app --reload --port 8008`")
    pass
