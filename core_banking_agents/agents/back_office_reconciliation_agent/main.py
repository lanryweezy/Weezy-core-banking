# FastAPI app for Back Office Reconciliation Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from typing import Dict, Any, List
import logging
from datetime import datetime
import asyncio # For mock background task

from .schemas import (
    ReconciliationTaskInput, ReconciliationReportOutput, ReconciliationStatus
)
# Placeholder for agent interaction logic
# from .agent import start_reconciliation_workflow_async

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Stores (Mock Databases) ---
MOCK_RECON_TASKS_DB: Dict[str, ReconciliationTaskInput] = {} # task_id -> ReconciliationTaskInput
MOCK_RECON_REPORTS_DB: Dict[str, ReconciliationReportOutput] = {} # task_id -> ReconciliationReportOutput

app = FastAPI(
    title="Back Office Reconciliation Agent API",
    description="Manages and executes reconciliation tasks between internal ledgers and external data sources (e.g., payment processors, NIBSS reports).",
    version="0.1.0",
    contact={
        "name": "Core Banking Operations AI Team",
        "email": "ai-recon@examplebank.ng",
    },
)

# --- Background Task Runner (Placeholder) ---
# async def run_reconciliation_background(task_input: ReconciliationTaskInput, initial_report: ReconciliationReportOutput):
#     task_id = task_input.task_id
#     logger.info(f"Background task started for reconciliation task: {task_id}")
#     # agent_report_data_dict = await start_reconciliation_workflow_async(task_input.model_dump())
#     # MOCK_RECON_REPORTS_DB[task_id] = ReconciliationReportOutput(**agent_report_data_dict)
#     # logger.info(f"Background task completed for task {task_id}. Report status: {agent_report_data_dict.get('status')}")
#     # Simulate agent processing:
#     import random
#     await asyncio.sleep(random.randint(10,30)) # Simulate longer processing time for recon

#     # This is a very basic mock update. Real agent would provide detailed report.
#     if task_id in MOCK_RECON_REPORTS_DB:
#         current_report = MOCK_RECON_REPORTS_DB[task_id]
#         current_report.status = random.choice(["Completed", "CompletedWithDiscrepancies", "Failed"]) # type: ignore
#         current_report.status_message = f"Mock agent reconciliation result: {current_report.status}"
#         current_report.generation_timestamp = datetime.utcnow()
#         if current_report.status != "Failed":
#             # Populate with some mock summary stats
#             current_report.summary_stats = ReconciliationSummaryStats( # type: ignore
#                 total_internal_records_processed=random.randint(900,1100),
#                 total_external_records_processed=random.randint(900,1100),
#                 matched_records_count=random.randint(850,950),
#                 # ... other stats
#             )
#         logger.info(f"Background task (mock) updated report for task {task_id} to status {current_report.status}")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Back Office Reconciliation Agent."""
    logger.info("Back Office Reconciliation Agent root endpoint accessed.")
    return {"message": "Back Office Reconciliation Agent is running. See /docs for API details."}

@app.post("/reconciliation/tasks", response_model=ReconciliationReportOutput, status_code=status.HTTP_202_ACCEPTED, tags=["Reconciliation Tasks"])
async def create_reconciliation_task(
    task_input: ReconciliationTaskInput,
    background_tasks: BackgroundTasks
):
    """
    Creates and schedules a new back-office reconciliation task.
    The AI agent will perform the reconciliation asynchronously based on the provided
    data sources and matching rules.
    """
    task_id = task_input.task_id
    logger.info(f"API: Received request to create reconciliation task: ID {task_id} for dates {task_input.reconciliation_date_from} to {task_input.reconciliation_date_to}")

    if task_id in MOCK_RECON_TASKS_DB or task_id in MOCK_RECON_REPORTS_DB:
        logger.warning(f"Reconciliation task with ID {task_id} already exists or is being processed.")
        # If a report exists and is completed, could return that.
        if task_id in MOCK_RECON_REPORTS_DB and MOCK_RECON_REPORTS_DB[task_id].status not in ["Pending", "Scheduled", "Running"]:
            return MOCK_RECON_REPORTS_DB[task_id]
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Reconciliation task ID {task_id} already exists or is active.")

    MOCK_RECON_TASKS_DB[task_id] = task_input

    # Create an initial report output with "Scheduled" status
    initial_report = ReconciliationReportOutput(
        task_id=task_id,
        reconciliation_date_from=task_input.reconciliation_date_from,
        reconciliation_date_to=task_input.reconciliation_date_to,
        status="Scheduled", # type: ignore
        status_message="Reconciliation task has been scheduled for processing by the AI agent."
    )
    MOCK_RECON_REPORTS_DB[task_id] = initial_report

    # TODO: Schedule the actual agent workflow in the background
    # background_tasks.add_task(run_reconciliation_background, task_input, initial_report)
    logger.info(f"API: Reconciliation task {task_id} created and scheduled (mock background task).")

    return initial_report

@app.get("/reconciliation/tasks/{task_id}/report", response_model=ReconciliationReportOutput, tags=["Reconciliation Tasks"])
async def get_reconciliation_task_report(task_id: str):
    """
    Retrieves the latest report (status and results) for a specific reconciliation task.
    Poll this endpoint for updates after creating a task.
    """
    logger.info(f"API: Fetching report for reconciliation task ID: {task_id}")

    report = MOCK_RECON_REPORTS_DB.get(task_id)
    if not report:
        # Check if the task input exists but report not yet generated (implies error before first report save)
        if task_id in MOCK_RECON_TASKS_DB:
            logger.warning(f"Reconciliation report for task ID {task_id} not yet available, but task exists. Returning pending state.")
            # Return a generic pending if somehow initial report wasn't saved but task is known
            return ReconciliationReportOutput(
                task_id=task_id,
                reconciliation_date_from=MOCK_RECON_TASKS_DB[task_id].reconciliation_date_from,
                reconciliation_date_to=MOCK_RECON_TASKS_DB[task_id].reconciliation_date_to,
                status="Pending", # type: ignore
                status_message="Report generation is pending or an issue occurred."
            )
        logger.warning(f"Reconciliation task or report with ID {task_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Reconciliation task/report with ID {task_id} not found.")

    logger.info(f"API: Returning report for task {task_id}. Status: {report.status}")
    return report

# --- Main block for Uvicorn ---
if __name__ == "__main__":
    logger.info("Back Office Reconciliation Agent FastAPI application. To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.back_office_reconciliation_agent.main:app --reload --port 8008`") # Assuming port 8008
    pass
