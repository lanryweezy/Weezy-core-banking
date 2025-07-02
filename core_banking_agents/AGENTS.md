# AGENTS.md - Instructions for AI Agents Working on This Project

This document provides general guidelines and conventions for AI agents (like you, Jules!) contributing to the `CoreBankingAIAgents` project. Agent-specific instructions may be found in `AGENTS.md` files within individual agent directories (e.g., `agents/customer_onboarding_agent/AGENTS.md`) if needed for highly specialized tasks.

## 1. General Principles

*   **Modularity**: Each AI agent's primary logic, tools, schemas, and API should be self-contained within its designated directory (e.g., `agents/customer_onboarding_agent/`). Shared, cross-cutting functionalities (like database connections, core utilities, shared Pydantic models if any) should reside in the `core/` directory.
*   **Clarity & Readability**: Code must be well-commented. Docstrings should clearly explain the purpose, arguments, and return values of functions, classes, tools, and Pydantic models. Agent roles, goals, and backstories should be descriptive.
*   **Configuration over Code**:
    *   Utilize a two-tier configuration system:
        *   `core/config.py` (for `core_settings`): Shared settings like database URLs, Redis/Qdrant connection details, default LLM parameters, global API keys.
        *   `<agent_folder>/config.py` (for agent-specific `settings`): Agent-specific parameters, model names, tool-specific API keys, or overrides for core settings.
    *   All sensitive information (API keys, passwords) and environment-specific settings (URLs, ports) **must** be loaded from environment variables (e.g., using `os.getenv()`) with sensible defaults for local development. A `.env` file (gitignored) can be used locally.
*   **Error Handling**: Implement robust error handling in tools, agent workflows, and API endpoints. Use FastAPI's `HTTPException` for API errors. Log errors comprehensively.
*   **Logging**: Employ consistent logging throughout agent operations. The standard Python `logging` module is preferred. Configure basic logging in each `main.py` or a shared utility.
*   **Idempotency**: Where applicable (e.g., some API POST/PUT operations, background tasks), design for idempotency if operations might be retried.

## 2. Python and FastAPI Conventions

*   Adhere to **PEP 8** for Python code style. Consider using a linter/formatter like Ruff or Black.
*   Use **type hints** for all function signatures, variable declarations, and Pydantic model fields.
*   For FastAPI (`main.py` in each agent):
    *   Organize endpoints logically using tags.
    *   Define request and response models using Pydantic schemas from the agent's `schemas.py`.
    *   Utilize FastAPI's dependency injection for shared resources (e.g., `get_db` from `core.database`).
    *   For operations that involve significant processing by the AI agent, use `BackgroundTasks` to offload the work from the main request-response cycle. The API should return an initial acknowledgment (e.g., `202 Accepted`) and provide another endpoint to poll for the result.

## 3. Agent Frameworks (CrewAI/LangChain)

*   **Agent Definitions (`agent.py`)**:
    *   Clearly define `role`, `goal`, and `backstory`.
    *   List all `tools` the agent is permitted to use.
    *   Specify the LLM. For initial development and testing, `FakeListLLM` from `langchain_community.llms.fake` is used to mock LLM responses and avoid API costs/dependencies. This will be replaced with actual LLMs (e.g., `ChatOpenAI`) later.
*   **Tool Definitions (`tools.py`)**:
    *   Each tool should have a clear name (using `@tool` decorator) and a detailed docstring explaining its purpose, arguments (with type hints), and return structure.
    *   Tools should perform a single, well-defined task.
    *   External API calls within tools (even if mocked initially) must include placeholders or comments for actual implementation details (error handling, API key usage).
*   **Task Definitions (`agent.py`)**:
    *   Clearly describe the task's objective, any specific context or inputs it needs, and the `expected_output` format (preferably a JSON string for structured data that can be easily parsed).
    *   Assign the task to the appropriate agent and specify any tools it's allowed to use for that task.
    *   Define task dependencies using `context_tasks` where appropriate for sequential or hierarchical processing.
*   **Workflow Orchestration (`agent.py`)**:
    *   The primary async function (e.g., `start_onboarding_process`) should encapsulate the logic for setting up the Crew (agent, tasks) and kicking off the process.
    *   This function should process the raw output from the Crew (typically the string result of the final task) and transform it into the structured dictionary format expected by the FastAPI layer (e.g., aligning with an `OutputSchema`).
    *   During initial development, this function might directly orchestrate tool calls before full CrewAI integration.

## 4. Data Handling and Persistence

*   **Pydantic Schemas (`schemas.py`)**: Define all data structures for API requests, responses, and complex tool inputs/outputs here. Use `Literal` types for controlled vocabularies. Include example data in `Config.json_schema_extra`.
*   **Mock Data Stores**: For current development, each agent's `main.py` uses in-memory Python dictionaries (e.g., `MOCK_ONBOARDING_DB`) to simulate databases or state persistence. This is for rapid prototyping.
*   **Planned Persistent Stores**:
    *   `core/database.py`: Configured for SQLAlchemy (SQLite default, PostgreSQL option) for structured relational data.
    *   `core/redis_client.py`: Configured for connecting to Redis, intended for caching, session management, task queues, and agent short-term/intermediate memory.
    *   `core/qdrant_client.py`: Configured for connecting to Qdrant, intended for vector storage for semantic search, RAG, and long-term AI memory.

## 5. Testing

*   **Unit/Component Tests**: Each `tools.py` and `agent.py` file should include an `if __name__ == "__main__":` block with test cases that demonstrate the functionality of the tools and the (mocked) agent workflows.
*   **API Testing**: FastAPI's automatic Swagger UI (`/docs`) and ReDoc (`/redoc`) are invaluable for manual API testing during development.
*   (Future) Automated API tests using `pytest` and `httpx` will be added.

## 6. Security Considerations

*   **API Keys & Secrets**: As per section 1, load from environment variables.
*   **Input Validation**: Pydantic models provide primary validation. Add custom validators in Pydantic models if more complex business rule validation is needed at the schema level.
*   **Authentication/Authorization**: Currently, agent APIs are not secured. This is a placeholder for future implementation (e.g., API key auth, OAuth2).

## 7. Nigerian Market Specifics

*   Ensure implementations related to KYC (BVN, NIN), payment systems (NIP), financial products, and regulatory reporting (CBN, NFIU, NDIC) align with Nigerian regulations and common practices.
*   Use "NGN" as the default currency where applicable. Consider proper handling for other currencies if supported.

## Workflow for AI Development Contributions

1.  **Understand Task**: Clarify requirements from the user/issue.
2.  **Plan**: Use `set_plan` to outline your implementation steps.
3.  **Implement**:
    *   Create/modify files in the appropriate agent or core directory.
    *   Follow schema-first approach for APIs (define Pydantic models in `schemas.py`).
    *   Develop tools in `tools.py` with clear contracts.
    *   Define agent and task logic in `agent.py`.
    *   Expose functionality via FastAPI endpoints in `main.py`.
    *   Add comments, docstrings, and type hints.
    *   Write test cases in `if __name__ == "__main__":` blocks or separate test files.
    *   Update `requirements.txt` if new dependencies are added.
4.  **Test (Simulated/Manual)**: Run your `if __name__ == "__main__":` tests. Manually test API endpoints via Swagger UI if applicable.
5.  **Review `AGENTS.md`**: Ensure your changes comply with these guidelines.
6.  **Submit**: Use `submit` with a clear, conventional commit message detailing the changes.

If any instruction is unclear or conflicts with a direct user request, prioritize the user's request but seek clarification if the conflict seems significant or detrimental. Your goal is to build robust, maintainable, and effective AI agent components.
