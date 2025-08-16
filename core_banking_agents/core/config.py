# Core settings for shared services like Database, Redis, Qdrant URLs, API keys for common services.
# Agent-specific configurations should reside in their respective config.py files but can inherit or use these.

import os
from typing import Optional, List # For type hinting if needed for some settings
# from dotenv import load_dotenv

# Load environment variables from .env file if it exists (good for local development)
# Ensure .env is in your .gitignore
# load_dotenv()

class CoreSettings:
    PROJECT_NAME: str = "CoreBankingAIAgents"
    PROJECT_VERSION: str = os.getenv("PROJECT_VERSION", "0.1.0") # Allow override from env
    DEBUG_MODE: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # --- Database Configuration ---
    # Default to SQLite for easy local setup if no specific URL is provided.
    # For production, always set DATABASE_URL in the environment.
    # Example PostgreSQL: "postgresql://user:password@host:port/database"
    # Example SQLite: "sqlite:///./core_bank_agents_data.db" (file in project root)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./core_bank_agents_data.db")
    # Optional DB Pool settings (more relevant for PostgreSQL/MySQL)
    # DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    # DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))


    # --- Redis Configuration ---
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None) # If your Redis is password-protected
    REDIS_DEFAULT_DB: int = int(os.getenv("REDIS_DEFAULT_DB", "0")) # Default DB for general use

    # Agent-specific Redis DB numbers (examples, adjust as needed)
    # These allow agents to use separate logical databases within the same Redis instance.
    # The RedisClient will look for REDIS_<CLIENT_NAME_UPPER>_DB.
    REDIS_ONBOARDING_DB: int = int(os.getenv("REDIS_ONBOARDING_DB", "1"))
    REDIS_TELLER_DB: int = int(os.getenv("REDIS_TELLER_DB", "2"))
    REDIS_CREDIT_DB: int = int(os.getenv("REDIS_CREDIT_DB", "3")) # For CreditAnalystAgent
    REDIS_FRAUD_DB: int = int(os.getenv("REDIS_FRAUD_DB", "4"))    # For FraudDetectionAgent
    REDIS_COMPLIANCE_DB: int = int(os.getenv("REDIS_COMPLIANCE_DB", "5")) # For ComplianceAgent
    REDIS_SUPPORT_DB: int = int(os.getenv("REDIS_SUPPORT_DB", "6")) # For CustomerSupportAgent
    REDIS_INSIGHTS_DB: int = int(os.getenv("REDIS_INSIGHTS_DB", "7")) # For FinanceInsightsAgent
    REDIS_RECON_DB: int = int(os.getenv("REDIS_RECON_DB", "8")) # For BackOfficeReconciliationAgent
    # Add more as other agents require dedicated Redis DBs


    # --- Qdrant (Vector Database) Configuration ---
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333")) # gRPC port
    QDRANT_REST_PORT: int = int(os.getenv("QDRANT_REST_PORT", "6334")) # REST port (optional for client, good for /readyz)
    QDRANT_URL: Optional[str] = os.getenv("QDRANT_URL", None) # e.g., "http://localhost:6333" or cloud URL. If set, might override host/port.
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY", None) # For Qdrant Cloud or secured instances
    # QDRANT_PREFER_GRPC: bool = os.getenv("QDRANT_PREFER_GRPC", "True").lower() in ("true", "1", "t")

    # Default Qdrant collection parameters (can be overridden by specific use cases)
    DEFAULT_EMBEDDING_SIZE: int = int(os.getenv("DEFAULT_EMBEDDING_SIZE", "384")) # Example: sentence-transformers/all-MiniLM-L6-v2
    # For OpenAI ada-002, use 1536. Choose based on your embedding model.
    DEFAULT_QDRANT_DISTANCE_METRIC: str = os.getenv("DEFAULT_QDRANT_DISTANCE_METRIC", "Cosine").upper() # "Cosine", "Euclid", "Dot"

    # Agent-specific Qdrant collection names (examples)
    QDRANT_ONBOARDING_COLLECTION: str = os.getenv("QDRANT_ONBOARDING_COLLECTION", "onboarding_customer_data")
    QDRANT_SUPPORT_KB_COLLECTION: str = os.getenv("QDRANT_SUPPORT_KB_COLLECTION", "support_knowledge_base")
    QDRANT_FRAUD_PATTERNS_COLLECTION: str = os.getenv("QDRANT_FRAUD_PATTERNS_COLLECTION", "fraud_transaction_patterns")
    # Add more as needed


    # --- General LLM Configuration (Defaults) ---
    # Agents can override these in their own config.py if they need specific models.
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None) # Ensure this is set in your .env for actual LLM use
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-3.5-turbo")
    # DEFAULT_LLM_TEMPERATURE: float = float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.1"))


    # --- Mock Core Banking System API (If agents interact with a central mock CBS) ---
    # MOCK_CBS_API_BASE_URL: str = os.getenv("MOCK_CBS_API_BASE_URL", "http://localhost:8080/api/v1/cbs")


    # --- External Service API Keys (Examples, manage carefully) ---
    # NIBSS_API_KEY: Optional[str] = os.getenv("NIBSS_API_KEY")
    # SMILE_IDENTITY_API_KEY: Optional[str] = os.getenv("SMILE_IDENTITY_API_KEY")


    # --- Logging Configuration ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    # Could add more log settings like format, file path, etc.

core_settings = CoreSettings()

if __name__ == "__main__":
    print(f"--- Core Project Settings ({core_settings.PROJECT_NAME} v{core_settings.PROJECT_VERSION}) ---")
    print(f"Debug Mode: {core_settings.DEBUG_MODE}")
    print(f"Log Level: {core_settings.LOG_LEVEL}")

    print("\nDatabase:")
    print(f"  URL: {core_settings.DATABASE_URL}")

    print("\nRedis:")
    print(f"  Host: {core_settings.REDIS_HOST}:{core_settings.REDIS_PORT}")
    print(f"  Password Set: {'Yes' if core_settings.REDIS_PASSWORD else 'No'}")
    print(f"  Default DB: {core_settings.REDIS_DEFAULT_DB}")
    print(f"  Onboarding DB: {core_settings.REDIS_ONBOARDING_DB}")
    print(f"  Fraud DB: {core_settings.REDIS_FRAUD_DB}")
    # ... print other agent DBs if desired

    print("\nQdrant:")
    if core_settings.QDRANT_URL:
        print(f"  URL: {core_settings.QDRANT_URL}")
    else:
        print(f"  Host: {core_settings.QDRANT_HOST}, Port: {core_settings.QDRANT_PORT}")
    print(f"  API Key Set: {'Yes' if core_settings.QDRANT_API_KEY else 'No'}")
    print(f"  Default Embedding Size: {core_settings.DEFAULT_EMBEDDING_SIZE}")
    print(f"  Default Distance Metric: {core_settings.DEFAULT_QDRANT_DISTANCE_METRIC}")
    print(f"  Support KB Collection: {core_settings.QDRANT_SUPPORT_KB_COLLECTION}")


    print("\nLLM:")
    print(f"  OpenAI API Key Set: {'Yes' if core_settings.OPENAI_API_KEY else 'No (Needed for real LLM use!)'}")
    print(f"  Default LLM Model: {core_settings.DEFAULT_LLM_MODEL}")

    print("\n--- End Core Settings ---")
