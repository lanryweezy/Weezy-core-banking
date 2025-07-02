# Configuration for Customer Support Agent

WEEZY_API_KEY = "dd8e9064465a8311.UF1vXkGPNWCb8jQ4NFybk0VxV7eXIIKLUEyhumSJISre" # General API Key, if needed

# CRM Integration (e.g., to fetch customer history, log interactions, create/update tickets)
# This would be the API of our crm_customer_support module.
CRM_API_BASE_URL = "http://localhost:8000/api/v1/crm-support" # Example
CREATE_TICKET_ENDPOINT = f"{CRM_API_BASE_URL}/tickets"
GET_TICKET_ENDPOINT = f"{CRM_API_BASE_URL}/tickets/{{ticket_id}}" # Or by reference
UPDATE_TICKET_ENDPOINT = f"{CRM_API_BASE_URL}/tickets/{{ticket_id}}"
ADD_TICKET_COMMENT_ENDPOINT = f"{CRM_API_BASE_URL}/tickets/{{ticket_id}}/comments"
GET_CUSTOMER_INTERACTIONS_ENDPOINT = f"{CRM_API_BASE_URL}/customers/{{customer_id}}/interactions" # Example

# Knowledge Base / SOP Documents Access
# This could be a vector database, a search engine over documents, or a wiki API.
KNOWLEDGE_BASE_SEARCH_API_URL = "http://localhost:5007/kb/search" # Example
# Or if using an LLM with RAG (Retrieval Augmented Generation):
# VECTOR_DB_URL = "qdrant_host:port" or "pinecone_api_key_and_env"
# EMBEDDING_MODEL_ENDPOINT = "http://localhost:5008/embed" # If using own embedding model

# Core Banking System API Access (for fetching specific data to answer queries)
# These would point to various CBS modules' APIs.
CUSTOMER_IDENTITY_API_URL = "http://localhost:8000/api/v1/customer-identity"
ACCOUNTS_LEDGER_API_URL = "http://localhost:8000/api/v1/accounts-ledger"
TRANSACTION_MANAGEMENT_API_URL = "http://localhost:8000/api/v1/transactions"
CARDS_WALLETS_API_URL = "http://localhost:8000/api/v1/cards-wallets"
LOAN_MANAGEMENT_API_URL = "http://localhost:8000/api/v1/loans"

# LLM Configuration (if agent uses LLM for understanding queries or drafting replies)
# LLM_SERVICE_API_URL = "http://localhost:8000/api/v1/ai-automation/llm/execute-task" # From our AI module
# DEFAULT_LLM_PROMPT_TEMPLATE_FOR_QUERY_UNDERSTANDING = "User query: '{query}'. Identify intent and key entities."
# DEFAULT_LLM_PROMPT_TEMPLATE_FOR_DRAFTING_REPLY = "Based on context: {context_info}, draft a polite reply for user query: '{query}'."

# Escalation Parameters
MAX_AGENT_ATTEMPTS_BEFORE_HUMAN_ESCALATION = 3 # If AI agent fails to resolve after 3 turns
COMPLEX_QUERY_KEYWORDS_FOR_ESCALATION = ["legal", "fraudulent charge", "account takeover", "formal complaint"] # Keywords that might trigger auto-escalation

# Standard Replies / Snippets (can be loaded from a file or DB)
# STANDARD_REPLIES_CONFIG_PATH = "./standard_replies.json"
STANDARD_REPLIES = {
    "GREETING": "Hello! I'm WeezySupport, your virtual assistant. How can I help you today?",
    "CANNOT_UNDERSTAND": "I'm sorry, I didn't quite understand that. Could you please rephrase or provide more details?",
    "ESCALATING_TO_HUMAN": "This issue seems to require human attention. I'm escalating your request to a customer support specialist. They will get back to you shortly. Your ticket reference is {ticket_ref}.",
    "TRANSACTION_NOT_FOUND": "I couldn't find a transaction with the details you provided. Could you please double-check the reference number or date?",
    "ACCOUNT_BLOCKED_INFO": "For account security, I cannot unblock accounts directly. Please call our support line at 01-WEEZYBANK or visit a branch for assistance with a blocked account."
}

# Channels supported by this agent (informational)
SUPPORTED_CHANNELS = ["CHATBOT", "EMAIL_ASSISTANT", "VOICE_ASSISTANT_NLU"]
