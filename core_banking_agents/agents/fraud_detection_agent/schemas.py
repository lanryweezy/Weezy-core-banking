# Pydantic schemas for Fraud Detection Agent

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime

class TransactionEvent(BaseModel):
    transaction_id: str = Field(..., example="TXN20231027ABC001")
    customer_id: Optional[str] = Field(None, example="CUST12345")
    account_id: Optional[str] = Field(None, example="ACC098765")
    amount: float = Field(..., example=150000.75)
    currency: str = Field(..., example="NGN")
    timestamp: datetime = Field(..., example=datetime.now())
    transaction_type: str = Field(..., example="NIP_Transfer") # e.g., CardPayment, ATMWithdrawal, BillPayment
    merchant_id: Optional[str] = Field(None, example="MERCH007")
    recipient_account: Optional[str] = Field(None, example="0123456789")
    recipient_bank: Optional[str] = Field(None, example="GTB")
    device_id: Optional[str] = Field(None, example="DEVICE_XYZ123")
    ip_address: Optional[str] = Field(None, example="192.168.1.100")
    user_agent: Optional[str] = Field(None, example="Mozilla/5.0 ...")
    location_lat: Optional[float] = Field(None, example=6.5244) # Lagos
    location_lon: Optional[float] = Field(None, example=3.3792)
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Other relevant transaction details")

class FraudScoreComponents(BaseModel):
    pattern_match_score: Optional[float] = Field(None, example=0.2)
    ml_anomaly_score: Optional[float] = Field(None, example=0.7)
    rules_engine_score: Optional[float] = Field(None, example=0.9)
    velocity_check_failed: Optional[bool] = Field(None, example=True)
    blacklist_hit: Optional[bool] = Field(None, example=False)

class FraudAlert(BaseModel):
    transaction_id: str
    is_fraudulent: bool = Field(..., example=True)
    fraud_score: float = Field(..., ge=0, le=1, example=0.95)
    status: str = Field(..., example="ActionRequired") # e.g., Clear, Suspicious, ActionRequired, Blocked
    reason: Optional[str] = Field(None, example="High anomaly score and unusual location.")
    rules_triggered: Optional[List[str]] = Field(None, example=["HighValueUnusualLocation", "NewDevice"])
    recommended_action: Optional[str] = Field(None, example="Block transaction and notify customer.")
    alert_timestamp: datetime = Field(default_factory=datetime.now)
    score_components: Optional[FraudScoreComponents] = None

# For updating rules (example)
class FraudRule(BaseModel):
    rule_id: str = Field(..., example="RULE001_HIGH_VALUE")
    description: str = Field(..., example="Flag transactions over 1,000,000 NGN to new beneficiaries.")
    condition: str = Field(..., example="amount > 1000000 and is_new_beneficiary == True") # Simplified rule syntax
    action: str = Field(..., example="FLAG_FOR_REVIEW") # FLAG_FOR_REVIEW, BLOCK_TRANSACTION
    priority: int = Field(1, example=1) # Higher number means higher priority
    is_active: bool = True

print("Fraud Detection Agent Pydantic schemas placeholder.")
