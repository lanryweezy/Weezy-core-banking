# Tools for Teller Agent
import requests
import random
import string
from . import config

# --- Core Banking API Tools ---
def get_account_balance(account_number: str) -> dict:
    """
    Fetches account balance from the Core Banking System.
    Input: Account number.
    Output: Dictionary with balance details or error.
    """
    # Placeholder - In a real system, this would call the actual Core Banking API.
    # from weezy_cbs.accounts_ledger_management.services import get_balance
    # return get_balance(account_number)
    url = config.ACCOUNT_BALANCE_ENDPOINT.format(account_number=account_number)
    headers = {"Authorization": f"Bearer {config.WEEZY_API_KEY}"} # Example auth
    try:
        # response = requests.get(url, headers=headers)
        # response.raise_for_status()
        # return response.json()
        print(f"Mock API Call: GET {url}")
        if "unknown" in account_number:
             return {"error": "Account not found", "account_number": account_number}
        return {"account_number": account_number, "ledger_balance": 10000.00, "available_balance": 9500.00, "currency": "NGN"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": f"Failed to fetch balance for {account_number}"}

def execute_transfer(from_account: str, to_account: str, amount: float, currency: str = "NGN", narration: str = None) -> dict:
    """
    Executes a fund transfer using the Core Banking System.
    Input: from_account, to_account, amount, currency, narration.
    Output: Dictionary with transaction status or error.
    """
    # Placeholder - In a real system, this would call the actual Core Banking API.
    # from weezy_cbs.transaction_management.services import process_transfer
    # return process_transfer(from_account, to_account, amount, currency, narration)
    url = config.ACCOUNT_TRANSFER_ENDPOINT
    payload = {
        "from_account": from_account,
        "to_account": to_account,
        "amount": amount,
        "currency": currency,
        "narration": narration or f"Transfer from {from_account} to {to_account}"
    }
    headers = {"Authorization": f"Bearer {config.WEEZY_API_KEY}"} # Example auth
    try:
        # response = requests.post(url, json=payload, headers=headers)
        # response.raise_for_status()
        # return response.json()
        print(f"Mock API Call: POST {url} with payload {payload}")
        if amount > 9000: # Simulate insufficient funds for testing
            return {"status": "failed", "message": "Insufficient funds", "transaction_id": None}
        return {"status": "success", "message": "Transfer successful", "transaction_id": "TRN" + "".join(random.choices(string.digits, k=10))}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": "Failed to execute transfer"}

def execute_deposit(account_number: str, amount: float, currency: str = "NGN", narration: str = None) -> dict:
    """
    Processes a deposit into an account via the Core Banking System.
    """
    url = config.ACCOUNT_DEPOSIT_ENDPOINT
    payload = {
        "account_number": account_number,
        "amount": amount,
        "currency": currency,
        "narration": narration or f"Cash deposit to {account_number}"
    }
    headers = {"Authorization": f"Bearer {config.WEEZY_API_KEY}"}
    try:
        # response = requests.post(url, json=payload, headers=headers)
        # response.raise_for_status()
        # return response.json()
        print(f"Mock API Call: POST {url} with payload {payload}")
        return {"status": "success", "message": "Deposit successful", "transaction_id": "DEP" + "".join(random.choices(string.digits, k=10)), "new_balance": 10000 + amount}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": f"Failed to process deposit for {account_number}"}

def execute_withdrawal(account_number: str, amount: float, currency: str = "NGN", narration: str = None) -> dict:
    """
    Processes a withdrawal from an account via the Core Banking System.
    """
    url = config.ACCOUNT_WITHDRAW_ENDPOINT
    payload = {
        "account_number": account_number,
        "amount": amount,
        "currency": currency,
        "narration": narration or f"Cash withdrawal from {account_number}"
    }
    headers = {"Authorization": f"Bearer {config.WEEZY_API_KEY}"}
    try:
        # response = requests.post(url, json=payload, headers=headers)
        # response.raise_for_status()
        # return response.json()
        print(f"Mock API Call: POST {url} with payload {payload}")
        if amount > 9500: # Simulate insufficient funds for testing (based on mock balance)
            return {"status": "failed", "message": "Insufficient available balance for withdrawal", "transaction_id": None}
        return {"status": "success", "message": "Withdrawal successful", "transaction_id": "WDL" + "".join(random.choices(string.digits, k=10)), "new_balance": 9500 - amount}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": f"Failed to process withdrawal for {account_number}"}


# --- OTP Service Tools ---
_mock_otp_store = {} # Simple in-memory store for mock OTPs

def request_otp(identifier: str) -> dict:
    """
    Requests an OTP for a given identifier (e.g., account number, phone number).
    Input: Identifier string.
    Output: Dictionary with OTP request status.
    """
    url = config.OTP_REQUEST_ENDPOINT
    payload = {"identifier": identifier}
    # In a real system:
    # headers = {"X-API-Key": config.OTP_SERVICE_API_KEY}
    # response = requests.post(url, json=payload, headers=headers)
    # response.raise_for_status()
    # return response.json()

    # Mock implementation:
    otp_code = "".join(random.choices(string.digits, k=6))
    _mock_otp_store[identifier] = otp_code # Store OTP for verification
    print(f"Mock OTP Service: Requested OTP for {identifier}. OTP is {otp_code} (for testing only)")
    return {"status": "success", "message": f"OTP sent to identifier linked with {identifier}."}


def verify_otp(identifier: str, otp_code: str) -> dict:
    """
    Verifies an OTP for a given identifier.
    Input: Identifier string, OTP code string.
    Output: Dictionary with OTP verification status.
    """
    url = config.OTP_VERIFY_ENDPOINT
    payload = {"identifier": identifier, "otp": otp_code}
    # In a real system:
    # headers = {"X-API-Key": config.OTP_SERVICE_API_KEY}
    # response = requests.post(url, json=payload, headers=headers)
    # response.raise_for_status()
    # return response.json()

    # Mock implementation:
    if _mock_otp_store.get(identifier) == otp_code:
        # Remove OTP after successful verification for one-time use
        _mock_otp_store.pop(identifier, None)
        print(f"Mock OTP Service: OTP {otp_code} verified successfully for {identifier}.")
        return {"status": "success", "message": "OTP verified successfully."}
    else:
        print(f"Mock OTP Service: OTP {otp_code} verification failed for {identifier}.")
        return {"status": "failed", "message": "Invalid OTP or OTP expired."}


if __name__ == '__main__':
    # Example usage (for testing tools individually)
    test_account_num = "1234567890"
    test_beneficiary_account_num = "0987654321"

    print("--- Testing Core Banking Tools ---")
    print("Balance Check:")
    balance_info = get_account_balance(test_account_num)
    print(balance_info)

    print("\nBalance Check (Unknown Account):")
    balance_info_unknown = get_account_balance("unknown_account")
    print(balance_info_unknown)

    print("\nDeposit:")
    deposit_result = execute_deposit(test_account_num, 500.00)
    print(deposit_result)

    print("\nWithdrawal (Sufficient Funds):")
    withdrawal_result = execute_withdrawal(test_account_num, 200.00)
    print(withdrawal_result)

    print("\nWithdrawal (Insufficient Funds):")
    withdrawal_result_insufficient = execute_withdrawal(test_account_num, 10000.00) # Based on mock available balance
    print(withdrawal_result_insufficient)

    print("\nTransfer (Sufficient Funds):")
    transfer_result = execute_transfer(test_account_num, test_beneficiary_account_num, 100.00)
    print(transfer_result)

    print("\nTransfer (Insufficient Funds):")
    transfer_result_insufficient = execute_transfer(test_account_num, test_beneficiary_account_num, 10000.00) # Based on mock general balance
    print(transfer_result_insufficient)

    print("\n--- Testing OTP Tools ---")
    otp_identifier = test_account_num # Could be phone number, etc.
    print(f"Requesting OTP for {otp_identifier}...")
    otp_req_status = request_otp(otp_identifier)
    print(otp_req_status)

    if otp_req_status.get("status") == "success":
        # In a real scenario, the user would provide this OTP
        # For testing, we use the one printed to console by the mock service
        test_otp_correct = _mock_otp_store.get(otp_identifier) # Peek at the mock OTP
        test_otp_incorrect = "000000"

        print(f"\nVerifying correct OTP ({test_otp_correct})...")
        verify_status_correct = verify_otp(otp_identifier, test_otp_correct)
        print(verify_status_correct)

        # Request again for the incorrect OTP test, as the previous one is consumed
        request_otp(otp_identifier)
        test_otp_correct_again = _mock_otp_store.get(otp_identifier)


        print(f"\nVerifying incorrect OTP ({test_otp_incorrect}) when correct is ({test_otp_correct_again})...")
        verify_status_incorrect = verify_otp(otp_identifier, test_otp_incorrect)
        print(verify_status_incorrect)

        # Test verifying again with the correct OTP (should fail if OTPs are one-time)
        print(f"\nVerifying correct OTP ({test_otp_correct_again}) again (should fail if consumed)...")
        verify_status_consumed = verify_otp(otp_identifier, test_otp_correct_again) # This should fail if OTPs are one-time
        print(verify_status_consumed) # Expected: failed because it was consumed by the previous successful check.

        if not _mock_otp_store.get(otp_identifier):
            print("OTP successfully consumed as expected.")
        else:
            print(f"OTP {test_otp_correct_again} for {otp_identifier} was not consumed from store, check logic.")
