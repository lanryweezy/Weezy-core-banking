# Database setup (e.g., SQLAlchemy for PostgreSQL or other SQL DBs)
# This file configures the database engine, session management, and base for models.

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session # Added Session for type hinting
import logging

# Import core_settings to get database URL
from .config import core_settings

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = core_settings.DATABASE_URL
# Example URLs:
# PostgreSQL: "postgresql://user:password@host:port/database"
# SQLite: "sqlite:///./core_bank_agents.db" (file will be created in the root of where app runs)

if SQLALCHEMY_DATABASE_URL is None:
    logger.error("DATABASE_URL is not set in core_settings. Please configure it.")
    # Fallback to a default SQLite DB for demonstration if not set, or raise an error
    SQLALCHEMY_DATABASE_URL = "sqlite:///./default_core_bank_agents.db"
    logger.warning(f"Using default SQLite DB: {SQLALCHEMY_DATABASE_URL}")


# Create SQLAlchemy engine
# For SQLite, connect_args={"check_same_thread": False} is needed.
# For PostgreSQL, these connect_args are not typically needed.
# Pool size and other parameters can be configured for production.
engine_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}
# Example for PostgreSQL pool settings (optional):
# elif SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
#     engine_args["pool_size"] = core_settings.DB_POOL_SIZE # Assuming these are in core_settings
#     engine_args["max_overflow"] = core_settings.DB_MAX_OVERFLOW

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_args)
except ImportError as e:
    logger.error(f"Database driver error: {e}. Ensure the correct database driver (e.g., psycopg2-binary for PostgreSQL, or sqlite3 is available).")
    # Depending on policy, could raise or exit. For now, will allow Base to be defined.
    engine = None


# SessionLocal will be used to create database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative SQLAlchemy models
Base = declarative_base()


# --- Dependency for FastAPI ---
def get_db() -> Session: # Changed yield type to Session for better type hinting
    """
    FastAPI dependency to get a DB session.
    Ensures the database session is always closed after the request.
    """
    if not engine:
        logger.error("Database engine not initialized. Cannot provide DB session.")
        raise RuntimeError("Database engine not initialized. Check DATABASE_URL and driver.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Database Initialization ---
def init_db():
    """
    Initializes the database by creating all tables defined by models
    that inherit from `Base`. This should be called cautiously, typically
    once at application startup or via a separate CLI command.
    For production, migrations (e.g., with Alembic) are preferred over create_all.
    """
    if not engine:
        logger.error("Database engine not initialized. Cannot create tables.")
        return

    try:
        logger.info(f"Initializing database at {SQLALCHEMY_DATABASE_URL}...")
        # Import all modules here that define models so that
        # they will be registered properly on the metadata. Otherwise
        # you will have to import them first before calling init_db().
        from . import models # This will make SQLAlchemy aware of models in models.py

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created (if they didn't exist).")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        # Depending on the application, you might want to raise this error.

if __name__ == "__main__":
    # This block allows manual DB initialization for development/testing.
    # Example: python -m core_banking_agents.core.database

    print(f"Attempting to initialize database using URL: {SQLALCHEMY_DATABASE_URL}")
    print("This will create tables defined in core/models.py if they don't exist.")

    # Test connection (optional, create_all will also test it)
    if engine:
        try:
            with engine.connect() as connection:
                print("Successfully connected to the database engine.")
        except Exception as e:
            print(f"Failed to connect to the database engine: {e}")
            exit(1) # Exit if connection fails before trying to init
    else:
        print("Database engine is not configured. Exiting.")
        exit(1)

    init_db()
    print("Database initialization process finished.")

    # Example: How to use get_db outside FastAPI (e.g., in a script)
    # print("\nExample of using get_db():")
    # db_session_generator = get_db()
    # try:
    #     db = next(db_session_generator)
    #     print("DB Session obtained.")
    #     # You can now use 'db' to interact with the database, e.g.:
    #     # from .models import OnboardingAttempt
    #     # first_attempt = db.query(OnboardingAttempt).first()
    #     # if first_attempt:
    #     #     print(f"First onboarding attempt from DB: {first_attempt.id} - {first_attempt.status}")
    #     # else:
    #     #     print("No onboarding attempts found in DB (table might be empty).")
    # finally:
    #     try: # Ensure the generator is exhausted to close the session
    #         next(db_session_generator)
    #     except StopIteration:
    #         pass # This is expected
    #     except Exception as e:
    #         print(f"Error closing session via generator: {e}")
    # print("DB Session closed.")
    print("\nCore database.py enhanced with SQLAlchemy setup, get_db, and init_db.")
