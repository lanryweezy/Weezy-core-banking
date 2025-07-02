# Configuration for Fraud Detection Agent

WEEZY_API_KEY = "dd8e9064465a8311.UF1vXkGPNWCb8jQ4NFybk0VxV7eXIIKLUEyhumSJISre" # General API Key, if needed

# AI/ML Fraud Detection Model Endpoint (from ai_automation_layer)
FRAUD_DETECTION_MODEL_API_URL = "http://localhost:8000/api/v1/ai-automation/predict/transaction-fraud"

# Rules Engine Configuration (could be a service or embedded logic)
# RULES_ENGINE_CONFIG_PATH = "./fraud_rules.json" # Path to a JSON file defining rules

# Thresholds for ML model scores or rule triggers
ML_FRAUD_SCORE_THRESHOLD_HIGH = 0.85 # Scores above this are considered high fraud risk
ML_FRAUD_SCORE_THRESHOLD_MEDIUM = 0.60 # Scores above this are medium risk, may need review or step-up

# Transaction Hold/Block API (part of Transaction Management or a dedicated risk action service)
TRANSACTION_HOLD_API_URL = "http://localhost:8000/api/v1/transactions/{transaction_id}/hold" # Example
TRANSACTION_UNHOLD_API_URL = "http://localhost:8000/api/v1/transactions/{transaction_id}/unhold" # Example
TRANSACTION_BLOCK_API_URL = "http://localhost:8000/api/v1/transactions/{transaction_id}/block" # Example

# Notification Service API (to alert human compliance/fraud agents)
# This might be a generic notification service or specific to compliance alerts.
# NOTIFICATION_SERVICE_API_URL = "http://localhost:5005/notify"
# COMPLIANCE_AGENT_EMAIL_GROUP = "fraud-alerts@weezybank.com"

# Data sources for behavioral patterns (these are conceptual, agent might query them)
# CUSTOMER_BEHAVIOR_DB_URL = "postgresql://user:pass@host:port/behavior_db"
# TRANSACTION_HISTORY_API_URL = "http://localhost:8000/api/v1/transactions/account/{account_number}"

# Parameters for pattern matching engine (if used separate from ML)
# Example: Velocity checks
MAX_TRANSACTIONS_PER_HOUR = 20
MAX_TRANSACTION_AMOUNT_PERCENTILE_INCREASE = 500 # % increase over user's 95th percentile amount
NEW_DEVICE_TRANSACTION_LIMIT = 50000.00 # Max amount for first transaction from a new device (NGN)
HIGH_FREQUENCY_THRESHOLD_SECONDS = 10 # Transactions closer than this are high frequency

# Blacklist/Whitelist sources (e.g., API endpoints or file paths)
# BLACKLIST_IP_API_URL = "http://localhost:5006/blacklist/ips"
# WHITELIST_ACCOUNT_API_URL = "http://localhost:5006/whitelist/accounts"

# Kafka/Queue details for live transaction stream (if agent consumes from a queue)
# KAFKA_BROKERS = "kafka1:9092,kafka2:9092"
# KAFKA_TRANSACTION_TOPIC = "live_transactions"
