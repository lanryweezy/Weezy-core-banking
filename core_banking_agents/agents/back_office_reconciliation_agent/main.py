# FastAPI app for Back Office Reconciliation Agent
from fastapi import FastAPI, BackgroundTasks
# from .schemas import ReconciliationTaskInput, ReconciliationReportOutput

app = FastAPI(
    title="Back Office Reconciliation Agent API",
    description="Matches internal ledger with external transaction logs (e.g., Paystack, Interswitch).",
    version="0.1.0"
)

# async def run_reconciliation_in_background(task_details: dict):
#     from .agent import run_reconciliation_workflow
#     run_reconciliation_workflow(task_details)


@app.get("/")
async def root():
    return {"message": "Back Office Reconciliation Agent is running."}

# @app.post("/start-reconciliation", response_model=dict) # Simple ack response
# async def start_reconciliation_task(task_input: ReconciliationTaskInput, background_tasks: BackgroundTasks):
#     # This would typically be triggered by a scheduler or an event (e.g., end-of-day)
#     # For API-triggered reconciliation:
#     # background_tasks.add_task(run_reconciliation_in_background, task_input.dict())
#     # return {"task_id": task_input.task_id, "status": "Scheduled", "message": "Reconciliation task scheduled."}
#     return {"task_id": "mock_task_id", "status": "Scheduled", "message": "Not Implemented"}


# @app.get("/reconciliation-status/{task_id}", response_model=ReconciliationReportOutput)
# async def get_reconciliation_status(task_id: str):
#     # from .memory import get_reconciliation_report # Assuming report is stored in memory/db
#     # report = get_reconciliation_report(task_id)
#     # if not report:
#     #     return {"task_id": task_id, "status": "NotFound", "summary": {}}
#     # return report
#     return {"task_id": task_id, "status": "MockStatusComplete", "summary": {"total_internal": 100, "total_external": 100, "matched": 98, "unmatched_internal": 2, "unmatched_external": 2}, "unmatched_items": []}

print("Back Office Reconciliation Agent FastAPI app placeholder.")
