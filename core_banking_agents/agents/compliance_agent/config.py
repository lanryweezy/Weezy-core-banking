# Configuration for Compliance Agent

import os

class Settings:
    AGENT_NAME: str = "ComplianceAgent"
    VERSION: str = "0.1.0"

    # Sanctions List API
    # SANCTIONS_API_ENDPOINT: str = os.getenv("SANCTIONS_API_ENDPOINT", "https://api.mock-sanctions-provider.com/v1/screen")
    # SANCTIONS_API_KEY: str = os.getenv("SANCTIONS_API_KEY", "your_sanctions_api_key")

    # Regulatory Reporting Endpoints (examples for CBN, NFIU)
    # CBN_FINA_PORTAL_URL: str = os.getenv("CBN_FINA_PORTAL_URL", "https://fina.cbn.gov.ng/submit") # Mock
    # NFIU_GOAML_URL: str = os.getenv("NFIU_GOAML_URL", "https://goaml.nfiu.gov.ng/upload") # Mock

    # Internal Policy Rule Engine Config
    # Path to internal policy rules file or DB connection
    # INTERNAL_POLICY_RULES_PATH: str = os.getenv("INTERNAL_POLICY_RULES_PATH", "./internal_compliance_rules.json")

    # LLM Configuration (for SAR drafting, policy interpretation)
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    # LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME_COMPLIANCE", "gpt-4-turbo") # Needs high quality

    # Redis (for memory.py: rules, cases, audit logs)
    # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    # REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    # REDIS_COMPLIANCE_DB: int = int(os.getenv("REDIS_COMPLIANCE_DB", 4))

    # Thresholds & Parameters
    CTR_THRESHOLD_NGN_INDIVIDUAL: int = 5000000
    CTR_THRESHOLD_NGN_CORPORATE: int = 10000000
    DEFAULT_RISK_SCORE_NEW_CUSTOMER: float = 0.3 # Initial risk score

    # Reporting templates paths
    # SAR_TEMPLATE_PATH: str = os.getenv("SAR_TEMPLATE_PATH", "./templates/sar_template.xml") # Example
    # CTR_TEMPLATE_PATH: str = os.getenv("CTR_TEMPLATE_PATH", "./templates/ctr_template.json") # Example

settings = Settings()

if __name__ == "__main__":
    print(f"Configuration for {settings.AGENT_NAME} v{settings.VERSION}")
    # print(f"Sanctions API Endpoint: {settings.SANCTIONS_API_ENDPOINT}")
    # print(f"CTR Threshold (Individual NGN): {settings.CTR_THRESHOLD_NGN_INDIVIDUAL}")
    # print(f"OpenAI Key available: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
    print("Compliance Agent configuration placeholder.")
