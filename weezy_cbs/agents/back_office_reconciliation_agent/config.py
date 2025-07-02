# Configuration for Back Office Reconciliation Agent

WEEZY_API_KEY = "dd8e9064465a8311.UF1vXkGPNWCb8jQ4NFybk0VxV7eXIIKLUEyhumSJISre" # General API Key, if needed

# Internal Ledger API (from accounts_ledger_management module)
LEDGER_API_BASE_URL = "http://localhost:8000/api/v1/accounts-ledger"
GET_LEDGER_ENTRIES_ENDPOINT = f"{LEDGER_API_BASE_URL}/accounts/{{account_number}}/ledger" # Or a bulk export endpoint for all relevant GLs/accounts
# Example: GET_DAILY_LEDGER_SNAPSHOT_ENDPOINT = f"{LEDGER_API_BASE_URL}/ledger/daily-snapshot?date={{date}}"

# Payment Processor API Configurations
# These would be from the payments_integration_layer configurations or direct SDKs.

# Paystack API (Example)
PAYSTACK_API_BASE_URL = "https://api.paystack.co" # From payments_integration_layer config
PAYSTACK_TRANSACTIONS_ENDPOINT = f"{PAYSTACK_API_BASE_URL}/transaction" # List transactions
PAYSTACK_SECRET_KEY = "sk_your_paystack_secret_key" # Should be securely managed, ideally via payments_integration_layer service

# Interswitch API (Example - conceptual, API details vary)
INTERSWITCH_API_BASE_URL = "https://api.interswitchgroup.com"
INTERSWITCH_TRANSACTIONS_ENDPOINT = f"{INTERSWITCH_API_BASE_URL}/transactions/query" # Conceptual
INTERSWITCH_CLIENT_ID = "your_interswitch_client_id"
INTERSWITCH_CLIENT_SECRET = "your_interswitch_client_secret"

# BankOne API (Example - if integrating with another core banking or MFB system)
# BANKONE_API_BASE_URL = "https://api.bankone.ng/v3"
# BANKONE_TRANSACTIONS_ENDPOINT = f"{BANKONE_API_BASE_URL}/transactions"
# BANKONE_AUTH_TOKEN = "your_bankone_auth_token"

# Reconciliation Parameters
DEFAULT_RECONCILIATION_DATE_RANGE_DAYS = 1 # Reconcile for yesterday's transactions by default
RECONCILIATION_MATCHING_FIELDS = ["transaction_id", "amount", "date", "reference_number"] # Fields to use for matching
RECONCILIATION_AMOUNT_TOLERANCE = 0.01 # NGN 0.01 (1 kobo) tolerance for amount matching

# Auto-resolution rules (conceptual - could be more complex logic)
# E.g., if amount matches and date is within 1 hour, and reference contains a common substring.
AUTO_RESOLVE_TIME_WINDOW_HOURS = 1
AUTO_RESOLVE_REFERENCE_SIMILARITY_THRESHOLD = 0.8 # e.g. Jaro-Winkler or Levenshtein distance

# Reporting / Output
RECONCILIATION_REPORT_EMAIL_TO = "backoffice-recon@weezybank.com"
RECONCILIATION_REPORT_PATH = "./recon_reports/" # Local path to save reports

# Supported external sources for reconciliation by this agent
SUPPORTED_RECON_SOURCES = ["PAYSTACK", "INTERSWITCH_SETTLEMENT"] # Add more as needed
