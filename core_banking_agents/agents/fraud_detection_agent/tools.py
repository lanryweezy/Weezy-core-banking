# Tools for Fraud Detection Agent

# from langchain.tools import tool
# import requests # For calling ML models or external services
# # import re # For regex-based pattern matching

# # This would likely be a more complex rules engine, possibly loaded from a DB or config file
# FRAUD_RULES_DATABASE = {
#     "high_value_threshold": 1000000, # NGN
#     "velocity_limit_per_hour": 5,
#     "suspicious_ip_list": ["1.2.3.4", "5.6.7.8"],
# }

# @tool("PatternMatchingTool")
# def pattern_matching_tool(transaction_data: dict) -> dict:
#     """
#     Checks transaction data against known fraud patterns (e.g., specific merchant codes, velocity checks, known bad IPs).
#     Input: Dictionary of transaction details.
#     Output: Dictionary with matched patterns and associated risk scores.
#     """
#     print(f"Pattern Matching Tool: Analyzing transaction {transaction_data.get('transaction_id')}")
#     alerts = []
#     if transaction_data.get("amount", 0) > FRAUD_RULES_DATABASE["high_value_threshold"]:
#         alerts.append({"pattern": "high_value_transaction", "details": f"Amount {transaction_data.get('amount')} exceeds threshold"})
#     if transaction_data.get("device_ip") in FRAUD_RULES_DATABASE["suspicious_ip_list"]:
#         alerts.append({"pattern": "suspicious_ip", "details": f"IP {transaction_data.get('device_ip')} is on watchlist"})
#     # Add more pattern checks here (e.g., regex on descriptions, velocity based on memory)
#     return {"matched_patterns": alerts, "risk_contribution": len(alerts) * 0.1}

# @tool("MLAnomalyDetectionTool")
# def ml_anomaly_detection_tool(transaction_features: dict) -> dict:
#     """
#     Scores a transaction using a Machine Learning anomaly detection model.
#     Input: Dictionary of features extracted from the transaction.
#     Output: Dictionary with anomaly score and model confidence.
#     """
#     print(f"ML Anomaly Detection Tool: Scoring transaction {transaction_features.get('transaction_id')}")
#     # Placeholder for actual ML model inference
#     # response = requests.post("ML_FRAUD_MODEL_ENDPOINT", json=transaction_features)
#     # return response.json()
#     # Mock response
#     anomaly_score = 0.0 # Default low score
#     if transaction_features.get("amount", 0) > 500000 and "Unknown" in transaction_features.get("location", ""):
#         anomaly_score = 0.75
#     elif transaction_features.get("amount", 0) > 2000000:
#         anomaly_score = 0.9

#     return {"anomaly_score": anomaly_score, "model_version": "v1.2", "confidence": 0.95 if anomaly_score > 0 else 0.5}

# @tool("RulesEngineTool")
# def rules_engine_tool(transaction_data: dict, pattern_results: dict, ml_results: dict) -> dict:
#     """
#     Combines inputs from pattern matching, ML models, and applies a final set of business rules
#     to determine if a transaction is fraudulent, suspicious, or clear.
#     Input: Transaction data, pattern matching results, ML model results.
#     Output: Final decision, overall fraud score, and reasons.
#     """
#     print(f"Rules Engine Tool: Evaluating transaction {transaction_data.get('transaction_id')}")
#     final_score = ml_results.get("anomaly_score", 0.0) + pattern_results.get("risk_contribution", 0.0)
#     is_fraudulent = False
#     status = "clear"
#     reasons = []

#     if final_score > 0.85:
#         is_fraudulent = True
#         status = "fraudulent"
#         reasons.append("High combined score from ML and patterns.")
#     elif final_score > 0.6:
#         status = "suspicious"
#         reasons.append("Moderate combined score, requires review.")

#     if pattern_results.get("matched_patterns"):
#         reasons.extend([p["details"] for p in pattern_results["matched_patterns"]])

#     # Example of a hard rule
#     if transaction_data.get("amount", 0) > 5000000 and transaction_data.get("device_ip") in FRAUD_RULES_DATABASE["suspicious_ip_list"]:
#         is_fraudulent = True
#         status = "fraudulent"
#         reasons.append("Very high value transaction from suspicious IP.")
#         final_score = 1.0 # Override score

#     return {
#         "transaction_id": transaction_data.get("transaction_id"),
#         "is_fraudulent": is_fraudulent,
#         "status": status, # clear, suspicious, fraudulent
#         "overall_fraud_score": min(final_score, 1.0), # Cap score at 1.0
#         "reasons": reasons
#     }

# @tool("AlertingTool")
# def alert_tool(transaction_id: str, severity: str, details: dict, recipient: str = "compliance_team@bank.com"):
#     """
#     Sends an alert if a transaction is flagged as suspicious or fraudulent.
#     Input: Transaction ID, severity ('high', 'medium', 'low'), details of the fraud, and recipient.
#     Output: Status of alert delivery.
#     """
#     subject = f"Fraud Alert ({severity}): Transaction {transaction_id}"
#     body = f"Potential fraudulent activity detected for transaction {transaction_id}.\nDetails: {details}"
#     print(f"Alerting Tool: Sending email to {recipient}\nSubject: {subject}\nBody: {body}")
#     # Placeholder for actual email/SMS/webhook call
#     return {"alert_sent": True, "recipient": recipient}


# List of tools for this agent
# tools = [pattern_matching_tool, ml_anomaly_detection_tool, rules_engine_tool, alert_tool]

print("Fraud Detection Agent tools placeholder.")
