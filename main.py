from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import uvicorn

from app import models as db_models # Renamed to avoid conflict
from app.db import engine, get_db, create_tables
from app.models import user as user_model # For Pydantic models later
from app.models import account as account_model
from app.models import transaction as transaction_model

# Create database tables if they don't exist
# In a production app, you'd use Alembic migrations.
# This is for easier initial setup.
db_models.Base.metadata.create_all(bind=engine) # Use the Base from app.models.base via app.models

app = FastAPI(
    title="Core Banking API",
    description="API for managing core banking operations, with AI and automation features.",
    version="0.1.0"
)

# --- Pydantic Schemas (Data Transfer Objects) ---
# We will define these in separate files (e.g., app/schemas.py) as we build out CRUD endpoints.
# For now, this is a placeholder.

# --- API Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Core Banking API"}

# Placeholder for health check
@app.get("/health")
async def health_check():
    # Add database connectivity check if needed
    return {"status": "ok"}

# Example: Create a User (very basic, without proper error handling or password hashing yet)
# We will move this to a dedicated router file later (e.g., app/api/v1/users.py)

# --- Routers ---
# We will add routers for each resource (users, accounts, etc.) later.
from app.api.v1 import api_v1_router
app.include_router(api_v1_router, prefix="/api/v1")
# app.include_router(users_router.router, prefix="/api/v1/users", tags=["users"]) # Covered by api_v1_router
# app.include_router(accounts_router.router, prefix="/api/v1/accounts", tags=["accounts"])


if __name__ == "__main__":
    print("Starting Uvicorn server...")
    # Note: For development, it's common to run uvicorn from the command line:
    # uvicorn main:app --reload
    # However, this allows running python main.py directly.
    uvicorn.run(app, host="0.0.0.0", port=8000)
