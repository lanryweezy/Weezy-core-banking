# Tools for Finance Insights Agent

# from langchain.tools import tool
# import pandas as pd
# import numpy as np
# from prophet import Prophet # For forecasting (example library)
# import matplotlib.pyplot as plt # For generating charts
# import base64 # To encode images for JSON transport
# from io import BytesIO

# # Mock data fetching function (in reality, this would query a DB or API)
# def _get_customer_transaction_data(customer_id: str, period_months: int = 12) -> pd.DataFrame:
#     # Generate sample data
#     rng = pd.date_range(end=pd.Timestamp.now(), periods=period_months * 30, freq='D')
#     data = pd.DataFrame({
#         'ds': rng,
#         'amount': np.random.uniform(-50000, 200000, size=len(rng)), # income and expenses
#         'category': np.random.choice(['Salary', 'Groceries', 'Transport', 'Utilities', 'Entertainment', 'Savings', 'LoanRepayment'], size=len(rng))
#     })
#     data.loc[data['category'] == 'Salary', 'amount'] = abs(data['amount']) # Salaries are positive
#     data.loc[data['category'] != 'Salary', 'amount'] = -abs(data['amount']) # Expenses are negative
#     return data.rename(columns={'amount': 'y'}) # Prophet expects 'ds' and 'y'

# @tool("FinancialDataAnalysisTool")
# def data_analysis_tool(customer_id: str, data_source_config: dict) -> dict:
#     """
#     Analyzes historical financial data (transactions, balances) for a customer or segment.
#     Calculates spending by category, income vs. expense ratios, savings rate, etc.
#     Input: customer_id (or segment_id), data_source_config (details on how to get data).
#     Output: Dictionary containing structured analysis results (e.g., spending breakdown).
#     """
#     print(f"Data Analysis Tool: Analyzing data for {customer_id} using {data_source_config}")
#     # df = _get_customer_transaction_data(customer_id, period_months=data_source_config.get("period_months", 12))
#     # spending_df = df[df['y'] < 0].copy()
#     # spending_df['y'] = abs(spending_df['y'])
#     # spending_by_category = spending_df.groupby('category')['y'].sum().sort_values(ascending=False).to_dict()

#     # income_df = df[df['y'] > 0]
#     # total_income = income_df['y'].sum()
#     # total_spending = spending_df['y'].sum()
#     # savings_rate = (total_income - total_spending) / total_income if total_income > 0 else 0

#     # Mock analysis
#     spending_by_category = {"Groceries": 50000, "Transport": 25000, "Utilities": 15000, "Entertainment": 20000}
#     total_income = 200000
#     total_spending = 110000
#     savings_rate = 0.45

#     return {
#         "spending_by_category": spending_by_category,
#         "total_income": total_income,
#         "total_spending": total_spending,
#         "savings_rate": savings_rate,
#         "analysis_period_months": data_source_config.get("period_months", 12)
#     }

# @tool("TimeSeriesForecastingTool")
# def forecasting_tool(customer_id: str, data_source_config: dict, forecast_horizon_months: int) -> dict:
#     """
#     Performs time-series forecasting (e.g., cash flow, balance projection) using models like Prophet or ARIMA.
#     Input: customer_id, data_source_config, and forecast_horizon_months.
#     Output: Dictionary with forecast data (dates and predicted values).
#     """
#     print(f"Forecasting Tool: Generating {forecast_horizon_months}-month forecast for {customer_id}")
#     # df = _get_customer_transaction_data(customer_id, period_months=data_source_config.get("historical_months", 24))
#     # # Aggregate to daily net cash flow for forecasting
#     # daily_cashflow = df.groupby('ds')['y'].sum().reset_index()

#     # model = Prophet()
#     # model.fit(daily_cashflow)
#     # future = model.make_future_dataframe(periods=forecast_horizon_months * 30)
#     # forecast_df = model.predict(future)

#     # # Select relevant columns (ds, yhat, yhat_lower, yhat_upper)
#     # forecast_output = forecast_df[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(forecast_horizon_months * 30)
#     # forecast_output['ds'] = forecast_output['ds'].dt.strftime('%Y-%m-%d') # Convert dates to string for JSON

#     # Mock forecast
#     forecast_dates = pd.date_range(start=pd.Timestamp.now() + pd.Timedelta(days=1), periods=forecast_horizon_months*4, freq='W')
#     forecast_data = {
#         "dates": [d.strftime('%Y-%m-%d') for d in forecast_dates],
#         "predicted_cashflow": np.random.randint(-10000, 10000, size=len(forecast_dates)).tolist()
#     }
#     return {"forecast_type": "weekly_net_cashflow", "horizon_months": forecast_horizon_months, "data": forecast_data}

# @tool("DataVisualizationTool")
# def visualization_tool(viz_type: str, data: dict, title: str) -> str:
#     """
#     Generates visualizations (charts, graphs) from financial data.
#     Input: viz_type ('pie_chart_spending', 'bar_chart_income_expense', 'line_forecast'), data (dict), title (str).
#     Output: Base64 encoded string of the generated image (e.g., PNG).
#     """
#     print(f"Visualization Tool: Generating '{viz_type}' titled '{title}'")
#     # plt.figure(figsize=(8, 6))
#     # if viz_type == 'pie_chart_spending' and 'spending_by_category' in data:
#     #     labels = data['spending_by_category'].keys()
#     #     sizes = data['spending_by_category'].values()
#     #     plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
#     #     plt.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
#     # elif viz_type == 'line_forecast' and 'dates' in data and 'predicted_cashflow' in data:
#     #     plt.plot(pd.to_datetime(data['dates']), data['predicted_cashflow'], marker='o')
#     #     plt.xticks(rotation=45)
#     #     plt.ylabel("Predicted Cashflow (NGN)")
#     #     plt.grid(True)
#     # else:
#     #     plt.text(0.5, 0.5, 'Unsupported chart type or data missing', ha='center', va='center')

#     # plt.title(title)
#     # buf = BytesIO()
#     # plt.savefig(buf, format="png")
#     # plt.close() # Close the figure to free memory
#     # image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
#     # return image_base64
#     return "mock_base64_encoded_image_string" # Placeholder

# @tool("RecommendationEngineTool")
# def recommendation_engine_tool(customer_id: str, analysis_results: dict, financial_goals: list = None) -> list:
#     """
#     Generates personalized financial recommendations (budgeting, savings, investments)
#     based on analysis results and customer's stated goals (if any).
#     Input: customer_id, analysis_results (from data_analysis_tool), optional list of financial_goals.
#     Output: List of recommendation strings or structured recommendation objects.
#     """
#     print(f"Recommendation Engine: Generating recommendations for {customer_id}")
#     recommendations = []
#     # if analysis_results.get("savings_rate", 0) < 0.1:
#     #     recommendations.append("Your savings rate is a bit low. Consider tracking your expenses in categories like 'Entertainment' or 'Dining Out' to find areas to save.")
#     # if analysis_results.get("spending_by_category", {}).get("Subscriptions", 0) > 10000:
#     #     recommendations.append("Review your subscriptions. You might be paying for services you no longer use.")

#     # # Mock recommendations based on goals
#     # if financial_goals:
#     #     if "buy_a_car" in financial_goals:
#     #         recommendations.append("To save for a car, consider setting up an automated monthly transfer to a dedicated savings account. We have high-yield options available.")
#     #     if "emergency_fund" in financial_goals and analysis_results.get("total_income",0) > 0 :
#     #         recommendations.append(f"Aim for an emergency fund covering 3-6 months of expenses (approx. NGN {analysis_results.get('total_spending',0)*3/12 :.0f} - NGN {analysis_results.get('total_spending',0)*6/12 :.0f} per month for your current spending).")

#     if not recommendations:
#         recommendations.append("Continue managing your finances well! Consider exploring investment options to grow your savings further.")

#     return [{"type": "general", "text": rec} for rec in recommendations]


# # List of tools for this agent
# # tools = [data_analysis_tool, forecasting_tool, visualization_tool, recommendation_engine_tool]

print("Finance Insights Agent tools placeholder.")
