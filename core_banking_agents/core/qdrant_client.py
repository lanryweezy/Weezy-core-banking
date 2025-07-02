# Centralized Qdrant client setup (for vector database interactions)

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse # For specific error handling
from typing import Optional, Dict, Any
import logging

# Import core_settings to get Qdrant configuration
from .config import core_settings

logger = logging.getLogger(__name__)

class QdrantDBClient:
    _client: Optional[QdrantClient] = None
    _client_config: Dict[str, Any] = {} # Stores the config used to initialize the client

    @classmethod
    def get_client(cls) -> Optional[QdrantClient]:
        """
        Retrieves a Qdrant client instance.
        The client is initialized once and cached.
        Configuration is sourced from core_settings.
        """
        if cls._client:
            # Optionally, add a ping or health check if Qdrant client supports it easily,
            # or if connections are found to be stale often. For now, assume cached client is good.
            # logger.debug("Returning cached Qdrant client.")
            return cls._client

        # --- Configuration from core_settings ---
        qdrant_url = getattr(core_settings, "QDRANT_URL", None)
        qdrant_api_key = getattr(core_settings, "QDRANT_API_KEY", None)
        qdrant_host = getattr(core_settings, "QDRANT_HOST", "localhost")
        qdrant_port = getattr(core_settings, "QDRANT_PORT", 6333) # gRPC port
        # qdrant_grpc_port = getattr(core_settings, "QDRANT_GRPC_PORT", 6333) # if REST port is different
        # qdrant_prefer_grpc = getattr(core_settings, "QDRANT_PREFER_GRPC", True)

        client_args: Dict[str, Any] = {}

        if qdrant_url: # Typically for Qdrant Cloud or specific deployments
            client_args["url"] = qdrant_url
            if qdrant_api_key:
                client_args["api_key"] = qdrant_api_key
            logger.info(f"Initializing Qdrant client with URL: {qdrant_url}")
        else: # For local Docker or similar, using host and port
            client_args["host"] = qdrant_host
            client_args["port"] = qdrant_port # qdrant_grpc_port if using separate ports
            # client_args["prefer_grpc"] = qdrant_prefer_grpc
            logger.info(f"Initializing Qdrant client with Host: {qdrant_host}, Port: {qdrant_port}")

        cls._client_config = client_args # Store for re-initialization if needed

        try:
            cls._client = QdrantClient(**client_args)
            # Perform a simple operation to confirm connectivity, e.g., list collections
            cls._client.get_collections()
            logger.info(f"Qdrant client connected successfully to target defined by: {client_args}")
            return cls._client
        except UnexpectedResponse as e: # Handles HTTP errors from REST if not using gRPC primarily
             logger.error(f"Qdrant connection error (UnexpectedResponse): {e.status_code} - {e.content}. Config: {client_args}", exc_info=True)
        except Exception as e: # Catches other errors like connection refused for gRPC
            logger.error(f"Qdrant connection error: {e}. Config: {client_args}", exc_info=True)

        cls._client = None # Ensure client is None if connection failed
        return None

    @classmethod
    def ensure_collection(
        cls,
        collection_name: str,
        vector_size: Optional[int] = None,
        distance_metric: Optional[models.Distance] = None,
        recreate_if_config_mismatch: bool = False # Advanced: DANGEROUS, drops collection
    ) -> bool:
        """
        Ensures a collection exists in Qdrant with the specified configuration.
        Creates it if it doesn't exist.

        Args:
            collection_name (str): The name of the collection.
            vector_size (Optional[int]): The size of vectors to be stored.
                                         Defaults to core_settings.DEFAULT_EMBEDDING_SIZE.
            distance_metric (Optional[models.Distance]): The distance metric for vectors.
                                                       Defaults to models.Distance.COSINE.
            recreate_if_config_mismatch (bool): If True and collection exists but with different config,
                                                it will be deleted and recreated. USE WITH EXTREME CAUTION.

        Returns:
            bool: True if the collection exists or was created successfully, False otherwise.
        """
        client = cls.get_client()
        if not client:
            logger.error(f"Cannot ensure collection '{collection_name}': Qdrant client not available.")
            return False

        effective_vector_size = vector_size if vector_size is not None else getattr(core_settings, "DEFAULT_EMBEDDING_SIZE", 768) # Default to a common size
        effective_distance_metric = distance_metric if distance_metric is not None else models.Distance.COSINE

        try:
            collection_exists = False
            try:
                collection_info = client.get_collection(collection_name=collection_name)
                logger.info(f"Qdrant collection '{collection_name}' already exists.")
                collection_exists = True

                # Check if existing config matches desired config
                current_config = collection_info.config.params
                if current_config.vectors_config: # Can be dict or VectorParams
                    if isinstance(current_config.vectors_config, dict): # Multiple named vectors
                        # This mock assumes a single default vector config for simplicity
                        # For named vectors, you'd need to specify which one to check or iterate
                        default_vector_config = current_config.vectors_config.get('') # Default unnamed vector
                        if default_vector_config:
                             actual_size = default_vector_config.size
                             actual_distance = default_vector_config.distance
                        else: # No default unnamed vector, complex scenario
                            logger.warning(f"Collection '{collection_name}' has named vectors. Config check skipped for this example.")
                            return True # Assume OK for now
                    else: # Single vector config (VectorParams)
                        actual_size = current_config.vectors_config.size
                        actual_distance = current_config.vectors_config.distance

                    config_matches = (actual_size == effective_vector_size and actual_distance == effective_distance_metric)

                    if not config_matches:
                        logger.warning(
                            f"Collection '{collection_name}' exists but with different configuration. "
                            f"Current: size={actual_size}, distance={actual_distance}. "
                            f"Desired: size={effective_vector_size}, distance={effective_distance_metric}."
                        )
                        if recreate_if_config_mismatch:
                            logger.warning(f"RECREATING collection '{collection_name}' due to config mismatch and recreate_if_config_mismatch=True. ALL DATA WILL BE LOST.")
                            client.delete_collection(collection_name=collection_name)
                            collection_exists = False # Force recreation
                        else:
                            logger.error("Config mismatch and recreate_if_config_mismatch is False. Collection not modified.")
                            return False # Indicate failure due to mismatch without recreation
                    else:
                        logger.info(f"Collection '{collection_name}' configuration matches desired settings.")


            except (UnexpectedResponse, ValueError) as e: # ValueError if collection does not exist (older client versions) or other client errors
                if isinstance(e, UnexpectedResponse) and e.status_code == 404:
                    logger.info(f"Qdrant collection '{collection_name}' does not exist. Will attempt to create.")
                    collection_exists = False
                elif "not found" in str(e).lower() or "Collection" in str(e) and "doesn't exist" in str(e): # For gRPC or other errors indicating not found
                    logger.info(f"Qdrant collection '{collection_name}' does not exist. Will attempt to create.")
                    collection_exists = False
                else: # Some other error during get_collection
                    raise e

            if not collection_exists:
                logger.info(f"Creating Qdrant collection: '{collection_name}' with vector size {effective_vector_size} and distance {effective_distance_metric}.")
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(size=effective_vector_size, distance=effective_distance_metric)
                )
                logger.info(f"Successfully created Qdrant collection: '{collection_name}'.")
            return True
        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection '{collection_name}': {e}", exc_info=True)
            return False

    @classmethod
    def close_client(cls):
        """Closes the Qdrant client connection if it's open."""
        if cls._client:
            try:
                cls._client.close()
                logger.info("Qdrant client closed.")
            except Exception as e:
                logger.error(f"Error closing Qdrant client: {e}")
            finally:
                cls._client = None

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print(f"--- Testing QdrantDBClient ---")
    print(f"Core settings: QDRANT_URL={getattr(core_settings, 'QDRANT_URL', 'N/A')}, QDRANT_HOST={getattr(core_settings, 'QDRANT_HOST', 'N/A')}")

    q_client = QdrantDBClient.get_client()

    if q_client:
        print("Successfully connected to Qdrant client.")

        test_collection_name = getattr(core_settings, "QDRANT_ONBOARDING_COLLECTION", "test_onboarding_collection_core")
        # Assume DEFAULT_EMBEDDING_SIZE is in core_settings, e.g., 1536 for OpenAI, or 768 for sentence-transformers
        test_vector_size = getattr(core_settings, "DEFAULT_EMBEDDING_SIZE", 384) # Smaller default for testing if not set

        print(f"\n1. Ensuring collection '{test_collection_name}' with vector size {test_vector_size}...")
        success_ensure = QdrantDBClient.ensure_collection(
            collection_name=test_collection_name,
            vector_size=test_vector_size,
            distance_metric=models.Distance.COSINE
        )
        if success_ensure:
            print(f"  Collection '{test_collection_name}' ensured successfully.")
            # You could add a point and retrieve it here as a further test.
            try:
                # Test adding a point
                q_client.upsert(
                    collection_name=test_collection_name,
                    points=[models.PointStruct(id=1, vector=[0.1] * test_vector_size, payload={"test": "data"})]
                )
                print(f"  Successfully upserted a test point to '{test_collection_name}'.")
                retrieved_points = q_client.get_points(collection_name=test_collection_name, ids=[1])
                print(f"  Retrieved test point: {retrieved_points}")
            except Exception as e:
                print(f"  Error during test upsert/get point: {e}")

        else:
            print(f"  Failed to ensure collection '{test_collection_name}'.")

        # Example of trying to ensure with different config (WITHOUT recreate)
        print(f"\n2. Ensuring collection '{test_collection_name}' again with different vector size (expect warning/failure if no recreate):")
        success_mismatch = QdrantDBClient.ensure_collection(
            collection_name=test_collection_name,
            vector_size=test_vector_size + 1, # Different size
            recreate_if_config_mismatch=False # Default, should fail or warn
        )
        if not success_mismatch:
             print(f"  Correctly handled config mismatch for '{test_collection_name}' without recreation.")
        else:
             print(f"  Unexpected: collection ensured despite config mismatch and no recreate flag, or it was recreated (check logs).")


        # Clean up by deleting the test collection (optional)
        # print(f"\n3. Deleting test collection '{test_collection_name}'...")
        # try:
        #    q_client.delete_collection(collection_name=test_collection_name)
        #    print(f"  Successfully deleted collection '{test_collection_name}'.")
        # except Exception as e:
        #    print(f"  Error deleting test collection '{test_collection_name}': {e}")

        QdrantDBClient.close_client()
    else:
        print("Failed to connect to Qdrant client. Check Qdrant server and core_settings configuration.")

    print("\n--- QdrantDBClient tests finished ---")
