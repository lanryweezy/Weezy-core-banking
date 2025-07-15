# Configuration for Back Office Reconciliation Agent

import os

class Settings:
    AGENT_NAME: str = "BackOfficeReconciliationAgent"
    VERSION: str = "0.1.0"

    # Data Source Configurations (examples)
    # These could be more detailed, perhaps loaded from a YAML or JSON config file
    # INTERNAL_LEDGER_API_BASE: str = os.getenv("INTERNAL_LEDGER_API_BASE", "http://mock-cbs-api/ledger")
    # PAYSTACK_API_KEY: str = os.getenv("PAYSTACK_API_KEY", "sk_your_paystack_key")
    # PAYSTACK_API_URL: str = "https://api.paystack.co/transaction"
    # INTERSWITCH_CLIENT_ID: str = os.getenv("INTERSWITCH_CLIENT_ID", "your_interswitch_client_id")
    # INTERSWITCH_CLIENT_SECRET: str = os.getenv("INTERSWITCH_CLIENT_SECRET", "your_interswitch_secret")
    # INTERSWITCH_API_URL: str = "https://sandbox.interswitchng.com/api/v2/quickteller/transactions" # Example

    # Default matching parameters
    DEFAULT_AMOUNT_TOLERANCE: float = 0.05 # e.g., 5 kobo for NGN amounts
    DEFAULT_TIMESTAMP_WINDOW_SECONDS: int = 300 # 5 minutes for matching transactions by time

    # Path to matching rules and auto-resolution rules configurations
    # MATCHING_RULES_PATH: str = os.getenv("MATCHING_RULES_PATH", "./recon_rules/matching_rules.json")
    # AUTO_RESOLUTION_RULES_PATH: str = os.getenv("AUTO_RESOLUTION_RULES_PATH", "./recon_rules/auto_resolution_rules.json")

    # Reporting settings
    # REPORT_OUTPUT_DIR: str = os.getenv("REPORT_OUTPUT_DIR", "/var/bankdata/recon_reports")
    # REPORT_EMAIL_RECIPIENTS: list[str] = os.getenv("REPORT_EMAIL_RECIPIENTS", "reconteam@bank.com,financeops@bank.com").split(',')

    # LLM Configuration (if used for interpreting discrepancies or report summarization)
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    # LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME_RECON", "gpt-3.5-turbo")

    # Redis (for memory.py: unmatched entries, error patterns, past reports)
    # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    # REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    # REDIS_RECON_DB: int = int(os.getenv("REDIS_RECON_DB", 6))

settings = Settings()

if __name__ == "__main__":
    print(f"Configuration for {settings.AGENT_NAME} v{settings.VERSION}")
    # print(f"Default Amount Tolerance: {settings.DEFAULT_AMOUNT_TOLERANCE}")
    # print(f"Report Output Directory: {settings.REPORT_OUTPUT_DIR}")
    # print(f"OpenAI Key available: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
    print("Back Office Reconciliation Agent configuration placeholder.")
