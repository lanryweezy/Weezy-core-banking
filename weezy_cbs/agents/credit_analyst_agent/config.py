# Configuration for Credit Analyst Agent

WEEZY_API_KEY = "dd8e9064465a8311.UF1vXkGPNWCb8jQ4NFybk0VxV7eXIIKLUEyhumSJISre" # General API Key, if needed

# Document Analysis (OCR + LLM) Service - could be a shared service or specific endpoint
DOCUMENT_ANALYSIS_SERVICE_URL = "http://localhost:5003/analyze_document" # Example

# Credit Scoring Model - this could be an internal model endpoint or a third-party API
# Option 1: Internal AI Model from ai_automation_layer
INTERNAL_CREDIT_SCORING_API_URL = "http://localhost:8000/api/v1/ai-automation/predict/credit-score" # Example FastAPI endpoint for our AI module

# Option 2: Third-party Credit Scoring Service (e.g. a specialized fintech provider)
# THIRD_PARTY_CREDIT_SCORING_API_URL = "https://api.thirdpartyscorer.com/v2/score"
# THIRD_PARTY_CREDIT_SCORING_API_KEY = "your_third_party_scorer_api_key"

# Risk Rules Database/Service - This might be a set of configurable rules or a dedicated rules engine API
# For simplicity, could be part of the agent's logic or a simple JSON config initially.
# RISK_RULES_ENGINE_URL = "http://localhost:5004/evaluate_risk_rules"

# Loan Application Module API (to fetch application details, update status)
LOAN_APPLICATION_API_BASE_URL = "http://localhost:8000/api/v1/loans/applications" # Example
GET_LOAN_APP_ENDPOINT = f"{LOAN_APPLICATION_API_BASE_URL}/{{application_id}}"
UPDATE_LOAN_APP_STATUS_ENDPOINT = f"{LOAN_APPLICATION_API_BASE_URL}/{{application_id}}/status" # Conceptual

# Thresholds and Parameters
MIN_ACCEPTABLE_CREDIT_SCORE = 580
MAX_DTI_RATIO = 0.45 # Debt-to-Income Ratio
AUTO_APPROVAL_SCORE_THRESHOLD = 720
AUTO_REJECTION_SCORE_THRESHOLD = 500

# Default currency for financial values if not specified
DEFAULT_CURRENCY = "NGN"
