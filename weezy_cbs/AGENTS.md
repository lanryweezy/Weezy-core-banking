# Instructions for AI Development Agents working on Weezy CBS

Welcome, AI Agent! This document provides guidelines and conventions to follow while working on the Weezy Core Banking System codebase.

## 1. Primary Language & Framework

*   **Python**: All backend code, including core modules and AI agents, **must** be written in Python (version 3.9+).
*   **FastAPI**: The primary web framework for exposing APIs for the core CBS modules. Ensure all new API endpoints are integrated correctly within this framework.
*   **SQLAlchemy**: Used as the ORM for database interactions. Define models in `<module>/models.py`.
*   **Pydantic**: Used for data validation and serialization (API request/response schemas). Define schemas in `<module>/schemas.py`.

## 2. Code Structure and Modularity

*   The system is highly modular. Each core banking function (e.g., `customer_identity_management`, `accounts_ledger_management`) and each AI agent type (e.g., `customer_onboarding_agent`) has its own dedicated directory.
*   Within each module/agent directory, stick to the established file naming conventions:
    *   `api.py`: FastAPI routers and endpoint definitions.
    *   `models.py`: SQLAlchemy database models.
    *   `schemas.py`: Pydantic schemas.
    *   `services.py`: Business logic layer.
    *   `agent.py`: Main agent logic (for agent directories).
    *   `tools.py`: Tools used by an agent (for agent directories).
    *   `config.py`: Configuration specific to an agent or module (avoid hardcoding).
*   Ensure new functionalities are placed within the appropriate module. If unsure, ask for clarification.

## 3. Database Interactions

*   All database model definitions must inherit from `weezy_cbs.database.Base`.
*   Use SQLAlchemy sessions provided via FastAPI dependencies (`Depends(get_db)`) for database operations in API endpoints and services.
*   Avoid raw SQL queries where possible. Use the ORM's capabilities. If complex queries are necessary, consider views or stored procedures (though the latter is less common in this stack).
*   Database table creation is currently handled by `weezy_cbs.database.create_all_tables()`. For production, Alembic migrations will be used. Do not make schema changes that require manual DB intervention without discussing.

## 4. API Design

*   Follow RESTful principles for API design.
*   Use Pydantic schemas for request and response bodies to ensure clear contracts and automatic validation.
*   Ensure API endpoints are added to the relevant module's router in `api.py` and that the router is included in `weezy_cbs/main.py`.
*   Tag your API endpoints appropriately in `main.py` for clear documentation.

## 5. AI Agent Development

*   AI Agents are intended to be developed potentially using frameworks like CrewAI, LangGraph, or AutoGen. The initial structure provides `agent.py` for the core logic and `tools.py` for the capabilities the agent can use.
*   Agent tools should interact with the core CBS modules via their defined APIs or service layers (if direct Python calls are feasible and make sense for performance/complexity).
*   Agent-specific configurations should go into the agent's `config.py`.
*   Store agent memory/history as per the design (e.g., in-memory for short-lived agents, or using a persistent store like Redis or the database for longer-term memory). The initial agent structures have a `self.memory` dictionary placeholder.

## 6. Configuration Management

*   Do not hardcode sensitive information (API keys, database URLs, secret keys).
*   The primary database URL is managed via the `DATABASE_URL` environment variable (see `weezy_cbs/database.py`).
*   Agent/module-specific configurations are in their respective `config.py` files. The API key `dd8e9064465a8311.UF1vXkGPNWCb8jQ4NFybk0VxV7eXIIKLUEyhumSJISre` is provided for general use where an API key might be conceptualized or for mock external services. For actual third-party services, specific keys will be managed securely (likely through environment variables or a secrets manager in a real deployment).

## 7. Logging and Error Handling

*   Implement proper error handling in services and API endpoints. Raise appropriate HTTPExceptions in the API layer.
*   (Placeholder for more detailed logging strategy - for now, use `print()` for debug/mock outputs if necessary, but aim for structured logging in real implementations).

## 8. Testing

*   (Placeholder for testing strategy - aim to write unit tests for services and functional tests for API endpoints. Pytest is the preferred framework).

## 9. Code Style and Quality

*   Follow PEP 8 Python style guidelines.
*   Use type hints for function signatures and variables.
*   Keep functions and classes focused on a single responsibility.
*   Write clear and concise comments where necessary, especially for complex logic.

## 10. Task Completion

*   When a task involves code changes, ensure you have:
    1.  Implemented the required functionality.
    2.  Added or updated relevant Pydantic schemas and SQLAlchemy models if data structures changed.
    3.  Exposed new functionality via FastAPI endpoints if it's an API-accessible feature.
    4.  (Ideally) Added tests for your changes.
    5.  Updated any relevant documentation (e.g., README.md if a major change, or comments in code).
*   When submitting your work, provide a clear commit message summarizing the changes.

By adhering to these guidelines, we can maintain a clean, consistent, and scalable codebase. Thank you for your contribution!
