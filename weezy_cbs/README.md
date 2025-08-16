# Weezy Core Banking System (CBS)

## Overview

Weezy CBS is a modern, modular Core Banking System designed to provide comprehensive banking functionalities tailored for diverse financial institutions, with a particular focus on the Nigerian market context. It leverages a Python-based stack with FastAPI for robust and scalable API development.

The system is architected into distinct modules, each responsible for a specific domain of banking operations, allowing for clarity, maintainability, and independent development where feasible.

## Core Modules

The Weezy CBS is composed of the following 16 core modules:

1.  **Customer & Identity Management (`customer_identity_management`)**: Handles customer onboarding (retail & SME), KYC/AML compliance (CBN guidelines), BVN/NIN integration, Customer 360° profiles, and multi-tiered accounts.
2.  **Accounts & Ledger Management (`accounts_ledger_management`)**: Manages various account types (Savings, Current, Fixed Deposit, Domiciliary), multi-currency support, double-entry ledger system, real-time balances, interest accrual, and dormant account handling.
3.  **Loan Management Module (`loan_management_module`)**: Covers loan origination, credit risk scoring (conceptual), guarantor/collateral handling, repayment scheduling, credit bureau integration (conceptual), and CBN CRMS reporting aspects.
4.  **Transaction Management (`transaction_management`)**: Manages internal and interbank transfers (NIP, RTGS, USSD concepts), bulk payments, standing orders, and transaction dispute handling.
5.  **Cards & Wallets Management (`cards_wallets_management`)**: Deals with virtual/physical cards (Verve, Mastercard, Visa concepts), ATM/POS integration (conceptual), wallet accounts, card issuance, PIN management, and cardless withdrawals.
6.  **Payments Integration Layer (`payments_integration_layer`)**: Focuses on integrating with payment gateways (NIBSS, Paystack, Flutterwave concepts), bill payment aggregators, and other payment channels like QR codes.
7.  **Deposit & Collection Module (`deposit_collection_module`)**: Handles cash/cheque deposits, agent banking operations (SANEF concept), and specialized collection services.
8.  **Compliance & Regulatory Reporting (`compliance_regulatory_reporting`)**: Manages AML/CFT monitoring, CTR/STR generation, and preparing data for regulatory bodies like CBN, NDIC, NFIU.
9.  **Treasury & Liquidity Management (`treasury_liquidity_management`)**: Tracks bank cash positions, FX management, treasury bill investments, interbank lending/borrowing, and CBN settlement reconciliation.
10. **Fees, Charges & Commission Engine (`fees_charges_commission_engine`)**: Provides a flexible engine for defining and applying various fees, charges (including VAT, Stamp Duty), commissions, and waivers.
11. **Core Infrastructure & Configuration Engine (`core_infrastructure_config_engine`)**: Manages foundational elements like branch/agent setup, staff user management (RBAC with roles/permissions), a generic product configuration engine, system-wide audit logging, and system settings.
12. **Digital Channels Modules (`digital_channels_modules`)**: Provides backend services for various customer-facing channels like Internet Banking, Mobile Banking, USSD, and Chatbots, including digital user profile management, session handling, and notifications.
13. **CRM & Customer Support (`crm_customer_support`)**: Manages customer relationships, support ticketing system, customer notes, marketing campaign management (conceptual), and FAQs.
14. **Reports & Analytics (`reports_analytics`)**: Enables definition, scheduling, and generation of various reports (operational, management, regulatory). Includes management of dashboard layouts.
15. **Third-Party & Fintech Integration (`third_party_fintech_integration`)**: Manages configurations and logs for integrations with external non-payment services like credit bureaus, identity verification services (NIMC concept), etc. Includes webhook handling.
16. **AI & Automation Layer (`ai_automation_layer`)**: Houses AI-driven capabilities, including metadata management for AI models, task logging, agent configurations (conceptual), and automated rule definitions. Provides conceptual services for credit scoring, fraud detection, etc.

## Technology Stack

*   **Backend Framework**: FastAPI
*   **Programming Language**: Python 3.9+
*   **Database**: PostgreSQL (implied by `psycopg2-binary` and schema features like JSONB)
*   **ORM**: SQLAlchemy
*   **Data Validation**: Pydantic
*   **Authentication**: JWT (using `python-jose`) with Passlib for password hashing
*   **Asynchronous HTTP Client**: HTTPX (for potential service-to-service calls)

## Setup Instructions (Conceptual)

1.  **Clone the Repository**:
    ```bash
    git clone <repository-url>
    cd weezy-cbs-project # Or your project's root directory
    ```

2.  **Create and Activate Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    Navigate to the `weezy_cbs` directory (or ensure `requirements.txt` is at the level you run pip from).
    ```bash
    pip install -r requirements.txt
    ```
    (Note: The `requirements.txt` is located inside the `weezy_cbs` package directory in this setup). If running from project root: `pip install -r weezy_cbs/requirements.txt`

4.  **Configure Database**:
    *   Ensure you have a PostgreSQL server running.
    *   Create a database (e.g., `weezy_cbs_db`).
    *   Set the `DATABASE_URL` environment variable:
        ```bash
        export DATABASE_URL="postgresql://youruser:yourpassword@yourhost:yourport/weezy_cbs_db"
        ```
        (Replace with your actual connection string).

5.  **Create Database Tables**:
    The system uses SQLAlchemy to define models. To create all tables:
    Navigate to the parent directory of `weezy_cbs` (if `weezy_cbs` is in your PYTHONPATH).
    ```bash
    python -m weezy_cbs.database
    ```
    This executes the `create_all_tables()` function in `weezy_cbs/database.py`.
    Alternatively, if running from the project root where `weezy_cbs` is a subdirectory:
    ```bash
    python weezy_cbs/database.py
    ```

6.  **Run the Application**:
    Navigate to the parent directory of `weezy_cbs`.
    ```bash
    uvicorn weezy_cbs.main:app --reload
    ```
    The application will typically be available at `http://127.0.0.1:8000`.

## API Documentation

FastAPI provides automatic interactive API documentation:

*   **Swagger UI**: `http://127.0.0.1:8000/docs`
*   **ReDoc**: `http://127.0.0.1:8000/redoc`

These interfaces allow you to explore and test all the API endpoints.

## Directory Structure

The project is primarily contained within the `weezy_cbs` package:

```
weezy_cbs/
├── __init__.py
├── main.py                     # Main FastAPI application
├── database.py                 # SQLAlchemy setup, Base, session management
├── requirements.txt            # Python dependencies
├── AGENTS.md                   # Instructions for AI development agents (this file)
├── customer_identity_management/ # Module 1
│   ├── __init__.py
│   ├── api.py
│   ├── models.py
│   ├── schemas.py
│   └── services.py
├── accounts_ledger_management/   # Module 2
│   └── ...
├── ...                         # Other 14 modules
└── agents/                     # Directory for AI Agent specific code/configs (if any beyond the AI module)
    ├── __init__.py
    └── customer_onboarding_agent/
        └── ...
```

Each module directory typically contains:
*   `api.py`: FastAPI routers and endpoints.
*   `models.py`: SQLAlchemy database models.
*   `schemas.py`: Pydantic data validation schemas.
*   `services.py`: Business logic and service layer functions.

This modular structure promotes separation of concerns and scalability.
