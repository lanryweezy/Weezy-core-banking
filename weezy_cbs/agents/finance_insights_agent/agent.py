# Agent for Financial Insights & Personalized Recommendations
import json # For pretty printing dicts if needed
from . import tools
from . import config # For default parameters
from datetime import datetime # For timestamps in memory
import pandas as pd # For data manipulation if tools return DataFrames

class FinanceInsightsAgent:
    def __init__(self, agent_id="finance_insights_agent_001", memory_storage=None):
        self.agent_id = agent_id
        self.role = "Provides financial analytics, forecasts, and personalized insights to customers or bank staff."
        # Memory: Stores customer goals, financial history summaries, previously generated insights to avoid repetition or build on them.
        # Example: self.memory = {
        #    "customer_CUST101": {
        #        "last_insight_generated_at": "2023-10-28T12:00:00Z",
        #        "financial_summary_cache": {"total_income": ..., "total_spending": ...},
        #        "active_goals": [{"name": "Vacation Fund", "progress": 0.6}],
        #        "communication_preferences": {"channel": "EMAIL", "frequency": "MONTHLY"}
        #    }
        # }
        self.memory = memory_storage if memory_storage is not None else {}

    def _get_customer_memory(self, customer_id: str) -> dict:
        if customer_id not in self.memory:
            self.memory[customer_id] = {
                "last_insight_generated_at": None,
                "financial_summary_cache": None,
                "transaction_data_cache_period": None, # e.g. "2023-01-01_to_2023-06-30"
                "active_goals": [], # Could be fetched from a goals module
                "communication_preferences": {} # Could be fetched from CRM/Digital Channels
            }
        return self.memory[customer_id]

    def _update_customer_memory(self, customer_id: str, update_data: dict):
        cust_mem = self._get_customer_memory(customer_id)
        cust_mem.update(update_data)
        cust_mem["last_insight_generated_at"] = datetime.utcnow().isoformat()

    def generate_financial_insights_for_customer(self, customer_id: str, account_number: str, force_refresh_data: bool = False) -> dict:
        """
        Main workflow to generate financial insights for a customer.
        Inputs:
            customer_id: The ID of the customer.
            account_number: The primary account number to analyze (can be extended for multiple accounts).
            force_refresh_data: If True, re-fetch and re-process data even if cached.
        Output:
            Dictionary containing textual summary, visualizations (links/data), and recommendations.
        """
        cust_mem = self._get_customer_memory(customer_id)

        # TODO: Add logic to check if insights were recently generated and if data needs refresh based on cache period.
        # For now, always proceed if force_refresh or no cache.

        # 1. Fetch Transaction History
        # For simplicity, assume one primary account for now. Real system would handle multiple accounts.
        transactions_list = tools.fetch_transaction_history(account_number, lookback_months=config.DEFAULT_TRANSACTION_HISTORY_LOOKBACK_MONTHS)
        if not transactions_list or len(transactions_list) < config.MIN_TRANSACTIONS_FOR_MEANINGFUL_INSIGHTS:
            return {"status": "error", "message": "Insufficient transaction data to generate meaningful insights."}

        transactions_df = pd.DataFrame(transactions_list)
        # Update cache info - this is simplified
        # cust_mem["transaction_data_cache_period"] = f"{transactions_df['transaction_date'].min()[:10]}_{transactions_df['transaction_date'].max()[:10]}"

        # 2. Categorize Transactions
        categorized_df = tools.categorize_transactions(transactions_list) # Tool now takes list of dicts

        # 3. Calculate Spending/Income Summary
        financial_summary = tools.calculate_spending_summary(categorized_df)
        cust_mem["financial_summary_cache"] = financial_summary # Cache this summary

        # 4. Forecast Cash Flow
        # Use the categorized (or raw if preferred by forecast tool) DataFrame
        cash_flow_forecast = tools.forecast_cash_flow(categorized_df, days_to_forecast=config.CASH_FLOW_FORECAST_PERIOD_DAYS)

        # 5. Generate Textual Summary
        text_summary = tools.generate_textual_summary(financial_summary, cash_flow_forecast)

        # 6. Generate Data Visualizations (conceptual - tool returns mock URLs/paths)
        visualizations = {}
        if financial_summary.get("spending_by_category"):
            visualizations["spending_breakdown_chart_url"] = tools.generate_data_visualization(
                data=financial_summary["spending_by_category"],
                chart_type=config.DEFAULT_CHART_TYPE_SPENDING_BREAKDOWN,
                title=f"Spending Breakdown for {account_number}"
            )
        if cash_flow_forecast.get("status") == "success" and cash_flow_forecast.get("forecast_data"):
             visualizations["cash_flow_trend_chart_url"] = tools.generate_data_visualization(
                data=cash_flow_forecast["forecast_data"], # List of {"ds": date, "yhat": value, ...}
                chart_type=config.DEFAULT_CHART_TYPE_CASH_FLOW_TREND,
                title=f"Cash Flow Forecast for {account_number}"
            )

        # 7. Suggest Savings Goals & Recommend Investment Options
        # Fetch customer profile for risk appetite, existing goals etc. (mocked for now)
        # customer_profile_data = tools.fetch_customer_profile(customer_id)
        customer_profile_data_mock = {"risk_appetite": "MEDIUM", "existing_goals": cust_mem["active_goals"]}

        suggested_goals = tools.suggest_savings_goals(financial_summary, existing_goals=customer_profile_data_mock["existing_goals"])
        recommended_investments = tools.recommend_investment_options(customer_profile_data_mock, financial_summary)

        # Update memory
        self._update_customer_memory(customer_id, {
            "financial_summary_cache": financial_summary,
            # "last_insight_details": {"text_summary": text_summary, ...} # Store the generated insight if needed
        })

        return {
            "status": "success",
            "customer_id": customer_id,
            "account_analyzed": account_number,
            "period_analyzed": f"Last {config.DEFAULT_TRANSACTION_HISTORY_LOOKBACK_MONTHS} months",
            "text_summary": text_summary,
            "financial_overview": financial_summary, # total income, spending, net, breakdown
            "cash_flow_forecast": cash_flow_forecast, # trend, data points
            "visualizations": visualizations, # URLs/paths to charts
            "recommended_savings_goals": suggested_goals,
            "recommended_investment_options": recommended_investments
        }

    def get_cached_insights_summary(self, customer_id: str) -> dict:
        """Retrieves a summary of the last generated insights for the customer from memory."""
        cust_mem = self._get_customer_memory(customer_id)
        if cust_mem.get("financial_summary_cache"):
            return {
                "customer_id": customer_id,
                "last_insight_generated_at": cust_mem.get("last_insight_generated_at"),
                "cached_financial_summary": cust_mem.get("financial_summary_cache"),
                "data_cache_period": cust_mem.get("transaction_data_cache_period")
            }
        return {"status": "not_found", "message": "No cached insights found for this customer."}

# Example Usage
if __name__ == "__main__":
    from datetime import datetime # For _update_customer_memory timestamp
    import decimal # For financial_summary Decimal values

    insights_agent = FinanceInsightsAgent()

    test_customer_id = "CUST_FIN_007"
    test_account_number = "0077700777" # Primary account for this customer

    print(f"--- Generating Financial Insights for Customer: {test_customer_id}, Account: {test_account_number} ---")

    insights_result = insights_agent.generate_financial_insights_for_customer(test_customer_id, test_account_number)

    if insights_result.get("status") == "success":
        print("\n--- Generated Insights ---")
        print(f"Customer ID: {insights_result['customer_id']}")
        print(f"Account Analyzed: {insights_result['account_analyzed']}")
        print(f"Period: {insights_result['period_analyzed']}")

        print("\nTextual Summary:")
        print(insights_result['text_summary'])

        print("\nFinancial Overview (Totals):")
        print(f"  Total Income: {insights_result['financial_overview']['total_income']:.2f}")
        print(f"  Total Spending: {insights_result['financial_overview']['total_spending']:.2f}")
        print(f"  Net Cash Flow: {insights_result['financial_overview']['net_cash_flow']:.2f}")

        # print("\nSpending Breakdown by Category:")
        # for cat, amt in insights_result['financial_overview']['spending_by_category'].items():
        #     print(f"  - {cat}: {amt:.2f}")

        print("\nCash Flow Forecast:")
        print(f"  Trend: {insights_result['cash_flow_forecast']['trend_prediction']}")
        # print(f"  Forecast Data (first 3 days): {insights_result['cash_flow_forecast']['forecast_data'][:3]}")

        print("\nVisualizations (Mock URLs/Paths):")
        for viz_name, viz_url in insights_result['visualizations'].items():
            print(f"  - {viz_name}: {viz_url}")

        print("\nRecommended Savings Goals:")
        for goal in insights_result['recommended_savings_goals']:
            print(f"  - {goal['name']}: {goal.get('description','')} (Target: {goal.get('target_amount') or goal.get('target_percentage_of_income')})")

        print("\nRecommended Investment Options:")
        for inv in insights_result['recommended_investment_options']:
            print(f"  - {inv['product_name']} ({inv['type']}): Risk {inv['risk_level']}, Expected Return {inv['expected_return_pa']}")
    else:
        print(f"\nError generating insights: {insights_result.get('message')}")

    print("\n--- Cached Insights Summary from Agent Memory ---")
    cached_summary = insights_agent.get_cached_insights_summary(test_customer_id)
    # Need to handle Decimal for json.dumps if not already str
    # print(json.dumps(cached_summary, indent=2, default=lambda o: str(o) if isinstance(o, decimal.Decimal) else o.__str__ if hasattr(o, '__str__') else None ))
    if cached_summary.get("cached_financial_summary"):
         print(f"Last generated: {cached_summary.get('last_insight_generated_at')}")
         print(f"Cached Total Income: {cached_summary['cached_financial_summary']['total_income']:.2f}")
    else:
        print(cached_summary.get("message"))
