from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# SQLALCHEMY_DATABASE_URL = "sqlite:///./weezy_cbs.db" # For SQLite
# For PostgreSQL, from environment variable or config:
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/weezy_cbs_db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
    # For SQLite, add: connect_args={"check_same_thread": False}
    # For production PostgreSQL, you might want to configure pool size, etc.
    # pool_size=10, max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables (call this from main.py or a migration script)
def create_all_tables():
    # Import all model modules here so Base knows about them
    # This is crucial. Base.metadata.create_all(engine) will only create tables
    # for models that have been imported and thus registered with Base.

    # Core CBS Modules
    from weezy_cbs.customer_identity_management import models as cust_models
    from weezy_cbs.accounts_ledger_management import models as acc_models
    from weezy_cbs.loan_management_module import models as loan_models
    from weezy_cbs.transaction_management import models as txn_models
    from weezy_cbs.cards_wallets_management import models as card_models
    from weezy_cbs.payments_integration_layer import models as pay_integ_models
    from weezy_cbs.deposit_collection_module import models as dep_coll_models
    from weezy_cbs.compliance_regulatory_reporting import models as comp_rep_models
    from weezy_cbs.treasury_liquidity_management import models as treasury_models
    from weezy_cbs.fees_charges_commission_engine import models as fee_models
    from weezy_cbs.core_infrastructure_config_engine import models as core_infra_models
    from weezy_cbs.digital_channels_modules import models as digital_chan_models
    from weezy_cbs.crm_customer_support import models as crm_models
    from weezy_cbs.reports_analytics import models as report_models
    from weezy_cbs.third_party_fintech_integration import models as third_party_models
    from weezy_cbs.ai_automation_layer import models as ai_models

    # Agents (if they have their own DB models, usually they don't directly)
    # from weezy_cbs.agents.customer_onboarding_agent import models as coa_models # Example if agent had models

    print("Creating all tables in the database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created (if they didn't exist).")

if __name__ == "__main__":
    # This allows running `python weezy_cbs/database.py` to create tables
    print("Running table creation script...")
    # You might want to add a confirmation step or command-line arg here
    # for safety in a real environment.
    # IMPORTANT: Ensure your database (e.g., 'weezy_cbs_db') exists before running this.
    # For PostgreSQL: createdb weezy_cbs_db
    create_all_tables()
