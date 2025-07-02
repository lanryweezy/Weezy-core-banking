# Weezy Core Banking System (CBS)

Weezy CBS is a modern, modular core banking software designed to provide comprehensive banking functionalities. This project aims to build a robust and scalable system leveraging Python and FastAPI for its backend infrastructure.

## Project Overview

This system is composed of several distinct modules, each responsible for a specific domain of banking operations. Additionally, it incorporates an AI Automation Layer with intelligent agents to enhance various processes.

### Core Banking System Modules:

1.  **Customer & Identity Management**: Handles customer onboarding, KYC/AML, BVN/NIN integration, and customer profiles.
2.  **Accounts & Ledger Management**: Manages savings, current, fixed deposit accounts, multi-currency support, and the double-entry ledger.
3.  **Loan Management Module**: Covers loan origination, credit scoring, collateral, repayments, and regulatory reporting for loans.
4.  **Transaction Management**: Processes internal and interbank transfers (NIP, RTGS, USSD), bulk payments, and standing orders.
5.  **Cards & Wallets Management**: Manages virtual/physical cards, ATM/POS integration, and e-wallets.
6.  **Payments Integration Layer**: Integrates with NIBSS, payment gateways (Paystack, Flutterwave), and bill payment aggregators.
7.  **Deposit & Collection Module**: Handles cash/cheque deposits, agent banking, and collections for third parties.
8.  **Compliance & Regulatory Reporting**: Manages AML/CFT monitoring, CTR/STR, and reporting to CBN, NDIC, NFIU.
9.  **Treasury & Liquidity Management**: Tracks bank's cash position, FX management, and interbank lending.
10. **Fees, Charges & Commission Engine**: Configures and applies various bank fees, charges, VAT, and stamp duties.
11. **Core Infrastructure & Config Engine**: Manages branches, agents, user roles (RBAC), product configuration, audit trails, and API management.
12. **Digital Channels Modules**: Container for Internet Banking, Mobile Banking, USSD, Agent Dashboard, and Chatbot interfaces.
13. **CRM & Customer Support**: Includes ticketing, complaint resolution, customer notes, and campaign management.
14. **Reports & Analytics**: Provides operational, management, and regulatory reports, plus data analytics capabilities.
15. **Third-Party & Fintech Integration**: Manages integrations with credit bureaus, NIMC, external loan originators, and BaaS partners.
16. **AI & Automation Layer**: Houses AI models and services for credit scoring, fraud detection, LLM task automation, etc.

### AI Agent Templates:

The system design includes several AI agents to automate and assist in various banking tasks:
*   Customer Onboarding Agent
*   Teller Agent
*   Credit Analyst Agent
*   Fraud Detection Agent
*   Compliance Agent
*   Customer Support Agent
*   Back Office Reconciliation Agent
*   Finance Insights Agent

These agents are intended to be built using frameworks like CrewAI, LangGraph, or AutoGen and will interact with the core CBS modules via their APIs.

## Technology Stack (Initial)

*   **Backend Framework**: FastAPI
*   **Database**: PostgreSQL (configurable via `DATABASE_URL` environment variable)
*   **ORM**: SQLAlchemy
*   **Data Validation**: Pydantic
*   **HTTP Client**: Requests
*   **Data Handling**: Pandas (for reconciliation, analytics)
*   **AI/ML**: (To be determined - placeholder for scikit-learn, TensorFlow/PyTorch, LLM SDKs)
*   **Language**: Python 3.9+

## Setup and Running

1.  **Prerequisites**:
    *   Python 3.9 or higher
    *   PostgreSQL server running
    *   Create a PostgreSQL database (e.g., `weezy_cbs_db`) and user.

2.  **Environment Variables**:
    Set the `DATABASE_URL` environment variable:
    ```bash
    export DATABASE_URL="postgresql://user:password@localhost:5432/weezy_cbs_db"
    ```
    (Replace `user`, `password`, `localhost`, `5432`, and `weezy_cbs_db` with your actual PostgreSQL connection details).
    You can also use a `.env` file with `python-dotenv` (add it to `requirements.txt` if used).

3.  **Installation**:
    ```bash
    # Create and activate a virtual environment (recommended)
    python -m venv venv
    source venv/bin/activate # On Windows: venv\Scripts\activate

    # Install dependencies
    pip install -r requirements.txt
    ```

4.  **Database Setup**:
    To create all necessary database tables (if they don't exist):
    Ensure your project root is in the `PYTHONPATH` or run from the project root's parent directory.
    ```bash
    python -m weezy_cbs.database
    ```
    Or, from the project root directory:
    ```bash
    python weezy_cbs/database.py
    ```
    *Note: For production environments, use a migration tool like Alembic instead of `create_all_tables()` directly.*

5.  **Running the Application**:
    ```bash
    uvicorn weezy_cbs.main:app --reload
    ```
    The API will typically be available at `http://127.0.0.1:8000`.
    Interactive API documentation (Swagger UI) will be at `http://127.0.0.1:8000/docs`.
    Alternative API documentation (ReDoc) will be at `http://127.0.0.1:8000/redoc`.

## Project Structure

The project is organized into modules, with each core CBS function and AI agent type having its own directory under `weezy_cbs/`.

*   `weezy_cbs/<module_name>/`: Contains specific logic for each CBS module.
    *   `api.py`: FastAPI routers and API endpoint definitions.
    *   `models.py`: SQLAlchemy database models.
    *   `schemas.py`: Pydantic schemas for data validation and serialization.
    *   `services.py`: Business logic and service layer functions.
*   `weezy_cbs/agents/<agent_name>/`: Contains logic for each AI agent.
    *   `agent.py`: Core agent workflow and logic.
    *   `tools.py`: Tools and functions used by the agent.
    *   `config.py`: Agent-specific configurations.
*   `weezy_cbs/database.py`: SQLAlchemy setup, database engine, and session management.
*   `weezy_cbs/main.py`: FastAPI application entry point, includes all module routers.
*   `weezy_cbs/requirements.txt`: Project dependencies.
*   `weezy_cbs/AGENTS.md`: Specific instructions for AI development agents working on this codebase.

## Further Development

*   Implement detailed business logic within each module's `services.py`.
*   Develop comprehensive unit and integration tests.
*   Set up database migrations using Alembic.
*   Implement robust authentication and authorization for API endpoints.
*   Develop the AI agent logic and integrate with LLM orchestration frameworks.
*   Build out the actual connections and data mapping for third-party integrations.
*   Refine data models and schemas based on detailed requirements.

## Contributing

(Details on contributing to be added later)
```
