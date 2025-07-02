# Configuration for Finance Insights Agent

WEEZY_API_KEY = "dd8e9064465a8311.UF1vXkGPNWCb8jQ4NFybk0VxV7eXIIKLUEyhumSJISre" # General API Key, if needed

# Data Sources - APIs to fetch customer transaction history and account balances
# These would point to relevant CBS modules.
ACCOUNTS_API_BASE_URL = "http://localhost:8000/api/v1/accounts-ledger"
GET_ACCOUNT_BALANCE_ENDPOINT = f"{ACCOUNTS_API_BASE_URL}/accounts/{{account_number}}/balance"
GET_ACCOUNT_TRANSACTIONS_ENDPOINT = f"{ACCOUNTS_API_BASE_URL}/accounts/{{account_number}}/ledger"
# Example: ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=1000

CUSTOMER_PROFILE_API_URL = "http://localhost:8000/api/v1/customer-identity/{{customer_id}}/profile360" # Example

# Time-series Forecasting Model/Service (if using an external or dedicated internal service)
# FORECASTING_SERVICE_API_URL = "http://localhost:5009/forecast/cashflow" # Example
# Or, if using libraries like Prophet/ARIMA directly within the agent's tools, no API URL needed here.

# Data Visualization Configuration (if agent generates charts directly or calls a service)
# CHART_GENERATION_SERVICE_API_URL = "http://localhost:5010/generate_chart" # Example
DEFAULT_CHART_TYPE_SPENDING_BREAKDOWN = "PIE_CHART"
DEFAULT_CHART_TYPE_CASH_FLOW_TREND = "LINE_CHART"
CHART_IMAGE_STORAGE_PATH = "./generated_charts/" # Local path, or S3 bucket

# Insight Generation Parameters
DEFAULT_TRANSACTION_HISTORY_LOOKBACK_MONTHS = 6
SPENDING_CATEGORIZATION_MODEL_ENDPOINT = "http://localhost:8000/api/v1/ai-automation/categorize/transaction" # Conceptual, if using ML for categorization
MIN_TRANSACTIONS_FOR_MEANINGFUL_INSIGHTS = 20 # Minimum number of transactions needed in period
CASH_FLOW_FORECAST_PERIOD_DAYS = 90 # Predict cash flow for next 90 days

# Savings Goals & Investment Options (can be static config or fetched from another module/service)
DEFAULT_SAVINGS_GOAL_SUGGESTIONS = [
    {"name": "Emergency Fund", "target_percentage_of_income": 0.15, "description": "Save for unexpected expenses."},
    {"name": "Vacation Fund", "target_amount": 200000.00, "timeframe_months": 12, "description": "Plan your next getaway!"},
    {"name": "Education Fund", "target_percentage_of_income": 0.10, "description": "Invest in your or your family's future learning."}
]
# INVESTMENT_OPTIONS_API_URL = "http://localhost:8000/api/v1/investment-products/list" # If dynamic

# Notification/Communication Preferences (if agent proactively sends insights)
# USER_COMMUNICATION_PREFERENCES_API_URL = "http://localhost:8000/api/v1/digital-channels/users/{{customer_id}}/preferences"
# DEFAULT_INSIGHT_DELIVERY_CHANNEL = "IN_APP_NOTIFICATION" # Or EMAIL, SMS

# LLM Service for generating textual summaries (if used)
# LLM_TEXT_SUMMARY_API_URL = "http://localhost:8000/api/v1/ai-automation/llm/execute-task"
# LLM_PROMPT_FOR_FINANCIAL_SUMMARY = """
# Given the following financial data:
# Income: {total_income}
# Spending: {total_spending}
# Top Spending Categories: {top_categories}
# Predicted Cash Flow Trend: {cash_flow_trend}
# Generate a concise, helpful financial summary for the customer.
# """

# Output formats for insights
DEFAULT_TEXT_SUMMARY_LENGTH = "MEDIUM" # SHORT, MEDIUM, LONG
EXPORT_FORMATS_SUPPORTED = ["PDF", "CSV"] # If insights can be exported
