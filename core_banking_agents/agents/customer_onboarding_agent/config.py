# Configuration for Customer Onboarding Agent

import os

class Settings:
    AGENT_NAME: str = "CustomerOnboardingAgent"
    VERSION: str = "0.1.0"

    # API Keys - consider loading from environment variables for security
    # SMILE_IDENTITY_API_KEY: str = os.getenv("SMILE_IDENTITY_API_KEY", "your_smile_identity_api_key")
    # NIBSS_API_KEY: str = os.getenv("NIBSS_API_KEY", "your_nibss_api_key")
    # COREID_API_KEY: str = os.getenv("COREID_API_KEY", "your_coreid_api_key")

    # Service Endpoints
    # OCR_SERVICE_URL: str = os.getenv("OCR_SERVICE_URL", "http://localhost:8001/ocr")
    # FACE_MATCH_SERVICE_URL: str = os.getenv("FACE_MATCH_SERVICE_URL", "http://localhost:8002/face_match")
    # BVN_VERIFICATION_URL: str = os.getenv("BVN_VERIFICATION_URL", "https://api.nibss-plc.com.ng/bvn/verify") # Example
    # NIN_VERIFICATION_URL: str = os.getenv("NIN_VERIFICATION_URL", "https://api.nimc.gov.ng/nin/verify") # Example

    # Thresholds
    MIN_FACE_MATCH_SCORE: float = 0.85

    # LLM Configuration (if using LangChain/CrewAI)
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    # LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4-turbo")

    # Qdrant/Redis (if used by memory.py)
    # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    # REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    # QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    # QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", 6333))
    # QDRANT_ONBOARDING_COLLECTION: str = "onboarding_interactions"


settings = Settings()

if __name__ == "__main__":
    print(f"Configuration for {settings.AGENT_NAME} v{settings.VERSION}")
    # print(f"Smile Identity Key (example): {settings.SMILE_IDENTITY_API_KEY}")
    # print(f"OpenAI Key available: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
    print("Customer Onboarding Agent configuration placeholder.")
