# Core settings for shared services like Database, Redis, Qdrant URLs, API keys for common services.
# Agent-specific configurations should reside in their respective config.py files.

import os
# from dotenv import load_dotenv

# Load environment variables from .env file if it exists (good for local development)
# load_dotenv()

class CoreSettings:
    PROJECT_NAME: str = "CoreBankingAIAgents"
    PROJECT_VERSION: str = "0.1.0"
    DEBUG_MODE: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # Database Configuration (example for PostgreSQL)
    # DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test_core.db") # Default to SQLite for easy start

    # Redis Configuration
    # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    # REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    # REDIS_DEFAULT_DB: int = int(os.getenv("REDIS_DEFAULT_DB", "0"))
    # Agent-specific DBs can be defined here or fetched by convention, e.g., REDIS_ONBOARDING_DB
    # REDIS_ONBOARDING_DB: int = int(os.getenv("REDIS_ONBOARDING_DB", "0"))
    # REDIS_TELLER_DB: int = int(os.getenv("REDIS_TELLER_DB", "1"))
    # ... and so on for other agents

    # Qdrant Configuration
    # QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    # QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    # QDRANT_URL: str = os.getenv("QDRANT_URL", f"http://{QDRANT_HOST}:{QDRANT_PORT}") # For client using URL
    # QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY") # If using Qdrant Cloud
    # QDRANT_ONBOARDING_COLLECTION: str = "onboarding_interactions_core" # Example collection name

    # General LLM Configuration (defaults, can be overridden by agent configs)
    # OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    # DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-3.5-turbo")
    # DEFAULT_EMBEDDING_SIZE: int = int(os.getenv("DEFAULT_EMBEDDING_SIZE", "1536")) # For OpenAI ada-002

    # Mock Core Banking System API (if agents interact with a central mock CBS)
    # MOCK_CBS_API_BASE_URL: str = os.getenv("MOCK_CBS_API_BASE_URL", "http://localhost:8080/api/v1/cbs")

    # NIBSS, Interswitch, etc. base URLs or API keys if shared globally
    # NIBSS_BASE_URL: str = os.getenv("NIBSS_BASE_URL", "https://api.nibss-plc.com.ng") # Example

    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()


core_settings = CoreSettings()

if __name__ == "__main__":
    print(f"Core Project: {core_settings.PROJECT_NAME} v{core_settings.PROJECT_VERSION}")
    print(f"Debug Mode: {core_settings.DEBUG_MODE}")
    # print(f"Database URL: {core_settings.DATABASE_URL}")
    # print(f"Redis Host: {core_settings.REDIS_HOST}:{core_settings.REDIS_PORT}, Default DB: {core_settings.REDIS_DEFAULT_DB}")
    # print(f"Qdrant URL: {core_settings.QDRANT_URL}")
    # print(f"Default LLM Model: {core_settings.DEFAULT_LLM_MODEL}")
    # print(f"Log Level: {core_settings.LOG_LEVEL}")
    print("Core config.py placeholder.")
