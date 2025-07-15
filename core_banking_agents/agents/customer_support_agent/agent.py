# LangChain/CrewAI agent logic for Customer Support Agent

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json # For parsing task outputs if CrewAI is used later

# Assuming schemas are in the same directory or accessible via path
from .schemas import CustomerQueryInput, SupportResponseOutput, SupportResponseStatus, ChatMessage, SuggestedSolution, SentimentLabel
# Import the defined tools
from .tools import knowledge_base_tool, crm_lookup_tool, core_banking_query_tool_support, escalation_tool

# from crewai import Agent, Task, Crew, Process
# from langchain_community.llms.fake import FakeListLLM
# from ..core.config import core_settings

logger = logging.getLogger(__name__)

# --- Agent Definition (Placeholder for CrewAI) ---
# llm_support_agent = FakeListLLM(responses=[
#     "Okay, I understand the customer's query. I will first check the knowledge base.",
#     "The knowledge base provided some information. Let me see if I need more details from CRM or Core Banking.",
#     "I need to check the transaction status from the Core Banking tool.",
#     "I have all the information. Now I will formulate the response.",
#     "The query is complex, I should escalate this to a human agent."
# ])

# customer_support_tools = [knowledge_base_tool, crm_lookup_tool, core_banking_query_tool_support, escalation_tool]

# support_ai_agent = Agent(
#     role="AI Customer Support Representative",
#     goal="Understand customer queries, provide accurate information using available tools (Knowledge Base, CRM, Core Banking read-only access), resolve issues where possible, and escalate to human agents when necessary. Maintain an empathetic and helpful tone.",
#     backstory=(
#         "A highly capable AI assistant dedicated to providing excellent customer service for a Nigerian bank. "
#         "It's trained to handle a wide range of common banking inquiries, from simple questions to troubleshooting transaction issues. "
#         "It prioritizes first-contact resolution but intelligently identifies situations requiring human expertise."
#     ),
#     tools=customer_support_tools,
#     llm=llm_support_agent,
#     verbose=True,
#     allow_delegation=False, # Usually, support agent decides to use tools or escalate
# )

# --- Task Definitions (Placeholders for CrewAI) ---
# def create_query_resolution_task(query_input_json: str) -> Task:
#     return Task(
#         description=f"""\
#         Resolve a customer query based on the provided details.
#         Customer Query Input (JSON string): '{query_input_json}'

#         Workflow:
#         1. (Optional) If customer_id is present, use CRMLookupTool to get customer context (e.g., past issues, segment).
#         2. Use KnowledgeBaseTool to search for solutions or information related to the query_text.
#         3. If the query seems to require specific account data (e.g., mentions "transaction", "card", "balance", specific amounts),
#            and if the KB didn't fully resolve it, use CoreBankingQueryTool_Support.
#            (Example: if query is "my card xxxx1234 is not working", use CoreBankingQueryTool_Support with type "card_status").
#         4. Based on the information gathered, formulate a helpful and empathetic response.
#         5. If the query cannot be resolved with available tools/info, or is too sensitive/complex (e.g., fraud report, major complaint),
#            use the EscalationTool to create a ticket for human review.
#         """,
#         expected_output="""\
#         A JSON string matching the SupportResponseOutput schema. This includes:
#         'query_id', 'response_text', 'status' (e.g., "InformationProvided", "Resolved", "EscalatedToHuman"),
#         'escalation_ticket_id' (if escalated), 'conversation_id', 'sentiment_of_query' (e.g. "Neutral"), etc.
#         """,
#         agent=support_ai_agent,
#         tools=customer_support_tools
#     )

# --- Main Workflow Function (Direct Tool Usage for now, to be replaced by CrewAI kickoff) ---

async def process_customer_query_async(query_input: CustomerQueryInput) -> Dict[str, Any]:
    """
    Simulates the customer support agent's workflow by directly calling tools.
    This will eventually be replaced by CrewAI agent execution.
    """
    q_id = query_input.query_id
    logger.info(f"Agent: Starting query processing for Query ID: {q_id}, Customer: {query_input.customer_id}")
    logger.info(f"Agent: Query Text: \"{query_input.query_text}\"")

    response_text = "We are looking into your query. Please wait a moment." # Default initial
    response_status: SupportResponseStatus = "Processing" # type: ignore
    escalation_ticket_id: Optional[str] = None
    suggested_solutions: List[Dict[str,Any]] = []
    detected_intent: Optional[str] = None # Placeholder for intent detection

    # 1. (Optional) CRM Lookup for context
    crm_data: Optional[Dict[str, Any]] = None
    if query_input.customer_id:
        logger.debug(f"Agent: Calling CRMLookupTool for customer {query_input.customer_id}")
        crm_result = crm_lookup_tool.run({"customer_id": query_input.customer_id, "data_points": ["full_name", "last_interaction_summary", "segment"]})
        if crm_result.get("data_found"):
            crm_data = crm_result.get("retrieved_data")
            logger.info(f"Agent: CRM data found for {query_input.customer_id}: {crm_data}")
            # Could use crm_data to personalize response or guide next steps

    # 2. Knowledge Base Search
    logger.debug(f"Agent: Calling KnowledgeBaseTool for query: \"{query_input.query_text}\"")
    kb_result = knowledge_base_tool.run({"query_text": query_input.query_text})

    if kb_result.get("search_successful") and kb_result.get("results"):
        best_kb_article = kb_result["results"][0] # Take the first/best match
        suggested_solutions.append({
            "source": f"KnowledgeBaseArticle_#{best_kb_article.get('id', 'N/A')}",
            "solution_summary": best_kb_article.get("summary", "Refer to KB article."),
            "confidence": 0.85 # Mock confidence
        })
        response_text = f"Based on our knowledge base (Article: {best_kb_article.get('title')}): {best_kb_article.get('summary')}"
        if best_kb_article.get("steps"):
            response_text += "\nSuggested steps:\n" + "\n".join([f"- {step}" for step in best_kb_article["steps"]])
        response_status = "InformationProvided" # type: ignore
        detected_intent = best_kb_article.get("category", "GeneralInquiry") # Use KB category as intent
        logger.info(f"Agent: Found relevant KB article: {best_kb_article.get('title')}")
    else:
        logger.info(f"Agent: No direct match in Knowledge Base. Will consider other tools or generic response.")

    # 3. Core Banking Query (if needed and KB was not sufficient)
    # Simple keyword-based trigger for this mock. Real intent detection would be better.
    query_lower = query_input.query_text.lower()
    needs_core_banking_check = False
    core_banking_query_type: Optional[Literal["transaction_status", "card_status", "recent_transactions"]] = None
    core_banking_params: Dict[str, Any] = {}

    if "transaction" in query_lower or "transfer" in query_lower or "nip" in query_lower or "debited" in query_lower:
        needs_core_banking_check = True
        core_banking_query_type = "transaction_status"
        # Mock: try to extract a transaction ID if mentioned (very naive)
        import re
        match = re.search(r'(TRN\w+|TXN\w+)', query_input.query_text.upper())
        if match:
            core_banking_params["transaction_id"] = match.group(0)
        else: # If no ID, maybe it's a general transaction query, tool might not find specific.
            core_banking_params["transaction_id"] = "UNKNOWN_FROM_QUERY"

    elif "card" in query_lower and ("block" in query_lower or "lost" in query_lower or "stolen" in query_lower or "status" in query_lower or "working" in query_lower):
        needs_core_banking_check = True
        core_banking_query_type = "card_status"
        # Mock: try to extract last 4 digits (very naive)
        match = re.search(r'(\d{4})', query_input.query_text)
        if match:
            core_banking_params["card_last4_digits"] = match.group(0)

    if needs_core_banking_check and core_banking_query_type and response_status != "Resolved": # type: ignore
        logger.debug(f"Agent: Query suggests need for Core Banking check. Type: {core_banking_query_type}, Params: {core_banking_params}")
        cb_result = core_banking_query_tool_support.run({
            "customer_id": query_input.customer_id,
            "query_type": core_banking_query_type,
            "query_params": core_banking_params
        })
        logger.info(f"Agent: CoreBankingQueryTool_Support result: {cb_result}")
        if cb_result.get("status") == "Success":
            # Append or refine response_text based on cb_result
            response_text += f"\n\nCore Banking System Info ({core_banking_query_type}): {json.dumps(cb_result.get('result_data'))}"
            response_status = "InformationProvided" # type: ignore # Or Resolved if this answers it fully
        elif cb_result.get("status") == "NotFound":
            response_text += f"\n\nRegarding your query on {core_banking_query_type}: I couldn't find the specific details with the information provided ({core_banking_params})."
        else: # Error
            response_text += f"\n\nThere was an issue retrieving details for {core_banking_query_type}. Please try again later or contact human support."
            # Status might remain InformationProvided or become more specific if this was the main point.

    # 4. Escalation Logic (Simplified)
    # If no good KB match and core banking didn't resolve, or if query is complex/sensitive by keywords
    is_complex_or_sensitive = any(kw in query_lower for kw in ["complaint", "fraud", "dispute", "legal", "urgent help"])

    if response_status not in ["Resolved", "InformationProvided"] or is_complex_or_sensitive : # type: ignore
        if response_status != "InformationProvided" or (is_complex_or_sensitive and response_status == "InformationProvided"): # Escalate if complex even if some info was given
            logger.info(f"Agent: Query seems unresolved or complex/sensitive. Escalating. Query: {q_id}")
            escalation_reason = "AI agent could not fully resolve the query with available tools."
            if is_complex_or_sensitive:
                escalation_reason = "Query involves sensitive or complex issue requiring human attention."

            esc_result = escalation_tool.run({
                "query_id": q_id, "customer_id": query_input.customer_id,
                "reason_for_escalation": escalation_reason,
                "summary_of_issue": query_input.query_text,
                "urgency": "High" if is_complex_or_sensitive else "Medium"
            })
            if esc_result.get("escalation_successful"):
                escalation_ticket_id = esc_result.get("ticket_id")
                response_text = f"Thank you for your patience. Your query (ID: {q_id}) requires further attention. It has been escalated to our human support team. Your ticket ID is {escalation_ticket_id}. They will get back to you shortly."
                response_status = "EscalatedToHuman" # type: ignore
            else:
                response_text = "I am unable to fully resolve your query at this moment and also faced an issue escalating it. Please contact our support line directly."
                # Status might remain "Processing" or a specific error status.

    # If after all steps, status is still "Processing", provide a generic holding message.
    if response_status == "Processing": # type: ignore
        response_text = "Thank you for your query. We are looking into it and will provide an update soon."
        response_status = "PendingCustomerReply" # type: ignore # Or a more specific pending status

    # Mock sentiment analysis
    sentiment_of_query: SentimentLabel = "Neutral" # type: ignore
    if any(w in query_lower for w in ["help", "issue", "problem", "failed", "complaint", "urgent"]):
        sentiment_of_query = "Negative" # type: ignore
    elif any(w in query_lower for w in ["thanks", "great", "perfect", "good"]):
        sentiment_of_query = "Positive" # type: ignore


    final_response_payload = {
        "query_id": q_id,
        "conversation_id": query_input.conversation_id,
        "response_text": response_text,
        "status": response_status,
        "timestamp": datetime.utcnow(), # Use current time for response
        "sentiment_of_query": sentiment_of_query,
        "intent_detected": detected_intent, # From KB or future NLU step
        "suggested_solutions_considered": suggested_solutions if suggested_solutions else None,
        "escalation_ticket_id": escalation_ticket_id,
    }

    logger.info(f"Agent: Query processing finished for {q_id}. Final Status: {response_status}, Response Text: '{response_text[:100]}...'")
    return final_response_payload


if __name__ == "__main__":
    import asyncio

    async def test_support_agent_workflow():
        print("--- Testing Customer Support Agent Workflow (Direct Tool Usage) ---")

        queries = [
            CustomerQueryInput(customer_id="CUST-SPT-001", channel="Chat", query_text="Hi, I forgot my internet banking password."),
            CustomerQueryInput(customer_id="CUST-SPT-007", channel="InApp", query_text="My NIP transfer TXNFAILED456 failed. What should I do?"),
            CustomerQueryInput(customer_id="CUST-SPT-001", channel="Email", query_text="I think my card xxxx1234 might be compromised, please help block it urgently! This is a serious complaint."),
            CustomerQueryInput(customer_id="CUST-NEW-001", channel="Chat", query_text="What are your savings account interest rates?") # KB might not have this
        ]

        for i, query in enumerate(queries):
            print(f"\n--- Test Query {i+1} ---")
            print(f"Input: {query.model_dump_json(indent=2, exclude_none=True)}")
            response_payload = await process_customer_query_async(query)
            print(f"Output for Query {query.query_id}:")
            print(json.dumps(response_payload, indent=2, default=str))
            # Validate against schema
            try:
                SupportResponseOutput(**response_payload)
                print(f"  (Schema validation successful for query {query.query_id})")
            except Exception as e:
                print(f"  (SCHEMA VALIDATION FAILED for query {query.query_id}: {e})")


    # asyncio.run(test_support_agent_workflow())
    print("Customer Support Agent logic (agent.py). Contains workflow to process queries using tools (mocked execution).")
