# Configuration for Compliance Agent

WEEZY_API_KEY = "dd8e9064465a8311.UF1vXkGPNWCb8jQ4NFybk0VxV7eXIIKLUEyhumSJISre" # General API Key, if needed

# Sanctions List API (e.g., OFAC, UN, EU, UK HMT - could be a commercial provider like Refinitiv, Dow Jones)
# For mock, we might use a local file or simple list.
# SANCTIONS_API_PROVIDER_URL = "https://api.sanctionschecker.com/v1/screen"
# SANCTIONS_API_KEY = "your_sanctions_checker_api_key"
# Or, if using internal service from third_party_fintech_integration:
SANCTIONS_SCREENING_SERVICE_URL = "http://localhost:8000/api/v1/third-party-integrations/sanction-screening" # Example

# AML Rules Database/Service - This might be a set of configurable rules from compliance_regulatory_reporting module
# or direct access to its models/services.
# AML_RULES_SERVICE_URL = "http://localhost:8000/api/v1/compliance-reporting/aml-rules/evaluate" # Conceptual
# For now, agent might use hardcoded rules or simple config.

# Audit Trail Generation - API endpoint to log compliance actions
# This would likely call the AuditLog service in core_infrastructure_config_engine.
AUDIT_LOG_API_URL = "http://localhost:8000/api/v1/core-config/audit-logs" # Example

# Regulatory Reporting Service API (from compliance_regulatory_reporting module)
# For preparing/triggering SAR, CTR, etc.
REGULATORY_REPORTING_API_URL = "http://localhost:8000/api/v1/compliance-reporting/reports" # Example
SUBMIT_SAR_ENDPOINT = f"{REGULATORY_REPORTING_API_URL}/nfiu-str/submit" # Conceptual for submitting data for an STR
LOG_CTR_ENDPOINT = f"{REGULATORY_REPORTING_API_URL}/nfiu-ctr/log-transaction" # Conceptual

# Customer & Transaction Data Sources
# These would be internal APIs to fetch necessary data for checks.
CUSTOMER_DATA_API_URL = "http://localhost:8000/api/v1/customer-identity" # Example
TRANSACTION_DATA_API_URL = "http://localhost:8000/api/v1/transactions" # Example

# Thresholds for AML rules (if not managed by a dedicated rules engine service)
# Example: Large transaction threshold for extra scrutiny (different from CTR threshold which is regulatory)
LARGE_TRANSACTION_AML_THRESHOLD_NGN = 2000000.00 # NGN 2 Million for general AML check
HIGH_RISK_COUNTRY_LIST = ["COUNTRY_X", "COUNTRY_Y"] # List of ISO country codes considered high risk

# STR (Suspicious Transaction Report) generation parameters
NFIU_PORTAL_URL_FOR_SUBMISSION = "https://nfiu.gov.ng/goaml" # For documentation/manual reference
DEFAULT_STR_NARRATIVE_TEMPLATE = "Suspicious activity detected for customer {customer_name} (BVN: {bvn}). Transaction ID: {transaction_id}. Reason: {reason_for_suspicion}."

# Sanction list update frequency (informational, actual updates handled by provider/batch job)
# SANCTION_LIST_LAST_UPDATED_CHECK_URL = "https://api.sanctionschecker.com/v1/list_status"

# Default risk scoring parameters for customers (if this agent contributes to or uses it)
# INITIAL_CUSTOMER_RISK_SCORE = 50 # Medium
# HIGH_RISK_SCORE_THRESHOLD = 75
# LOW_RISK_SCORE_THRESHOLD = 25
