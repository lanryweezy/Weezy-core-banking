# Configuration for Teller Agent

import os

class Settings:
    AGENT_NAME: str = "TellerAgent"
    VERSION: str = "0.1.0"

    # Core Banking System API endpoint
    # CORE_BANKING_API_URL: str = os.getenv("CORE_BANKING_API_URL", "http://mock-cbs/api")

    # OTP Service Configuration
    # OTP_SERVICE_URL: str = os.getenv("OTP_SERVICE_URL", "http://mock-otp-service/otp")
    # OTP_DEFAULT_LENGTH: int = 6
    # OTP_EXPIRY_SECONDS: int = 300

    # LLM Configuration (if using LangChain/CrewAI)
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    # LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME_TELLER", "gpt-3.5-turbo")

    # Redis (if used by memory.py)
    # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    # REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    # REDIS_TELLER_DB: int = int(os.getenv("REDIS_TELLER_DB", 1))

settings = Settings()

if __name__ == "__main__":
    print(f"Configuration for {settings.AGENT_NAME} v{settings.VERSION}")
    # print(f"Core Banking API URL: {settings.CORE_BANKING_API_URL}")
    # print(f"OpenAI Key available: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
    print("Teller Agent configuration placeholder.")
