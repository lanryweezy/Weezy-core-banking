from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import engine, Base, get_db, create_all_tables # Import your DB setup

# Import API routers from various modules
from weezy_cbs.customer_identity_management import api as cim_api
from weezy_cbs.accounts_ledger_management import api as alm_api
from weezy_cbs.loan_management_module import api as loan_api
from weezy_cbs.transaction_management import api as txn_api
from weezy_cbs.cards_wallets_management import api as card_api
from weezy_cbs.payments_integration_layer import api as pay_integ_api
from weezy_cbs.deposit_collection_module import api as dep_coll_api
from weezy_cbs.compliance_regulatory_reporting import api as comp_rep_api
from weezy_cbs.treasury_liquidity_management import api as treasury_api
from weezy_cbs.fees_charges_commission_engine import api as fee_api
from weezy_cbs.core_infrastructure_config_engine import api as core_infra_api
from weezy_cbs.digital_channels_modules import api as digital_chan_api
from weezy_cbs.crm_customer_support import api as crm_api
from weezy_cbs.reports_analytics import api as report_api
from weezy_cbs.third_party_fintech_integration import api as third_party_api
from weezy_cbs.ai_automation_layer import api as ai_api

# Create all database tables if they don't exist
# In a production setup, you'd likely use Alembic for migrations.
# This is suitable for initial development.
# Base.metadata.create_all(bind=engine)
# It's better to call create_all_tables() from database.py as it imports all models.
# To run this manually: `python -m weezy_cbs.database` (if database.py has `if __name__ == "__main__": create_all_tables()`)
# Or, add a startup event.

app = FastAPI(
    title="Weezy Core Banking System (CBS)",
    description="API for the Weezy CBS, providing comprehensive banking functionalities.",
    version="0.1.0",
)

@app.on_event("startup")
async def startup_event():
    # This is a good place to run create_all_tables() if you want it on app start for dev
    # However, for production, Alembic is preferred.
    # For now, we can comment it out and assume tables are created manually via script.
    # print("Creating database tables on startup...")
    # create_all_tables() # This function needs to be defined in database.py and ensure all models are imported there
    # print("Database tables checked/created.")
    pass

# Include routers from each module
# The prefix here defines the base path for all routes in that router.
app.include_router(cim_api.router, prefix="/api/v1", tags=["Customer Identity"])
app.include_router(alm_api.router, prefix="/api/v1", tags=["Accounts & Ledger"])
app.include_router(loan_api.router, prefix="/api/v1", tags=["Loans"])
app.include_router(txn_api.router, prefix="/api/v1", tags=["Transactions"])
app.include_router(card_api.router, prefix="/api/v1", tags=["Cards & Wallets"])
app.include_router(pay_integ_api.router, prefix="/api/v1", tags=["Payments Integration"])
app.include_router(dep_coll_api.router, prefix="/api/v1", tags=["Deposits & Collections"])
app.include_router(comp_rep_api.router, prefix="/api/v1", tags=["Compliance & Reporting"])
app.include_router(treasury_api.router, prefix="/api/v1", tags=["Treasury & Liquidity"])
app.include_router(fee_api.router, prefix="/api/v1", tags=["Fees & Charges"])
app.include_router(core_infra_api.router, prefix="/api/v1", tags=["Core Infrastructure & Config"])
app.include_router(digital_chan_api.router, prefix="/api/v1", tags=["Digital Channels"])
app.include_router(crm_api.router, prefix="/api/v1", tags=["CRM & Customer Support"])
app.include_router(report_api.router, prefix="/api/v1", tags=["Reports & Analytics"])
app.include_router(third_party_api.router, prefix="/api/v1", tags=["Third-Party Integrations"])
app.include_router(ai_api.router, prefix="/api/v1", tags=["AI & Automation"])


@app.get("/health", tags=["System"])
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint. Verifies API is running and can connect to the database.
    """
    try:
        # Try a simple query to check DB connection
        db.execute(text("SELECT 1")).fetchone()
        db_status = "connected"
    except Exception as e:
        # print(f"Database connection error: {e}") # Log this
        db_status = "disconnected"
        # Optionally, raise HTTPException if DB connection is critical for health
        # raise HTTPException(status_code=503, detail=f"Database connection error: {e}")

    return {"status": "ok", "database": db_status, "timestamp": datetime.utcnow().isoformat()}

# To run this application (after installing dependencies):
# uvicorn weezy_cbs.main:app --reload
#
# And to create database tables (if not using Alembic and not running in startup event):
# Ensure your PostgreSQL server is running and the database 'weezy_cbs_db' is created.
# Then run: python -m weezy_cbs.database
# (This assumes your project root is the parent of 'weezy_cbs' directory and it's in PYTHONPATH)
# Or, from within the 'weezy_cbs' directory's parent: python weezy_cbs/database.py

# Import 'text' from sqlalchemy for the health check query
from sqlalchemy import text
from datetime import datetime # For timestamp in health check
