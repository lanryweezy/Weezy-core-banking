# Pydantic schemas for Finance Insights Agent

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class DataSouceConfigInput(BaseModel):
    source_type: str = Field("api", example="api") # api, database_query, file_upload
    connection_details: Optional[Dict[str, Any]] = Field(None, example={"api_endpoint": "/transactions", "auth_token": "secret"})
    query_parameters: Optional[Dict[str, Any]] = Field(None, example={"period_months": 12, "include_categories": True})

class InsightsRequest(BaseModel):
    request_id: Optional[str] = Field(None, example="INSREQ20231027XYZ") # Can be auto-generated
    customer_id: Optional[str] = Field(None, example="CUSTFIN001") # For customer-specific insights
    segment_id: Optional[str] = Field(None, example="AFFLUENT_SEGMENT") # For segment-level insights
    # If neither customer_id nor segment_id is provided, it implies bank-wide or general insights.
    data_source: DataSouceConfigInput
    requested_insight_types: List[str] = Field(..., example=["spending_analysis", "cashflow_forecast", "investment_recommendations"])
    forecast_horizon_months: Optional[int] = Field(3, example=6)
    financial_goals: Optional[List[Dict[str, Any]]] = Field(None, example=[{"goal": "Retirement", "target_age": 60}])

class SpendingAnalysis(BaseModel):
    period_start_date: date
    period_end_date: date
    total_income: float
    total_spending: float
    net_cashflow: float
    spending_by_category: Dict[str, float] = Field(..., example={"Groceries": 50000, "Transport": 30000})
    savings_rate: Optional[float] = Field(None, example=0.15) # (Income - Spending) / Income
    chart_base64: Optional[str] = Field(None, description="Base64 encoded image of spending chart")

class CashflowForecast(BaseModel):
    forecast_period_start_date: date
    forecast_period_end_date: date
    forecast_granularity: str = Field("monthly", example="weekly") # weekly, monthly
    predicted_cashflows: List[Dict[str, Any]] = Field(..., example=[{"date": "2023-11-30", "net_cashflow": 25000}])
    confidence_interval_lower: Optional[List[float]] = None
    confidence_interval_upper: Optional[List[float]] = None
    chart_base64: Optional[str] = Field(None, description="Base64 encoded image of forecast chart")

class Recommendation(BaseModel):
    recommendation_id: str = Field(..., example="REC001_BUDGET_ADJUST")
    recommendation_type: str = Field(..., example="Budgeting") # Budgeting, Savings, Investment, DebtManagement
    short_title: str = Field(..., example="Review Subscription Spending")
    description: str = Field(..., example="Consider reviewing your monthly subscriptions to identify potential savings.")
    potential_impact: Optional[str] = Field(None, example="Save up to NGN 5,000 monthly.")
    actionable_steps: Optional[List[str]] = Field(None)
    confidence_score: Optional[float] = Field(None, example=0.75)

class InsightsReport(BaseModel):
    report_id: str = Field(..., example="FINREP20231027XYZ")
    request_id: Optional[str] = None
    customer_id: Optional[str] = None
    segment_id: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)
    summary: Optional[str] = Field(None, example="Overall financial health is stable with opportunities for increased savings.")
    spending_analysis: Optional[SpendingAnalysis] = None
    cashflow_forecast: Optional[CashflowForecast] = None
    recommendations: Optional[List[Recommendation]] = None
    custom_insights: Optional[List[Dict[str, Any]]] = Field(None) # For other ad-hoc insights

print("Finance Insights Agent Pydantic schemas placeholder.")
