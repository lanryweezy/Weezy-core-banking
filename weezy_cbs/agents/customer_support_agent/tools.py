# Tools for Customer Support Agent
import requests
import json
from . import config
# from weezy_cbs.crm_customer_support.schemas import SupportTicketCreateRequest, TicketCommentCreateRequest # etc.
# from weezy_cbs.ai_automation_layer.schemas import LLMTaskRequest # If using LLM service

# Placeholder for schemas if not importing
class SupportTicketCreateRequestSchema(dict): pass
class TicketCommentCreateRequestSchema(dict): pass
class LLMTaskRequestSchema(dict): pass

# --- CRM Integration Tools ---
def create_support_ticket_in_crm(customer_id: Optional[str], reporter_name: str, reporter_email: str, subject: str, description: str, channel: str, priority: str = "MEDIUM") -> dict:
    """Creates a new support ticket in the CRM system."""
    payload = SupportTicketCreateRequestSchema(
        customer_id=customer_id, # May be None if not an existing customer
        reporter_name=reporter_name,
        reporter_email=reporter_email,
        subject=subject,
        description=description,
        channel_origin=channel.upper(), # Ensure matches enum values in CRM module
        priority=priority.upper()
    )
    try:
        # response = requests.post(config.CREATE_TICKET_ENDPOINT, json=payload, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return {"status": "success", "ticket_details": response.json()} # Should match SupportTicketResponse

        print(f"Mock CRM API Call: POST {config.CREATE_TICKET_ENDPOINT} with payload {payload}")
        mock_ticket_id = "TCKT" + str(random.randint(10000, 99999))
        return {
            "status": "success",
            "ticket_details": {
                "id": random.randint(1,100), "ticket_reference": mock_ticket_id, "status": "OPEN",
                "subject": subject, "reporter_email": reporter_email,
                # ... other fields from SupportTicketResponse
            }
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to create ticket in CRM: {str(e)}"}

def add_comment_to_crm_ticket(ticket_id: str, comment_text: str, commenter_type: str = "AGENT", is_internal: bool = False) -> dict:
    """Adds a comment to an existing support ticket in the CRM."""
    # Assuming ticket_id is the CRM's ticket reference or internal ID.
    # The CRM API endpoint might take ticket_reference or internal DB ID.
    url = config.ADD_TICKET_COMMENT_ENDPOINT.format(ticket_id=ticket_id) # Adjust if endpoint uses ref vs id
    payload = TicketCommentCreateRequestSchema(
        comment_text=comment_text,
        commenter_type=commenter_type.upper(), # AGENT, CUSTOMER, SYSTEM
        is_internal_note=is_internal
    )
    try:
        # response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return {"status": "success", "comment_details": response.json()} # Should match TicketCommentResponse
        print(f"Mock CRM API Call: POST {url} with payload {payload}")
        return {"status": "success", "comment_details": {"id": random.randint(100,200), "comment_text": comment_text, "commenter_type": commenter_type}}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to add comment to ticket {ticket_id}: {str(e)}"}

def get_customer_interaction_history(customer_id: str) -> dict:
    """Fetches past interaction history for a customer from CRM."""
    url = config.GET_CUSTOMER_INTERACTIONS_ENDPOINT.format(customer_id=customer_id)
    try:
        # response = requests.get(url, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return {"status": "success", "interactions": response.json()} # List of InteractionLogResponse
        print(f"Mock CRM API Call: GET {url}")
        return {"status": "success", "interactions": [
            {"interaction_type": "PHONE_CALL", "subject": "Balance Inquiry", "date": "2023-10-01"},
            {"interaction_type": "TICKET_LOGGED", "subject": "Failed Transfer TCKT123", "date": "2023-09-15"}
        ]}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to fetch customer interaction history: {str(e)}"}


# --- Knowledge Base / SOP Search Tool ---
def search_knowledge_base(query: str, top_k: int = 3) -> dict:
    """Searches the knowledge base or SOP documents for relevant information."""
    payload = {"query": query, "top_k": top_k}
    try:
        # response = requests.post(config.KNOWLEDGE_BASE_SEARCH_API_URL, json=payload)
        # response.raise_for_status()
        # return {"status": "success", "results": response.json()} # List of search results (e.g. doc snippets, links)
        print(f"Mock KB Search: Query='{query}', TopK={top_k}")
        results = []
        if "card block" in query.lower():
            results.append({"title": "How to Block a Lost Card", "snippet": "To block a lost card, log into mobile app > Cards > Select Card > Block. Or call ...", "relevance_score": 0.9})
        if "transfer failed" in query.lower():
            results.append({"title": "Troubleshooting Failed Transfers", "snippet": "Check beneficiary details, account balance, and daily limits. Common NIP error codes: 07 (Invalid Account), 51 (Insufficient Funds)...", "relevance_score": 0.85})
        if not results:
            results.append({"title": "General FAQ", "snippet": "For other issues, please visit our FAQ page at weezybank.com/faq or contact support.", "relevance_score": 0.5})
        return {"status": "success", "results": results[:top_k]}

    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Knowledge base search request failed: {str(e)}"}

# --- Core Banking System Data Lookup Tools (Examples) ---
def get_account_balance_from_core(account_number: str) -> dict:
    """Fetches account balance from the Accounts & Ledger module."""
    url = f"{config.ACCOUNTS_LEDGER_API_URL}/accounts/{account_number}/balance"
    try:
        # response = requests.get(url, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return {"status": "success", "balance_details": response.json()} # AccountBalanceResponse
        print(f"Mock Core API Call: GET {url}")
        if account_number == "0000000000": return {"status": "error", "message": "Account not found (mock)."}
        return {"status": "success", "balance_details": {"account_number": account_number, "available_balance": random.uniform(1000,100000), "currency": "NGN"}}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to fetch account balance for {account_number}: {str(e)}"}

def get_transaction_status_from_core(transaction_reference: str) -> dict:
    """Fetches transaction status from the Transaction Management module."""
    url = f"{config.TRANSACTION_MANAGEMENT_API_URL}/{transaction_reference}/status"
    try:
        # response = requests.get(url, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return {"status": "success", "transaction_status": response.json()} # TransactionStatusQueryResponse
        print(f"Mock Core API Call: GET {url}")
        if "UNKNOWN" in transaction_reference.upper(): return {"status": "error", "message": "Transaction not found (mock)."}
        return {"status": "success", "transaction_status": {"transaction_id": transaction_reference, "status": random.choice(["SUCCESSFUL", "PENDING", "FAILED"]), "amount": 5000}}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to fetch transaction status for {transaction_reference}: {str(e)}"}

# --- LLM Tools (If agent uses LLM for NLU or drafting replies) ---
def understand_query_with_llm(user_query: str) -> dict:
    """Uses LLM to identify intent and extract entities from user query."""
    payload = LLMTaskRequestSchema(
        task_type="NLU_CHATBOT_INTENT", # Or a more generic "UNDERSTAND_QUERY"
        input_text=user_query,
        # context_data={"prompt_template": config.DEFAULT_LLM_PROMPT_TEMPLATE_FOR_QUERY_UNDERSTANDING.format(query=user_query)}
    )
    try:
        # response = requests.post(config.LLM_SERVICE_API_URL, json=payload, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # llm_result = response.json() # Assuming LLMTaskResponse
        # return {"status": "success", "intent": llm_result.get("processed_output", {}).get("intent"), "entities": llm_result.get("processed_output", {}).get("entities")}
        print(f"Mock LLM NLU: Processing query '{user_query}'")
        intent = "UNKNOWN"
        entities = {}
        if "balance" in user_query.lower(): intent = "CHECK_BALANCE"
        if "block" in user_query.lower() and "card" in user_query.lower(): intent = "BLOCK_CARD"
        if "transfer" in user_query.lower() and "failed" in user_query.lower():
            intent = "QUERY_FAILED_TRANSACTION"
            entities["transaction_type"] = "transfer"
        # Extract account number if present (simple regex or keyword based for mock)
        import re
        acc_match = re.search(r'\b(\d{10})\b', user_query)
        if acc_match: entities["account_number"] = acc_match.group(1)

        return {"status": "success", "intent": intent, "entities": entities}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"LLM query understanding request failed: {str(e)}"}

def draft_reply_with_llm(user_query: str, context_info: dict, kb_search_results: Optional[list] = None) -> dict:
    """Uses LLM to draft a reply based on query, context, and KB results."""
    # prompt_context = f"Context: {json.dumps(context_info)}. "
    # if kb_search_results:
    #     prompt_context += f"Relevant KB Articles: {json.dumps([res['snippet'] for res in kb_search_results[:2]])}. "

    # payload = LLMTaskRequestSchema(
    #     task_type="DRAFT_CUSTOMER_REPLY",
    #     input_text=user_query, # The original user query
    #     context_data={"prompt_template": config.DEFAULT_LLM_PROMPT_TEMPLATE_FOR_DRAFTING_REPLY.format(context_info=prompt_context, query=user_query)}
    # )
    # try:
    #     response = requests.post(config.LLM_SERVICE_API_URL, json=payload, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
    #     response.raise_for_status()
    #     llm_result = response.json()
    #     return {"status": "success", "draft_reply": llm_result.get("processed_output")}
    # except requests.exceptions.RequestException as e:
    #     return {"status": "error", "message": f"LLM reply drafting request failed: {str(e)}"}

    print(f"Mock LLM Draft Reply: For query '{user_query}' with context {list(context_info.keys())}")
    reply = f"Thank you for your query about '{user_query}'. "
    if context_info.get("intent") == "CHECK_BALANCE" and context_info.get("balance_details"):
        reply += f"Your balance for account {context_info['balance_details']['account_number']} is {context_info['balance_details']['currency']} {context_info['balance_details']['available_balance']:.2f}. "
    elif kb_search_results:
        reply += f"I found this information that might help: '{kb_search_results[0]['snippet']}'. "
    else:
        reply += config.STANDARD_REPLIES.get("CANNOT_UNDERSTAND", "I will look into that for you. ")
    reply += "Is there anything else I can assist with?"
    return {"status": "success", "draft_reply": reply}


if __name__ == '__main__':
    import random # For mock data in tool tests
    print("--- Testing Customer Support Agent Tools ---")

    # 1. Test CRM Ticket Creation
    print("\n1. Create Support Ticket:")
    ticket_res = create_support_ticket_in_crm(
        customer_id="CUST123", reporter_name="Test User", reporter_email="test@example.com",
        subject="Test Ticket from Agent Tool", description="This is a test ticket description.",
        channel="CHATBOT"
    )
    print(json.dumps(ticket_res, indent=2))
    mock_ticket_ref = ticket_res.get("ticket_details", {}).get("ticket_reference", "TCKT_MOCK_MAIN")


    # 2. Test Add Comment to Ticket
    if ticket_res.get("status") == "success":
        print(f"\n2. Add Comment to Ticket {mock_ticket_ref}:")
        comment_res = add_comment_to_crm_ticket(mock_ticket_ref, "This is a test comment from the agent tool.", "AGENT")
        print(json.dumps(comment_res, indent=2))

    # 3. Test KB Search
    print("\n3. Knowledge Base Search (card block):")
    kb_res_card = search_knowledge_base("how to block my card")
    print(json.dumps(kb_res_card, indent=2))

    print("\n4. Knowledge Base Search (failed transfer):")
    kb_res_transfer = search_knowledge_base("my transfer failed what do I do")
    print(json.dumps(kb_res_transfer, indent=2))

    # 5. Test Core Banking Lookups
    print("\n5. Get Account Balance (0123456789):")
    bal_res = get_account_balance_from_core("0123456789")
    print(json.dumps(bal_res, indent=2))

    print("\n6. Get Transaction Status (TXNREF123):")
    txn_stat_res = get_transaction_status_from_core("TXNREF123")
    print(json.dumps(txn_stat_res, indent=2))

    # 7. Test LLM Query Understanding
    query1 = "What's my balance on account 0123456789?"
    print(f"\n7. LLM Understand Query ('{query1}'):")
    nlu_res1 = understand_query_with_llm(query1)
    print(json.dumps(nlu_res1, indent=2))

    query2 = "My NIP transfer to 0581122334 for 5000 naira failed yesterday, reference TXNABC."
    print(f"\n8. LLM Understand Query ('{query2}'):")
    nlu_res2 = understand_query_with_llm(query2)
    print(json.dumps(nlu_res2, indent=2))

    # 9. Test LLM Reply Drafting
    if nlu_res1.get("status") == "success" and bal_res.get("status") == "success":
        context_for_reply = {**nlu_res1, **bal_res} # Combine NLU output and fetched data
        print(f"\n9. LLM Draft Reply for Balance Query:")
        draft_res = draft_reply_with_llm(query1, context_for_reply, kb_res_card.get("results")) # Pass some KB results too
        print(json.dumps(draft_res, indent=2))
