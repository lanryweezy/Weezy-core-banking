# Configuration for the Credit Analyst AI Agent

# Name of the AIAgentConfig entry in the database (conceptual link)
AGENT_CONFIG_NAME = "CreditAnalystAIAgent_v1"

# --- Model Configurations ---
# Credit Scoring Model to use (references AIModelMetadata.model_name)
CREDIT_SCORING_MODEL_NAME = "NIGERIAN_CREDIT_SCORER" # As defined in ai_automation_layer services
CREDIT_SCORING_MODEL_VERSION = None # None means use latest active version

# (Optional) Fraud Detection Model to consult during assessment
# FRAUD_DETECTION_MODEL_NAME = "TRANSACTION_FRAUD_DETECTOR" # Example
# FRAUD_DETECTION_MODEL_VERSION = None

# --- Rule Engine Configurations ---
# Identifier for the set of lending rules to apply (references AutomatedRule.module_area or a specific group ID)
LENDING_RULE_SET_ID = "GENERAL_PERSONAL_LOAN_RULES_V1"

# --- Decision Thresholds (Examples - these could also be part of the rule set) ---
# Minimum acceptable credit score for automatic consideration
MIN_CREDIT_SCORE_THRESHOLD_AUTO = 650

# Score range for mandatory human review, even if rules pass
CREDIT_SCORE_MANUAL_REVIEW_RANGE_MIN = 580
CREDIT_SCORE_MANUAL_REVIEW_RANGE_MAX = 649

# Maximum Debt-to-Income (DTI) ratio acceptable (conceptual, requires income & existing debt data)
MAX_DTI_RATIO = 0.45

# --- Output & Logging ---
# Default reasons for rejection if specific rule isn't hit but score is too low
DEFAULT_REJECTION_REASON_LOW_SCORE = "Credit score below minimum threshold."
DEFAULT_REJECTION_REASON_HIGH_RISK = "Application assessed as high risk based on overall profile."

# Logging level for this agent
LOG_LEVEL = "INFO" # DEBUG, INFO, WARNING, ERROR

# --- Agent Behavior ---
# Whether to automatically update loan application status or only provide recommendation
AUTO_UPDATE_APPLICATION_STATUS = True # If False, agent recommends, human updates

# If using an LLM for summarizing findings or generating rationale
# LLM_FOR_RATIONALE_GENERATION = "CREDIT_ANALYST_ASSISTANT_LLM_V1" # AIModelMetadata.model_name

# print(f"Credit Analyst Agent Config Loaded: Scoring Model - {CREDIT_SCORING_MODEL_NAME}, Rule Set - {LENDING_RULE_SET_ID}")
