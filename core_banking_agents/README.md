# Core Banking AI Agents Project

This project aims to develop a suite of AI agents for a modern, AI-native core banking system tailored for the Nigerian market. These agents are designed to handle various banking operations, leveraging LLM orchestration frameworks like CrewAI, LangGraph, or AutoGen.

## Project Structure

The project is organized into several key directories:

-   `agents/`: Contains the specific logic for each AI agent. Each agent has its own subdirectory with modules for:
    -   `main.py`: FastAPI application for the agent.
    -   `agent.py`: Core agent logic (e.g., using CrewAI).
    -   `tools.py`: Tools the agent can use.
    -   `memory.py`: Agent's memory management.
    -   `schemas.py`: Pydantic schemas for data validation.
    -   `config.py`: Agent-specific configurations.
-   `core/`: Shared core functionalities:
    -   `database.py`: Database setup (e.g., SQLAlchemy).
    -   `redis_client.py`: Centralized Redis client.
    -   `qdrant_client.py`: Centralized Qdrant client for vector DB.
    -   `utils.py`: Common utility functions.
    -   `config.py`: Core project settings.
-   `tests/`: Unit and integration tests.
-   `docs/`: Project documentation.
-   `scripts/`: Helper scripts for development, deployment, etc. (Future addition)

## Implemented Agents (Placeholders)

1.  **Customer Onboarding Agent**: Manages KYC, verification, and account creation.
2.  **Teller Agent**: Handles deposits, withdrawals, transfers, and balance checks.
3.  **Credit Analyst Agent**: Assesses loan applications.
4.  **Fraud Detection Agent**: Monitors real-time transactions for suspicious activity.
5.  **Compliance Agent**: Enforces AML/KYC rules and regulatory monitoring.
6.  **Customer Support Agent**: Resolves complaints and queries.
7.  **Back Office Reconciliation Agent**: Matches internal ledger with external logs.
8.  **Finance Insights Agent**: Provides financial analytics and forecasts.

## Technology Stack (Planned)

-   Python 3.9+
-   FastAPI: For creating API endpoints for agents.
-   LangChain / CrewAI / AutoGen: For LLM orchestration and agent logic.
-   SQLAlchemy: For relational database interactions.
-   Redis: For caching, session management, and agent memory.
-   Qdrant: For vector database capabilities (AI memory, semantic search).
-   Pandas: For data manipulation, especially in reconciliation and insights.
-   Matplotlib/Seaborn (or other viz libraries): For generating charts.
-   Prophet/ARIMA (or other time-series libraries): For forecasting.
-   Docker & Docker Compose: For containerization and local environment setup.

## Setup and Installation

(To be detailed later)

```bash
# Example setup steps
# python -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt
#
# # To run a specific agent's FastAPI app (example)
# # uvicorn core_banking_agents.agents.customer_onboarding_agent.main:app --reload --port 8001
```

## Running Tests

(To be detailed later)

```bash
# pytest
```

## AGENTS.md

Please refer to the `AGENTS.md` file in the root directory for general instructions and conventions for AI development within this project. Agent-specific `AGENTS.md` files may exist within their respective directories.

---

*This README is a placeholder and will be updated as the project progresses.*
