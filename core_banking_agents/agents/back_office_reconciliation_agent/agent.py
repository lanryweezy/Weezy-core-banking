# LangChain/CrewAI agent logic for Back Office Reconciliation Agent

from typing import Dict, Any, List, Optional
from datetime import datetime, date
import logging
import json

# Assuming schemas are in the same directory or accessible via path
from .schemas import (
    ReconciliationTaskInput, ReconciliationReportOutput, ReconciliationStatus,
    ReconciliationSummaryStats, MatchedPairDetail, UnmatchedRecordDetail, ReconciliationRecord
)
# Import the defined tools
from .tools import data_extraction_tool, data_comparison_tool, discrepancy_reporting_tool

# from crewai import Agent, Task, Crew, Process
# from langchain_community.llms.fake import FakeListLLM
# from ..core.config import core_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- Agent Definition (Placeholder for CrewAI) ---
# llm_recon_agent = FakeListLLM(responses=[
#     "Okay, I will start the reconciliation process based on the task input.",
#     "First, I'll extract data from the internal source.",
#     "Next, I'll extract data from the external source.",
#     "Data extraction complete. Now, I will compare the two datasets using the provided matching rules.",
#     "Comparison complete. Finally, I will format the discrepancies and generate the report summary."
# ])

# reconciliation_tools = [data_extraction_tool, data_comparison_tool, discrepancy_reporting_tool]

# reconciliation_ai_agent = Agent(
#     role="AI Reconciliation Analyst",
#     goal="Automate the matching of internal ledger entries with external transaction logs (e.g., from payment processors, NIBSS), identify discrepancies, and prepare comprehensive reconciliation reports.",
#     backstory=(
#         "An meticulous AI agent designed to handle the complex and often voluminous task of back-office reconciliation. "
#         "It systematically fetches data from specified internal and external sources for given periods, applies defined matching rules "
#         "to compare records, and clearly reports on matched items, unmatched items, and any discrepancies found. "
#         "Its aim is to improve accuracy, speed, and efficiency in the reconciliation process."
#     ),
#     tools=reconciliation_tools,
#     llm=llm_recon_agent,
#     verbose=True,
#     allow_delegation=False,
# )

# --- Task Definitions (Placeholders for CrewAI) ---
# def create_reconciliation_tasks(task_input_json: str) -> List[Task]:
#     tasks = []
#     # Task 1: Extract Internal Data
#     extract_internal_task = Task(
#         description=f"Extract data from the internal source specified in the reconciliation task input: '{task_input_json}'. Use DataExtractionTool.",
#         expected_output="JSON string from DataExtractionTool: {'status': ..., 'data': [...], 'records_count': ...}.",
#         agent=reconciliation_ai_agent, tools=[data_extraction_tool]
#     )
#     tasks.append(extract_internal_task)

#     # Task 2: Extract External Data
#     extract_external_task = Task(
#         description=f"Extract data from the external source specified in the reconciliation task input: '{task_input_json}'. Use DataExtractionTool.",
#         expected_output="JSON string from DataExtractionTool: {'status': ..., 'data': [...], 'records_count': ...}.",
#         agent=reconciliation_ai_agent, tools=[data_extraction_tool]
#     )
#     tasks.append(extract_external_task)

#     # Task 3: Compare Data
#     compare_task = Task(
#         description=f"Compare the extracted internal and external datasets (from previous tasks) using the matching rules in '{task_input_json}'. Use DataComparisonTool.",
#         expected_output="JSON string from DataComparisonTool: {'matched_pairs': ..., 'unmatched_internal': ..., 'unmatched_external': ..., 'summary_stats': ...}.",
#         agent=reconciliation_ai_agent, tools=[data_comparison_tool], context_tasks=[extract_internal_task, extract_external_task]
#     )
#     tasks.append(compare_task)

#     # Task 4: Report Discrepancies & Finalize Report
#     report_task = Task(
#         description=f"Format discrepancies (unmatched items from comparison task) and generate the final reconciliation report structure using DiscrepancyReportingTool. The task input was '{task_input_json}'.",
#         expected_output="JSON string representing the complete ReconciliationReportOutput, including summary stats, formatted discrepancies, and overall status.",
#         agent=reconciliation_ai_agent, tools=[discrepancy_reporting_tool], context_tasks=[compare_task]
#     )
#     tasks.append(report_task)
#     return tasks


# --- Main Workflow Function (Direct Tool Usage for now) ---

async def start_reconciliation_workflow_async(task_input: ReconciliationTaskInput) -> Dict[str, Any]:
    """
    Simulates the back-office reconciliation workflow by directly calling tools.
    This will eventually be replaced by CrewAI agent execution.
    """
    task_id = task_input.task_id
    logger.info(f"Agent: Starting reconciliation workflow for Task ID: {task_id}, Dates: {task_input.reconciliation_date_from} to {task_input.reconciliation_date_to}")

    report_output_dict: Dict[str, Any] = { # Initialize with fields from ReconciliationReportOutput
        "report_id": f"RECREP-{task_id.split('-')[-1]}-{datetime.utcnow().strftime('%Y%m%d%H%M')}",
        "task_id": task_id,
        "reconciliation_date_from": task_input.reconciliation_date_from.isoformat(), # Ensure string for JSON
        "reconciliation_date_to": task_input.reconciliation_date_to.isoformat(),
        "generation_timestamp": datetime.utcnow().isoformat(),
        "status": "Running", # type: ignore
        "status_message": "Reconciliation process started.",
        "summary_stats": None,
        "matched_pairs": None,
        "unmatched_internal_items": None,
        "unmatched_external_items": None,
        "error_log": []
    }

    # 1. Extract Internal Data
    # For mock, we use reconciliation_date_from. Real tool might handle date ranges.
    logger.info(f"Agent: Extracting internal data for task {task_id} using source '{task_input.source_internal.source_name}'.")
    internal_data_result = data_extraction_tool.run({
        "data_source_config": task_input.source_internal.model_dump(mode='json'),
        "reconciliation_date_str": task_input.reconciliation_date_from.isoformat()
    })
    if internal_data_result.get("status") != "Success":
        err_msg = f"Failed to extract internal data: {internal_data_result.get('message')}"
        logger.error(f"Agent: {err_msg} for task {task_id}")
        report_output_dict["status"] = "Failed" # type: ignore
        report_output_dict["status_message"] = err_msg
        report_output_dict["error_log"].append(err_msg) # type: ignore
        return report_output_dict
    internal_data = internal_data_result.get("data", [])
    logger.info(f"Agent: Extracted {len(internal_data)} internal records for task {task_id}.")

    # 2. Extract External Data
    logger.info(f"Agent: Extracting external data for task {task_id} using source '{task_input.source_external.source_name}'.")
    external_data_result = data_extraction_tool.run({
        "data_source_config": task_input.source_external.model_dump(mode='json'),
        "reconciliation_date_str": task_input.reconciliation_date_from.isoformat() # Using from_date for mock simplicity
    })
    if external_data_result.get("status") != "Success":
        err_msg = f"Failed to extract external data: {external_data_result.get('message')}"
        logger.error(f"Agent: {err_msg} for task {task_id}")
        report_output_dict["status"] = "Failed" # type: ignore
        report_output_dict["status_message"] = err_msg
        report_output_dict["error_log"].append(err_msg) # type: ignore
        return report_output_dict
    external_data = external_data_result.get("data", [])
    logger.info(f"Agent: Extracted {len(external_data)} external records for task {task_id}.")

    # 3. Compare Data
    logger.info(f"Agent: Comparing data for task {task_id}.")
    comparison_result = data_comparison_tool.run({
        "internal_data": internal_data,
        "external_data": external_data,
        "matching_rules": [rule.model_dump(mode='json') for rule in task_input.matching_rules]
    })
    if comparison_result.get("status") != "Success":
        err_msg = f"Data comparison failed: {comparison_result.get('message')}"
        logger.error(f"Agent: {err_msg} for task {task_id}")
        report_output_dict["status"] = "Failed" # type: ignore
        report_output_dict["status_message"] = err_msg
        report_output_dict["error_log"].append(err_msg) # type: ignore
        return report_output_dict

    logger.info(f"Agent: Data comparison successful for task {task_id}. Summary: {comparison_result.get('summary_stats')}")

    # Populate report with comparison results
    # The tool outputs dicts that should align with Pydantic models, direct assignment for now
    report_output_dict["summary_stats"] = ReconciliationSummaryStats(**comparison_result.get("summary_stats", {})).model_dump()
    # For matched_pairs, unmatched_internal_items, unmatched_external_items, parse each record
    # This is simplified for the mock. A real agent would ensure data aligns with ReconciliationRecord, MatchedPairDetail etc.
    report_output_dict["matched_pairs"] = comparison_result.get("matched_pairs") # List of dicts
    report_output_dict["unmatched_internal_items"] = comparison_result.get("unmatched_internal") # List of dicts
    report_output_dict["unmatched_external_items"] = comparison_result.get("unmatched_external") # List of dicts


    # 4. Format Discrepancies (using DiscrepancyReportingTool - this tool is more for formatting a section of the report)
    # The main structure is already built above. This tool might add more narrative or specific views.
    # For this mock, its output is largely informational and used for status_message.
    logger.info(f"Agent: Formatting discrepancies for task {task_id}.")
    discrepancy_report_parts = discrepancy_reporting_tool.run({
        "unmatched_internal": report_output_dict["unmatched_internal_items"] or [],
        "unmatched_external": report_output_dict["unmatched_external_items"] or [],
        "comparison_summary": report_output_dict["summary_stats"] or {}
    })

    # Update status based on discrepancies
    if comparison_result.get("summary_stats", {}).get("unmatched_internal_count", 0) > 0 or \
       comparison_result.get("summary_stats", {}).get("unmatched_external_count", 0) > 0:
        report_output_dict["status"] = "CompletedWithDiscrepancies" # type: ignore
        report_output_dict["status_message"] = discrepancy_report_parts.get("report_sections", {}).get("summary_message", "Reconciliation completed with discrepancies.")
    else:
        report_output_dict["status"] = "Completed" # type: ignore
        report_output_dict["status_message"] = discrepancy_report_parts.get("report_sections", {}).get("summary_message", "Reconciliation completed successfully, all items matched.")

    report_output_dict["generation_timestamp"] = datetime.utcnow().isoformat() # Final timestamp

    logger.info(f"Agent: Reconciliation workflow completed for Task ID: {task_id}. Final Status: {report_output_dict['status']}")
    return report_output_dict


if __name__ == "__main__":
    import asyncio
    from .schemas import DataSourceConfig, MatchingRuleConfig, MatchingKey # For test input

    async def test_reconciliation_workflow():
        print("--- Testing Back Office Reconciliation Agent Workflow (Direct Tool Usage) ---")

        test_task_input = ReconciliationTaskInput(
            reconciliation_date_from=date.today() - timedelta(days=1),
            reconciliation_date_to=date.today() - timedelta(days=1),
            source_internal=DataSourceConfig(source_name="MockInternalLedger", source_type="InternalLedger"),
            source_external=DataSourceConfig(source_name="MockExternalGateway", source_type="PaymentGatewayLog"),
            matching_rules=[MatchingRuleConfig(
                description="Test Rule: Match transaction_id/external_session_id and amount",
                primary_keys=[MatchingKey(internal_field_name="transaction_id", external_field_name="external_session_id")],
                amount_field_internal="amount", amount_field_external="transaction_amount",
                amount_tolerance_absolute=0.10 # 10 kobo
            )]
        )
        task_id_test = test_task_input.task_id

        print(f"\nTesting with Task ID: {task_id_test}")
        report_dict = await start_reconciliation_workflow_async(test_task_input)

        print("\n--- Final Reconciliation Report (as dict from Agent Workflow) ---")
        print(json.dumps(report_dict, indent=2, default=str)) # Use default=str for date/datetime

        # Validate if it can be parsed by ReconciliationReportOutput Pydantic model
        try:
            parsed_report = ReconciliationReportOutput(**report_dict)
            print("\nSuccessfully parsed agent output into ReconciliationReportOutput schema.")
            # print(parsed_report.model_dump_json(indent=2))
        except Exception as e:
            print(f"\nError parsing agent output into ReconciliationReportOutput schema: {e}")

    # asyncio.run(test_reconciliation_workflow())
    print("Back Office Reconciliation Agent logic (agent.py). Contains workflow to run reconciliation using tools (mocked execution).")
