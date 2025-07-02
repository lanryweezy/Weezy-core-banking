# Configuration for Teller Agent

WEEZY_API_KEY = "dd8e9064465a8311.UF1vXkGPNWCb8jQ4NFybk0VxV7eXIIKLUEyhumSJISre" # General API Key, if needed

# Core Banking API endpoints (examples, replace with actual)
CORE_BANKING_API_BASE_URL = "http://localhost:8000/api/v1/core" # Assuming FastAPI app for core modules
ACCOUNT_BALANCE_ENDPOINT = f"{CORE_BANKING_API_BASE_URL}/accounts/{{account_number}}/balance"
ACCOUNT_TRANSFER_ENDPOINT = f"{CORE_BANKING_API_BASE_URL}/transactions/transfer"
ACCOUNT_DEPOSIT_ENDPOINT = f"{CORE_BANKING_API_BASE_URL}/transactions/deposit"
ACCOUNT_WITHDRAW_ENDPOINT = f"{CORE_BANKING_API_BASE_URL}/transactions/withdraw"

# OTP Service configuration (example)
OTP_SERVICE_URL = "http://localhost:5002/otp" # Example OTP microservice
OTP_VERIFY_ENDPOINT = f"{OTP_SERVICE_URL}/verify"
OTP_REQUEST_ENDPOINT = f"{OTP_SERVICE_URL}/request"

# Transaction limits (examples)
MAX_WITHDRAWAL_PER_TRANSACTION = 150000  # Naira
MAX_TRANSFER_PER_TRANSACTION = 500000    # Naira
DAILY_WITHDRAWAL_LIMIT = 500000          # Naira
DAILY_TRANSFER_LIMIT = 1000000           # Naira

# Teller Agent specific settings
DEFAULT_CURRENCY = "NGN"
