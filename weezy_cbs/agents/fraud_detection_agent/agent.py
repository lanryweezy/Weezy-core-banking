# Agent for Real-time Transaction Fraud Detection
import json # For pretty printing dicts if needed
from . import tools
from . import config

class FraudDetectionAgent:
    def __init__(self, agent_id="fraud_detection_agent_001", memory_storage=None):
        self.agent_id = agent_id
        self.role = "Monitors real-time transactions for suspicious activity."
        # Memory: Stores user behavior patterns (e.g. avg tx amount, common locations/devices, typical tx times),
        # short-term transaction history for velocity checks, references to blacklists/whitelists.
        # Example: self.memory = {
        #    "customer_CUST101": {
        #        "behavior_profile": {"avg_tx_amount": 5000, "common_devices": ["DEV001"], ...},
        #        "recent_tx_timestamps": [datetime_objs...],
        #        "recent_tx_amounts": [float_values...],
        #    },
        #    "global_blacklists": {"ips": ["1.2.3.4"], "accounts": ["000BADACC0"]}
        # }
        self.memory = memory_storage if memory_storage is not None else {}
        self._load_initial_memory() # Load blacklists or pre-computed profiles if any

    def _load_initial_memory(self):
        # Placeholder: In a real system, load from DB or config files
        # self.memory["global_blacklists"] = {
        #     "ips": tools.get_blacklisted_ips(), # Assuming tool to fetch this
        #     "accounts": tools.get_blacklisted_accounts()
        # }
        # self.memory["global_whitelists"] = { ... }
        pass

    def _get_customer_memory(self, customer_id: str) -> dict:
        if customer_id not in self.memory:
            self.memory[customer_id] = {
                "behavior_profile": self._fetch_customer_behavior_profile(customer_id), # Load on demand
                "recent_tx_timestamps": [],
                "recent_tx_amounts": [],
                "known_devices": [] # Could be preloaded or learned
            }
        return self.memory[customer_id]

    def _update_customer_memory(self, customer_id: str, transaction_data: dict):
        cust_mem = self._get_customer_memory(customer_id)

        # Update recent transactions (keep a sliding window, e.g., last 20-50)
        cust_mem["recent_tx_timestamps"].append(datetime.fromisoformat(transaction_data.get("transaction_timestamp"))) # Assuming ISO format string
        cust_mem["recent_tx_timestamps"] = sorted(cust_mem["recent_tx_timestamps"])[-50:] # Keep last 50, sorted

        cust_mem["recent_tx_amounts"].append(transaction_data.get("amount"))
        cust_mem["recent_tx_amounts"] = cust_mem["recent_tx_amounts"][-50:]

        if transaction_data.get("device_id") and transaction_data.get("device_id") not in cust_mem["known_devices"]:
            # Simple learning: add if seen a few times or if transaction was low risk
            # For now, just add it if agent decides to allow the transaction later.
            # This part needs more sophisticated logic for device profiling.
            pass

        # Potentially re-calculate parts of behavior_profile periodically or after significant events.

    def _fetch_customer_behavior_profile(self, customer_id: str) -> dict:
        # Placeholder: Fetch pre-computed profile from a data store or calculate based on historical transactions.
        # This would involve querying transaction history, customer data, etc.
        # For example:
        # historical_transactions = tools.get_transaction_history(customer_id, lookback_days=180)
        # profile = {"avg_tx_amount": ..., "common_beneficiaries": [...], ...}
        print(f"Mock Fetch Behavior Profile for {customer_id}")
        return { # Mock profile
            "avg_tx_amount": random.uniform(1000, 20000),
            "common_devices": [f"DEV{customer_id[-3:]}01", f"DEV{customer_id[-3:]}02"],
            "typical_tx_hours": [i for i in range(8, 20)], # 8 AM to 8 PM
            "historical_max_amount": random.uniform(50000, 200000),
            "historical_tx_count_last_30d": random.randint(5, 50)
        }


    def process_transaction_for_fraud(self, transaction_data: dict) -> dict:
        """
        Main workflow to analyze a single transaction for fraud.
        Input:
            transaction_data: Dictionary with comprehensive details of the transaction.
                              e.g., {
                                  "transaction_id": "TXN123", "customer_id": "CUST101",
                                  "amount": 5000.00, "currency": "NGN", "type": "NIP",
                                  "channel": "MOBILE_APP", "beneficiary_account": "098...",
                                  "beneficiary_bank_code": "058", "is_new_beneficiary": False,
                                  "device_id": "DEVXYZ123", "ip_address": "102.89.2.1",
                                  "transaction_timestamp": "2023-10-28T10:30:00Z", ...
                              }
        Output:
            Dictionary with overall assessment and recommended action.
            e.g., {"transaction_id": "TXN123", "assessment": "HIGH_RISK", "action": "BLOCK", "reason": "High ML score and new device."}
        """
        tx_id = transaction_data.get("transaction_id")
        customer_id = transaction_data.get("customer_id")

        if not tx_id or not customer_id:
            return {"transaction_id": tx_id, "assessment": "ERROR", "action": "FAIL_PROCESSING", "reason": "Missing transaction_id or customer_id."}

        cust_mem = self._get_customer_memory(customer_id)
        # For pattern matching, we need historical context from memory
        historical_tx_times = cust_mem["recent_tx_timestamps"]
        historical_tx_amounts = cust_mem["recent_tx_amounts"]
        known_devices = cust_mem.get("known_devices", []) # Use profile or learned list

        # --- Stage 1: Pattern Matching / Heuristics ---
        pattern_flags = []
        current_tx_time = datetime.fromisoformat(transaction_data.get("transaction_timestamp"))

        velocity_check = tools.check_transaction_velocity(customer_id, current_tx_time, historical_tx_times)
        if velocity_check.get("flag"): pattern_flags.append(velocity_check)

        amount_anomaly_check = tools.check_amount_anomaly(customer_id, transaction_data.get("amount"), historical_tx_amounts)
        if amount_anomaly_check.get("flag"): pattern_flags.append(amount_anomaly_check)

        device_anomaly_check = tools.check_new_device_anomaly(customer_id, transaction_data.get("device_id"), transaction_data.get("amount"), known_devices)
        if device_anomaly_check.get("flag"): pattern_flags.append(device_anomaly_check)

        # Add more pattern checks: IP reputation, unusual time, known blacklisted beneficiary, etc.
        # if transaction_data.get("beneficiary_account") in self.memory.get("global_blacklists",{}).get("accounts",[]):
        #    pattern_flags.append({"flag": "BENEFICIARY_BLACKLISTED"})

        # --- Stage 2: ML Model Prediction ---
        # Prepare features for ML model (might include raw tx_data + pattern_flags or derived features)
        ml_features = {**transaction_data, "pattern_flags_count": len(pattern_flags)} # Simplified feature prep
        ml_prediction_result = tools.get_ml_fraud_prediction(ml_features)

        # --- Stage 3: Rules Engine Evaluation (combines patterns, ML score, business rules) ---
        rules_engine_output = tools.evaluate_transaction_with_rules_engine(transaction_data, ml_prediction_result)

        # --- Stage 4: Decision & Action ---
        final_assessment = rules_engine_output.get("final_risk_level", "LOW") # LOW, MEDIUM, HIGH, CRITICAL
        recommended_action = rules_engine_output.get("recommended_action", "ALLOW") # ALLOW, BLOCK, HOLD, FLAG_FOR_REVIEW, REQUIRE_STEP_UP_AUTH
        triggered_rules_summary = ", ".join(rules_engine_output.get("triggered_rules", []))
        reason_for_action = f"Risk: {final_assessment}. Action: {recommended_action}. Triggered: {triggered_rules_summary or 'N/A'}. ML Score: {ml_prediction_result.get('fraud_score', 'N/A'):.2f}."

        action_result = None
        if recommended_action == "BLOCK":
            action_result = tools.block_transaction(tx_id, reason_for_action)
        elif recommended_action == "HOLD" or recommended_action == "FLAG_FOR_REVIEW":
            action_result = tools.hold_transaction(tx_id, reason_for_action)
            # Notify human compliance agent if HOLD or FLAG_FOR_REVIEW
            if action_result and action_result.get("status") == "success":
                tools.notify_compliance_agent({
                    "transaction_id": tx_id, "customer_id": customer_id,
                    "reason": reason_for_action, "details": transaction_data
                })
        elif recommended_action == "REQUIRE_STEP_UP_AUTH":
            # This would typically mean the transaction processing flow needs to prompt user for OTP, etc.
            # The agent itself might not directly handle OTP, but signals it's needed.
            action_result = {"status": "success", "message": "Step-up authentication required by fraud engine."}
            # No direct tool call here, this output informs the orchestrator.
        else: # ALLOW
            action_result = {"status": "success", "message": "Transaction allowed by fraud engine."}

        # --- Stage 5: Update Memory ---
        # Only add to history if transaction is not immediately blocked due to critical fraud.
        # Or, always add, but also update behavior profile based on confirmed fraud later.
        if recommended_action != "BLOCK": # Or based on specific risk levels
            self._update_customer_memory(customer_id, transaction_data)
            if transaction_data.get("device_id") and transaction_data.get("device_id") not in cust_mem["known_devices"]:
                 cust_mem["known_devices"].append(transaction_data.get("device_id")) # Simple learning for now

        return {
            "transaction_id": tx_id,
            "assessment": final_assessment,
            "action_taken_by_agent": recommended_action, # What the agent decided
            "action_execution_result": action_result, # Result of trying to execute the action
            "reason": reason_for_action,
            "ml_score": ml_prediction_result.get("fraud_score"),
            "pattern_flags": pattern_flags,
            "rules_triggered": rules_engine_output.get("triggered_rules")
        }

    def get_customer_fraud_profile_summary(self, customer_id: str) -> dict:
        """Retrieves a summary of the customer's fraud-related memory/profile."""
        if customer_id in self.memory:
            cust_mem = self.memory[customer_id]
            return {
                "customer_id": customer_id,
                "behavior_profile_summary": {
                    "avg_tx_amount": cust_mem.get("behavior_profile",{}).get("avg_tx_amount"),
                    "known_devices_count": len(cust_mem.get("known_devices",[]))
                },
                "recent_tx_count": len(cust_mem.get("recent_tx_timestamps",[]))
            }
        return {"status": "not_found", "message": "No fraud profile data found for this customer."}


# Example of how this agent might be used (e.g. by a stream processor or API endpoint)
if __name__ == "__main__":
    from datetime import datetime, timedelta # For _update_customer_memory timestamp

    fraud_agent = FraudDetectionAgent()

    # Simulate a stream of transactions
    transactions_to_process = [
        {
            "transaction_id": "TXN_NORM_001", "customer_id": "CUST101", "amount": 1500.00,
            "currency": "NGN", "type": "NIP", "channel": "MOBILE_APP",
            "beneficiary_account": "0123456789", "beneficiary_bank_code": "058", "is_new_beneficiary": False,
            "device_id": "DEV_CUST101_01", "ip_address": "192.168.1.10", "transaction_timestamp": datetime.utcnow().isoformat()
        },
        { # Slightly higher amount, still normal
            "transaction_id": "TXN_NORM_002", "customer_id": "CUST101", "amount": 25000.00,
            "currency": "NGN", "type": "NIP", "channel": "MOBILE_APP",
            "beneficiary_account": "0123456788", "beneficiary_bank_code": "033", "is_new_beneficiary": False,
            "device_id": "DEV_CUST101_01", "ip_address": "192.168.1.11", "transaction_timestamp": (datetime.utcnow() + timedelta(seconds=60)).isoformat()
        },
        { # Suspicious: High amount, new beneficiary, new device, potentially "blacklisted" IP
            "transaction_id": "TXN_SUSP_001", "customer_id": "CUST101", "amount": 850000.00,
            "currency": "NGN", "type": "NIP", "channel": "WEB",
            "beneficiary_account": "1010101010", "beneficiary_bank_code": "011", "is_new_beneficiary": True,
            "device_id": "DEV_UNKNOWN_BROWSER_XYZ", "ip_address": "1.2.3.4", "transaction_timestamp": (datetime.utcnow() + timedelta(seconds=120)).isoformat()
        }
    ]

    print("--- Processing Transactions for Fraud ---")
    for tx_data in transactions_to_process:
        print(f"\nProcessing Transaction: {tx_data['transaction_id']}")
        result = fraud_agent.process_transaction_for_fraud(tx_data)
        print(json.dumps(result, indent=2, default=str)) # Use default=str for datetime if any in result

    print("\n--- Customer CUST101 Fraud Profile Summary ---")
    print(json.dumps(fraud_agent.get_customer_fraud_profile_summary("CUST101"), indent=2, default=str))
