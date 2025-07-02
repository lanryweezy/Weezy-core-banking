# Pydantic schemas for Fraud Detection Agent

from pydantic import BaseModel, Field, HttpUrl, EmailStr, IPvAnyAddress
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import uuid

# --- Enums and Helper Models ---
RiskLevel = Literal["Low", "Medium", "High", "Critical"]
FraudActionRecommended = Literal["Allow", "FlagForReview", "ChallengeOTP", "BlockTransaction", "SuspendAccount"]
TransactionChannel = Literal["MobileApp", "WebApp", "USSD", "POS", "ATM", "BranchTeller", "ThirdPartyAPI"]

class DeviceInformation(BaseModel):
    device_id: Optional[str] = Field(None, example="DEVICE_XYZ123ABC")
    ip_address: Optional[IPvAnyAddress] = Field(None, example="198.51.100.10")
    user_agent: Optional[str] = Field(None, example="Mozilla/5.0 (Linux; Android 11; SM-A205U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.58 Mobile Safari/537.36")
    # fingerprintjs_id: Optional[str] = Field(None, example="fp_abc123xyz") # Example of a more advanced fingerprint

class Geolocation(BaseModel):
    latitude: Optional[float] = Field(None, example=6.5244)  # Lagos
    longitude: Optional[float] = Field(None, example=3.3792)
    city: Optional[str] = Field(None, example="Lagos")
    country_code: Optional[str] = Field(None, example="NG")

# --- Request Model (Input to the Fraud Detection System) ---
class TransactionEventInput(BaseModel):
    event_id: str = Field(default_factory=lambda: f"FRDEVT-{uuid.uuid4().hex[:12].upper()}")
    transaction_id: str = Field(..., example="TRN-BANK-001234567") # The bank's unique transaction ID
    timestamp: datetime = Field(default_factory=datetime.utcnow, example="2023-10-30T10:20:30Z")

    customer_id: Optional[str] = Field(None, example="CUST-00789")
    account_number: Optional[str] = Field(None, example="0123456789")

    transaction_type: str = Field(..., example="NIPTransferOut") # e.g., CardPayment, ATMWithdrawal, BillPayment, LoginAttempt
    amount: float = Field(..., ge=0, example=75000.00)
    currency: str = Field(..., example="NGN")

    channel: Optional[TransactionChannel] = Field(None, example="MobileApp")

    # Beneficiary/Counterparty details (if applicable)
    counterparty_account_number: Optional[str] = Field(None, example="9876543210")
    counterparty_bank_code: Optional[str] = Field(None, example="058") # CBN Bank Code
    counterparty_name: Optional[str] = Field(None, example="Acme Corp Supplies")

    # Contextual Information
    device_info: Optional[DeviceInformation] = None
    geolocation_info: Optional[Geolocation] = None

    # Additional metadata specific to the transaction type or channel
    metadata: Optional[Dict[str, Any]] = Field(None, example={"merchant_category_code": "5411", "is_first_time_beneficiary": True})

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TRN-XYZ-20231030-001",
                "customer_id": "CUST-SAFE-001", "account_number": "1010101010",
                "transaction_type": "NIPTransferOut", "amount": 50000.00, "currency": "NGN", "channel": "MobileApp",
                "counterparty_account_number": "2020202020", "counterparty_bank_code": "044", "counterparty_name": "Risky Biz Ltd",
                "device_info": {"device_id": "DEV_MOB_001", "ip_address": "102.89.23.10", "user_agent": "MyBankApp v3.2 Android 12"},
                "geolocation_info": {"latitude": 9.0820, "longitude": 8.6753, "city": "Abuja", "country_code": "NG"},
                "metadata": {"is_new_device_for_customer": False, "beneficiary_added_recently": True}
            }
        }

# --- Response Model (Output from the Fraud Detection System) ---
class FraudRuleMatch(BaseModel):
    rule_id: str = Field(..., example="RULE_HIGH_VALUE_NEW_BEN")
    rule_name: str = Field(..., example="High Value Transfer to New Beneficiary")
    score_impact: Optional[float] = Field(None, example=30.0, description="Points added/subtracted by this rule")
    description: Optional[str] = Field(None, example="Transaction amount exceeds NGN 200,000 to a beneficiary added in last 24 hours.")

class FraudAnalysisOutput(BaseModel):
    event_id: str # Corresponds to the input event_id
    analysis_id: str = Field(default_factory=lambda: f"FRDANL-{uuid.uuid4().hex[:12].upper()}")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)

    fraud_score: Optional[float] = Field(None, ge=0, le=100, example=75.5, description="Overall fraud score (0-100, higher is riskier)")
    risk_level: Optional[RiskLevel] = Field(None, example="High")

    triggered_rules: Optional[List[FraudRuleMatch]] = Field(None)
    anomaly_details: Optional[List[str]] = Field(None, example=["Unusual login location for this customer.", "Transaction amount significantly higher than average."])

    recommended_action: Optional[FraudActionRecommended] = Field(None, example="BlockTransaction")
    reason_for_action: Optional[str] = Field(None, example="High fraud score due to multiple risky indicators.")

    # For cases where analysis is pending or couldn't be completed
    status: Literal["Completed", "PendingAnalysis", "FailedToAnalyze"] = "PendingAnalysis"

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "FRDEVT-ABC123XYZ", "analysis_id": "FRDANL-DEF456UVW",
                "analysis_timestamp": "2023-10-30T10:21:00Z",
                "fraud_score": 85.0, "risk_level": "Critical",
                "triggered_rules": [
                    {"rule_id": "VELOCITY_001", "rule_name": "High Transaction Velocity", "score_impact": 40.0},
                    {"rule_id": "LOCATION_003", "rule_name": "Transaction from High-Risk IP Geolocation", "score_impact": 25.0}
                ],
                "anomaly_details": ["Transaction originated from a TOR exit node.", "Customer's account rarely performs transactions of this magnitude."],
                "recommended_action": "BlockTransaction",
                "reason_for_action": "Critical risk score due to high velocity and high-risk geolocation.",
                "status": "Completed"
            }
        }

if __name__ == "__main__":
    import json
    print("--- TransactionEventInput Schema ---")
    print(json.dumps(TransactionEventInput.model_json_schema(), indent=2))
    print("\n--- FraudAnalysisOutput Schema ---")
    print(json.dumps(FraudAnalysisOutput.model_json_schema(), indent=2))

    # Example instantiation
    # try:
    #     event_data = TransactionEventInput.Config.json_schema_extra["example"]
    #     event_input = TransactionEventInput(**event_data)
    #     print("\nValid TransactionEventInput instance:\n", event_input.model_dump_json(indent=2))

    #     analysis_data = FraudAnalysisOutput.Config.json_schema_extra["example"]
    #     analysis_output = FraudAnalysisOutput(**analysis_data)
    #     print("\nValid FraudAnalysisOutput instance:\n", analysis_output.model_dump_json(indent=2))
    # except Exception as e:
    #     print("\nError during schema instantiation example:", e)
    pass
