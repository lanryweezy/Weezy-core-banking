# Configuration for Finance Insights Agent

import os

class Settings:
    AGENT_NAME: str = "FinanceInsightsAgent"
    VERSION: str = "0.1.0"

    # Data Sources - Connection details for where to fetch financial data
    # CORE_BANKING_API_URL_FOR_INSIGHTS: str = os.getenv("CORE_BANKING_API_URL_FOR_INSIGHTS", "http://mock-cbs-api/insights_data")
    # DATA_WAREHOUSE_CONN_STRING: str = os.getenv("DATA_WAREHOUSE_CONN_STRING", "postgresql://user:pass@host:port/dw")

    # Forecasting Model Parameters
    # DEFAULT_FORECAST_HORIZON_MONTHS: int = 6
    # PROPHET_SEASONALITY_MODE: str = "multiplicative" # 'additive' or 'multiplicative'

    # Visualization Settings
    # CHART_DEFAULT_WIDTH_INCHES: int = 10
    # CHART_DEFAULT_HEIGHT_INCHES: int = 6
    # CHART_OUTPUT_FORMAT: str = "png" # png, jpg, svg

    # Recommendation Engine Parameters
    # Path to recommendation rules or model if applicable
    # RECOMMENDATION_RULES_PATH: str = os.getenv("RECOMMENDATION_RULES_PATH", "./insights_rules/recommendations.json")
    # MIN_CONFIDENCE_FOR_RECOMMENDATION: float = 0.6

    # LLM Configuration (for generating narrative summaries, interpreting data, personalizing advice)
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    # LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME_INSIGHTS", "gpt-4-turbo") # High quality model needed

    # Redis (for memory.py: customer goals, past reports, feedback)
    # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    # REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    # REDIS_INSIGHTS_DB: int = int(os.getenv("REDIS_INSIGHTS_DB", 7))

settings = Settings()

if __name__ == "__main__":
    print(f"Configuration for {settings.AGENT_NAME} v{settings.VERSION}")
    # print(f"Default Forecast Horizon: {settings.DEFAULT_FORECAST_HORIZON_MONTHS} months")
    # print(f"OpenAI Key available: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
    print("Finance Insights Agent configuration placeholder.")
