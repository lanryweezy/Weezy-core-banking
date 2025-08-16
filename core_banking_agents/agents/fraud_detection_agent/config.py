# Configuration for Fraud Detection Agent

import os

class Settings:
    AGENT_NAME: str = "FraudDetectionAgent"
    VERSION: str = "0.1.0"

    # Stream Processing (e.g., Kafka)
    # KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    # KAFKA_TRANSACTION_TOPIC: str = os.getenv("KAFKA_TRANSACTION_TOPIC", "raw_transactions")
    # KAFKA_ALERTS_TOPIC: str = os.getenv("KAFKA_ALERTS_TOPIC", "fraud_alerts")
    # KAFKA_CONSUMER_GROUP: str = os.getenv("KAFKA_CONSUMER_GROUP", "fraud_detection_group")

    # ML Model Endpoint
    # ML_FRAUD_MODEL_ENDPOINT: str = os.getenv("ML_FRAUD_MODEL_ENDPOINT", "http://localhost:8006/predict_fraud")

    # Rules Engine Configuration
    # Path to rules file or DB connection for rules
    # FRAUD_RULES_PATH: str = os.getenv("FRAUD_RULES_PATH", "./fraud_rules.json") # Example

    # Alerting Configuration
    # ALERT_EMAIL_RECIPIENTS: List[str] = os.getenv("ALERT_EMAIL_RECIPIENTS", "fraudteam@bank.com,compliance@bank.com").split(',')
    # ALERT_SMS_NUMBERS: List[str] = os.getenv("ALERT_SMS_NUMBERS", "+2348000000000").split(',')
    # WEBHOOK_ALERT_URL: str = os.getenv("WEBHOOK_ALERT_URL", "https://ops.bank.com/hooks/fraud_alert")

    # LLM Configuration (if used for summarizing alerts or interpreting patterns)
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    # LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME_FRAUD", "gpt-3.5-turbo")

    # Redis (for memory.py: velocity, blacklists, fingerprints)
    # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    # REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    # REDIS_FRAUD_DB: int = int(os.getenv("REDIS_FRAUD_DB", 3))

    # Thresholds and Parameters
    DEFAULT_ANOMALY_SCORE_THRESHOLD: float = 0.75
    HIGH_RISK_SCORE_THRESHOLD: float = 0.90
    TRANSACTION_VELOCITY_WINDOW_SECONDS: int = 3600 # 1 hour
    MAX_TRANSACTIONS_PER_WINDOW_PER_USER: int = 10

settings = Settings()

if __name__ == "__main__":
    print(f"Configuration for {settings.AGENT_NAME} v{settings.VERSION}")
    # print(f"Kafka Transaction Topic: {settings.KAFKA_TRANSACTION_TOPIC}")
    # print(f"ML Fraud Model Endpoint: {settings.ML_FRAUD_MODEL_ENDPOINT}")
    # print(f"Default Anomaly Score Threshold: {settings.DEFAULT_ANOMALY_SCORE_THRESHOLD}")
    # print(f"OpenAI Key available: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
    print("Fraud Detection Agent configuration placeholder.")
