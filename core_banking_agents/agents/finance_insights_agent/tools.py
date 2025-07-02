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

    print("\nFinance Insights Agent tools (TransactionAggregationTool implemented with mocks).")
