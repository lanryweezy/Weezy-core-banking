# Tools for Customer Support Agent

from langchain.tools import tool
from typing import Dict, Any, List, Optional, Literal
import random
import logging
import uuid
from datetime import datetime

# Assuming schemas might be imported for type hinting
# from .schemas import QueryChannel # Example

logger = logging.getLogger(__name__)

# --- Mock Data for Tools ---
MOCK_KNOWLEDGE_BASE = {
    "password reset": {
        "id": "KB001", "title": "How to Reset Internet Banking Password",
        "summary": "Customers can reset their password via the 'Forgot Password' link on the login page or by calling support for a guided reset.",
        "keywords": ["password", "reset", "forgot", "login", "internet banking"],
        "steps": ["Go to login page.", "Click 'Forgot Password'.", "Enter registered email/phone.", "Follow OTP verification.", "Set new password."],
        "category": "AccountAccess"
    },
    "failed nip transfer": {
        "id": "KB002", "title": "Troubleshooting Failed NIP Transfers",
        "summary": "If a NIP transfer fails but the account is debited, NIBSS typically processes an auto-reversal within 24 hours. If not, a formal dispute may be needed.",
        "keywords": ["nip", "transfer", "failed", "debit", "reversal", "transaction"],
        "steps": ["Advise customer to wait 24 hours for auto-reversal.", "If not reversed, guide to fill dispute form.", "Check transaction status using CoreBankingQueryTool."],
        "category": "Transactions"
    },
    "block card": {
        "id": "KB003", "title": "How to Block a Lost/Stolen Card",
        "summary": "Cards can be blocked via the mobile app, internet banking, USSD, or by calling support.",
        "keywords": ["block", "card", "lost", "stolen", "atm card", "debit card"],
        "steps": ["Verify customer identity.", "Use CoreBankingQueryTool to action card block.", "Confirm block to customer.", "Advise on card replacement process."],
        "category": "CardServices"
    }
}

MOCK_CRM_DATA = {
    "CUST-SPT-001": {
        "customer_id": "CUST-SPT-001", "full_name": "Aisha Bello", "segment": "Retail",
        "last_interaction_summary": "Resolved issue with mobile app login on 2023-10-15.",
        "open_tickets_count": 0,
        "contact_preferences": {"channel": "Email", "email": "aisha.b@example.com"},
        "notes": "Prefers detailed explanations."
    },
    "CUST-SPT-007": {
        "customer_id": "CUST-SPT-007", "full_name": "David Okon", "segment": "SME",
        "last_interaction_summary": "Inquired about loan products on 2023-10-20.",
        "open_tickets_count": 1, "open_ticket_ids": ["TCKT-HIGH-001"],
        "contact_preferences": {"channel": "Phone", "phone": "08011122233"},
        "notes": "Usually busy, prefers quick resolutions."
    }
}

MOCK_CORE_BANKING_SUPPORT_DATA = { # Simplified view for support queries
    "transactions": {
        "TXN789012": {"status": "Successful", "amount": 5000, "currency": "NGN", "description": "NIP Transfer to John Doe", "date": "2023-10-28"},
        "TXNFAILED456": {"status": "Failed", "reason": "Insufficient Funds", "amount": 15000, "currency": "NGN", "description": "Bill Payment - DSTV", "date": "2023-10-29"},
    },
    "cards": {
        "CUST-SPT-001_CARD1": {"card_number_masked": "xxxx-1234", "status": "Active", "type": "Verve Debit"},
        "CUST-SPT-007_CARD1": {"card_number_masked": "xxxx-5678", "status": "Blocked (Lost)", "type": "Mastercard Debit"},
    }
}


@tool("KnowledgeBaseTool")
def knowledge_base_tool(query_text: str, filters: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Simulates searching a knowledge base (FAQs, SOPs) for relevant articles or solutions.

    Args:
        query_text (str): The customer's query or keywords to search for.
        filters (Optional[List[str]]): Categories or tags to filter results by (e.g., "AccountAccess", "Transactions").

    Returns:
        Dict[str, Any]: Contains 'search_successful' (bool) and 'results' (List of matching articles/solutions).
                        Each result has 'id', 'title', 'summary', 'steps', 'category'.
    """
    logger.info(f"KnowledgeBaseTool: Searching for query='{query_text}', filters={filters}")
    results = []
    query_lower = query_text.lower()

    for key, article in MOCK_KNOWLEDGE_BASE.items():
        match_score = 0
        # Check keywords
        for kw in article.get("keywords", []):
            if kw in query_lower:
                match_score += 2
        # Check title
        if article.get("title", "").lower() in query_lower or query_lower in article.get("title", "").lower():
            match_score += 5
        # Check summary
        if query_lower in article.get("summary", "").lower():
            match_score += 1

        # Apply filters if any
        passes_filter = True
        if filters:
            passes_filter = article.get("category") in filters or any(f.lower() in article.get("title","").lower() for f in filters)

        if match_score > 2 and passes_filter: # Some arbitrary threshold for relevance
            results.append(article)

    if results:
        # Sort by relevance (mocked by score, or just return as found)
        logger.info(f"KnowledgeBaseTool: Found {len(results)} relevant articles for '{query_text}'.")
        return {"search_successful": True, "results": results}
    else:
        logger.info(f"KnowledgeBaseTool: No direct match found for '{query_text}'.")
        return {"search_successful": False, "results": [], "message": "No direct articles found. Try rephrasing or using broader terms."}

@tool("CRMLookupTool")
def crm_lookup_tool(customer_id: str, data_points: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Simulates fetching customer data from a CRM system.

    Args:
        customer_id (str): The unique identifier for the customer.
        data_points (Optional[List[str]]): Specific data points to retrieve
                                           (e.g., "last_interaction_summary", "open_tickets_count").
                                           If None, returns all available mock data for the customer.
    Returns:
        Dict[str, Any]: Contains 'customer_id', 'data_found' (bool), and
                        'retrieved_data' (dict of requested data points or all data).
    """
    logger.info(f"CRMLookupTool: Fetching data for customer_id='{customer_id}', data_points={data_points}")

    if customer_id in MOCK_CRM_DATA:
        customer_data = MOCK_CRM_DATA[customer_id]
        retrieved_data = {}
        if data_points:
            for point in data_points:
                if point in customer_data:
                    retrieved_data[point] = customer_data[point]
                else:
                    retrieved_data[point] = None # Indicate data point not found for this customer
        else: # Return all data for customer
            retrieved_data = customer_data

        logger.info(f"CRMLookupTool: Data found for customer '{customer_id}'.")
        return {"customer_id": customer_id, "data_found": True, "retrieved_data": retrieved_data}
    else:
        logger.warning(f"CRMLookupTool: No CRM data found for customer_id '{customer_id}'.")
        return {"customer_id": customer_id, "data_found": False, "retrieved_data": {}, "message": "Customer not found in CRM."}

@tool("CoreBankingQueryTool_Support")
def core_banking_query_tool_support(
    customer_id: str, # For context/authorization check, though not used in this mock's data lookup directly
    query_type: Literal["transaction_status", "card_status", "recent_transactions"],
    query_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Simulates read-only queries to the Core Banking System relevant for customer support.
    Requires customer_id for authorization context.

    Args:
        customer_id (str): Customer ID for context.
        query_type (str): Type of query: "transaction_status", "card_status", "recent_transactions".
        query_params (Dict[str, Any]): Parameters for the query
                                      (e.g., {"transaction_id": "TXN123"},
                                      {"card_last4_digits": "1234"},
                                      {"account_number": "0012345678", "limit": 5}).
    Returns:
        Dict[str, Any]: Contains 'query_type', 'status' ("Success", "NotFound", "Error"),
                        and 'result_data' (dict of results or error message).
    """
    logger.info(f"CoreBankingQueryTool_Support: Customer '{customer_id}', QueryType '{query_type}', Params: {query_params}")

    if query_type == "transaction_status":
        txn_id = query_params.get("transaction_id")
        if txn_id in MOCK_CORE_BANKING_SUPPORT_DATA["transactions"]:
            return {"query_type": query_type, "status": "Success", "result_data": MOCK_CORE_BANKING_SUPPORT_DATA["transactions"][txn_id]}
        else:
            return {"query_type": query_type, "status": "NotFound", "result_data": {"message": f"Transaction ID '{txn_id}' not found."}}

    elif query_type == "card_status":
        card_key_prefix = f"{customer_id}_CARD" # Mocking: find any card for this customer
        card_last4 = query_params.get("card_last4_digits")

        found_card = None
        for key, card_info in MOCK_CORE_BANKING_SUPPORT_DATA["cards"].items():
            if key.startswith(card_key_prefix) and (not card_last4 or card_info["card_number_masked"].endswith(card_last4)):
                found_card = card_info
                break
        if found_card:
             return {"query_type": query_type, "status": "Success", "result_data": found_card}
        else:
            return {"query_type": query_type, "status": "NotFound", "result_data": {"message": f"Card details not found for customer '{customer_id}' matching criteria."}}

    elif query_type == "recent_transactions":
        # This is highly simplified. Real system would query by account_number.
        limit = query_params.get("limit", 3)
        # Just return a few transactions as mock, not actually filtering by account
        all_txns = list(MOCK_CORE_BANKING_SUPPORT_DATA["transactions"].values())
        return {"query_type": query_type, "status": "Success", "result_data": {"transactions": all_txns[:limit]}}

    else:
        return {"query_type": query_type, "status": "Error", "result_data": {"message": f"Unsupported query type: {query_type}"}}


@tool("EscalationTool")
def escalation_tool(
    query_id: str,
    customer_id: str,
    reason_for_escalation: str,
    summary_of_issue: str,
    urgency: Literal["Low", "Medium", "High"] = "Medium"
) -> Dict[str, Any]:
    """
    Simulates escalating an issue to a human support tier or creating a formal support ticket.

    Args:
        query_id (str): The original query ID that is being escalated.
        customer_id (str): The customer ID.
        reason_for_escalation (str): Why the AI agent is escalating this.
        summary_of_issue (str): A brief summary of the unresolved issue.
        urgency (Literal["Low", "Medium", "High"]): Urgency of the escalation.

    Returns:
        Dict[str, Any]: Contains 'escalation_successful' (bool), 'ticket_id' (Optional[str]), 'message'.
    """
    logger.info(f"EscalationTool: Escalating query_id='{query_id}' for customer_id='{customer_id}'. Reason: '{reason_for_escalation}', Urgency: {urgency}")

    # Simulate creating a ticket ID
    ticket_id = f"ESCTCKT-{query_id[:5]}-{random.randint(100,999)}"

    # In a real system, this would integrate with a ticketing system (Jira, Zendesk, custom DB)
    # For now, just log and return success
    # MOCK_TICKETS_DB[ticket_id] = { "query_id": query_id, ... } // If we had access to main.py's DB

    message = f"Issue escalated successfully. Human support will review. Ticket ID: {ticket_id}"
    logger.info(message)
    return {"escalation_successful": True, "ticket_id": ticket_id, "message": message}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("--- Testing CustomerSupportAgent Tools ---")

    print("\n1. Testing KnowledgeBaseTool:")
    kb_res_pw = knowledge_base_tool.run({"query_text": "how to reset password"})
    print(f"  KB (Password Reset): Found={kb_res_pw['search_successful']}, Results Count={len(kb_res_pw['results'])}")
    if kb_res_pw['results']: print(f"    Example Title: {kb_res_pw['results'][0]['title']}")

    kb_res_nip = knowledge_base_tool.run({"query_text": "NIP transfer failed", "filters": ["Transactions"]})
    print(f"  KB (NIP Failed w/ Filter): Found={kb_res_nip['search_successful']}, Results Count={len(kb_res_nip['results'])}")

    kb_res_none = knowledge_base_tool.run({"query_text": "how to fly to moon"})
    print(f"  KB (No Match): Found={kb_res_none['search_successful']}, Message: {kb_res_none.get('message')}")


    print("\n2. Testing CRMLookupTool:")
    crm_res1 = crm_lookup_tool.run({"customer_id": "CUST-SPT-001", "data_points": ["full_name", "segment", "last_interaction_summary"]})
    print(f"  CRM (CUST-SPT-001): Found={crm_res1['data_found']}, Name={crm_res1.get('retrieved_data',{}).get('full_name')}")

    crm_res2 = crm_lookup_tool.run({"customer_id": "CUST-UNKNOWN-999"})
    print(f"  CRM (UNKNOWN): Found={crm_res2['data_found']}, Message={crm_res2.get('message')}")


    print("\n3. Testing CoreBankingQueryTool_Support:")
    cb_txn_res = core_banking_query_tool_support.run({"customer_id": "CUST-SPT-007", "query_type": "transaction_status", "query_params": {"transaction_id": "TXNFAILED456"}})
    print(f"  CoreBanking (Txn Status): Status={cb_txn_res['status']}, Result={cb_txn_res.get('result_data',{}).get('status')}")

    cb_card_res = core_banking_query_tool_support.run({"customer_id": "CUST-SPT-007", "query_type": "card_status", "query_params": {"card_last4_digits": "5678"}})
    print(f"  CoreBanking (Card Status): Status={cb_card_res['status']}, Result={cb_card_res.get('result_data',{}).get('status')}")

    cb_recent_res = core_banking_query_tool_support.run({"customer_id": "CUST-SPT-001", "query_type": "recent_transactions", "query_params": {"account_number": "1234509876", "limit": 1}})
    print(f"  CoreBanking (Recent Txns): Status={cb_recent_res['status']}, Count={len(cb_recent_res.get('result_data',{}).get('transactions',[]))}")


    print("\n4. Testing EscalationTool:")
    esc_res = escalation_tool.run({
        "query_id": "QRY12345", "customer_id": "CUST-SPT-001",
        "reason_for_escalation": "AI unable to resolve complex NIP dispute.",
        "summary_of_issue": "Customer claims N50,000 NIP debit not reversed after 48 hours.",
        "urgency": "High"
    })
    print(f"  Escalation: Success={esc_res['escalation_successful']}, TicketID={esc_res.get('ticket_id')}")

    print("\nCustomer Support Agent tools implemented with mocks.")
