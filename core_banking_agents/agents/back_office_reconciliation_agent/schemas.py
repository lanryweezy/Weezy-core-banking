# Pydantic schemas for Back Office Reconciliation Agent

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

class DataSource(BaseModel):
    source_type: str = Field(..., example="internal") # internal, external (e.g. Paystack, Interswitch, NIBSS)
    source_name: str = Field(..., example="CoreLedgerNIP")
    api_endpoint: Optional[str] = Field(None, example="http://cbs-internal/api/nip_ledger")
    file_path_template: Optional[str] = Field(None, example="/mnt/recon_files/nibss_nip_{date}.csv")

class MatchingRule(BaseModel):
    rule_id: str = Field(..., example="MR001")
    description: str = Field(..., example="Match Transaction ID and Amount within tolerance")
    internal_field: str = Field(..., example="internal_txn_ref")
    external_field: str = Field(..., example="processor_txn_id")
    match_type: str = Field(..., example="exact_match") # exact_match, fuzzy_match, range_match, amount_tolerance
    tolerance: Optional[float] = Field(None, example=0.01) # For amount_tolerance
    weight: Optional[float] = Field(None, example=1.0) # For weighted matching scores

class ReconciliationTaskInput(BaseModel):
    task_id: Optional[str] = Field(None, example="RECON20231027NIP01") # Can be auto-generated
    reconciliation_date: date = Field(..., example="2023-10-26")
    internal_source: DataSource
    external_source: DataSource
    matching_rules: List[MatchingRule]
    auto_resolution_rules_ids: Optional[List[str]] = Field(None, example=["AR001_small_fee_diff"])

class TransactionRecord(BaseModel): # Generic structure for a transaction line item
    record_id: str # Unique ID within its source file/dataset
    transaction_reference: Optional[str] = None
    amount: float
    timestamp: datetime
    description: Optional[str] = None
    is_debit: Optional[bool] = None # True for debit, False for credit
    additional_fields: Dict[str, Any] = {}

class MatchedPair(BaseModel):
    internal_record: TransactionRecord
    external_record: TransactionRecord
    match_score: Optional[float] = Field(None, example=0.98)
    match_rule_id: Optional[str] = None

class UnmatchedRecord(BaseModel):
    source_name: str
    record: TransactionRecord
    reason_for_no_match: Optional[str] = Field(None, example="No corresponding record in other source")

class AutoResolvedItem(BaseModel):
    original_discrepancy: Any # Could be an unmatched record or a pair with differences
    resolution_rule_id: str
    resolution_details: str
    resolved_internal_record: Optional[TransactionRecord] = None
    resolved_external_record: Optional[TransactionRecord] = None

class ReconciliationSummary(BaseModel):
    total_internal_records: int
    total_external_records: int
    total_internal_value: float
    total_external_value: float
    matched_records_count: int
    matched_value: float
    unmatched_internal_count: int
    unmatched_internal_value: float
    unmatched_external_count: int
    unmatched_external_value: float
    auto_resolved_count: int
    items_for_manual_review_count: int

class ReconciliationReportOutput(BaseModel):
    report_id: str = Field(..., example="RECREP20231027NIP01")
    task_id: str
    reconciliation_date: date
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    status: str = Field(..., example="Completed") # Pending, Running, Completed, Failed
    summary: ReconciliationSummary
    matched_pairs: Optional[List[MatchedPair]] = Field(None) # Might be too large for direct output, link to file/DB instead
    unmatched_internal_items: Optional[List[UnmatchedRecord]] = Field(None)
    unmatched_external_items: Optional[List[UnmatchedRecord]] = Field(None)
    auto_resolved_items: Optional[List[AutoResolvedItem]] = Field(None)
    items_for_manual_review: Optional[List[Any]] = Field(None) # Could be UnmatchedRecord or MatchedPair with issues
    error_log: Optional[List[str]] = Field(None)

print("Back Office Reconciliation Agent Pydantic schemas placeholder.")
