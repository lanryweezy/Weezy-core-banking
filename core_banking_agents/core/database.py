# Database setup (e.g., SQLAlchemy for PostgreSQL or other SQL DBs)
# This file configures the database engine, session management, and base for models.

from sqlalchemy import create_engine, event # Added event for listener example
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import logging

# Import core_settings to get database URL
from .config import core_settings

logger = logging.getLogger(__name__)
# Configure logger for this module if not configured globally
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


SQLALCHEMY_DATABASE_URL = core_settings.DATABASE_URL
# Example URLs:
# PostgreSQL: "postgresql://user:password@host:port/database"
# SQLite: "sqlite:///./core_bank_agents_data.db"

engine = None
SessionLocal = None

if SQLALCHEMY_DATABASE_URL is None:
    logger.critical("DATABASE_URL is not set in core_settings. Database functionality will be disabled.")
    # No engine or SessionLocal will be created. get_db will fail.
else:
    logger.info(f"Database URL configured: {SQLALCHEMY_DATABASE_URL[:SQLALCHEMY_DATABASE_URL.find('@') if '@' in SQLALCHEMY_DATABASE_URL else 30]}...") # Log safely

    engine_args = {}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        engine_args["connect_args"] = {"check_same_thread": False}
        # For SQLite, ensure foreign key constraints are enabled on connect if desired (good practice)
        # This requires a listener if "check_same_thread" is False, or can be done per session.
        # Simpler way for SQLite is often to ensure ORM handles relationships correctly.
        # @event.listens_for(engine, "connect")
        # def set_sqlite_pragma(dbapi_connection, connection_record):
        #     cursor = dbapi_connection.cursor()
        #     cursor.execute("PRAGMA foreign_keys=ON")
        #     cursor.close()
        logger.info("SQLite database configured with check_same_thread=False.")

    # Example for PostgreSQL pool settings (optional, from core_settings if defined):
    # elif SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
    #     engine_args["pool_size"] = getattr(core_settings, "DB_POOL_SIZE", 5)
    #     engine_args["max_overflow"] = getattr(core_settings, "DB_MAX_OVERFLOW", 10)
    #     logger.info(f"PostgreSQL configured with pool_size={engine_args['pool_size']}, max_overflow={engine_args['max_overflow']}")

    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_args)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("SQLAlchemy engine and SessionLocal created successfully.")
    except ImportError as e: # Driver missing
        logger.critical(f"Database driver error for {SQLALCHEMY_DATABASE_URL}: {e}. Ensure correct driver is installed (e.g., psycopg2-binary for PostgreSQL).", exc_info=True)
        engine = None # Ensure engine is None if creation failed
        SessionLocal = None
    except Exception as e: # Other SQLAlchemy engine creation errors
        logger.critical(f"Failed to create SQLAlchemy engine for {SQLALCHEMY_DATABASE_URL}: {e}", exc_info=True)
        engine = None
        SessionLocal = None


# Base class for declarative SQLAlchemy models
Base = declarative_base()


# --- Dependency for FastAPI ---
def get_db() -> Session:
    """
    FastAPI dependency to get a DB session.
    Ensures the database session is always closed after the request.
    """
    if not SessionLocal: # Check if SessionLocal was successfully created
        logger.error("SessionLocal is not initialized. Database connection might have failed.")
        raise RuntimeError("Database session factory not available. Check DB configuration and logs.")

    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e: # Catch SQLAlchemy specific errors during session use
        logger.error(f"Database operation failed during request: {e}", exc_info=True)
        db.rollback() # Rollback on error
        raise # Re-raise after rollback to let FastAPI handle it or for further upstack handling
    finally:
        db.close()

# --- Database Initialization ---
def init_db(attempt_create_all: bool = True):
    """
    Initializes the database. If attempt_create_all is True, it tries to create
    all tables defined by models that inherit from `Base`.
    This should be called cautiously, typically once at application startup (if desired and safe)
    or via a separate CLI command. For production, migrations (e.g., with Alembic) are preferred.
    """
    if not engine:
        logger.error("Database engine not initialized. Cannot proceed with init_db.")
        return False

    logger.info(f"Attempting to connect and initialize database schema at {str(engine.url)} (if attempt_create_all=True).")

    try:
        # Test connection
        with engine.connect() as connection:
            logger.info("Successfully connected to the database engine.")

        if attempt_create_all:
            logger.info("Importing models from core.models for table creation...")
            # Import all modules here that define models so that
            # they will be registered properly on the metadata. Otherwise
            # you will have to import them first before calling init_db().
            from . import models # This makes Base.metadata aware of models in core/models.py

            logger.info(f"Creating tables defined in Base.metadata (if they don't exist): {list(Base.metadata.tables.keys())}")
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables checked/created successfully.")
        else:
            logger.info("Skipping Base.metadata.create_all() as attempt_create_all is False.")
        return True

    except OperationalError as e: # Common for DB not found, access denied, etc.
        logger.error(f"Database operational error during init_db for {str(engine.url)}: {e}", exc_info=True)
        logger.error("Please ensure the database server is running, accessible, and the database itself exists if not using SQLite.")
    except SQLAlchemyError as e: # Other SQLAlchemy errors
        logger.error(f"A SQLAlchemy error occurred during init_db for {str(engine.url)}: {e}", exc_info=True)
    except Exception as e: # Catch-all for other unexpected errors
        logger.error(f"An unexpected error occurred during init_db for {str(engine.url)}: {e}", exc_info=True)

    return False


if __name__ == "__main__":
    # This block allows manual DB initialization for development/testing.
    # To run: python -m core_banking_agents.core.database

    print(f"--- Manual Database Initialization Script ---")
    print(f"Target Database URL from settings: {SQLALCHEMY_DATABASE_URL if SQLALCHEMY_DATABASE_URL else 'NOT SET'}")

    if not engine:
        print("SQLAlchemy engine is not initialized (likely due to missing URL or driver). Cannot proceed.")
        print("Please check your .env file or environment variables for DATABASE_URL.")
        print("If using PostgreSQL, ensure 'psycopg2-binary' is installed.")
        print("If using SQLite, this script will attempt to create the .db file in the current directory (or as specified in URL).")
        exit(1)

    print("\nThis script will attempt to connect to the database and create all tables")
    print("defined in `core_banking_agents.core.models.py` if they do not already exist.")
    print("For production environments, use a proper migration tool like Alembic.\n")

    user_confirm = input("Proceed with database initialization? (yes/no): ").strip().lower()

    if user_confirm == "yes":
        print("Initializing database...")
        success = init_db(attempt_create_all=True)
        if success:
            print("Database initialization process completed successfully.")
            # You could add a small test query here if desired, e.g., count tables
        else:
            print("Database initialization process FAILED. Check logs above for errors.")
    else:
        print("Database initialization cancelled by user.")

    print("\n--- End Manual Database Initialization Script ---")
