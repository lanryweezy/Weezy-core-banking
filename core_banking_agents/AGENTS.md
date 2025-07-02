# AGENTS.md - Instructions for AI Agents Working on This Project

This document provides general guidelines and conventions for AI agents (like you, Jules!) contributing to the `CoreBankingAIAgents` project. Agent-specific instructions may be found in `AGENTS.md` files within individual agent directories (e.g., `agents/customer_onboarding_agent/AGENTS.md`).

## 1. General Principles

*   **Modularity**: Each agent should be self-contained within its designated directory. Shared functionalities should reside in the `core/` directory.
*   **Clarity**: Code should be well-commented, especially the logic within agent workflows, tool definitions, and complex Pydantic schemas.
*   **Configuration over Code**: Where possible, use configuration files (e.g., `config.py` within each agent, `core/config.py` for shared settings) for parameters, API keys, and endpoints rather than hardcoding them. Load sensitive information from environment variables.
*   **Error Handling**: Implement robust error handling in tools and agent workflows. Provide informative error messages.
*   **Logging**: Use appropriate logging throughout the agent operations. (A centralized logging setup might be added to `core/` later). Standard Python `logging` module is preferred.

## 2. Python and FastAPI Conventions

*   Follow **PEP 8** for Python code style. Use a linter/formatter like Ruff or Black if possible.
*   Use **type hints** for all function signatures and variable declarations.
*   For FastAPI:
    *   Organize endpoints logically.
    *   Use Pydantic models defined in `schemas.py` for request and response validation.
    *   Utilize FastAPI's dependency injection system for shared resources like DB sessions or clients.

## 3. Agent Frameworks (CrewAI/LangChain)

*   **Agent Definitions (`agent.py`)**:
    *   Clearly define the `role`, `goal`, and `backstory` for each agent.
    *   List all `tools` the agent is permitted to use.
    *   Specify the LLM to be used. Consider performance and cost implications (e.g., `gpt-3.5-turbo` for simpler tasks, `gpt-4-turbo` or `gpt-4o` for complex reasoning).
*   **Tool Definitions (`tools.py`)**:
    *   Each tool should have a clear name and a detailed docstring explaining its purpose, inputs, and outputs. Use the `@tool` decorator if using LangChain/CrewAI tools.
    *   Tools should be focused and perform a single, well-defined task.
    *   External API calls within tools must handle potential errors (network issues, API errors) gracefully.
*   **Task Definitions (`agent.py`)**:
    *   Clearly describe the task, expected inputs, and the desired `expected_output` format (preferably JSON for structured data).
    *   Assign the task to the appropriate agent.
*   **Memory (`memory.py`)**:
    *   Implement agent-specific memory solutions here. This might involve:
        *   Short-term memory for conversation context (e.g., using Redis).
        *   Long-term memory for persistent knowledge (e.g., Qdrant for vector similarity search, SQL DB for structured data).
    *   Ensure memory access is efficient and secure.

## 4. API Design (FastAPI `main.py`)

*   Endpoints should be RESTful.
*   Use clear and consistent naming for paths and parameters.
*   Version your API if significant changes are expected (e.g., `/api/v1/...`). The current agent structure implies individual FastAPI apps, so versioning might be per-agent.

## 5. Configuration (`config.py`)

*   Use a class-based approach for settings (e.g., `class Settings:`).
*   Load values from environment variables using `os.getenv()`, providing sensible defaults.
*   Agent-specific configurations go into the agent's `config.py`.
*   Shared configurations (DB URLs, common API keys, Redis/Qdrant host/port) go into `core/config.py`. Agents can import `core_settings` from `core.config`.

## 6. Database (`core/database.py`)

*   If using SQLAlchemy, define models clearly, potentially in a `models.py` file per agent or a central `core/models.py` if schemas are shared. (This project currently has schemas in `schemas.py` per agent, which are Pydantic models for API validation, not necessarily DB models).
*   Database interactions should be handled through repository patterns or service layers if complexity grows.

## 7. Vector Database (`core/qdrant_client.py`)

*   When using Qdrant for AI memory or semantic search:
    *   Define collection names clearly, perhaps in `core/config.py` or agent-specific configs.
    *   Ensure appropriate vector sizes and distance metrics are used for collections.
    *   Handle embedding generation consistently (e.g., using a specific OpenAI model or a sentence transformer).

## 8. Testing

*   Write unit tests for tools, agent logic, and utility functions.
*   Write integration tests for FastAPI endpoints.
*   (Placeholder: Testing infrastructure to be further defined).

## 9. Security

*   **API Keys & Secrets**: Never hardcode API keys or sensitive credentials. Load them from environment variables (managed via `.env` locally or secrets management in production).
*   **Input Validation**: Use Pydantic schemas rigorously for all API inputs.
*   **Output Sanitization**: Be cautious when returning data, especially if it incorporates external content. (Placeholder: To be detailed further).
*   **Authentication/Authorization**: (Placeholder: Mechanisms for securing agent APIs to be defined. Could involve API keys, OAuth2, etc.).

## 10. Nigerian Market Specifics

*   When implementing features related to KYC, BVN/NIN, payment systems (NIP, USSD), or regulatory reporting (CBN, NDIC, NFIU), ensure that the logic and data models align with Nigerian regulations and standards.
*   Currency should be handled appropriately, with "NGN" as a common default. VAT and Stamp Duty calculations should be accurate if implemented.

## Workflow for Making Changes

1.  **Understand the Task**: Clarify requirements.
2.  **Plan**: Use the `set_plan` tool to outline your steps.
3.  **Implement**:
    *   Create or modify files.
    *   Add comments and docstrings.
    *   Update `requirements.txt` if new dependencies are added.
4.  **Test (Simulated)**: Mentally review your changes. If a testing framework were active, you'd run tests.
5.  **Review `AGENTS.md`**: Ensure your changes comply with these guidelines.
6.  **Submit**: Use `submit` with a clear commit message.

By following these guidelines, you will help maintain a clean, robust, and scalable codebase. If any instruction is unclear or conflicts with the user's request, please ask for clarification.
