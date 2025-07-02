# Agent for Teller Operations
from . import tools
from . import config
from datetime import datetime, timedelta

class TellerAgent:
    def __init__(self, agent_id="teller_agent_001", memory_storage=None):
        self.agent_id = agent_id
        self.role = "Handles deposits, withdrawals, transfers, and balance checks."
        # Memory: Stores frequent beneficiaries, past transactions for a user session or user ID
        # Example: self.memory = {"user_X": {"frequent_beneficiaries": [], "past_transactions": []}}
        self.memory = memory_storage if memory_storage is not None else {}
        # For tracking daily limits (simplified, would be persistent in a real system)
        self.daily_transaction_totals = {} # { (user_id, date_str): {"withdrawal": 0, "transfer": 0} }

    def _get_user_memory(self, user_id: str):
        if user_id not in self.memory:
            self.memory[user_id] = {
                "frequent_beneficiaries": [],
                "past_transactions": [],
                "pending_otp_verification": None # { "action": "transfer", "details": {...} }
            }
        return self.memory[user_id]

    def _add_past_transaction(self, user_id: str, transaction_details: dict):
        user_mem = self._get_user_memory(user_id)
        user_mem["past_transactions"].insert(0, transaction_details) # Add to the beginning
        user_mem["past_transactions"] = user_mem["past_transactions"][:10] # Keep last 10

    def _update_daily_limits(self, user_id: str, transaction_type: str, amount: float) -> bool:
        """Updates and checks daily transaction limits. Returns True if within limits."""
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        user_date_key = (user_id, today_str)

        if user_date_key not in self.daily_transaction_totals:
            self.daily_transaction_totals[user_date_key] = {"withdrawal": 0.0, "transfer": 0.0}

        current_total = self.daily_transaction_totals[user_date_key].get(transaction_type, 0.0)

        limit_exceeded = False
        if transaction_type == "withdrawal":
            if current_total + amount > config.DAILY_WITHDRAWAL_LIMIT:
                limit_exceeded = True
        elif transaction_type == "transfer":
            if current_total + amount > config.DAILY_TRANSFER_LIMIT:
                limit_exceeded = True

        if limit_exceeded:
            return False # Limit would be exceeded

        # If not exceeded, update the total
        self.daily_transaction_totals[user_date_key][transaction_type] += amount
        return True


    def request_transaction_otp(self, user_id: str, account_number: str, action: str, details: dict) -> dict:
        """Requests OTP for a transaction and stores pending action."""
        user_mem = self._get_user_memory(user_id)

        # Simple check: is there already a pending OTP for this user?
        if user_mem.get("pending_otp_verification"):
            return {"status": "failed", "message": "Another OTP verification is already pending for this user."}

        otp_request_result = tools.request_otp(identifier=account_number) # Using account_number as OTP identifier
        if otp_request_result.get("status") == "success":
            user_mem["pending_otp_verification"] = {
                "action": action,
                "details": details,
                "account_number": account_number, # Store account_number for OTP verification
                "timestamp": datetime.utcnow()
            }
            return {"status": "success", "message": "OTP requested. Please provide the OTP to complete the transaction."}
        else:
            return {"status": "failed", "message": "OTP request failed.", "details": otp_request_result}

    def _handle_transaction(self, user_id: str, account_number: str, transaction_type: str, amount: float, **kwargs) -> dict:
        """Generic handler for amount-based transactions with limit checks."""
        limit_type_map = {
            "deposit": None, # No daily limit check for deposits in this example
            "withdraw": "withdrawal",
            "transfer_out": "transfer" # Assuming 'transfer' in limits config refers to outgoing
        }
        config_limit_map = {
            "deposit": None,
            "withdraw": config.MAX_WITHDRAWAL_PER_TRANSACTION,
            "transfer_out": config.MAX_TRANSFER_PER_TRANSACTION
        }

        # Per-transaction amount limit check
        max_amount_per_transaction = config_limit_map.get(transaction_type)
        if max_amount_per_transaction is not None and amount > max_amount_per_transaction:
            return {"status": "failed", "message": f"{transaction_type.replace('_', ' ').capitalize()} amount exceeds per-transaction limit of {max_amount_per_transaction} {config.DEFAULT_CURRENCY}."}

        # Daily limit check (if applicable)
        daily_limit_key = limit_type_map.get(transaction_type)
        if daily_limit_key:
            if not self._update_daily_limits(user_id, daily_limit_key, amount):
                daily_limit_value = config.DAILY_WITHDRAWAL_LIMIT if daily_limit_key == "withdrawal" else config.DAILY_TRANSFER_LIMIT
                return {"status": "failed", "message": f"This transaction would exceed your daily {daily_limit_key} limit of {daily_limit_value} {config.DEFAULT_CURRENCY}."}

        # Execute actual transaction
        result = {}
        if transaction_type == "deposit":
            result = tools.execute_deposit(account_number, amount, currency=kwargs.get("currency", config.DEFAULT_CURRENCY), narration=kwargs.get("narration"))
        elif transaction_type == "withdraw":
            result = tools.execute_withdrawal(account_number, amount, currency=kwargs.get("currency", config.DEFAULT_CURRENCY), narration=kwargs.get("narration"))
        elif transaction_type == "transfer_out":
            result = tools.execute_transfer(
                from_account=account_number,
                to_account=kwargs.get("to_account"),
                amount=amount,
                currency=kwargs.get("currency", config.DEFAULT_CURRENCY),
                narration=kwargs.get("narration")
            )

        if result.get("status") == "success":
            self._add_past_transaction(user_id, {**result, "type": transaction_type, "amount": amount, "timestamp": datetime.utcnow().isoformat()})
        else: # Rollback daily limit if transaction failed
            if daily_limit_key:
                today_str = datetime.utcnow().strftime('%Y-%m-%d')
                user_date_key = (user_id, today_str)
                if user_date_key in self.daily_transaction_totals and daily_limit_key in self.daily_transaction_totals[user_date_key]:
                     self.daily_transaction_totals[user_date_key][daily_limit_key] -= amount


        return result

    def process_transaction_with_otp(self, user_id: str, otp_code: str) -> dict:
        """Processes a pending transaction after OTP verification."""
        user_mem = self._get_user_memory(user_id)
        pending_action = user_mem.get("pending_otp_verification")

        if not pending_action:
            return {"status": "failed", "message": "No pending transaction found for OTP verification."}

        # OTP Expiry Check (e.g. 5 minutes)
        if datetime.utcnow() - pending_action["timestamp"] > timedelta(minutes=5):
            user_mem["pending_otp_verification"] = None # Clear expired pending action
            return {"status": "failed", "message": "OTP has expired. Please try the transaction again."}

        # Verify OTP
        otp_verification_result = tools.verify_otp(identifier=pending_action["account_number"], otp_code=otp_code)
        if otp_verification_result.get("status") != "success":
            # Potentially implement retry limits for OTP here
            return {"status": "failed", "message": "OTP verification failed.", "details": otp_verification_result}

        # OTP verified, proceed with action
        action_type = pending_action["action"]
        details = pending_action["details"]
        account_number = pending_action["account_number"]

        user_mem["pending_otp_verification"] = None # Clear after use

        if action_type == "withdraw":
            return self._handle_transaction(user_id, account_number, "withdraw", details["amount"], currency=details.get("currency"), narration=details.get("narration"))
        elif action_type == "transfer":
            return self._handle_transaction(user_id, account_number, "transfer_out", details["amount"], to_account=details["to_account"], currency=details.get("currency"), narration=details.get("narration"))
        else:
            return {"status": "failed", "message": f"Unknown pending action type: {action_type}"}


    def get_balance(self, user_id: str, account_number: str) -> dict:
        """Handles balance check requests."""
        # Here, user_id might be used for logging/audit, not strictly for memory for balance check
        # No OTP usually needed for balance check itself, but platform might enforce session auth
        result = tools.get_account_balance(account_number)
        if "error" not in result:
             self._add_past_transaction(user_id, {"type": "balance_check", "account": account_number, "timestamp": datetime.utcnow().isoformat(), **result})
        return result

    def deposit_funds(self, user_id: str, account_number: str, amount: float, currency: str = config.DEFAULT_CURRENCY, narration: str = None) -> dict:
        """Handles deposit requests. Usually doesn't require OTP from depositor."""
        return self._handle_transaction(user_id, account_number, "deposit", amount, currency=currency, narration=narration)

    def get_user_transaction_history(self, user_id: str) -> list:
        user_mem = self._get_user_memory(user_id)
        return user_mem["past_transactions"]

# Example Usage (for testing the agent)
if __name__ == "__main__":
    teller_agent = TellerAgent()
    test_user = "user123"
    test_account = "ACC001"
    beneficiary_account = "ACC002"

    print("--- Teller Agent Test ---")

    # Balance Check
    print("\n1. Balance Check:")
    balance_details = teller_agent.get_balance(test_user, test_account)
    print(balance_details)

    # Deposit
    print("\n2. Deposit Funds:")
    deposit_receipt = teller_agent.deposit_funds(test_user, test_account, 5000.00, narration="Monthly savings")
    print(deposit_receipt)
    print(f"History after deposit: {teller_agent.get_user_transaction_history(test_user)[0]}")


    # Withdrawal - Step 1: Request OTP
    print("\n3. Withdrawal (Request OTP):")
    withdrawal_amount = 1000.00
    otp_req_withdraw = teller_agent.request_transaction_otp(
        user_id=test_user,
        account_number=test_account,
        action="withdraw",
        details={"amount": withdrawal_amount, "currency": "NGN", "narration": "ATM withdrawal"}
    )
    print(otp_req_withdraw)

    # Withdrawal - Step 2: Process with OTP
    if otp_req_withdraw.get("status") == "success":
        # Simulate user providing OTP (retrieve from mock store for test)
        mock_otp = tools._mock_otp_store.get(test_account)
        print(f"(Test Info: Mock OTP for {test_account} is {mock_otp})")

        print("\n4. Withdrawal (Process with correct OTP):")
        withdrawal_receipt = teller_agent.process_transaction_with_otp(test_user, mock_otp)
        print(withdrawal_receipt)
        if withdrawal_receipt.get("status") == "success":
            print(f"History after withdrawal: {teller_agent.get_user_transaction_history(test_user)[0]}")
            print(f"Daily withdrawal total for {test_user}: {teller_agent.daily_transaction_totals.get((test_user, datetime.utcnow().strftime('%Y-%m-%d')), {}).get('withdrawal')}")


    # Transfer - Step 1: Request OTP
    print("\n5. Transfer (Request OTP):")
    transfer_amount = 500.00
    otp_req_transfer = teller_agent.request_transaction_otp(
        user_id=test_user,
        account_number=test_account,
        action="transfer",
        details={"amount": transfer_amount, "to_account": beneficiary_account, "currency": "NGN", "narration": "Utility bill"}
    )
    print(otp_req_transfer)

    # Transfer - Step 2: Process with OTP
    if otp_req_transfer.get("status") == "success":
        mock_otp_transfer = tools._mock_otp_store.get(test_account)
        print(f"(Test Info: Mock OTP for {test_account} is {mock_otp_transfer})")

        print("\n6. Transfer (Process with correct OTP):")
        transfer_receipt = teller_agent.process_transaction_with_otp(test_user, mock_otp_transfer)
        print(transfer_receipt)
        if transfer_receipt.get("status") == "success":
            print(f"History after transfer: {teller_agent.get_user_transaction_history(test_user)[0]}")
            print(f"Daily transfer total for {test_user}: {teller_agent.daily_transaction_totals.get((test_user, datetime.utcnow().strftime('%Y-%m-%d')), {}).get('transfer')}")


    # Test exceeding daily withdrawal limit
    print("\n7. Withdrawal (Attempt to exceed daily limit):")
    # First, make a large withdrawal that is within per-transaction but close to daily limit
    large_withdrawal_amount = config.DAILY_WITHDRAWAL_LIMIT - withdrawal_amount - 10000 # Leave 10k headroom from previous withdrawal

    if large_withdrawal_amount > 0 and large_withdrawal_amount <= config.MAX_WITHDRAWAL_PER_TRANSACTION :
        print(f"  Making a large withdrawal of {large_withdrawal_amount} to approach daily limit...")
        otp_req_large_w = teller_agent.request_transaction_otp(test_user, test_account, "withdraw", {"amount": large_withdrawal_amount})
        if otp_req_large_w.get("status") == "success":
            mock_otp_large_w = tools._mock_otp_store.get(test_account)
            teller_agent.process_transaction_with_otp(test_user, mock_otp_large_w)
            print(f"  Daily withdrawal total for {test_user} after large withdrawal: {teller_agent.daily_transaction_totals.get((test_user, datetime.utcnow().strftime('%Y-%m-%d')), {}).get('withdrawal')}")

    # Now try to withdraw more, expecting daily limit to be hit
    otp_req_exceed_w = teller_agent.request_transaction_otp(
        user_id=test_user,
        account_number=test_account,
        action="withdraw",
        details={"amount": 20000.00} # This should exceed the limit
    )
    print(otp_req_exceed_w)
    if otp_req_exceed_w.get("status") == "success":
        mock_otp_exceed_w = tools._mock_otp_store.get(test_account)
        result_exceed_w = teller_agent.process_transaction_with_otp(test_user, mock_otp_exceed_w)
        print(result_exceed_w) # Expected to fail due to daily limit
        # Check that the daily total was not incorrectly incremented on failure
        print(f"  Daily withdrawal total for {test_user} after FAILED limit exceeding withdrawal: {teller_agent.daily_transaction_totals.get((test_user, datetime.utcnow().strftime('%Y-%m-%d')), {}).get('withdrawal')}")

    print("\nFinal Transaction History for user:")
    for entry in teller_agent.get_user_transaction_history(test_user):
        print(entry)
