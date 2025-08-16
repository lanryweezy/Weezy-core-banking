# Tools for Finance Insights Agent

from langchain.tools import tool
from typing import Dict, Any, List, Optional, Literal
import random
import logging
from datetime import datetime, timedelta, date

# Assuming schemas might be imported for type hinting if complex objects are passed
# from .schemas import ... # Example

logger = logging.getLogger(__name__)

# --- Mock Data Generation for Tool ---
def _generate_mock_transactions(customer_id: str, start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """Generates a list of mock transactions for a given period."""
    transactions: List[Dict[str, Any]] = []
    num_days = (end_date - start_date).days + 1

    # Income sources and spending categories
    income_sources = ["Salary", "Business Revenue", "Investment Returns", "Freelance Gig"]
    spending_categories = ["Groceries", "Transport", "Utilities", "Rent/Mortgage", "Entertainment",
                           "Shopping", "Healthcare", "Education", "Travel", "Miscellaneous"]

    # Simulate a primary income source (e.g., Salary) occurring monthly or bi-weekly
    # For simplicity, let's assume one major income event if period covers it.
    if num_days >= 25: # If period is roughly a month or more
        transactions.append({
            "date": (end_date - timedelta(days=random.randint(0,5))).isoformat(), # Near end of period
            "description": random.choice(["Monthly Salary", "Main Business Income"]),
            "amount": random.uniform(150000, 700000), # Positive for income
            "category": "Salary/PrimaryIncome", # Special category for primary income
            "type": "Credit"
        })

    # Simulate other smaller incomes
    for _ in range(random.randint(0, num_days // 15)): # 0 to ~2 smaller incomes per month
        transactions.append({
            "date": (start_date + timedelta(days=random.randint(0, num_days-1))).isoformat(),
            "description": random.choice(["Side Hustle Payment", "Investment Dividend", "Gift Received"]),
            "amount": random.uniform(5000, 50000),
            "category": random.choice(income_sources[1:]), # Exclude primary source here
            "type": "Credit"
        })

    # Simulate spending transactions
    num_spending_transactions = random.randint(num_days // 2, num_days * 2) # 0.5 to 2 spending txns per day
    for _ in range(num_spending_transactions):
        transactions.append({
            "date": (start_date + timedelta(days=random.randint(0, num_days-1))).isoformat(),
            "description": f"{random.choice(spending_categories)} purchase at Merchant {random.randint(100,999)}",
            "amount": -random.uniform(500, 25000), # Negative for spending
            "category": random.choice(spending_categories),
            "type": "Debit"
        })

    # Sort by date (optional, but good practice)
    transactions.sort(key=lambda x: x["date"])
    return transactions


@tool("TransactionAggregationTool")
def transaction_aggregation_tool(
    customer_id: str,
    period: Literal["last_7_days", "last_30_days", "current_month", "last_month", "last_3_months", "year_to_date"] = "last_30_days",
    custom_start_date: Optional[str] = None, # YYYY-MM-DD
    custom_end_date: Optional[str] = None    # YYYY-MM-DD
) -> Dict[str, Any]:
    """
    Simulates fetching and aggregating transactions for a customer over a specified period.
    Calculates total income, total spending, net cashflow, and breakdowns by category/source.

    Args:
        customer_id (str): The customer's unique identifier.
        period (str): Predefined period like "last_30_days", "current_month", etc.
                      Ignored if custom_start_date and custom_end_date are provided.
        custom_start_date (Optional[str]): Custom start date in YYYY-MM-DD format.
        custom_end_date (Optional[str]): Custom end date in YYYY-MM-DD format.

    Returns:
        Dict[str, Any]: A dictionary containing aggregated financial data:
                        'customer_id', 'period_start_date', 'period_end_date',
                        'total_income_ngn', 'total_spending_ngn', 'net_cashflow_ngn',
                        'spending_by_category': Dict[str, float],
                        'income_by_source': Dict[str, float],
                        'raw_transaction_count': int,
                        'status': 'Success' or 'Error',
                        'message': Optional error message.
    """
    logger.info(f"TransactionAggregationTool: Aggregating transactions for customer '{customer_id}', period='{period}', custom_start='{custom_start_date}', custom_end='{custom_end_date}'")

    today = date.today()
    start_dt: date
    end_dt: date = today

    if custom_start_date and custom_end_date:
        try:
            start_dt = date.fromisoformat(custom_start_date)
            end_dt = date.fromisoformat(custom_end_date)
            if start_dt > end_dt:
                return {"status": "Error", "message": "Custom start date cannot be after custom end date."}
        except ValueError:
            return {"status": "Error", "message": "Invalid custom date format. Please use YYYY-MM-DD."}
    else:
        if period == "last_7_days":
            start_dt = today - timedelta(days=6)
        elif period == "last_30_days":
            start_dt = today - timedelta(days=29)
        elif period == "current_month":
            start_dt = today.replace(day=1)
        elif period == "last_month":
            first_day_current_month = today.replace(day=1)
            end_dt = first_day_current_month - timedelta(days=1)
            start_dt = end_dt.replace(day=1)
        elif period == "last_3_months":
            # Approximately last 90 days for simplicity for mock
            start_dt = today - timedelta(days=89)
        elif period == "year_to_date":
            start_dt = today.replace(month=1, day=1)
        else:
            return {"status": "Error", "message": f"Unsupported period: {period}. Supported are: last_7_days, last_30_days, current_month, last_month, last_3_months, year_to_date, or custom dates."}

    # Simulate fetching transactions (in a real system, this would query a database)
    if "error_customer" in customer_id.lower(): # Simulate an error case
        return {"status": "Error", "message": f"Simulated error fetching data for customer {customer_id}."}

    mock_transactions = _generate_mock_transactions(customer_id, start_dt, end_dt)

    total_income = 0.0
    total_spending = 0.0
    spending_by_category: Dict[str, float] = {}
    income_by_source: Dict[str, float] = {}

    for txn in mock_transactions:
        amount = txn["amount"]
        category = txn["category"]
        if amount > 0: # Income
            total_income += amount
            income_by_source[category] = income_by_source.get(category, 0) + amount
        else: # Spending (amount is negative)
            total_spending += abs(amount)
            spending_by_category[category] = spending_by_category.get(category, 0) + abs(amount)

    net_cashflow = total_income - total_spending

    logger.info(f"TransactionAggregationTool: Aggregation complete for customer '{customer_id}'. Income: {total_income:.2f}, Spending: {total_spending:.2f}")

    return {
        "status": "Success",
        "customer_id": customer_id,
        "period_start_date": start_dt.isoformat(),
        "period_end_date": end_dt.isoformat(),
        "total_income_ngn": round(total_income, 2),
        "total_spending_ngn": round(total_spending, 2),
        "net_cashflow_ngn": round(net_cashflow, 2),
        "spending_by_category": {k: round(v,2) for k,v in spending_by_category.items()},
        "income_by_source": {k: round(v,2) for k,v in income_by_source.items()},
        "raw_transaction_count": len(mock_transactions),
        "message": f"Successfully aggregated {len(mock_transactions)} transactions."
    }


# Placeholder for other insight tools (forecasting, visualization, recommendation)
# @tool("CashflowForecastingTool") ...
# @tool("FinancialVisualizationTool") ...
# @tool("InvestmentRecommendationTool") ...


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("--- Testing FinanceInsightsAgent Tools ---")

    print("\n1. Testing TransactionAggregationTool:")
    cust_id = "CUST-FIN-001"

    res_last_30d = transaction_aggregation_tool.run({"customer_id": cust_id, "period": "last_30_days"})
    print(f"  Last 30 Days for {cust_id}: Status={res_last_30d['status']}")
    if res_last_30d['status'] == 'Success':
        print(f"    Income: {res_last_30d['total_income_ngn']}, Spending: {res_last_30d['total_spending_ngn']}, Net: {res_last_30d['net_cashflow_ngn']}")
        print(f"    Spending Categories: {json.dumps(res_last_30d['spending_by_category'], indent=2)}")
        print(f"    Income Sources: {json.dumps(res_last_30d['income_by_source'], indent=2)}")

    res_current_month = transaction_aggregation_tool.run({"customer_id": cust_id, "period": "current_month"})
    print(f"\n  Current Month for {cust_id}: Status={res_current_month['status']}")
    if res_current_month['status'] == 'Success':
         print(f"    Income: {res_current_month['total_income_ngn']}, TxnCount: {res_current_month['raw_transaction_count']}")

    res_custom_period = transaction_aggregation_tool.run({
        "customer_id": cust_id,
        "custom_start_date": (date.today() - timedelta(days=10)).isoformat(),
        "custom_end_date": date.today().isoformat()
    })
    print(f"\n  Custom Period (last 10 days) for {cust_id}: Status={res_custom_period['status']}")
    if res_custom_period['status'] == 'Success':
         print(f"    Net Cashflow: {res_custom_period['net_cashflow_ngn']}")

    res_error_period = transaction_aggregation_tool.run({"customer_id": cust_id, "period": "unknown_period"})
    print(f"\n  Error Period for {cust_id}: Status={res_error_period['status']}, Message='{res_error_period.get('message')}'")

    res_error_customer = transaction_aggregation_tool.run({"customer_id": "error_customer_id", "period": "last_7_days"})
    print(f"\n  Error Customer: Status={res_error_customer['status']}, Message='{res_error_customer.get('message')}'")


@tool("CashflowForecastingTool")
def cashflow_forecasting_tool(
    aggregated_transaction_data: Dict[str, Any],
    forecast_horizon_months: int = 3
) -> Dict[str, Any]:
    """
    Simulates cash flow forecasting based on aggregated transaction data.
    In a real system, this would use time-series models like Prophet or ARIMA.

    Args:
        aggregated_transaction_data (Dict[str, Any]): Output from TransactionAggregationTool
                                                     (must contain 'net_cashflow_ngn', 'period_start_date', 'period_end_date').
        forecast_horizon_months (int): Number of months to forecast ahead.

    Returns:
        Dict[str, Any]: Contains 'status', 'forecast_period_start_date',
                        'forecast_period_end_date', 'predicted_cashflows' (List of monthly forecasts),
                        and an optional 'message'.
    """
    logger.info(f"CashflowForecastingTool: Forecasting for {forecast_horizon_months} months. Input data keys: {aggregated_transaction_data.keys()}")

    if aggregated_transaction_data.get("status") != "Success":
        return {"status": "Error", "message": "Input aggregated_transaction_data indicates an error or is missing."}

    net_cashflow = aggregated_transaction_data.get("net_cashflow_ngn")
    period_start_str = aggregated_transaction_data.get("period_start_date")
    period_end_str = aggregated_transaction_data.get("period_end_date")

    if net_cashflow is None or period_start_str is None or period_end_str is None:
        return {"status": "Error", "message": "Missing essential fields (net_cashflow_ngn, period_start_date, period_end_date) in input data."}

    try:
        period_start_dt = date.fromisoformat(period_start_str)
        period_end_dt = date.fromisoformat(period_end_str)
        num_days_in_period = (period_end_dt - period_start_dt).days + 1
        if num_days_in_period <= 0: num_days_in_period = 30 # Avoid division by zero for very short periods
    except ValueError:
         return {"status": "Error", "message": "Invalid date format in input data."}


    # Simplified mock forecast: Assume average monthly cashflow based on the period, then project with some variance.
    avg_monthly_cashflow = (net_cashflow / num_days_in_period) * 30.44 # Avg days in month

    predicted_cashflows: List[Dict[str, Any]] = []
    forecast_start_date = period_end_dt + timedelta(days=1)

    current_month_start = forecast_start_date.replace(day=1)

    for i in range(forecast_horizon_months):
        # Get the first day of the next month
        if i == 0:
            month_to_forecast_start = current_month_start
        else:
            # Add a month correctly, handling year rollovers
            year = month_to_forecast_start.year + (month_to_forecast_start.month // 12)
            month = month_to_forecast_start.month % 12 + 1
            month_to_forecast_start = date(year, month, 1)

        # Mock some variability
        variance_factor = random.uniform(0.8, 1.2)
        forecasted_value = avg_monthly_cashflow * variance_factor

        predicted_cashflows.append({
            "month_year": month_to_forecast_start.strftime("%Y-%m"),
            "predicted_net_cashflow_ngn": round(forecasted_value, 2),
            "confidence_notes": "Mock forecast with random variance."
        })

    forecast_end_date_approx = month_to_forecast_start # Last month forecasted

    return {
        "status": "Success",
        "forecast_period_start_date": forecast_start_date.isoformat(),
        "forecast_period_end_date_approx": forecast_end_date_approx.isoformat(), # End of the last forecasted month
        "forecast_horizon_months": forecast_horizon_months,
        "predicted_monthly_cashflows": predicted_cashflows,
        "message": f"Generated mock cashflow forecast for {forecast_horizon_months} months."
    }


@tool("FinancialRecommendationTool")
def financial_recommendation_tool(
    customer_id: str,
    aggregated_data: Dict[str, Any], # From TransactionAggregationTool
    forecast_data: Optional[Dict[str, Any]] = None, # From CashflowForecastingTool
    customer_goals: Optional[List[str]] = None # e.g., ["save_for_car", "reduce_debt"]
) -> Dict[str, Any]:
    """
    Simulates generating personalized financial recommendations based on aggregated data,
    forecasts, and customer goals.

    Args:
        customer_id (str): The customer's ID.
        aggregated_data (Dict[str, Any]): Output from TransactionAggregationTool.
        forecast_data (Optional[Dict[str, Any]]): Output from CashflowForecastingTool.
        customer_goals (Optional[List[str]]): List of customer's financial goals.

    Returns:
        Dict[str, Any]: Contains 'recommendations' (List of recommendation dicts).
                        Each recommendation has 'type', 'title', 'description', 'potential_impact'.
    """
    logger.info(f"FinancialRecommendationTool: Generating recommendations for customer '{customer_id}'. Goals: {customer_goals}")
    recommendations: List[Dict[str, Any]] = []

    if aggregated_data.get("status") != "Success":
        return {"status": "Error", "message": "Cannot generate recommendations without valid aggregated data.", "recommendations": []}

    net_cashflow = aggregated_data.get("net_cashflow_ngn", 0.0)
    spending_by_cat = aggregated_data.get("spending_by_category", {})
    income_by_src = aggregated_data.get("income_by_source", {})
    total_spending = aggregated_data.get("total_spending_ngn", 0.0)
    total_income = aggregated_data.get("total_income_ngn", 0.0)

    # Budgeting Advice
    if total_spending > 0 and total_income > 0 and (total_spending / total_income) > 0.85: # Spending > 85% of income
        recommendations.append({
            "type": "Budgeting", "title": "Review Spending Habits",
            "description": "Your spending is currently a significant portion of your income. Consider tracking expenses closely to identify areas for potential savings.",
            "potential_impact": "Improved savings rate, better cash flow management."
        })

    # Identify largest spending category (excluding Rent/Mortgage if too dominant)
    top_spend_cat = None
    max_spend = 0
    for cat, amount in spending_by_cat.items():
        if cat.lower() not in ["rent/mortgage", "loanrepayment"] and amount > max_spend:
            max_spend = amount
            top_spend_cat = cat
    if top_spend_cat and total_spending > 0 and (max_spend / total_spending) > 0.25: # If one cat is >25% of non-essential spend
         recommendations.append({
            "type": "Budgeting", "title": f"Analyze Spending in '{top_spend_cat}'",
            "description": f"A notable portion of your spending is on '{top_spend_cat}'. Review recent transactions in this category for optimization opportunities.",
            "potential_impact": f"Reduce spending on '{top_spend_cat}'."
        })

    # Savings Advice
    if net_cashflow < (total_income * 0.1) and total_income > 0: # Saving less than 10% of income
        recommendations.append({
            "type": "Savings", "title": "Boost Your Savings",
            "description": "Aim to save at least 10-15% of your income. Setting up an automated monthly transfer to a savings account can help achieve this.",
            "potential_impact": "Faster progress towards financial goals, increased emergency fund."
        })
    elif net_cashflow > (total_income * 0.2) and total_income > 0: # Saving well
         recommendations.append({
            "type": "Savings", "title": "Consider High-Yield Savings Options",
            "description": "You have a good positive cash flow. Explore high-yield savings accounts or short-term investments to make your money work harder.",
            "potential_impact": "Increased returns on savings."
        })

    # Investment Advice (very generic mock)
    if net_cashflow > 50000 and total_income > 200000: # Some arbitrary threshold
        recommendations.append({
            "type": "Investment", "title": "Explore Investment Opportunities",
            "description": "With your current financial health, you might consider exploring investment options like mutual funds or treasury bills to grow your wealth. Consult a financial advisor for personalized options.",
            "potential_impact": "Long-term wealth growth."
        })

    # Goal-based advice (mock)
    if customer_goals:
        if "save_for_car" in customer_goals:
            recommendations.append({
                "type": "GoalSpecific", "title": "Saving for a Car",
                "description": "To accelerate savings for a car, allocate a specific amount from your monthly net cashflow towards this goal. Consider a separate 'car fund' account.",
                "potential_impact": "Achieve car purchase goal sooner."
            })
        if "reduce_debt" in customer_goals and total_spending > 0: # Assuming some spending might be debt repayment
            recommendations.append({
                "type": "GoalSpecific", "title": "Accelerate Debt Reduction",
                "description": "Prioritize paying off high-interest debts. If you have positive cash flow, consider allocating extra towards debt repayment.",
                "potential_impact": "Reduce interest payments, become debt-free faster."
            })

    if not recommendations:
        recommendations.append({
            "type": "General", "title": "Maintain Good Financial Habits",
            "description": "Your financial overview looks stable. Continue to monitor your spending and savings regularly.",
            "potential_impact": "Sustained financial well-being."
        })

    return {"status": "Success", "recommendations": recommendations}


@tool("FinancialVisualizationTool")
def financial_visualization_tool(
    chart_type: Literal["spending_pie", "cashflow_trend_line", "income_vs_expense_bar"],
    data: Dict[str, Any], # E.g., output from aggregation or forecasting tool
    title: Optional[str] = None
) -> Dict[str, Any]:
    """
    (Placeholder/Mock) Simulates generating data for a financial visualization or a chart image.
    In a real system, this would use a library like Matplotlib/Seaborn or a charting API
    and could return a base64 encoded image or chart configuration JSON.

    Args:
        chart_type (str): Type of chart (e.g., "spending_pie", "cashflow_trend_line").
        data (Dict[str, Any]): Data to be visualized.
        title (Optional[str]): Title for the chart.

    Returns:
        Dict[str, Any]: Contains 'chart_type', 'status' ("Success_DataOnly", "Success_ImagePlaceholder"),
                        'chart_data_for_frontend' (if applicable), or 'image_placeholder_url'.
    """
    logger.info(f"FinancialVisualizationTool: Request for chart_type='{chart_type}', Title='{title}'")

    if chart_type == "spending_pie" and "spending_by_category" in data:
        return {
            "status": "Success_DataOnly", "chart_type": chart_type, "title": title or "Spending Breakdown",
            "chart_data_for_frontend": { # Data suitable for frontend charting libs (e.g., Chart.js, D3)
                "labels": list(data["spending_by_category"].keys()),
                "values": list(data["spending_by_category"].values())
            },
            "message": "Data for spending pie chart prepared."
        }
    elif chart_type == "cashflow_trend_line" and "predicted_monthly_cashflows" in data:
         # Assuming data["predicted_monthly_cashflows"] is a list of {"month_year": "YYYY-MM", "predicted_net_cashflow_ngn": ...}
        return {
            "status": "Success_DataOnly", "chart_type": chart_type, "title": title or "Cashflow Forecast Trend",
            "chart_data_for_frontend": {
                "labels": [item["month_year"] for item in data["predicted_monthly_cashflows"]],
                "values": [item["predicted_net_cashflow_ngn"] for item in data["predicted_monthly_cashflows"]]
            },
            "message": "Data for cashflow trend line chart prepared."
        }
    else:
        return {
            "status": "Error", "chart_type": chart_type,
            "message": f"Unsupported chart type '{chart_type}' or required data missing for this mock."
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("--- Testing FinanceInsightsAgent Tools (Continued) ---")

    # Sample aggregated data (output from TransactionAggregationTool)
    sample_agg_data_good = {
        "status": "Success", "customer_id": "CUST-FIN-001",
        "period_start_date": "2023-09-01", "period_end_date": "2023-09-30",
        "total_income_ngn": 500000.00, "total_spending_ngn": 350000.00, "net_cashflow_ngn": 150000.00,
        "spending_by_category": {"Groceries": 80000, "Transport": 40000, "Rent/Mortgage": 150000, "Entertainment": 50000, "Utilities": 30000},
        "income_by_source": {"Salary/PrimaryIncome": 480000, "Freelance Gig": 20000},
        "raw_transaction_count": 50
    }
    sample_agg_data_tight = {
        "status": "Success", "customer_id": "CUST-FIN-002",
        "period_start_date": "2023-09-01", "period_end_date": "2023-09-30",
        "total_income_ngn": 200000.00, "total_spending_ngn": 190000.00, "net_cashflow_ngn": 10000.00,
        "spending_by_category": {"Groceries": 70000, "Transport": 50000, "Rent/Mortgage": 60000, "Entertainment": 10000},
        "income_by_source": {"Salary/PrimaryIncome": 200000},
        "raw_transaction_count": 40
    }

    print("\n2. Testing CashflowForecastingTool:")
    forecast_res1 = cashflow_forecasting_tool.run({"aggregated_transaction_data": sample_agg_data_good, "forecast_horizon_months": 3})
    print(f"  Forecast (Good Cashflow): Status={forecast_res1['status']}")
    if forecast_res1['status'] == 'Success':
        print(f"    Horizon: {forecast_res1['forecast_horizon_months']} months, Predictions: {len(forecast_res1['predicted_monthly_cashflows'])}")
        # print(f"    {json.dumps(forecast_res1['predicted_monthly_cashflows'], indent=2)}")

    forecast_res2 = cashflow_forecasting_tool.run({"aggregated_transaction_data": sample_agg_data_tight, "forecast_horizon_months": 6})
    print(f"  Forecast (Tight Cashflow): Status={forecast_res2['status']}")
    if forecast_res2['status'] == 'Success':
        print(f"    Horizon: {forecast_res2['forecast_horizon_months']} months, Predictions: {len(forecast_res2['predicted_monthly_cashflows'])}")


    print("\n3. Testing FinancialRecommendationTool:")
    recom_res1 = financial_recommendation_tool.run({
        "customer_id": "CUST-FIN-001", "aggregated_data": sample_agg_data_good,
        "forecast_data": forecast_res1, "customer_goals": ["save_for_car"]
    })
    print(f"  Recommendations (Good Cashflow): Status={recom_res1['status']}, Count={len(recom_res1.get('recommendations',[]))}")
    # if recom_res1.get('recommendations'): print(json.dumps(recom_res1['recommendations'], indent=2))

    recom_res2 = financial_recommendation_tool.run({
        "customer_id": "CUST-FIN-002", "aggregated_data": sample_agg_data_tight,
        "customer_goals": ["reduce_debt", "emergency_fund"]
    })
    print(f"  Recommendations (Tight Cashflow): Status={recom_res2['status']}, Count={len(recom_res2.get('recommendations',[]))}")
    # if recom_res2.get('recommendations'): print(json.dumps(recom_res2['recommendations'], indent=2))


    print("\n4. Testing FinancialVisualizationTool (Placeholder):")
    viz_res_pie = financial_visualization_tool.run({"chart_type": "spending_pie", "data": sample_agg_data_good['spending_by_category'], "title": "My Spending"})
    print(f"  Visualization (Pie Chart Data): Status={viz_res_pie['status']}")
    # if viz_res_pie.get('chart_data_for_frontend'): print(json.dumps(viz_res_pie['chart_data_for_frontend'], indent=2))

    viz_res_line = financial_visualization_tool.run({"chart_type": "cashflow_trend_line", "data": forecast_res1.get('predicted_monthly_cashflows', {}), "title": "Cashflow Outlook"}) # Data needs to be list of dicts
    # This test might fail if forecast_res1['predicted_monthly_cashflows'] is not the expected dict structure
    # Corrected data structure for line chart test:
    line_chart_data = {"predicted_monthly_cashflows": forecast_res1.get('predicted_monthly_cashflows', [])}
    viz_res_line = financial_visualization_tool.run({"chart_type": "cashflow_trend_line", "data": line_chart_data, "title": "Cashflow Outlook"})
    print(f"  Visualization (Line Chart Data): Status={viz_res_line['status']}")


    print("\nFinance Insights Agent tools (TransactionAggregation, CashflowForecasting, FinancialRecommendation, FinancialVisualization implemented with mocks).")
