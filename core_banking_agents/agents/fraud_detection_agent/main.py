# FastAPI app for Fraud Detection Agent
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from typing import Dict, Any, List
import logging
from datetime import datetime

from .schemas import TransactionEventInput, FraudAnalysisOutput, RiskLevel, FraudActionRecommended
# Placeholder for agent interaction logic
# from .agent import analyze_transaction_for_fraud_async

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- In-memory Store (Mock Log for Transaction Events) ---
# In a real system, events would likely come from a message queue (e.g., Kafka)
# and results stored in a database or another queue.
MOCK_TRANSACTION_EVENTS_LOG: List[Dict[str, Any]] = []
MOCK_FRAUD_ANALYSIS_RESULTS: Dict[str, FraudAnalysisOutput] = {} # event_id -> FraudAnalysisOutput

app = FastAPI(
    title="Fraud Detection Agent API",
    description="Monitors real-time transactions for suspicious activity and provides fraud analysis.",
    version="0.1.0",
    contact={
        "name": "Core Banking AI Security Team",
        "email": "ai-security@examplebank.ng",
    },
)

# --- Background Task Runner (Placeholder) ---
# async def run_fraud_analysis_background(event: TransactionEventInput):
#     logger.info(f"Background task started for fraud analysis of event: {event.event_id}")
#     # agent_analysis_result = await analyze_transaction_for_fraud_async(event.model_dump())
#     # MOCK_FRAUD_ANALYSIS_RESULTS[event.event_id] = FraudAnalysisOutput(**agent_analysis_result)
#     # logger.info(f"Background task completed for event {event.event_id}. Analysis result: {agent_analysis_result.get('risk_level')}")
#     # Simulate agent processing:
#     import time, random
#     await asyncio.sleep(random.randint(1,3)) # Simulate processing time

#     mock_risk = random.choice(["Low", "Medium", "High", "Critical"])
#     mock_score = random.uniform(0,100)
#     mock_action = random.choice(["Allow", "FlagForReview", "BlockTransaction"])

#     analysis_result = FraudAnalysisOutput(
#         event_id=event.event_id,
#         fraud_score=mock_score,
#         risk_level=mock_risk, # type: ignore
#         recommended_action=mock_action, # type: ignore
#         reason_for_action=f"Mock analysis: {mock_risk} risk due to simulated factors.",
#         status="Completed"
#     )
#     MOCK_FRAUD_ANALYSIS_RESULTS[event.event_id] = analysis_result
#     logger.info(f"Background task (mock) completed for {event.event_id}. Risk: {mock_risk}")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint for the Fraud Detection Agent."""
    logger.info("Fraud Detection Agent root endpoint accessed.")
    return {"message": "Fraud Detection Agent is running. Submit transactions to /events/transaction for analysis. See /docs."}

@app.post("/events/transaction", response_model=FraudAnalysisOutput, status_code=status.HTTP_202_ACCEPTED, tags=["Fraud Analysis"])
async def submit_transaction_event(
    event_input: TransactionEventInput,
    background_tasks: BackgroundTasks # To simulate async agent processing
):
    """
    Submits a financial transaction event for fraud analysis.
    The analysis is typically performed asynchronously by the AI Fraud Detection Agent.
    This endpoint acknowledges receipt and returns an initial pending status.
    """
    logger.info(f"Received transaction event for analysis: ID {event_input.event_id}, Type {event_input.transaction_type}, Amount {event_input.amount} {event_input.currency}")

    if event_input.event_id in MOCK_FRAUD_ANALYSIS_RESULTS:
        logger.warning(f"Transaction event with ID {event_input.event_id} has already been submitted.")
        # Optionally, return the existing analysis or an error. For now, allow re-submission for simplicity of mock.
        # raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Event ID {event_input.event_id} already processed or pending.")

    # Log the event (simplified)
    MOCK_TRANSACTION_EVENTS_LOG.append({
        "event_id": event_input.event_id,
        "transaction_id": event_input.transaction_id,
        "timestamp": event_input.timestamp,
        "status": "ReceivedForAnalysis"
    })
    if len(MOCK_TRANSACTION_EVENTS_LOG) > 1000: # Keep log size manageable for mock
        MOCK_TRANSACTION_EVENTS_LOG.pop(0)

    # Create an initial "PendingAnalysis" response
    initial_analysis = FraudAnalysisOutput(
        event_id=event_input.event_id,
        status="PendingAnalysis",
        reason_for_action="Transaction event received and queued for fraud analysis by AI agent."
    )
    MOCK_FRAUD_ANALYSIS_RESULTS[event_input.event_id] = initial_analysis

    # TODO: Schedule the actual agent workflow in the background
    # background_tasks.add_task(run_fraud_analysis_background, event_input)
    logger.info(f"Transaction event {event_input.event_id} accepted. Fraud analysis agent workflow scheduled (mock background task).")

    return initial_analysis

@app.get("/analysis/{event_id}", response_model=FraudAnalysisOutput, tags=["Fraud Analysis"])
async def get_fraud_analysis_result(event_id: str):
    """
    Retrieves the fraud analysis result for a given event ID.
    The analysis is performed asynchronously. Poll this endpoint for updates.
    """
    logger.info(f"Fetching fraud analysis result for event ID: {event_id}")

    analysis_result = MOCK_FRAUD_ANALYSIS_RESULTS.get(event_id)
    if not analysis_result:
        logger.warning(f"Fraud analysis for event ID {event_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fraud analysis for event ID {event_id} not found. Ensure the event was submitted first.")

    logger.info(f"Returning analysis for event {event_id}. Status: {analysis_result.status}, Risk: {analysis_result.risk_level}")
    return analysis_result


# --- Main block for Uvicorn ---
if __name__ == "__main__":
    logger.info("Fraud Detection Agent FastAPI application. To run, use Uvicorn from project root:")
    logger.info("`uvicorn core_banking_agents.agents.fraud_detection_agent.main:app --reload --port 8004`")
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8004) # If main.py is at root of module context for run
    pass
