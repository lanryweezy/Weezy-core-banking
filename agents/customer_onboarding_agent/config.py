# Configuration for the Customer Onboarding AI Agent

# Name of the AIAgentConfig entry in the database (conceptual link)
# This could be used to load more dynamic configurations if AIAgentConfig service is used.
AGENT_CONFIG_NAME = "CustomerOnboardingAIAgent_v1"

# Default OCR Model to use (references AIModelMetadata.model_name)
DEFAULT_OCR_MODEL_NAME = "STANDARD_OCR_MODEL_V1"
# Alternative: DEFAULT_OCR_MODEL_ID = 123 # Referencing AIModelMetadata.id

# Default initial customer tier upon successful basic onboarding
DEFAULT_INITIAL_CUSTOMER_TIER = "TIER_1" # Should match CBNSupportedAccountTier enum value

# Minimum confidence score from OCR to auto-accept a field (conceptual)
MIN_OCR_CONFIDENCE_FOR_AUTO_ACCEPT = 0.85

# Fields to prioritize for extraction from ID documents via OCR
# This is highly conceptual and depends on the OCR service capabilities
ID_DOCUMENT_OCR_PRIORITY_FIELDS = [
    "first_name",
    "last_name",
    "date_of_birth",
    "document_number",
    "expiry_date",
    "gender",
    "address_street", # Example, OCR might not reliably get full structured address
    "address_city",
    "address_state"
]

# Maximum number of documents to process in a single onboarding session (example limit)
MAX_DOCUMENTS_PER_SESSION = 3

# Parameters for interacting with NIBSS/NIMC (conceptual, actual keys would be in APIServiceConfig)
# These might just be service names that the tools then use to look up full config.
BVN_VERIFICATION_SERVICE_NAME = "NIBSS_BVN_VALIDATION" # Matches APIServiceConfig.service_name
NIN_VERIFICATION_SERVICE_NAME = "NIMC_NIN_VALIDATION"   # Matches APIServiceConfig.service_name

# Logging level for this agent (conceptual)
LOG_LEVEL = "INFO" # DEBUG, INFO, WARNING, ERROR

# If the agent uses a specific LLM for understanding unstructured input or conversation
# This could point to an AIModelMetadata entry of type LLM_TASK_AUTOMATION
# LLM_MODEL_FOR_ONBOARDING_ASSISTANCE = "ONBOARDING_HELPER_LLM_V1"

# Fields that are considered mandatory for Tier 1 onboarding completion by this agent
# This is a simplified representation of business rules.
MANDATORY_FIELDS_TIER_1 = ["first_name", "last_name", "phone_number", "date_of_birth"]

# Print configuration on load (for debugging or insight)
# print(f"Customer Onboarding Agent Config Loaded: OCR Model - {DEFAULT_OCR_MODEL_NAME}, Default Tier - {DEFAULT_INITIAL_CUSTOMER_TIER}")
