# LangChain/CrewAI agent logic for Finance Insights Agent

from typing import Dict, Any, List, Optional
from datetime import datetime, date
import logging
import json

# Assuming schemas are in the same directory or accessible via path
from .schemas import (
    InsightsRequest, InsightsReport, SpendingAnalysis, CashflowForecast, Recommendation,
    DataSouceConfigInput # For type hinting if used directly
)
# Import the defined tools
from .tools import (
    transaction_aggregation_tool,
    cashflow_forecasting_tool,
    financial_recommendation_tool,
    financial_visualization_tool
)

# from crewai import Agent, Task, Crew, Process
# from langchain_community.llms.fake import FakeListLLM
# from ..core.config import core_settings

logger = logging.getLogger(__name__)

# --- Agent Definition (Placeholder for CrewAI) ---
# llm_finance_advisor = FakeListLLM(responses=[
#     "Okay, I will generate financial insights based on the request.",
#     "First, I'll aggregate the transaction data for the specified period.",
#     "Next, if requested, I'll perform a cashflow forecast.",
#     "Then, if requested, I'll generate financial recommendations.",
#     "Finally, I will compile all insights into a report."
# ])

# finance_insights_tools = [
#     transaction_aggregation_tool, cashflow_forecasting_tool,
#     financial_recommendation_tool, financial_visualization_tool
# ]

# financial_advisor_agent = Agent(
#     role="AI Financial Insights Analyst",
#     goal="Analyze customer or bank-level financial data to provide actionable insights, cash flow forecasts, spending analyses, visualizations, and personalized recommendations for savings or investments.",
#     backstory=(
#         "An intelligent AI agent specializing in financial data analysis and insight generation. "
#         "It processes transaction histories and account balances to identify trends, predict future cash flows, "
#         "and create visualizations to communicate findings effectively. "
#         "It offers personalized advice on budgeting, saving, and investment opportunities."
#     ),
#     tools=finance_insights_tools,
#     llm=llm_finance_advisor,
#     verbose=True,
#     allow_delegation=False, # Or True if sub-tasks like viz generation are delegated
# )

# --- Task Definitions (Placeholders for CrewAI) ---
# def create_financial_insights_tasks(insights_request_json: str) -> List[Task]:
#     tasks = []
#     # Parse insights_request_json to get customer_id, requested_insight_types, etc.
#     # Dynamically create tasks based on requested_insight_types.

#     # Task 1: Transaction Aggregation (Always run)
#     aggregation_task = Task(
#         description=f"Aggregate financial transactions for the entity detailed in the insights request: '{insights_request_json}'. Use TransactionAggregationTool.",
#         expected_output="JSON string with aggregated data (total income/spending, breakdowns by category/source, etc.).",
#         agent=financial_advisor_agent, tools=[transaction_aggregation_tool]
#     )
#     tasks.append(aggregation_task)

#     # Task 2: Cashflow Forecasting (If requested)
#     # if "cashflow_forecast" in requested_insight_types:
#     #     forecasting_task = Task(
#     #         description=f"Generate a cashflow forecast using aggregated data (from previous task) and forecast horizon from request: '{insights_request_json}'. Use CashflowForecastingTool.",
#     #         expected_output="JSON string with forecast data (predicted monthly cashflows).",
#     #         agent=financial_advisor_agent, tools=[cashflow_forecasting_tool], context_tasks=[aggregation_task]
#     #     )
#     #     tasks.append(forecasting_task)

#     # Task 3: Financial Recommendations (If requested)
#     # if "recommendations" in requested_insight_types:
#     #     recommendation_task = Task(
#     #         description=f"Generate financial recommendations using aggregated data, forecast (if available), and goals from request: '{insights_request_json}'. Use FinancialRecommendationTool.",
#     #         expected_output="JSON string with a list of recommendations.",
#     #         agent=financial_advisor_agent, tools=[financial_recommendation_tool],
#     #         context_tasks=[aggregation_task] + ([forecasting_task] if "forecasting_task" in locals() else [])
#     #     )
#     #     tasks.append(recommendation_task)

#     # Task 4: Compile Report (Final task)
#     # report_compilation_task = Task(
#     #     description="Compile all generated insights (aggregation, forecast, recommendations, visualizations if any) into a comprehensive report matching the InsightsReport schema.",
#     #     expected_output="JSON string of the final InsightsReport.",
#     #     agent=financial_advisor_agent, context_tasks=tasks[:-1] # All tasks before this one
#     # )
#     # tasks.append(report_compilation_task)
#     return tasks


# --- Main Workflow Function (Direct Tool Usage for now) ---

async def generate_financial_insights_async(request: InsightsRequest) -> Dict[str, Any]:
    """
    Simulates the financial insights generation workflow by directly calling tools.
    This will eventually be replaced by CrewAI agent execution.
    """
    request_id = request.request_id or f"INSREQ-{uuid.uuid4().hex[:10].upper()}" # Ensure request_id
    logger.info(f"Agent: Starting financial insights generation for Request ID: {request_id}, Customer: {request.customer_id}")

    # Initialize parts of the report
    report_dict: Dict[str, Any] = {
        "report_id": f"FINREP-{request_id.split('-')[-1]}", # Generate a report ID
        "request_id": request_id,
        "customer_id": request.customer_id,
        "segment_id": request.segment_id,
        "generated_at": datetime.utcnow().isoformat(), # Will be parsed by Pydantic
        "summary": None,
        "spending_analysis": None,
        "cashflow_forecast": None,
        "recommendations": None,
        "custom_insights": [] # For any other generated text/data
    }

    # 1. Transaction Aggregation (always performed as it's base for others)
    logger.info(f"Agent: Calling TransactionAggregationTool for request {request_id}")
    # data_source config might need to be passed to the tool if it's not just customer_id based
    # For mock, tool uses customer_id and period from request.data_source.query_parameters
    aggregation_params = {
        "customer_id": request.customer_id,
        "period": request.data_source.query_parameters.get("period", "last_30_days"),
        "custom_start_date": request.data_source.query_parameters.get("custom_start_date"),
        "custom_end_date": request.data_source.query_parameters.get("custom_end_date"),
    }
    # Filter out None values from params before passing to tool
    aggregation_params_cleaned = {k: v for k, v in aggregation_params.items() if v is not None}

    agg_result = transaction_aggregation_tool.run(aggregation_params_cleaned)

    if agg_result.get("status") != "Success":
        logger.error(f"Agent: TransactionAggregationTool failed for {request_id}: {agg_result.get('message')}")
        report_dict["summary"] = f"Error: Could not aggregate transaction data. {agg_result.get('message')}"
        # Return early with error or partial report
        return report_dict

    logger.info(f"Agent: TransactionAggregationTool successful for {request_id}.")

    # Populate SpendingAnalysis part of the report
    report_dict["spending_analysis"] = SpendingAnalysis(
        period_start_date=date.fromisoformat(agg_result["period_start_date"]),
        period_end_date=date.fromisoformat(agg_result["period_end_date"]),
        total_income=agg_result["total_income_ngn"],
        total_spending=agg_result["total_spending_ngn"],
        net_cashflow=agg_result["net_cashflow_ngn"],
        spending_by_category=agg_result["spending_by_category"],
        # savings_rate can be calculated here if needed: (income - spending) / income
    ).model_dump() # Convert to dict for the main report_dict

    # Add visualization for spending if requested
    if "spending_visualization" in request.requested_insight_types:
        viz_data_spending = financial_visualization_tool.run({
            "chart_type": "spending_pie",
            "data": {"spending_by_category": agg_result["spending_by_category"]}, # Pass only relevant part
            "title": "Spending Breakdown"
        })
        if viz_data_spending.get("status", "").startswith("Success"):
            # Storing the data for frontend rendering, not an image string for this mock
            report_dict["spending_analysis"]["chart_data_for_frontend"] = viz_data_spending.get("chart_data_for_frontend")


    # 2. Cashflow Forecasting (if requested)
    forecast_data_for_recommendations: Optional[Dict[str, Any]] = None
    if "cashflow_forecast" in request.requested_insight_types:
        logger.info(f"Agent: Calling CashflowForecastingTool for request {request_id}")
        forecast_result = cashflow_forecasting_tool.run({
            "aggregated_transaction_data": agg_result, # Pass full agg_result
            "forecast_horizon_months": request.forecast_horizon_months or 3
        })
        if forecast_result.get("status") == "Success":
            logger.info(f"Agent: CashflowForecastingTool successful for {request_id}.")
            report_dict["cashflow_forecast"] = CashflowForecast(
                forecast_period_start_date=date.fromisoformat(forecast_result["forecast_period_start_date"]),
                forecast_period_end_date=date.fromisoformat(forecast_result["forecast_period_end_date_approx"]), # Use approx
                forecast_granularity="monthly", # Mock default
                predicted_cashflows=forecast_result["predicted_monthly_cashflows"]
            ).model_dump()
            forecast_data_for_recommendations = forecast_result # Pass to recommendation tool

            # Add visualization for forecast if requested
            if "forecast_visualization" in request.requested_insight_types: # Another specific request type for viz
                viz_data_forecast = financial_visualization_tool.run({
                    "chart_type": "cashflow_trend_line",
                    "data": {"predicted_monthly_cashflows": forecast_result["predicted_monthly_cashflows"]},
                    "title": "Cashflow Forecast"
                })
                if viz_data_forecast.get("status", "").startswith("Success") and report_dict["cashflow_forecast"]:
                     report_dict["cashflow_forecast"]["chart_data_for_frontend"] = viz_data_forecast.get("chart_data_for_frontend")
        else:
            logger.warning(f"Agent: CashflowForecastingTool failed for {request_id}: {forecast_result.get('message')}")
            report_dict["custom_insights"].append({"type": "ForecastError", "message": forecast_result.get('message')})


    # 3. Financial Recommendations (if requested)
    if "recommendations" in request.requested_insight_types:
        logger.info(f"Agent: Calling FinancialRecommendationTool for request {request_id}")
        recom_result = financial_recommendation_tool.run({
            "customer_id": request.customer_id,
            "aggregated_data": agg_result,
            "forecast_data": forecast_data_for_recommendations,
            "customer_goals": [goal.get("goal") for goal in request.financial_goals] if request.financial_goals else None # Extract goal strings
        })
        if recom_result.get("status") == "Success":
            logger.info(f"Agent: FinancialRecommendationTool successful for {request_id}.")
            # Convert list of recommendation dicts to list of Recommendation Pydantic models
            recommendations_list = [Recommendation(**rec_dict) for rec_dict in recom_result.get("recommendations", [])]
            report_dict["recommendations"] = [rec.model_dump() for rec in recommendations_list]
        else:
            logger.warning(f"Agent: FinancialRecommendationTool failed for {request_id}: {recom_result.get('message')}")
            report_dict["custom_insights"].append({"type": "RecommendationError", "message": recom_result.get('message')})

    # 4. Generate Overall Summary (Simplified)
    if report_dict["spending_analysis"]:
        summary_parts = [f"Financial insights for customer {request.customer_id or 'N/A'}."]
        sa = report_dict["spending_analysis"]
        summary_parts.append(f"Over the period {sa['period_start_date']} to {sa['period_end_date']}, total income was NGN {sa['total_income']:.2f} and total spending was NGN {sa['total_spending']:.2f}, resulting in a net cashflow of NGN {sa['net_cashflow']:.2f}.")
        if report_dict.get("cashflow_forecast"):
            cf = report_dict["cashflow_forecast"]
            summary_parts.append(f"Cashflow forecast for the next {len(cf['predicted_cashflows'])} months suggests an average monthly net of NGN {sum(p['predicted_net_cashflow_ngn'] for p in cf['predicted_cashflows'])/len(cf['predicted_cashflows']):.2f} (mock).")
        if report_dict.get("recommendations"):
            summary_parts.append(f"{len(report_dict['recommendations'])} financial recommendations provided.")
        report_dict["summary"] = " ".join(summary_parts)
    else:
        report_dict["summary"] = "Basic insights generated. Aggregation data might be missing or had errors."


    logger.info(f"Agent: Financial insights generation complete for request ID: {request_id}. Summary: {report_dict['summary'][:100]}...")
    return report_dict


if __name__ == "__main__":
    import asyncio
    from .schemas import DataSouceConfigInput # For test data

    async def test_finance_insights_workflow():
        print("--- Testing Finance Insights Agent Workflow (Direct Tool Usage) ---")

        test_request_1 = InsightsRequest(
            customer_id="CUST-FIN-TEST-001",
            data_source=DataSouceConfigInput(
                query_parameters={"period": "last_3_months"}
            ),
            requested_insight_types=["spending_analysis", "cashflow_forecast", "recommendations", "spending_visualization", "forecast_visualization"],
            forecast_horizon_months=3,
            financial_goals=[{"goal": "save_for_rent", "target_amount": 500000}]
        )

        print(f"\nTesting with Request ID (auto-generated for): {test_request_1.customer_id}, Types: {test_request_1.requested_insight_types}")
        insights_report_dict = await generate_financial_insights_async(test_request_1)

        print("\n--- Final Insights Report (as dict) ---")
        print(json.dumps(insights_report_dict, indent=2, default=str))

        # Validate if it can be parsed by InsightsReport Pydantic model
        try:
            parsed_report = InsightsReport(**insights_report_dict)
            print("\nSuccessfully parsed agent output into InsightsReport schema.")
            # print(parsed_report.model_dump_json(indent=2))
        except Exception as e:
            print(f"\nError parsing agent output into InsightsReport schema: {e}")

    # asyncio.run(test_finance_insights_workflow())
    print("Finance Insights Agent logic (agent.py). Contains workflow to generate insights using tools (mocked execution).")
