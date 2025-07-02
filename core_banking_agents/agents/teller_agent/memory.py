# Memory management for Teller Agent
# This could store frequent beneficiaries or past transaction summaries for quick reference.

# import redis
# import json

# redis_client = redis.Redis(host='localhost', port=6379, db=1) # Using a different DB for Teller Agent

# FREQUENT_BENEFICIARIES_KEY_PREFIX = "teller_agent:beneficiaries:"
# PAST_TRANSACTIONS_KEY_PREFIX = "teller_agent:transactions:"

def add_frequent_beneficiary(customer_id: str, beneficiary_account: str, beneficiary_name: str):
    """Adds a beneficiary to the customer's list of frequent beneficiaries."""
    key = f"{FREQUENT_BENEFICIARIES_KEY_PREFIX}{customer_id}"
    beneficiary_data = {"account": beneficiary_account, "name": beneficiary_name}
    # In a real scenario, you'd probably store a list and avoid duplicates
    # For simplicity, let's assume one main beneficiary or a simple overwrite for this mock.
    # redis_client.lpush(key, json.dumps(beneficiary_data)) # To store a list
    # redis_client.sadd(key, json.dumps(beneficiary_data)) # To store a set of unique beneficiaries
    print(f"Memory: Adding frequent beneficiary {beneficiary_account} for customer {customer_id}")
    pass

def get_frequent_beneficiaries(customer_id: str) -> list:
    """Retrieves frequent beneficiaries for a customer."""
    key = f"{FREQUENT_BENEFICIARIES_KEY_PREFIX}{customer_id}"
    # beneficiaries_json = redis_client.lrange(key, 0, -1) # Example for list
    # return [json.loads(b) for b in beneficiaries_json]
    print(f"Memory: Retrieving frequent beneficiaries for customer {customer_id}")
    return [{"account": "0987654321", "name": "Jane Doe"}] # Mock data

def log_transaction_summary(customer_id: str, transaction_summary: dict):
    """Logs a summary of a transaction for quick recall."""
    key = f"{PAST_TRANSACTIONS_KEY_PREFIX}{customer_id}"
    # redis_client.lpush(key, json.dumps(transaction_summary))
    # redis_client.ltrim(key, 0, 9) # Keep only the last 10 transactions
    print(f"Memory: Logging transaction summary for customer {customer_id}: {transaction_summary}")
    pass

def get_past_transactions(customer_id: str, limit: int = 5) -> list:
    """Retrieves a list of past transaction summaries."""
    key = f"{PAST_TRANSACTIONS_KEY_PREFIX}{customer_id}"
    # transactions_json = redis_client.lrange(key, 0, limit - 1)
    # return [json.loads(t) for t in transactions_json]
    print(f"Memory: Retrieving past transactions for customer {customer_id}")
    return [ # Mock data
        {"type": "transfer", "amount": 5000, "to": "0987654321", "date": "2023-10-26"},
        {"type": "deposit", "amount": 20000, "date": "2023-10-25"}
    ]

print("Teller Agent memory management placeholder.")
