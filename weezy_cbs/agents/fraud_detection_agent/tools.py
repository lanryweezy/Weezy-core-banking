# Tools for Fraud Detection Agent
import requests
import json
from datetime import datetime, timedelta
from . import config
# from weezy_cbs.ai_automation_layer.schemas import TransactionFraudCheckRequest # If calling internal AI service
# from weezy_cbs.shared import http_client_wrapper # For robust HTTP calls

# Placeholder for schemas if not importing
class TransactionFraudCheckRequestSchema(dict): pass

# --- Pattern Matching Engine Components (Simplified Examples) ---
# In a real system, this might be a more sophisticated library or service (e.g., Drools, custom stream processor)

def check_transaction_velocity(customer_id: str, transaction_time: datetime, historical_tx_times: list[datetime]) -> dict:
    """Checks if current transaction exceeds velocity limits for the customer."""
    recent_tx_in_hour = [
        t for t in historical_tx_times
        if transaction_time - timedelta(hours=1) < t <= transaction_time
    ]
    if len(recent_tx_in_hour) >= config.MAX_TRANSACTIONS_PER_HOUR:
        return {"flag": "HIGH_HOURLY_VELOCITY", "count": len(recent_tx_in_hour), "limit": config.MAX_TRANSACTIONS_PER_HOUR}

    # Check for high frequency (multiple transactions too close together)
    if len(historical_tx_times) > 0:
        last_tx_time = max(historical_tx_times) # Assuming sorted or find most recent relevant one
        if (transaction_time - last_tx_time).total_seconds() < config.HIGH_FREQUENCY_THRESHOLD_SECONDS:
             return {"flag": "HIGH_FREQUENCY_TRANSACTION", "time_diff_seconds": (transaction_time - last_tx_time).total_seconds(), "threshold": config.HIGH_FREQUENCY_THRESHOLD_SECONDS}
    return {"flag": None}


def check_amount_anomaly(customer_id: str, transaction_amount: float, historical_tx_amounts: list[float]) -> dict:
    """Checks if transaction amount is unusually high for the customer."""
    if not historical_tx_amounts:
        return {"flag": "NO_HISTORY_FOR_AMOUNT_CHECK"} # Cannot determine anomaly without history

    # Example: Using 95th percentile (requires more data or pre-calculated percentiles)
    # For simplicity, let's use max amount + percentage increase for mock
    max_historical_amount = max(historical_tx_amounts) if historical_tx_amounts else 0

    if max_historical_amount > 0 and transaction_amount > (max_historical_amount * (1 + config.MAX_TRANSACTION_AMOUNT_PERCENTILE_INCREASE / 100)):
        return {"flag": "AMOUNT_SIGNIFICANTLY_HIGHER_THAN_USUAL", "current_amount": transaction_amount, "max_historical": max_historical_amount}
    return {"flag": None}

def check_new_device_anomaly(customer_id: str, device_id: str, transaction_amount: float, known_customer_devices: list[str]) -> dict:
    """Checks for anomalies related to new or unrecognized devices."""
    if device_id not in known_customer_devices:
        if transaction_amount > config.NEW_DEVICE_TRANSACTION_LIMIT:
            return {"flag": "LARGE_TRANSACTION_FROM_NEW_DEVICE", "device_id": device_id, "amount": transaction_amount, "limit": config.NEW_DEVICE_TRANSACTION_LIMIT}
        return {"flag": "TRANSACTION_FROM_NEW_DEVICE", "device_id": device_id} # Informational flag
    return {"flag": None}

# --- ML Anomaly Detection Tool (Calls our internal AI service) ---
def get_ml_fraud_prediction(transaction_data: dict) -> dict:
    """
    Calls the internal AI/ML model for fraud prediction.
    Input:
        transaction_data: A dictionary containing all features required by the model.
                          This should align with `TransactionFraudCheckRequest` schema of the AI service.
    Output:
        Dictionary with prediction (e.g., fraud score, is_fraud_suspected) or error.
    """
    # Ensure transaction_data has a 'transaction_id' for the request schema,
    # and other features are nested under a 'features' key if that's what the AI service expects.
    # Example: payload = TransactionFraudCheckRequestSchema(transaction_id=transaction_data['id'], features=transaction_data)

    payload = {
        "transaction_id": transaction_data.get("transaction_id", "UNKNOWN_TX_ID"),
        "features": transaction_data # Pass all data as features for the AI service
    }

    try:
        # response = requests.post(config.FRAUD_DETECTION_MODEL_API_URL, json=payload)
        # response.raise_for_status()
        # return response.json() # Should match TransactionFraudCheckResponse from ai_automation_layer

        print(f"Mock ML Fraud Prediction: Analyzing transaction {payload['transaction_id']}")
        # Simulate ML model response
        mock_score = random.uniform(0.01, 0.99)
        is_suspected = mock_score > config.ML_FRAUD_SCORE_THRESHOLD_HIGH

        return {
            "transaction_id": payload['transaction_id'],
            "is_fraud_suspected": is_suspected,
            "fraud_score": mock_score,
            "reason": "ML model detected anomalous patterns." if is_suspected else "ML model indicates normal patterns.",
            "prediction_log_id": "mock_ml_pred_log_" + payload['transaction_id']
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"ML fraud prediction service request failed: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error during ML fraud prediction: {str(e)}"}

# --- Rules Engine Tool (Conceptual - could be more complex) ---
def evaluate_transaction_with_rules_engine(transaction_data: dict, ml_prediction_data: Optional[dict] = None) -> dict:
    """
    Evaluates transaction data against a set of predefined fraud rules.
    Can also incorporate ML prediction results as part of rule conditions.
    Input:
        transaction_data: Dictionary of current transaction details.
        ml_prediction_data: Optional output from `get_ml_fraud_prediction`.
    Output:
        Dictionary with triggered rules, overall risk assessment, and recommended action.
    """
    # This is a simplified rule evaluation. A real rules engine (Drools, custom) would be more robust.
    # Rules could be loaded from config.RULES_ENGINE_CONFIG_PATH

    print(f"Mock Rules Engine: Evaluating transaction {transaction_data.get('transaction_id')}")
    triggered_rules = []
    recommended_action = "ALLOW"
    final_risk_level = "LOW"

    # Example Rule 1: High ML score + large amount from new beneficiary
    if ml_prediction_data and ml_prediction_data.get("fraud_score", 0) > config.ML_FRAUD_SCORE_THRESHOLD_MEDIUM:
        if transaction_data.get("amount", 0) > 100000 and transaction_data.get("is_new_beneficiary") is True:
            triggered_rules.append("HIGH_ML_SCORE_LARGE_NEW_BENEFICIARY")
            recommended_action = "REQUIRE_STEP_UP_AUTH" # Or "FLAG_FOR_REVIEW"
            final_risk_level = "MEDIUM"

    # Example Rule 2: Transaction from blacklisted IP
    # if tools.is_ip_blacklisted(transaction_data.get("ip_address")):
    #    triggered_rules.append("TRANSACTION_FROM_BLACKLISTED_IP")
    #    recommended_action = "BLOCK"
    #    final_risk_level = "CRITICAL"
    if transaction_data.get("ip_address") == "1.2.3.4": # Mock blacklisted IP
        triggered_rules.append("TRANSACTION_FROM_BLACKLISTED_IP_MOCK")
        recommended_action = "BLOCK"
        final_risk_level = "CRITICAL"

    # Example Rule 3: Velocity check (using the pattern matching tool conceptually)
    # velocity_check = check_transaction_velocity(...) -> this would need historical data access
    # if velocity_check.get("flag") == "HIGH_HOURLY_VELOCITY":
    #    triggered_rules.append("HIGH_HOURLY_VELOCITY_RULE")
    #    if final_risk_level != "CRITICAL": recommended_action = "FLAG_FOR_REVIEW"; final_risk_level = "MEDIUM"

    # Combine with ML score if action still ALLOW and ML score is high
    if recommended_action == "ALLOW" and ml_prediction_data and ml_prediction_data.get("is_fraud_suspected") is True:
        triggered_rules.append("ML_MODEL_FLAGGED_FRAUD_NO_SPECIFIC_RULE_HIT")
        recommended_action = "FLAG_FOR_REVIEW"
        final_risk_level = "HIGH" if ml_prediction_data.get("fraud_score",0) > config.ML_FRAUD_SCORE_THRESHOLD_HIGH else "MEDIUM"

    return {
        "triggered_rules": triggered_rules,
        "recommended_action": recommended_action, # ALLOW, BLOCK, REQUIRE_STEP_UP_AUTH, FLAG_FOR_REVIEW
        "final_risk_level": final_risk_level # LOW, MEDIUM, HIGH, CRITICAL
    }

# --- Action Tools (Holding/Blocking Transactions, Notifying Agents) ---
def hold_transaction(transaction_id: str, reason: str) -> dict:
    """Calls an API to place a temporary hold on a transaction."""
    url = config.TRANSACTION_HOLD_API_URL.format(transaction_id=transaction_id)
    payload = {"reason": reason, "hold_duration_minutes": 60} # Example duration
    try:
        # response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return {"status": "success", "message": f"Transaction {transaction_id} placed on hold."}
        print(f"Mock API Call: POST {url} with payload {payload}")
        return {"status": "success", "message": f"Transaction {transaction_id} placed on hold (mock)."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to hold transaction {transaction_id}: {str(e)}"}

def block_transaction(transaction_id: str, reason: str) -> dict:
    """Calls an API to permanently block a transaction."""
    url = config.TRANSACTION_BLOCK_API_URL.format(transaction_id=transaction_id)
    payload = {"reason": reason}
    try:
        # response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return {"status": "success", "message": f"Transaction {transaction_id} blocked."}
        print(f"Mock API Call: POST {url} with payload {payload}")
        return {"status": "success", "message": f"Transaction {transaction_id} blocked (mock)."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to block transaction {transaction_id}: {str(e)}"}

def notify_compliance_agent(alert_details: dict) -> dict:
    """Sends a notification (e.g., email, SMS, Slack) to a human compliance/fraud agent."""
    # payload = {
    #     "recipient": config.COMPLIANCE_AGENT_EMAIL_GROUP, # Or specific agent ID
    #     "subject": f"Fraud Alert: Transaction {alert_details.get('transaction_id', 'N/A')}",
    #     "body": f"Potential fraud detected. Details: \n{json.dumps(alert_details, indent=2)} \nPlease investigate.",
    #     "channel": "EMAIL" # Or "SMS", "SLACK" etc.
    # }
    try:
        # response = requests.post(config.NOTIFICATION_SERVICE_API_URL, json=payload)
        # response.raise_for_status()
        # return {"status": "success", "message": "Compliance agent notified."}
        print(f"Mock Notification: Alerting compliance about: {alert_details.get('transaction_id', 'N/A')}")
        return {"status": "success", "message": "Compliance agent notified (mock)."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to notify compliance agent: {str(e)}"}


if __name__ == '__main__':
    print("--- Testing Fraud Detection Agent Tools ---")

    mock_tx_id = "TXN789012"
    mock_tx_data_normal = {
        "transaction_id": mock_tx_id,
        "amount": 5000.00,
        "currency": "NGN",
        "type": "NIP_TRANSFER",
        "channel": "MOBILE_APP",
        "beneficiary_account": "0987654321",
        "beneficiary_bank_code": "058",
        "is_new_beneficiary": False,
        "customer_id": "CUST101",
        "device_id": "DEV001",
        "ip_address": "192.168.1.10",
        # ... other relevant features for the ML model and rules
    }
    mock_tx_data_suspicious = {
        "transaction_id": "TXN_SUSP_001",
        "amount": 750000.00,
        "currency": "NGN",
        "type": "NIP_TRANSFER",
        "channel": "WEB_NEW_DEVICE",
        "beneficiary_account": "1122334455",
        "beneficiary_bank_code": "044",
        "is_new_beneficiary": True,
        "customer_id": "CUST102",
        "device_id": "DEV_UNKNOWN_XYZ", # New device
        "ip_address": "1.2.3.4", # Mock blacklisted IP
    }

    # 1. Test ML Fraud Prediction
    print("\n1. ML Fraud Prediction (Normal Tx):")
    ml_pred_normal = get_ml_fraud_prediction(mock_tx_data_normal)
    print(ml_pred_normal)

    print("\n2. ML Fraud Prediction (Suspicious Tx):")
    ml_pred_suspicious = get_ml_fraud_prediction(mock_tx_data_suspicious)
    print(ml_pred_suspicious)

    # 3. Test Rules Engine
    print("\n3. Rules Engine Evaluation (Normal Tx, Normal ML):")
    rules_eval_normal = evaluate_transaction_with_rules_engine(mock_tx_data_normal, ml_pred_normal)
    print(rules_eval_normal)

    print("\n4. Rules Engine Evaluation (Suspicious Tx, Suspicious ML):")
    rules_eval_suspicious = evaluate_transaction_with_rules_engine(mock_tx_data_suspicious, ml_pred_suspicious)
    print(rules_eval_suspicious)

    # 5. Test Action Tools based on suspicious evaluation
    if rules_eval_suspicious.get("recommended_action") == "BLOCK":
        print(f"\n5a. Blocking transaction {mock_tx_data_suspicious['transaction_id']}:")
        block_result = block_transaction(mock_tx_data_suspicious['transaction_id'], f"Blocked by rules: {rules_eval_suspicious['triggered_rules']}")
        print(block_result)
    elif rules_eval_suspicious.get("recommended_action") == "FLAG_FOR_REVIEW":
        print(f"\n5b. Holding transaction {mock_tx_data_suspicious['transaction_id']} and Notifying Compliance:")
        hold_result = hold_transaction(mock_tx_data_suspicious['transaction_id'], f"Flagged by rules: {rules_eval_suspicious['triggered_rules']}")
        print(hold_result)
        if hold_result.get("status") == "success":
            notify_result = notify_compliance_agent({
                "transaction_id": mock_tx_data_suspicious['transaction_id'],
                "reason": f"Flagged by rules: {rules_eval_suspicious['triggered_rules']}",
                "ml_score": ml_pred_suspicious.get("fraud_score"),
                "risk_level": rules_eval_suspicious.get("final_risk_level")
            })
            print(notify_result)

    # Test Pattern Matching (conceptual, needs historical data)
    print("\n6. Pattern Matching (Velocity - mock, needs history):")
    # These require historical_tx_times, historical_tx_amounts, known_customer_devices to be passed
    # For standalone test, we can mock these:
    now = datetime.utcnow()
    mock_history_times = [now - timedelta(minutes=i*5) for i in range(1,5)] # 4 txns in last 20 mins
    velocity_res = check_transaction_velocity("CUST101", now, mock_history_times)
    print(f"Velocity Check: {velocity_res}")

    mock_history_amounts = [1000.0, 2500.0, 500.0, 10000.0]
    amount_anomaly_res = check_amount_anomaly("CUST101", 200000.00, mock_history_amounts) # High amount
    print(f"Amount Anomaly Check (High): {amount_anomaly_res}")
    amount_anomaly_res_norm = check_amount_anomaly("CUST101", 3000.00, mock_history_amounts) # Normal amount
    print(f"Amount Anomaly Check (Normal): {amount_anomaly_res_norm}")

    mock_known_devices = ["DEV001", "DEV002"]
    new_device_res = check_new_device_anomaly("CUST101", "DEV_NEW_ABC", 60000.00, mock_known_devices) # Large tx from new device
    print(f"New Device Check (Large Tx): {new_device_res}")
    new_device_res_small = check_new_device_anomaly("CUST101", "DEV_NEW_XYZ", 10000.00, mock_known_devices) # Small tx from new device
    print(f"New Device Check (Small Tx): {new_device_res_small}")
    known_device_res = check_new_device_anomaly("CUST101", "DEV001", 20000.00, mock_known_devices) # Tx from known device
    print(f"New Device Check (Known Device): {known_device_res}")
