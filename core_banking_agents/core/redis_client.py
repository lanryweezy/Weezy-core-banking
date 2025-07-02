# Centralized Redis client setup

import redis
import logging
from typing import Optional, Dict

# Import core_settings to get Redis configuration
from .config import core_settings

logger = logging.getLogger(__name__)

class RedisClient:
    _clients: Dict[str, redis.Redis] = {} # Cache for client connections: client_name -> Redis instance

    @classmethod
    def get_client(cls, client_name: str = "default", db: Optional[int] = None) -> Optional[redis.Redis]:
        """
        Retrieves a Redis client instance.
        Connections are cached by client_name.

        Args:
            client_name (str): A name for this client connection (e.g., "default", "onboarding_cache", "session_store").
                               This name is used for caching the connection.
            db (Optional[int]): The Redis database number to connect to.
                                If None, it tries to derive from core_settings based on client_name
                                (e.g., REDIS_ONBOARDING_CACHE_DB), falling back to REDIS_DEFAULT_DB.

        Returns:
            Optional[redis.Redis]: A Redis client instance if connection is successful, else None.
        """

        # Determine the effective client key for caching (name + db if db is explicitly specified)
        # This allows for same name but different DBs to be cached separately if needed, though typically
        # client_name implies a specific DB via config.
        cache_key = f"{client_name}_{db}" if db is not None else client_name

        if cache_key in cls._clients:
            try:
                # Check if the cached client is still connected
                if cls._clients[cache_key].ping():
                    # logger.debug(f"Returning cached Redis client: {cache_key}")
                    return cls._clients[cache_key]
                else:
                    logger.warning(f"Cached Redis client {cache_key} failed ping. Attempting to reconnect.")
                    del cls._clients[cache_key] # Remove stale client
            except redis.exceptions.ConnectionError:
                logger.warning(f"Cached Redis client {cache_key} connection error. Attempting to reconnect.")
                del cls._clients[cache_key] # Remove stale client

        # --- Configuration from core_settings ---
        redis_host = getattr(core_settings, "REDIS_HOST", "localhost")
        redis_port = getattr(core_settings, "REDIS_PORT", 6379)

        if db is None: # If DB not explicitly passed, try to get it from config based on client_name
            # Convention: core_settings might have REDIS_<CLIENT_NAME>_DB
            # Example: if client_name is "onboarding_cache", look for core_settings.REDIS_ONBOARDING_CACHE_DB
            db_setting_name = f"REDIS_{client_name.upper()}_DB"
            redis_db_to_use = getattr(core_settings, db_setting_name, None)
            if redis_db_to_use is None: # Fallback to default DB if specific one not found
                redis_db_to_use = getattr(core_settings, "REDIS_DEFAULT_DB", 0)
            logger.debug(f"For client '{client_name}', using Redis DB: {redis_db_to_use} (derived from config or default).")
        else: # DB was explicitly passed as an argument
            redis_db_to_use = db
            logger.debug(f"For client '{client_name}', using explicitly passed Redis DB: {redis_db_to_use}.")

        try:
            logger.info(f"Attempting to connect Redis client '{cache_key}' to {redis_host}:{redis_port}, DB: {redis_db_to_use}")
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db_to_use,
                decode_responses=True, # Decode responses from bytes to strings automatically
                socket_connect_timeout=5, # Timeout for connection
                socket_timeout=5          # Timeout for operations
            )
            r.ping()  # Verify connection
            cls._clients[cache_key] = r
            logger.info(f"Redis client '{cache_key}' connected successfully.")
            return r
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error for client '{cache_key}' ({redis_host}:{redis_port}, DB: {redis_db_to_use}): {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred while connecting Redis client '{cache_key}': {e}", exc_info=True)

        return None

    @classmethod
    def close_all_clients(cls):
        """Closes all cached client connections."""
        logger.info("Closing all Redis client connections.")
        for client_name, client in cls._clients.items():
            try:
                client.close()
                logger.info(f"Closed Redis client: {client_name}")
            except Exception as e:
                logger.error(f"Error closing Redis client {client_name}: {e}")
        cls._clients.clear()


if __name__ == "__main__":
    # Configure logging for standalone script execution
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print(f"--- Testing RedisClient ---")
    print(f"Core settings: REDIS_HOST={getattr(core_settings, 'REDIS_HOST', 'N/A')}, REDIS_PORT={getattr(core_settings, 'REDIS_PORT', 'N/A')}")
    print(f"Core settings: REDIS_DEFAULT_DB={getattr(core_settings, 'REDIS_DEFAULT_DB', 'N/A')}")
    print(f"Core settings: REDIS_ONBOARDING_DB={getattr(core_settings, 'REDIS_ONBOARDING_DB', 'N/A')}") # Assumes this might be in config
    print(f"Core settings: REDIS_TELLER_DB={getattr(core_settings, 'REDIS_TELLER_DB', 'N/A')}")       # Assumes this might be in config

    # Test default client
    print("\n1. Testing default client (DB should be core_settings.REDIS_DEFAULT_DB or 0):")
    default_client = RedisClient.get_client()
    if default_client:
        print(f"  Default client obtained. Setting test key...")
        default_client.set("core_redis_test_default", "connected_default_db")
        val = default_client.get("core_redis_test_default")
        print(f"  Got value from default client: '{val}'")
        default_client.delete("core_redis_test_default")
    else:
        print("  Failed to get default Redis client.")

    # Test named client, inferring DB from core_settings convention
    # Assuming core_settings.REDIS_ONBOARDING_DB = 1 (or some other value)
    print("\n2. Testing named client 'onboarding' (DB should be core_settings.REDIS_ONBOARDING_DB):")
    # To make this test work, ensure core_settings.REDIS_ONBOARDING_DB is defined in your core/config.py
    # For example, add: REDIS_ONBOARDING_DB: int = int(os.getenv("REDIS_ONBOARDING_DB", "1"))
    onboarding_db_val = getattr(core_settings, "REDIS_ONBOARDING_DB", 1) # Default to 1 for testing if not in config

    # Simulate that core_settings has this attribute for the test to run meaningfully
    if not hasattr(core_settings, "REDIS_ONBOARDING_DB"):
         print(f"  Note: core_settings.REDIS_ONBOARDING_DB not explicitly defined. Test will use default {onboarding_db_val} for client 'onboarding'.")
         # setattr(core_settings, "REDIS_ONBOARDING_DB", onboarding_db_val) # Temporarily set for test run if needed

    onboarding_client = RedisClient.get_client(client_name="onboarding") # Relies on convention in get_client
    if onboarding_client:
        print(f"  Onboarding client obtained. Setting test key...")
        onboarding_client.set("core_redis_test_onboarding", "connected_onboarding_db")
        val = onboarding_client.get("core_redis_test_onboarding")
        print(f"  Got value from onboarding client: '{val}' (DB should be {onboarding_db_val})")
        onboarding_client.delete("core_redis_test_onboarding")
    else:
        print("  Failed to get onboarding Redis client.")

    # Test named client with explicit DB override
    print("\n3. Testing named client 'teller_explicit_db' with explicit DB 2:")
    teller_client_explicit = RedisClient.get_client(client_name="teller_explicit_db", db=2)
    if teller_client_explicit:
        print(f"  Teller (explicit DB) client obtained. Setting test key...")
        teller_client_explicit.set("core_redis_test_teller_db2", "connected_teller_db_explicit_2")
        val = teller_client_explicit.get("core_redis_test_teller_db2")
        print(f"  Got value from teller (explicit DB) client: '{val}' (DB should be 2)")
        teller_client_explicit.delete("core_redis_test_teller_db2")
    else:
        print("  Failed to get teller (explicit DB) Redis client.")

    # Test getting the same client again (should be cached)
    print("\n4. Testing cached client (default):")
    default_client_cached = RedisClient.get_client()
    if default_client_cached:
        print(f"  Default client (cached) obtained: {'Same object as first default' if default_client is default_client_cached else 'Different object'}")
    else:
        print("  Failed to get cached default client.")

    # Test connection error (e.g., if Redis server is down or wrong port)
    # print("\n5. Testing connection error (simulated by changing port temporarily in core_settings):")
    # original_port = getattr(core_settings, "REDIS_PORT", 6379)
    # setattr(core_settings, "REDIS_PORT", 9999) # Set to a wrong port
    # RedisClient._clients.clear() # Clear cache to force reconnect attempt
    # error_client = RedisClient.get_client("error_test")
    # if error_client:
    #     print("  Error client connected (unexpected).")
    # else:
    #     print("  Error client failed to connect (expected).")
    # setattr(core_settings, "REDIS_PORT", original_port) # Restore original port
    # RedisClient._clients.clear() # Clear cache again

    RedisClient.close_all_clients()
    print("\n--- RedisClient tests finished ---")
