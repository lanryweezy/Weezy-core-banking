# Tools for Finance Insights Agent
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import random # For mock data
import decimal # For financial calculations
# from fbprophet import Prophet # Example for time-series forecasting, if used directly
# import matplotlib.pyplot as plt # Example for data visualization, if used directly

from . import config
# from weezy_cbs.ai_automation_layer.schemas import LLMTaskRequest # If using LLM service for summaries

# Placeholder for schemas
class LLMTaskRequestSchema(dict): pass

# --- Data Fetching Tools ---
def fetch_transaction_history(account_number: str, lookback_months: int = config.DEFAULT_TRANSACTION_HISTORY_LOOKBACK_MONTHS) -> list[dict]:
    """Fetches transaction history for a given account and lookback period."""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=lookback_months * 30) # Approximate months

    url = config.GET_ACCOUNT_TRANSACTIONS_ENDPOINT.format(account_number=account_number)
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "limit": 5000 # Fetch a good number of transactions; pagination might be needed for real API
    }
    try:
        # response = requests.get(url, params=params, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return response.json().get("items", []) # Assuming API returns list under 'items'

        print(f"Mock Transaction History Fetch: Account='{account_number}', Start='{start_date}', End='{end_date}'")
        # Simulate transaction data
        mock_transactions = []
        current_date = start_date
        base_balance = 100000
        for i in range(lookback_months * 20): # ~20 transactions per month
            tx_type = random.choice(["DEBIT", "CREDIT"])
            amount = random.uniform(500, 50000 if tx_type == "CREDIT" else 25000)
            if tx_type == "DEBIT": base_balance -= amount
            else: base_balance += amount

            mock_transactions.append({
                "transaction_id": f"FT_MOCK_{i}",
                "account_id": account_number, # Actually account_id (db id) in real ledger model
                "entry_type": tx_type,
                "amount": decimal.Decimal(str(round(amount,2))),
                "currency": "NGN",
                "narration": f"{random.choice(['Groceries', 'Salary', 'Airtime', 'Restaurant', 'Transfer to Friend', 'Bill Payment'])}",
                "transaction_date": (start_date + timedelta(days=i * (lookback_months * 30 // (lookback_months * 20)))).isoformat() + "T" + datetime.now().time().isoformat()[:8], # Spread out transactions
                "value_date": (start_date + timedelta(days=i * (lookback_months * 30 // (lookback_months * 20)))).isoformat(),
                "balance_after": decimal.Decimal(str(round(base_balance,2)))
            })
        return mock_transactions

    except requests.exceptions.RequestException as e:
        print(f"Error fetching transaction history for {account_number}: {str(e)}")
        return []

def fetch_account_balances(account_numbers: list[str]) -> list[dict]:
    """Fetches current balances for a list of accounts."""
    balances = []
    for acc_num in account_numbers:
        url = config.GET_ACCOUNT_BALANCE_ENDPOINT.format(account_number=acc_num)
        try:
            # response = requests.get(url, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
            # response.raise_for_status()
            # balances.append(response.json()) # Assuming AccountBalanceResponse structure
            print(f"Mock Account Balance Fetch: Account='{acc_num}'")
            balances.append({
                "account_number": acc_num,
                "ledger_balance": decimal.Decimal(str(random.uniform(50000, 500000))),
                "available_balance": decimal.Decimal(str(random.uniform(40000, 480000))),
                "currency": "NGN"
            })
        except requests.exceptions.RequestException as e:
            print(f"Error fetching balance for {acc_num}: {str(e)}")
            balances.append({"account_number": acc_num, "error": str(e)})
    return balances

# --- Data Analysis Tools ---
def categorize_transactions(transactions: list[dict]) -> pd.DataFrame:
    """
    Categorizes transactions into spending/income categories.
    Can use rules-based logic or an ML model.
    """
    df = pd.DataFrame(transactions)
    if df.empty: return df

    print("Mock Transaction Categorization: Processing transactions...")
    # Simple rule-based categorization based on narration keywords for mock
    def _categorize(narration):
        narration_lower = str(narration).lower()
        if "salary" in narration_lower or "income" in narration_lower: return "Income"
        if "groceries" in narration_lower or "supermarket" in narration_lower: return "Groceries"
        if "airtime" in narration_lower or "data" in narration_lower: return "Utilities (Telco)"
        if "restaurant" in narration_lower or "food" in narration_lower or "cafe" in narration_lower: return "Food & Dining"
        if "bill" in narration_lower or "electricity" in narration_lower or "dstv" in narration_lower: return "Bills & Utilities"
        if "transfer" in narration_lower or "sent" in narration_lower: return "Transfers"
        if "loan" in narration_lower or "repayment" in narration_lower: return "Loan Repayments"
        return "Miscellaneous"

    df['category'] = df['narration'].apply(_categorize)

    # Distinguish income vs spending based on entry_type
    df['transaction_flow'] = df['entry_type'].apply(lambda x: 'INCOME' if x == 'CREDIT' else 'SPENDING')
    df.loc[df['category'] == 'Income', 'transaction_flow'] = 'INCOME' # Ensure "Income" category is flow INCOME

    return df

def calculate_spending_summary(categorized_transactions_df: pd.DataFrame) -> dict:
    """Calculates total spending, income, and breakdown by category."""
    if categorized_transactions_df.empty:
        return {"total_income": decimal.Decimal("0.0"), "total_spending": decimal.Decimal("0.0"), "spending_by_category": {}, "income_sources": {}}

    # Ensure 'amount' is Decimal
    categorized_transactions_df['amount'] = categorized_transactions_df['amount'].apply(lambda x: decimal.Decimal(str(x)))

    income_df = categorized_transactions_df[categorized_transactions_df['transaction_flow'] == 'INCOME']
    spending_df = categorized_transactions_df[categorized_transactions_df['transaction_flow'] == 'SPENDING']

    total_income = income_df['amount'].sum()
    total_spending = spending_df['amount'].sum()

    spending_by_category = spending_df.groupby('category')['amount'].sum().apply(lambda x: round(x, 2)).to_dict()
    income_sources = income_df.groupby('category')['amount'].sum().apply(lambda x: round(x, 2)).to_dict()

    # Convert Decimal to str for JSON serialization if this dict is returned directly
    # spending_by_category = {k: str(v) for k, v in spending_by_category.items()}
    # income_sources = {k: str(v) for k, v in income_sources.items()}

    return {
        "total_income": total_income,
        "total_spending": total_spending,
        "net_cash_flow": total_income - total_spending,
        "spending_by_category": spending_by_category,
        "income_sources": income_sources
    }

def forecast_cash_flow(historical_transactions_df: pd.DataFrame, days_to_forecast: int = config.CASH_FLOW_FORECAST_PERIOD_DAYS) -> dict:
    """
    Predicts future cash flow using time-series forecasting (e.g., Prophet, ARIMA).
    This is a simplified mock. A real implementation is complex.
    """
    if historical_transactions_df.empty or 'transaction_date' not in historical_transactions_df.columns:
        return {"status": "error", "message": "Insufficient data for forecasting."}

    print(f"Mock Cash Flow Forecasting: For next {days_to_forecast} days.")
    # Ensure 'transaction_date' is datetime
    historical_transactions_df['transaction_date'] = pd.to_datetime(historical_transactions_df['transaction_date'])

    # Aggregate daily net flow for forecasting input (ds, y for Prophet)
    # df_daily_flow = historical_transactions_df.copy()
    # df_daily_flow['flow_value'] = df_daily_flow.apply(lambda row: row['amount'] if row['entry_type'] == 'CREDIT' else -row['amount'], axis=1)
    # daily_net = df_daily_flow.groupby(pd.Grouper(key='transaction_date', freq='D'))['flow_value'].sum().reset_index()
    # daily_net.rename(columns={'transaction_date': 'ds', 'flow_value': 'y'}, inplace=True)

    # if len(daily_net) < 10: # Need enough data points for forecasting
    #     return {"status": "error", "message": "Not enough daily data points for reliable forecasting."}

    # model = Prophet() # Example using Prophet
    # model.fit(daily_net)
    # future_dates = model.make_future_dataframe(periods=days_to_forecast)
    # forecast_df = model.predict(future_dates)

    # Extract relevant columns (ds, yhat, yhat_lower, yhat_upper)
    # forecast_output = forecast_df[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(days_to_forecast).to_dict('records')

    # Mock forecast output
    mock_forecast_output = []
    last_date = historical_transactions_df['transaction_date'].max() if not historical_transactions_df.empty else datetime.utcnow()
    current_yhat = random.uniform(-5000, 15000) # Starting point for mock trend
    for i in range(1, days_to_forecast + 1):
        current_yhat += random.uniform(-2000, 2000) # Add some noise/trend
        mock_forecast_output.append({
            "ds": (last_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "yhat": round(current_yhat, 2), # Predicted net flow
            "yhat_lower": round(current_yhat - random.uniform(1000,5000), 2),
            "yhat_upper": round(current_yhat + random.uniform(1000,5000), 2)
        })

    # Determine overall trend
    trend = "STABLE"
    if len(mock_forecast_output) > 1:
        start_val = mock_forecast_output[0]['yhat']
        end_val = mock_forecast_output[-1]['yhat']
        if end_val > start_val * 1.1: trend = "IMPROVING"
        elif end_val < start_val * 0.9: trend = "DECLINING"

    return {
        "status": "success",
        "forecast_period_days": days_to_forecast,
        "trend_prediction": trend, # e.g. "IMPROVING", "STABLE", "DECLINING"
        "forecast_data": mock_forecast_output # List of {"date": YYYY-MM-DD, "predicted_net_flow": float, "lower_bound": float, "upper_bound": float}
    }

# --- Text & Visualization Tools ---
def generate_textual_summary(financial_summary: dict, cash_flow_forecast: dict) -> str:
    """
    Generates a human-readable textual summary of financial insights.
    Can use an LLM or template-based approach.
    """
    # Using a template-based approach for mock
    # llm_payload = LLMTaskRequestSchema(
    #     task_type="GENERATE_REPORT_SUMMARY", # Or custom type
    #     context_data={
    #         "total_income": str(financial_summary.get("total_income")),
    #         "total_spending": str(financial_summary.get("total_spending")),
    #         "top_categories": sorted(financial_summary.get("spending_by_category", {}).items(), key=lambda item: item[1], reverse=True)[:3],
    #         "cash_flow_trend": cash_flow_forecast.get("trend_prediction", "N/A")
    #     },
    #     # input_text=config.LLM_PROMPT_FOR_FINANCIAL_SUMMARY.format(...) # Populate the prompt
    # )
    # llm_response = requests.post(config.LLM_TEXT_SUMMARY_API_URL, json=llm_payload).json()
    # return llm_response.get("processed_output", "Could not generate summary.")

    print("Mock Textual Summary Generation...")
    income = financial_summary.get('total_income', decimal.Decimal(0))
    spending = financial_summary.get('total_spending', decimal.Decimal(0))
    net_flow = income - spending

    summary = f"Financial Snapshot:\n"
    summary += f"- Total Income: {income:.2f} NGN\n"
    summary += f"- Total Spending: {spending:.2f} NGN\n"
    summary += f"- Net Cash Flow: {net_flow:.2f} NGN\n"

    top_spending = sorted(financial_summary.get("spending_by_category", {}).items(), key=lambda item: item[1], reverse=True)
    if top_spending:
        summary += f"- Top Spending Categories:\n"
        for cat, amt in top_spending[:3]: # Top 3
            summary += f"  - {cat}: {amt:.2f} NGN ({ (amt/spending*100) if spending > 0 else 0 :.1f}% of total spending)\n"

    summary += f"- Cash Flow Forecast ({cash_flow_forecast.get('forecast_period_days')} days): Trend is {cash_flow_forecast.get('trend_prediction', 'N/A')}.\n"

    if net_flow > 0:
        summary += f"\nRecommendation: Great job with a positive cash flow! Consider allocating some of your surplus of {net_flow:.2f} NGN towards savings or investments."
    else:
        summary += f"\nRecommendation: Your spending exceeded your income by {abs(net_flow):.2f} NGN. Review your spending categories to identify areas for potential savings."

    return summary

def generate_data_visualization(data: Any, chart_type: str, title: str) -> str:
    """
    Generates a data visualization (e.g., pie chart for spending, line chart for cash flow).
    Output: URL to the generated image or image data itself (e.g. base64).
    This is a placeholder. Real implementation uses matplotlib, seaborn, plotly, or a chart service.
    """
    # payload = {"data": data, "chart_type": chart_type, "title": title}
    # response = requests.post(config.CHART_GENERATION_SERVICE_API_URL, json=payload)
    # response.raise_for_status()
    # return response.json().get("chart_image_url")

    print(f"Mock Data Visualization: Type='{chart_type}', Title='{title}'")
    # Simulate saving a file and returning a path/URL
    mock_file_name = f"{title.replace(' ', '_').lower()}_{chart_type.lower()}_{random.randint(1000,9999)}.png"
    # with open(config.CHART_IMAGE_STORAGE_PATH + mock_file_name, "w") as f:
    #    f.write(f"Mock chart data for: {title}") # In reality, save image bytes
    return f"{config.CHART_IMAGE_STORAGE_PATH}{mock_file_name}" # Return mock path


# --- Recommendation Tools ---
def suggest_savings_goals(financial_summary: dict, existing_goals: Optional[list] = None) -> list[dict]:
    """Suggests relevant savings goals based on financial summary and existing goals."""
    suggestions = []
    # For mock, just return a couple from default config if no existing goals conflict
    print("Mock Savings Goal Suggestion...")
    if not existing_goals or len(existing_goals) < 2:
        for goal_template in config.DEFAULT_SAVINGS_GOAL_SUGGESTIONS[:2]:
            suggestion = goal_template.copy()
            if "target_percentage_of_income" in suggestion and financial_summary.get("total_income", 0) > 0:
                suggestion["suggested_monthly_saving"] = round(financial_summary["total_income"] * decimal.Decimal(str(suggestion["target_percentage_of_income"])), 2)
            suggestions.append(suggestion)
    return suggestions

def recommend_investment_options(customer_profile: dict, financial_summary: dict) -> list[dict]:
    """Recommends investment options based on customer risk profile, financial situation."""
    # This would involve fetching customer's risk profile, available investment products, etc.
    print("Mock Investment Recommendation...")
    recommendations = []
    if financial_summary.get("net_cash_flow", decimal.Decimal(0)) > 20000: # If good positive cash flow
        recommendations.append({"product_name": "WeezyBank Mutual Fund - Balanced", "type": "Mutual Fund", "expected_return_pa": "8-12%", "risk_level": "Medium"})
    if customer_profile.get("risk_appetite") == "HIGH": # Assuming this field in profile
        recommendations.append({"product_name": "Nigerian Stock Market ETF", "type": "ETF", "expected_return_pa": "10-20%", "risk_level": "High"})
    if not recommendations:
        recommendations.append({"product_name": "High-Yield Savings Account", "type": "Savings", "expected_return_pa": "5-7%", "risk_level": "Low"})
    return recommendations


if __name__ == '__main__':
    print("--- Testing Finance Insights Agent Tools ---")
    mock_account = "0102030405"

    # 1. Fetch Transaction History
    print("\n1. Fetching Transaction History:")
    transactions = fetch_transaction_history(mock_account, lookback_months=1) # Short lookback for test
    if transactions:
        print(f"Fetched {len(transactions)} transactions. First one: {transactions[0]['narration'] if transactions else 'N/A'}")

        # 2. Categorize Transactions
        print("\n2. Categorizing Transactions:")
        categorized_df = categorize_transactions(transactions)
        # print(f"Categorized DataFrame (sample):\n{categorized_df[['transaction_date', 'amount', 'category', 'transaction_flow']].head()}")

        # 3. Calculate Spending Summary
        print("\n3. Calculating Spending Summary:")
        summary = calculate_spending_summary(categorized_df)
        print(json.dumps(summary, indent=2, default=str)) # default=str for Decimal

        # 4. Forecast Cash Flow
        print("\n4. Forecasting Cash Flow:")
        cash_flow_fc = forecast_cash_flow(categorized_df, days_to_forecast=30)
        print(json.dumps(cash_flow_fc, indent=2, default=str))

        # 5. Generate Textual Summary
        print("\n5. Generating Textual Summary:")
        text_summary = generate_textual_summary(summary, cash_flow_fc)
        print(text_summary)

        # 6. Generate Data Visualization (mock)
        print("\n6. Generating Spending Breakdown Chart (Mock):")
        spending_chart_url = generate_data_visualization(summary.get("spending_by_category"), "PIE_CHART", "Monthly Spending Breakdown")
        print(f"Spending Chart URL: {spending_chart_url}")

        # 7. Suggest Savings Goals
        print("\n7. Suggesting Savings Goals:")
        goals = suggest_savings_goals(summary)
        print(json.dumps(goals, indent=2, default=str))

        # 8. Recommend Investment Options
        print("\n8. Recommending Investment Options:")
        mock_cust_profile = {"risk_appetite": "MEDIUM", "investment_horizon_years": 5}
        investments = recommend_investment_options(mock_cust_profile, summary)
        print(json.dumps(investments, indent=2, default=str))
    else:
        print("No transactions fetched, skipping further tests.")

    # Test Fetch Account Balances
    print("\n9. Fetching Account Balances:")
    balances = fetch_account_balances([mock_account, "0011223344"])
    print(json.dumps(balances, indent=2, default=str))
