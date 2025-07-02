# Pydantic schemas for Back Office Reconciliation Agent

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any, Literal
from datetime import date, datetime
import uuid

# --- Enums and Helper Models ---
DataSourceType = Literal["InternalLedger", "PaymentGatewayLog", "BankStatementFile", "NIBSSReport"]
MatchRuleCondition = Literal["ExactMatch", "ExactMatchIgnoreCase", "AmountWithinTolerance", "TimestampProximity", "CustomLogic"]
ReconciliationStatus = Literal["Pending", "Scheduled", "Running", "Completed", "Failed", "CompletedWithDiscrepancies"]

class DataSourceConfig(BaseModel):
    source_id: str = Field(default_factory=lambda: f"DS-{uuid.uuid4().hex[:6].upper()}")
    source_name: str = Field(..., example="CoreBankingLedger_NIP")
    source_type: DataSourceType = Field(..., example="InternalLedger")
    # Connection/Access details
    api_endpoint: Optional[HttpUrl] = Field(None, example="https://api.bank.com/ledger/nip/extract")
    file_path_template: Optional[str] = Field(None, example="/mnt/recon_files/nibss_nip_settlement_{YYYYMMDD}.csv")
    # auth_details: Optional[Dict[str, Any]] = Field(None, description="e.g., API key, OAuth creds") # Sensitive, handle carefully
    # data_format_details: Optional[Dict[str, Any]] = Field(None, description="e.g., CSV delimiter, JSON path to records")

class MatchingKey(BaseModel):
    internal_field_name: str = Field(..., example="transaction_reference")
    external_field_name: str = Field(..., example="nibss_session_id")

class MatchingRuleConfig(BaseModel):
    rule_id: str = Field(default_factory=lambda: f"MRULE-{uuid.uuid4().hex[:6].upper()}")
    description: str = Field(..., example="Primary match on Transaction ID/Session ID")
    primary_keys: List[MatchingKey] # Fields that MUST match for a pair to be considered initially

    # Secondary checks for matched pairs or for fuzzy matching logic
    amount_field_internal: Optional[str] = Field("amount", example="amount")
    amount_field_external: Optional[str] = Field("transaction_amount", example="transaction_amount")
    amount_tolerance_percent: Optional[float] = Field(None, ge=0, le=100, example=0.01) # e.g. 0.01%
    amount_tolerance_absolute: Optional[float] = Field(None, ge=0, example=0.50) # e.g. 50 kobo

    timestamp_field_internal: Optional[str] = Field("transaction_date", example="transaction_date")
    timestamp_field_external: Optional[str] = Field("value_date", example="value_date")
    timestamp_proximity_seconds: Optional[int] = Field(None, ge=0, example=300) # e.g., 5 minutes

    # More complex rules can be added here or identified by a 'custom_logic_id' to be handled by agent
    # custom_logic_identifier: Optional[str] = None


# --- Request Model ---
class ReconciliationTaskInput(BaseModel):
    task_id: str = Field(default_factory=lambda: f"RECTASK-{uuid.uuid4().hex[:10].upper()}")
    reconciliation_date_from: date = Field(..., example="2023-10-29")
    reconciliation_date_to: date = Field(..., example="2023-10-29") # Can be same for daily recon

    source_internal: DataSourceConfig
    source_external: DataSourceConfig

    matching_rules: List[MatchingRuleConfig] = Field(..., min_length=1)
    # auto_resolution_rules_ids: Optional[List[str]] = Field(None, example=["AR001_small_fee_diff"]) # For future agent use
    requested_by: Optional[str] = Field(None, example="FinanceOpsUser001")

    class Config:
        json_schema_extra = {
            "example": {
                "reconciliation_date_from": "2023-10-29", "reconciliation_date_to": "2023-10-29",
                "source_internal": {
                    "source_name": "CBS_Ledger_NIPOutward", "source_type": "InternalLedger",
                    "api_endpoint": "https://internal.mybank.com/api/ledger/nip?date={YYYYMMDD}"
                },
                "source_external": {
                    "source_name": "NIBSS_NIP_SettlementReport", "source_type": "NIBSSReport",
                    "file_path_template": "/sftp/nibss/reports/nip_settlement_{YYYYMMDD}.csv"
                },
                "matching_rules": [{
                    "description": "Match NIP Session ID and Amount",
                    "primary_keys": [{"internal_field_name": "nip_session_id", "external_field_name": "SessionID"}],
                    "amount_field_internal": "debit_amount", "amount_field_external": "Amount",
                    "amount_tolerance_absolute": 0.01 # 1 kobo
                }]
            }
        }

# --- Response Model ---
class ReconciliationRecord(BaseModel): # Generic structure for a transaction line item in report
    record_id_in_source: str # Unique ID within its source file/dataset (e.g., row number, internal txn id)
    source_name: str # e.g., CBS_Ledger_NIPOutward, NIBSS_NIP_SettlementReport
    key_fields: Dict[str, Any] = Field(..., description="Fields used for matching, e.g. {'nip_session_id': 'XYZ', 'amount': 1000}")
    all_fields: Dict[str, Any] # All other fields from this record

class MatchedPairDetail(BaseModel):
    internal_record: ReconciliationRecord
    external_record: ReconciliationRecord
    match_rule_id_applied: str
    match_score: Optional[float] = Field(None, example=1.0) # If scoring is used

class UnmatchedRecordDetail(BaseModel):
    source_of_unmatched: Literal["Internal", "External"]
    record: ReconciliationRecord
    reason_for_no_match: Optional[str] = Field(None, example="No corresponding record in other source based on primary keys.")
    suggested_action: Optional[str] = Field(None, example="Investigate manually. Possible timing issue or data error.")

class ReconciliationSummaryStats(BaseModel):
    total_internal_records_processed: int = 0
    total_external_records_processed: int = 0
    total_internal_value_ngn: float = 0.0 # Assuming NGN for summary, can be more complex
    total_external_value_ngn: float = 0.0

    matched_records_count: int = 0
    matched_value_ngn: float = 0.0 # Sum of matched amounts (e.g., from internal side)

    unmatched_internal_count: int = 0
    unmatched_internal_value_ngn: float = 0.0
    unmatched_external_count: int = 0
    unmatched_external_value_ngn: float = 0.0

    # auto_resolved_count: int = 0 # For future when agent does auto-resolution
    # items_for_manual_review_count: int # = unmatched_internal + unmatched_external - auto_resolved (if applicable)

class ReconciliationReportOutput(BaseModel):
    report_id: str = Field(default_factory=lambda: f"RECREP-{uuid.uuid4().hex[:10].upper()}")
    task_id: str # From ReconciliationTaskInput

    reconciliation_date_from: date
    reconciliation_date_to: date
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)

    status: ReconciliationStatus = "Pending"
    status_message: Optional[str] = "Reconciliation task is scheduled."

    summary_stats: Optional[ReconciliationSummaryStats] = None

    # For brevity in API response, these might be paginated or links to downloadable files in real system
    # For now, allow them to be optional and potentially large lists if included directly.
    matched_pairs: Optional[List[MatchedPairDetail]] = None
    unmatched_internal_items: Optional[List[UnmatchedRecordDetail]] = None
    unmatched_external_items: Optional[List[UnmatchedRecordDetail]] = None
    # auto_resolved_items: Optional[List[Any]] = None # Placeholder for auto-resolved items

    error_log: Optional[List[str]] = Field(None, description="Log of errors encountered during the reconciliation process.")

    class Config:
        json_schema_extra = {
            "example": {
                "report_id": "RECREP-XYZ123ABC", "task_id": "RECTASK-DEF456UVW",
                "reconciliation_date_from": "2023-10-29", "reconciliation_date_to": "2023-10-29",
                "generation_timestamp": "2023-10-30T18:00:00Z", "status": "CompletedWithDiscrepancies",
                "status_message": "Reconciliation complete. 2 internal and 1 external items unmatched.",
                "summary_stats": {
                    "total_internal_records_processed": 1000, "total_external_records_processed": 999,
                    "total_internal_value_ngn": 50000000.00, "total_external_value_ngn": 49985000.00,
                    "matched_records_count": 998, "matched_value_ngn": 49970000.00,
                    "unmatched_internal_count": 2, "unmatched_internal_value_ngn": 30000.00,
                    "unmatched_external_count": 1, "unmatched_external_value_ngn": 15000.00
                },
                # "unmatched_internal_items": [...] # Example list of UnmatchedRecordDetail
            }
        }

if __name__ == "__main__":
    import json
    print("--- ReconciliationTaskInput Schema ---")
    print(json.dumps(ReconciliationTaskInput.model_json_schema(), indent=2))
    print("\n--- ReconciliationReportOutput Schema ---")
    print(json.dumps(ReconciliationReportOutput.model_json_schema(), indent=2))

    # Example Instantiation
    # try:
    #     task_input_data = ReconciliationTaskInput.Config.json_schema_extra["example"]
    #     task_input = ReconciliationTaskInput(**task_input_data)
    #     print("\nValid ReconciliationTaskInput instance:\n", task_input.model_dump_json(indent=2))

    #     report_output_data = ReconciliationReportOutput.Config.json_schema_extra["example"]
    #     report_output = ReconciliationReportOutput(**report_output_data)
    #     print("\nValid ReconciliationReportOutput instance:\n", report_output.model_dump_json(indent=2))
    # except Exception as e:
    #     print("\nError during schema instantiation example:", e)
    pass
