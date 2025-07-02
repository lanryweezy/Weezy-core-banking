# Agent for Customer Support (Chat/Voice/Email)
import json # For pretty printing dicts if needed
from . import tools
from . import config # For standard replies, escalation rules

class CustomerSupportAgent:
    def __init__(self, agent_id="customer_support_agent_001", memory_storage=None):
        self.agent_id = agent_id
        self.role = "Resolves complaints, queries, and assists customers via chat/voice/email."
        # Memory: Stores conversation history (ticket ID, user queries, agent replies, state),
        # customer context (if identified/authenticated), effectiveness of FAQs/KB articles.
        # Example: self.memory = {
        #    "session_CHAT123": {
        #        "customer_id": "CUSTXYZ", "ticket_ref": "TCKT001",
        #        "conversation_log": [{"user": "...", "agent": "...", "timestamp": ...}],
        #        "current_intent": "CHECK_BALANCE", "required_entities": ["account_number"],
        #        "collected_entities": {}, "resolution_attempts": 0
        #    }
        # }
        self.memory = memory_storage if memory_storage is not None else {}
        self.standard_replies = config.STANDARD_REPLIES # Load standard replies

    def _get_session_memory(self, session_id: str, initial_user_query: Optional[str] = None, customer_id: Optional[str] = None) -> dict:
        if session_id not in self.memory:
            self.memory[session_id] = {
                "customer_id": customer_id,
                "ticket_ref": None,
                "conversation_log": [],
                "current_intent": None,
                "last_identified_intent": None,
                "required_entities": [],
                "collected_entities": {},
                "resolution_attempts": 0,
                "escalation_pending": False,
                "last_agent_message": None,
                "suggested_kb_articles": []
            }
            if initial_user_query:
                 self.memory[session_id]["conversation_log"].append({"speaker": "USER", "message": initial_user_query, "timestamp": datetime.utcnow().isoformat()})
        return self.memory[session_id]

    def _update_session_memory(self, session_id: str, update_data: dict):
        if session_id in self.memory:
            self.memory[session_id].update(update_data)
        else: # Should not happen if _get_session_memory called first
            self.memory[session_id] = update_data

    def _log_conversation_turn(self, session_id: str, speaker: str, message: str):
        session_mem = self._get_session_memory(session_id)
        session_mem["conversation_log"].append({"speaker": speaker.upper(), "message": message, "timestamp": datetime.utcnow().isoformat()})
        if speaker.upper() == "AGENT":
            session_mem["last_agent_message"] = message


    def handle_customer_query(self, session_id: str, user_query: str, customer_context: Optional[dict] = None) -> dict:
        """
        Main workflow to handle a customer's query.
        Inputs:
            session_id: Unique ID for the current conversation session.
            user_query: The natural language query from the customer.
            customer_context: Optional dictionary with known customer details (e.g., customer_id, name, email if authenticated).
        Output:
            Dictionary containing the agent's reply, and potentially actions taken or required.
            e.g., {"reply": "...", "action_taken": "FETCHED_BALANCE", "session_state": {...}, "is_escalated": False}
        """
        # Initialize or retrieve session memory
        session_mem = self._get_session_memory(session_id, initial_user_query=user_query, customer_id=customer_context.get("customer_id"))
        if customer_context and not session_mem.get("customer_id"): # Update customer_id if context provided later
            session_mem["customer_id"] = customer_context.get("customer_id")

        self._log_conversation_turn(session_id, "USER", user_query)
        session_mem["resolution_attempts"] += 1

        # 1. Understand the query (Intent Recognition & Entity Extraction) using LLM/NLU tool
        nlu_result = tools.understand_query_with_llm(user_query)
        intent = nlu_result.get("intent", "UNKNOWN")
        entities = nlu_result.get("entities", {})

        session_mem["current_intent"] = intent
        session_mem["collected_entities"].update(entities) # Merge new entities with existing
        self._update_session_memory(session_id, {"current_intent": intent, "collected_entities": session_mem["collected_entities"]})


        # 2. Check for escalation conditions
        if session_mem["resolution_attempts"] > config.MAX_AGENT_ATTEMPTS_BEFORE_HUMAN_ESCALATION or \
           any(keyword in user_query.lower() for keyword in config.COMPLEX_QUERY_KEYWORDS_FOR_ESCALATION):
            return self._escalate_to_human_agent(session_id, user_query, "Exceeded attempts or complex keyword detected.")

        # 3. Fulfill the intent
        reply_message = self.standard_replies.get("CANNOT_UNDERSTAND") # Default reply
        action_taken = None

        if intent == "CHECK_BALANCE":
            # Required entity: account_number. If not collected, ask for it.
            acc_num = session_mem["collected_entities"].get("account_number")
            if not acc_num: # Try to get from customer_context if linked to a primary account
                # acc_num = customer_context.get("primary_account_number") # Needs logic to fetch this
                # if acc_num: session_mem["collected_entities"]["account_number"] = acc_num
                # else:
                reply_message = "Sure, I can help with that. Which account number would you like to check the balance for?"
                session_mem["required_entities"] = ["account_number"] # Mark what's needed
            else:
                balance_info = tools.get_account_balance_from_core(acc_num)
                if balance_info.get("status") == "success":
                    details = balance_info.get("balance_details", {})
                    reply_message = f"The available balance for account {details.get('account_number')} is {details.get('currency')} {details.get('available_balance', 0.0):.2f}."
                    action_taken = f"FETCHED_BALANCE_FOR_{acc_num}"
                else:
                    reply_message = f"Sorry, I couldn't fetch the balance for account {acc_num}. Reason: {balance_info.get('message', 'Service error')}"
                session_mem["required_entities"] = [] # Clear required entities after fulfillment

        elif intent == "BLOCK_CARD":
            # Needs card identifier (e.g. last 4 digits, or selection if multiple cards)
            # For simplicity, assume customer has one card or implies which one.
            # In real scenario, might ask "Which card ending in XXXX would you like to block?"
            # card_block_status = tools.block_card_in_core(customer_id=session_mem["customer_id"], card_identifier="LAST4_1234")
            reply_message = config.STANDARD_REPLIES.get("ACCOUNT_BLOCKED_INFO") # Using this as a generic "sensitive action" reply for mock
            action_taken = "PROVIDED_INFO_ON_CARD_BLOCK"

        elif intent == "QUERY_FAILED_TRANSACTION":
            txn_ref = session_mem["collected_entities"].get("transaction_reference") # Or extract from query
            if not txn_ref:
                # Ask for transaction reference or date/amount to help find it
                reply_message = "I can help with that. Do you have the transaction reference number, or approximate date and amount?"
                session_mem["required_entities"] = ["transaction_reference_or_details"]
            else:
                txn_status_info = tools.get_transaction_status_from_core(txn_ref)
                if txn_status_info.get("status") == "success":
                    details = txn_status_info.get("transaction_status", {})
                    reply_message = f"For transaction {details.get('transaction_id')}, the status is {details.get('status')}. Amount: {details.get('amount')}."
                    if details.get("status") == "FAILED":
                        reply_message += f" Reason: {details.get('response_message', 'Not specified')}."
                    action_taken = f"FETCHED_TXN_STATUS_FOR_{txn_ref}"
                else:
                    reply_message = config.STANDARD_REPLIES.get("TRANSACTION_NOT_FOUND")
                session_mem["required_entities"] = []

        elif intent != "UNKNOWN": # Intent recognized but no specific handler yet
            # Try Knowledge Base Search
            kb_results = tools.search_knowledge_base(user_query)
            session_mem["suggested_kb_articles"] = kb_results.get("results", [])
            if kb_results.get("status") == "success" and kb_results.get("results"):
                top_result = kb_results["results"][0]
                reply_message = f"I found this information that might help: '{top_result.get('snippet', 'Please check our FAQs.')}' (Source: {top_result.get('title')}). Does this answer your question?"
                action_taken = "PROVIDED_KB_ARTICLE"
            else: # Fallback if KB doesn't help or intent is truly unhandled by simple logic
                reply_message = self.standard_replies.get("CANNOT_UNDERSTAND") + " I can try to find a human agent for you if you'd like."
                action_taken = "FALLBACK_UNHANDLED_INTENT"

        # If reply_message is still the default "CANNOT_UNDERSTAND" and intent was not UNKNOWN, it implies a logic gap.
        # If intent IS "UNKNOWN", then "CANNOT_UNDERSTAND" is appropriate.
        if intent == "UNKNOWN" and reply_message == self.standard_replies.get("CANNOT_UNDERSTAND"):
             # Try a more general KB search or use LLM to draft a generic helpful reply if possible
            llm_draft = tools.draft_reply_with_llm(user_query, {"intent": "UNKNOWN"}, session_mem["suggested_kb_articles"])
            if llm_draft.get("status") == "success" and llm_draft.get("draft_reply"):
                reply_message = llm_draft.get("draft_reply")
            action_taken = "ATTEMPTED_LLM_ASSISTED_REPLY_FOR_UNKNOWN"


        # 4. Log conversation and update memory
        self._log_conversation_turn(session_id, "AGENT", reply_message)
        session_mem["last_identified_intent"] = intent # Store the intent that led to this reply
        self._update_session_memory(session_id, {"last_agent_message": reply_message, "last_identified_intent": intent})

        return {
            "reply": reply_message,
            "action_taken": action_taken,
            "session_id": session_id,
            "current_intent": intent,
            "collected_entities": session_mem["collected_entities"],
            "is_escalated": session_mem["escalation_pending"]
        }

    def _escalate_to_human_agent(self, session_id: str, user_query: str, reason: str) -> dict:
        session_mem = self._get_session_memory(session_id)
        session_mem["escalation_pending"] = True

        # Create a CRM ticket if one doesn't exist for this session
        if not session_mem.get("ticket_ref"):
            # Attempt to create a ticket with available info
            cust_id_for_ticket = session_mem.get("customer_id") # May be None
            # Try to get reporter details from first user message or customer_context if available
            first_user_message = next((log["message"] for log in session_mem["conversation_log"] if log["speaker"] == "USER"), user_query)

            # Placeholder for fetching actual reporter name/email if customer_id is known
            reporter_name_in = f"Customer {cust_id_for_ticket or 'Unknown'}"
            reporter_email_in = f"{cust_id_for_ticket or 'unknown_user'}@weezybank.com" # Needs real email

            ticket_creation_result = tools.create_support_ticket_in_crm(
                customer_id=cust_id_for_ticket,
                reporter_name=reporter_name_in, # Needs better source
                reporter_email=reporter_email_in, # Needs better source
                subject=f"Escalated Chat/Support Session: {session_id} - Query: {user_query[:50]}...",
                description=f"Session escalated due to: {reason}.\n\nLast user query: {user_query}\n\nConversation Log:\n{json.dumps(session_mem['conversation_log'], indent=2)}",
                channel="CHATBOT_ESCALATION" # Or specific channel
            )
            if ticket_creation_result.get("status") == "success":
                session_mem["ticket_ref"] = ticket_creation_result.get("ticket_details",{}).get("ticket_reference")
            else: # Failed to create ticket, escalation message might need to change
                 session_mem["ticket_ref"] = "ESCALATION_TICKET_FAILED" # Indicate failure

        reply = self.standard_replies.get("ESCALATING_TO_HUMAN").format(ticket_ref=session_mem.get("ticket_ref", "N/A"))
        self._log_conversation_turn(session_id, "AGENT", reply)
        self._update_session_memory(session_id, {"last_agent_message": reply})

        return {
            "reply": reply,
            "action_taken": "ESCALATED_TO_HUMAN_AGENT",
            "session_id": session_id,
            "is_escalated": True,
            "ticket_reference": session_mem.get("ticket_ref")
        }

    def get_session_details(self, session_id: str) -> dict:
        if session_id in self.memory:
            return self.memory[session_id]
        return {"status": "not_found", "message": "No session found for this ID."}

# Example Usage
if __name__ == "__main__":
    from datetime import datetime # For _log_conversation_turn timestamp
    from typing import Optional # For type hinting in main block

    support_agent = CustomerSupportAgent()
    session_id_test = "CHAT_SESSION_001"

    print("--- Simulating Customer Support Conversation ---")

    queries = [
        "Hello, I need help.",
        "I want to check my account balance for 0123456789",
        "My NIP transfer failed, reference is TXNREF123. What happened?",
        "How can I block my lost Verve card?",
        "This is too complicated, I want to speak to a human." # This should trigger escalation
    ]

    customer_mock_context = {"customer_id": "CUST007", "name": "James Bond", "primary_account_number": "0070070007"}

    for i, q in enumerate(queries):
        print(f"\nTurn {i+1}: USER > {q}")
        response = support_agent.handle_customer_query(session_id_test, q, customer_context=customer_mock_context if i==0 else None)
        print(f"Turn {i+1}: AGENT > {response.get('reply')}")
        print(f"   (Action: {response.get('action_taken')}, Intent: {response.get('current_intent')}, Escalated: {response.get('is_escalated')})")
        if response.get("is_escalated"):
            print(f"   (Ticket Ref: {response.get('ticket_reference')})")
            break # End simulation if escalated

    print("\n--- Final Session Memory ---")
    # print(json.dumps(support_agent.get_session_details(session_id_test), indent=2, default=str)) # default=str for datetime objects
    final_mem = support_agent.get_session_details(session_id_test)
    # Print selected parts of memory to avoid overly long output
    print(f"Session ID: {session_id_test}")
    print(f"Customer ID: {final_mem.get('customer_id')}")
    print(f"Ticket Ref: {final_mem.get('ticket_ref')}")
    print(f"Escalation Pending: {final_mem.get('escalation_pending')}")
    print(f"Resolution Attempts: {final_mem.get('resolution_attempts')}")
    print("Last few conversation turns:")
    for turn in final_mem.get("conversation_log", [])[-4:]: # Print last 4 turns
        print(f"  {turn['speaker']} ({turn['timestamp']}): {turn['message']}")
