# Configuration for Credit Analyst Agent

import os

class Settings:
    AGENT_NAME: str = "CreditAnalystAgent"
    VERSION: str = "0.1.0"

    # Document Analysis (OCR/LLM Service)
    # DOCUMENT_ANALYSIS_SERVICE_URL: str = os.getenv("DOCUMENT_ANALYSIS_SERVICE_URL", "http://localhost:8003/analyze_document")

    # Credit Scoring Model Endpoint
    # CREDIT_SCORING_MODEL_URL: str = os.getenv("CREDIT_SCORING_MODEL_URL", "http://localhost:8004/score_applicant")
    # CREDIT_SCORING_MODEL_API_KEY: str = os.getenv("CREDIT_SCORING_MODEL_API_KEY", "your_scoring_model_api_key")

    # Risk Rules Database/Service
    # RISK_RULES_DB_CONNECTION_STRING: str = os.getenv("RISK_RULES_DB_CONNECTION_STRING", "sqlite:///./risk_rules.db")
    # Or, if it's an API:
    # RISK_RULES_API_URL: str = os.getenv("RISK_RULES_API_URL", "http://localhost:8005/check_rules")

    # LLM Configuration (if using LangChain/CrewAI)
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    # LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME_ANALYST", "gpt-4-turbo")

    # Qdrant/Redis (if used by memory.py)
    # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    # REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    # REDIS_ANALYST_DB: int = int(os.getenv("REDIS_ANALYST_DB", 2))
    # QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    # QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", 6333))
    # QDRANT_LOAN_APPLICATIONS_COLLECTION: str = "loan_applications_archive"

    # Decision Thresholds (examples)
    MIN_ACCEPTABLE_CREDIT_SCORE: int = 620
    MAX_DTI_RATIO: float = 0.45 # Debt-to-Income

settings = Settings()

if __name__ == "__main__":
    print(f"Configuration for {settings.AGENT_NAME} v{settings.VERSION}")
    # print(f"Credit Scoring Model URL: {settings.CREDIT_SCORING_MODEL_URL}")
    # print(f"Min Acceptable Credit Score: {settings.MIN_ACCEPTABLE_CREDIT_SCORE}")
    # print(f"OpenAI Key available: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
    print("Credit Analyst Agent configuration placeholder.")
