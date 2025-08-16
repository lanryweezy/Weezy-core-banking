# Memory management for Customer Support Agent
# Stores conversation history, customer preferences, past issues, and sentiment.

# import redis
# import json
# from datetime import datetime, timedelta

# redis_client = redis.Redis(host='localhost', port=6379, db=5) # DB for Customer Support Agent

# CHAT_HISTORY_PREFIX = "support_agent:chat_history:"
# CUSTOMER_PREFERENCES_PREFIX = "support_agent:preferences:"
# PAST_ISSUES_PREFIX = "support_agent:past_issues:" # Could link to CRM ticket IDs
# CUSTOMER_SENTIMENT_PREFIX = "support_agent:sentiment:"

# CONVERSATION_TTL_SECONDS = 24 * 60 * 60 # 24 hours

def log_chat_message(customer_id: str, role: str, message: str, conversation_id: str = None):
    """Logs a message to the customer's chat history for the current conversation."""
    if not conversation_id:
        conversation_id = get_or_create_conversation_id(customer_id)

    key = f"{CHAT_HISTORY_PREFIX}{customer_id}:{conversation_id}"
    entry = {"role": role, "message": message, "timestamp": datetime.now().isoformat()}
    # redis_client.rpush(key, json.dumps(entry))
    # redis_client.expire(key, CONVERSATION_TTL_SECONDS) # Keep history for a limited time
    print(f"Memory: Logging chat message for customer {customer_id} (Conv ID: {conversation_id}): {role} - {message[:50]}...")
    pass

def get_chat_history(customer_id: str, conversation_id: str = None, limit: int = 20) -> list:
    """Retrieves the recent chat history for a customer's conversation."""
    if not conversation_id:
        # Try to get the active conversation ID, or default to a generic one for recent non-specific history
        conversation_id = redis_client.get(f"{CHAT_HISTORY_PREFIX}{customer_id}:active_conv_id")
        if conversation_id:
            conversation_id = conversation_id.decode()
        else: # Fallback or if no active_conv_id logic is implemented
            print(f"Memory: No active conversation ID for {customer_id}, fetching general history (mock).")
            return [{"role": "system", "message": "Previous conversation ended.", "timestamp": (datetime.now() - timedelta(hours=1)).isoformat()}]


    key = f"{CHAT_HISTORY_PREFIX}{customer_id}:{conversation_id}"
    # messages_json = redis_client.lrange(key, -limit, -1) # Get last 'limit' messages
    # history = [json.loads(msg) for msg in messages_json]
    print(f"Memory: Retrieving chat history for customer {customer_id} (Conv ID: {conversation_id}), limit {limit}.")
    # Mock history
    history = [
        {"role": "user", "message": "Hello, I have an issue.", "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat()},
        {"role": "agent", "message": "Hello! How can I help you today?", "timestamp": (datetime.now() - timedelta(minutes=4)).isoformat()}
    ]
    return history

def get_or_create_conversation_id(customer_id: str) -> str:
    """Gets the current active conversation ID or creates a new one."""
    active_conv_key = f"{CHAT_HISTORY_PREFIX}{customer_id}:active_conv_id"
    # conversation_id = redis_client.get(active_conv_key)
    # if conversation_id:
    #     # Check if the corresponding history key still exists (i.e., hasn't expired)
    #     if redis_client.exists(f"{CHAT_HISTORY_PREFIX}{customer_id}:{conversation_id.decode()}"):
    #         return conversation_id.decode()

    # # Create a new conversation ID
    new_conv_id = f"conv_{int(datetime.now().timestamp())}"
    # redis_client.set(active_conv_key, new_conv_id, ex=CONVERSATION_TTL_SECONDS)
    print(f"Memory: Created new conversation ID for customer {customer_id}: {new_conv_id}")
    return new_conv_id


def store_customer_preference(customer_id: str, preference_key: str, preference_value: Any):
    """Stores a customer preference."""
    # redis_client.hset(f"{CUSTOMER_PREFERENCES_PREFIX}{customer_id}", preference_key, json.dumps(preference_value))
    print(f"Memory: Storing preference for customer {customer_id}: {preference_key} = {preference_value}")
    pass

def get_customer_preference(customer_id: str, preference_key: str) -> Any:
    """Retrieves a customer preference."""
    # value_json = redis_client.hget(f"{CUSTOMER_PREFERENCES_PREFIX}{customer_id}", preference_key)
    # return json.loads(value_json) if value_json else None
    print(f"Memory: Retrieving preference for customer {customer_id}: {preference_key}")
    if preference_key == "communication_channel": return "email" # Mock
    return None

def update_customer_sentiment(customer_id: str, sentiment_score: float, conversation_id: str = None):
    """Updates the sentiment score for the customer, possibly tied to a conversation."""
    key = f"{CUSTOMER_SENTIMENT_PREFIX}{customer_id}"
    if conversation_id:
        key = f"{key}:{conversation_id}"
    # redis_client.set(key, sentiment_score, ex=CONVERSATION_TTL_SECONDS * 2) # Keep sentiment a bit longer
    print(f"Memory: Updating sentiment for customer {customer_id} (Conv ID: {conversation_id}) to {sentiment_score}")
    pass

def get_average_sentiment(customer_id: str) -> Optional[float]:
    """Retrieves an aggregated sentiment score for the customer."""
    # This would be more complex, e.g., averaging scores over time or from recent conversations.
    # For simplicity, let's assume one main score is stored.
    # score = redis_client.get(f"{CUSTOMER_SENTIMENT_PREFIX}{customer_id}")
    # return float(score) if score else None
    print(f"Memory: Retrieving average sentiment for customer {customer_id}")
    return 0.75 # Mock positive sentiment

print("Customer Support Agent memory management placeholder.")
