# Configuration for Customer Support Agent

import os

class Settings:
    AGENT_NAME: str = "CustomerSupportAgent"
    VERSION: str = "0.1.0"

    # CRM Integration
    # CRM_API_BASE_URL: str = os.getenv("CRM_API_BASE_URL", "https://api.mock-crm.com/v1")
    # CRM_API_KEY: str = os.getenv("CRM_API_KEY", "your_crm_api_key")

    # Knowledge Base
    # Path to knowledge base files or API endpoint
    # KNOWLEDGE_BASE_PATH: str = os.getenv("KNOWLEDGE_BASE_PATH", "./kb_data.json") # Could be a Vector DB connection too
    # Or if API:
    # KNOWLEDGE_BASE_API_URL: str = os.getenv("KNOWLEDGE_BASE_API_URL", "http://localhost:8007/query_kb")

    # Core Banking API (for read-only queries relevant to support)
    # CORE_BANKING_SUPPORT_API_URL: str = os.getenv("CORE_BANKING_SUPPORT_API_URL", "http://mock-cbs/api/support")

    # Notification Services (for sending updates to customers, if agent handles this)
    # SMS_GATEWAY_URL: str = os.getenv("SMS_GATEWAY_URL", "https://api.mocksmsgateway.com/send")
    # EMAIL_SERVICE_URL: str = os.getenv("EMAIL_SERVICE_URL", "https://api.mockemailservice.com/send")

    # LLM Configuration
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    # LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME_SUPPORT", "gpt-4o") # Good conversational model

    # Redis (for memory.py: chat history, preferences, sentiment)
    # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    # REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    # REDIS_SUPPORT_DB: int = int(os.getenv("REDIS_SUPPORT_DB", 5))

    # Default settings
    DEFAULT_LANGUAGE: str = "en" # English
    MAX_CHAT_HISTORY_MESSAGES: int = 20 # Number of past messages to consider in context

settings = Settings()

if __name__ == "__main__":
    print(f"Configuration for {settings.AGENT_NAME} v{settings.VERSION}")
    # print(f"CRM API Base URL: {settings.CRM_API_BASE_URL}")
    # print(f"Knowledge Base Path/URL: {settings.KNOWLEDGE_BASE_PATH if settings.KNOWLEDGE_BASE_PATH else settings.KNOWLEDGE_BASE_API_URL}")
    # print(f"OpenAI Key available: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
    print("Customer Support Agent configuration placeholder.")
