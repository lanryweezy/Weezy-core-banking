# Tools for Back Office Reconciliation Agent

from langchain.tools import tool
from pydantic import HttpUrl # For type hinting if URLs are passed directly
from typing import Dict, Any, List, Optional, Literal
import random
import logging
import pandas as pd # Useful for data comparison, even in mocks
from datetime import date, datetime, timedelta

# Assuming schemas might be imported for type hinting complex inputs (DataSourceConfig, MatchingRuleConfig)
# from .schemas import DataSourceConfig, MatchingRuleConfig # For this mock, tools take Dicts

logger = logging.getLogger(__name__)

# --- Helper to Generate Mock Transaction Data ---
def _generate_mock_recon_data(source_name: str, recon_date: date, num_records: int, id_prefix: str, amount_range: tuple =(100, 100000)) -> List[Dict[str, Any]]:
    """Generates a list of mock transaction records for reconciliation."""
    records = []
    for i in range(num_records):
        txn_id_val = f"{id_prefix}-{recon_date.strftime('%Y%m%d')}-{i:04d}"
        amount_val = round(random.uniform(amount_range[0], amount_range[1]), 2)
        # Simulate slight variations in timestamps around the recon_date
        base_datetime = datetime.combine(recon_date, datetime.min.time()) + timedelta(hours=random.randint(0,23), minutes=random.randint(0,59))

        record = {
            "record_id_in_source": str(uuid.uuid4()), # Unique ID for this specific record in this source
            "source_name": source_name,
            # Key fields that might be used for matching
            "transaction_id": txn_id_val, # Primary matching key
            "amount": amount_val,
            "value_date": base_datetime.isoformat(),
            "description": f"Mock transaction {i} from {source_name}",
            # Other potential fields
            "currency": "NGN",
            "channel": random.choice(["API", "File", "System"]),
            "customer_ref": f"CUST{random.randint(1000,9999)}",
        }
        # Introduce slight variations for external source for testing matching logic
        if "external" in source_name.lower() or "nibss" in source_name.lower():
            record["amount"] = round(amount_val * random.uniform(0.999, 1.001), 2) # Slight amount diff
            record["value_date"] = (base_datetime + timedelta(seconds=random.randint(-60, 60))).isoformat() # Slight time diff
            # External might have different field names for the same concept
            record["external_session_id"] = record.pop("transaction_id") # Rename key
            record["transaction_amount"] = record.pop("amount")
            record["posting_date"] = record.pop("value_date")

        records.append(record)
    return records


@tool("DataExtractionTool")
def data_extraction_tool(data_source_config: Dict[str, Any], reconciliation_date_str: str) -> Dict[str, Any]:
    """
    Simulates extracting data from a specified data source (internal or external) for a given date.
    In a real system, this would connect to databases, call APIs, or read files (SFTP, local).

    Args:
        data_source_config (Dict[str, Any]): Configuration for the data source,
                                             mimicking DataSourceConfig schema.
                                             Expected keys: 'source_name', 'source_type',
                                             'api_endpoint' (optional), 'file_path_template' (optional).
        reconciliation_date_str (str): The date for which to extract data (YYYY-MM-DD).

    Returns:
        Dict[str, Any]: Contains 'status' ("Success", "Error"),
                        'data' (List of transaction record dictionaries),
                        'records_count', and 'message' (if error).
    """
    source_name = data_source_config.get("source_name", "UnknownSource")
    source_type = data_source_config.get("source_type", "UnknownType")
    logger.info(f"DataExtractionTool: Extracting data for '{source_name}' (Type: {source_type}) for date {reconciliation_date_str}")

    try:
        recon_date = date.fromisoformat(reconciliation_date_str)
    except ValueError:
        return {"status": "Error", "message": f"Invalid date format for reconciliation_date_str: {reconciliation_date_str}. Use YYYY-MM-DD."}

    if "error_source" in source_name.lower():
        return {"status": "Error", "message": f"Simulated error connecting to data source '{source_name}'.", "data": [], "records_count": 0}

    # Simulate data generation
    num_records = random.randint(950, 1050) # Generate a variable number of records
    id_prefix = "INT" if "internal" in source_name.lower() or "ledger" in source_name.lower() else "EXT"

    mock_data = _generate_mock_recon_data(source_name, recon_date, num_records, id_prefix)

    # Simulate some records missing from one source, or extra in another
    if "external" in source_name.lower() and random.random() < 0.1: # 10% chance external has fewer
        mock_data = mock_data[:-random.randint(1,5)]
    elif "internal" in source_name.lower() and random.random() < 0.05: # 5% chance internal has fewer
        mock_data = mock_data[:-random.randint(1,3)]


    logger.info(f"DataExtractionTool: Successfully extracted {len(mock_data)} records for '{source_name}'.")
    return {"status": "Success", "data": mock_data, "records_count": len(mock_data), "message": "Data extracted successfully."}


@tool("DataComparisonTool")
def data_comparison_tool(
    internal_data: List[Dict[str, Any]],
    external_data: List[Dict[str, Any]],
    matching_rules: List[Dict[str, Any]] # List of dicts mimicking MatchingRuleConfig
) -> Dict[str, Any]:
    """
    Simulates comparing two datasets (internal and external transactions) based on matching rules.
    Uses Pandas DataFrames for efficient comparison in this mock.

    Args:
        internal_data (List[Dict[str, Any]]): List of internal transaction records.
        external_data (List[Dict[str, Any]]): List of external transaction records.
        matching_rules (List[Dict[str, Any]]): Configuration for matching.
                                              Focuses on 'primary_keys' (list of MatchingKey dicts)
                                              and amount/timestamp tolerance for this mock.

    Returns:
        Dict[str, Any]: Contains 'matched_pairs', 'unmatched_internal', 'unmatched_external',
                        and 'summary_stats' (counts and values).
    """
    logger.info(f"DataComparisonTool: Comparing {len(internal_data)} internal records with {len(external_data)} external records.")
    if not internal_data and not external_data:
        return {"status": "Warning", "message": "Both internal and external datasets are empty.",
                "matched_pairs": [], "unmatched_internal": [], "unmatched_external": [],
                "summary_stats": {"internal_total":0, "external_total":0, "matched_count":0}}

    df_internal = pd.DataFrame(internal_data)
    df_external = pd.DataFrame(external_data)

    # --- Mock matching logic ---
    # For simplicity, assume the first rule's primary_keys are the main ones.
    # A real tool would iterate through rules or apply more complex logic.
    primary_match_keys_config = matching_rules[0].get("primary_keys", []) if matching_rules else []

    if not primary_match_keys_config:
        logger.error("DataComparisonTool: No primary matching keys provided in rules.")
        return {"status": "Error", "message": "Primary matching keys are required.", "matched_pairs": [], "unmatched_internal": internal_data, "unmatched_external": external_data, "summary_stats": {}}

    # Prepare for merge: rename external columns to match internal ones based on primary_keys config
    # Example: if internal key is 'transaction_id' and external is 'external_session_id'
    rename_map = {pk['external_field_name']: pk['internal_field_name'] for pk in primary_match_keys_config if pk['external_field_name'] in df_external.columns}
    df_external_renamed = df_external.rename(columns=rename_map)

    merge_on_keys = [pk['internal_field_name'] for pk in primary_match_keys_config]

    # Perform outer join to find all matches and mismatches on primary keys
    merged_df = pd.merge(df_internal, df_external_renamed, on=merge_on_keys, how='outer', suffixes=('_internal', '_external'), indicator=True)

    # --- Identify Matched and Unmatched based on merge indicator ---
    # Matched on primary keys: _merge == 'both'
    # Only in internal: _merge == 'left_only'
    # Only in external: _merge == 'right_only'

    # Further refine "matched_on_keys" by applying amount/timestamp tolerances if configured
    # For this mock, we'll assume primary key match is enough for "matched_pairs" if no secondary checks defined or passed.
    # A real tool would have more sophisticated logic here.

    # Example: Get amount tolerance from the first rule (simplified)
    rule_config = matching_rules[0] if matching_rules else {}
    amount_tol_abs = rule_config.get("amount_tolerance_absolute", 0.01) # Default 1 kobo
    # These field names should be AFTER renaming external df for merge, so they would be like 'amount_internal', 'amount_external' if suffixes were applied on all columns
    # However, merge only adds suffixes to non-key columns that clash. Key columns used in 'on' do not get suffix.
    # So, we need to map original field names for amount.
    internal_amt_col = rule_config.get("amount_field_internal", "amount") # Default if not in rule
    external_amt_col_original = rule_config.get("amount_field_external", "transaction_amount") # Original name
    # If external_amt_col_original was renamed for merge (e.g. if it was also 'amount'), it would now be 'amount_external'
    # If it wasn't a merge key and didn't clash, it's still external_amt_col_original.
    # For simplicity, assuming merge suffixes are applied to amount fields if they clash.
    # If not, the tool would need to know the exact column names post-merge.

    # Let's assume 'amount_internal' and 'amount_external' are the columns after merge for amount.
    # This means they were not part of merge_on_keys and had same original name, or were explicitly named.
    # This part is tricky without knowing exact structure of incoming data vs rules.
    # For the mock _generate_mock_recon_data, internal has 'amount', external has 'transaction_amount'.
    # If rule says internal_field 'amount' and external_field 'transaction_amount', after renaming for merge
    # (if 'transaction_amount' was renamed to 'amount' for merge key), then merged_df would have 'amount_internal', 'amount_external'.
    # If 'amount' was NOT a merge key, then merged_df would have 'amount' (from internal) and 'transaction_amount' (from external).

    # Simplified secondary check:
    # For records matched on keys, check amount.
    # This mock assumes 'amount_internal' and 'amount_external' exist after merge if amounts need checking.
    # This requires that amount fields were not part of the merge_on_keys and had the same name or were handled by suffixes.
    # A more robust way is to use the original field names provided in the rule and access them from the _internal and _external suffixed columns.
    # For this mock, we'll assume the columns are `amount_internal` and `amount_external` if they were not merge keys.
    # If they *were* merge keys, the merge itself would have handled exact match.

    # This section is complex due to dynamic column names. A real tool would be more robust.
    # For now, let's assume if amount fields are to be compared, they are available with suffixes.
    # This mock will be simplified: items with _merge == 'both' are considered matched for now.
    # True reconciliation would iterate, apply tolerances, etc.

    matched_df_records = merged_df[merged_df['_merge'] == 'both'].drop(columns=['_merge']).to_dict(orient='records')
    unmatched_internal_records = merged_df[merged_df['_merge'] == 'left_only'].drop(columns=['_merge']).to_dict(orient='records')
    unmatched_external_records = merged_df[merged_df['_merge'] == 'right_only'].drop(columns=['_merge']).to_dict(orient='records')

    # Prepare summary (simplified values)
    summary = {
        "internal_total_records": len(df_internal),
        "external_total_records": len(df_external),
        "internal_total_value": df_internal[internal_amt_col].sum() if internal_amt_col in df_internal.columns and not df_internal.empty else 0,
        "external_total_value": df_external[external_amt_col_original].sum() if external_amt_col_original in df_external.columns and not df_external.empty else 0,
        "matched_count": len(matched_df_records),
        "unmatched_internal_count": len(unmatched_internal_records),
        "unmatched_external_count": len(unmatched_external_records),
    }

    logger.info(f"DataComparisonTool: Comparison complete. Matched: {summary['matched_count']}, Unmatched Internal: {summary['unmatched_internal_count']}, Unmatched External: {summary['unmatched_external_count']}")
    return {
        "status": "Success",
        "matched_pairs": matched_df_records,
        "unmatched_internal": unmatched_internal_records,
        "unmatched_external": unmatched_external_records,
        "summary_stats": summary
    }


@tool("DiscrepancyReportingTool")
def discrepancy_reporting_tool(
    unmatched_internal: List[Dict[str, Any]],
    unmatched_external: List[Dict[str, Any]],
    comparison_summary: Dict[str, Any] # From DataComparisonTool
) -> Dict[str, Any]:
    """
    Formats identified discrepancies and comparison summary for the final reconciliation report.

    Args:
        unmatched_internal (List[Dict[str, Any]]): List of unmatched internal records.
        unmatched_external (List[Dict[str, Any]]): List of unmatched external records.
        comparison_summary (Dict[str, Any]): Summary statistics from the comparison.

    Returns:
        Dict[str, Any]: Contains 'report_sections' (formatted discrepancies and summary).
    """
    logger.info(f"DiscrepancyReportingTool: Formatting discrepancies. Unmatched Internal: {len(unmatched_internal)}, External: {len(unmatched_external)}")

    report_sections = {
        "summary_message": (
            f"Reconciliation Summary: "
            f"Internal Records: {comparison_summary.get('internal_total_records',0)} (Value: {comparison_summary.get('internal_total_value',0):.2f}), "
            f"External Records: {comparison_summary.get('external_total_records',0)} (Value: {comparison_summary.get('external_total_value',0):.2f}). "
            f"Matched: {comparison_summary.get('matched_count',0)}. "
            f"Unmatched Internal: {comparison_summary.get('unmatched_internal_count',0)}, "
            f"Unmatched External: {comparison_summary.get('unmatched_external_count',0)}."
        ),
        "detailed_unmatched_internal": unmatched_internal[:10], # Show first 10 for brevity in mock
        "detailed_unmatched_external": unmatched_external[:10], # Show first 10
        "notes": "Full unmatched lists available in detailed logs/files (simulated)." if (len(unmatched_internal)>10 or len(unmatched_external)>10) else None
    }
    if not unmatched_internal and not unmatched_external and comparison_summary.get('matched_count',0)>0 :
         report_sections["summary_message"] = f"Reconciliation Successful! All {comparison_summary.get('matched_count',0)} records matched. " + report_sections["summary_message"]


    return {"status": "Success", "report_sections": report_sections}


if __name__ == "__main__":
    import uuid # For record_id_in_source in _generate_mock_recon_data
    logging.basicConfig(level=logging.INFO)
    print("--- Testing BackOfficeReconciliationAgent Tools ---")

    test_date_str = "2023-10-30"
    test_date_obj = date.fromisoformat(test_date_str)

    # 1. Test DataExtractionTool
    print("\n1. Testing DataExtractionTool:")
    internal_source_conf = {"source_name": "InternalLedger_Test", "source_type": "InternalLedger"}
    external_source_conf = {"source_name": "ExternalGateway_Test", "source_type": "PaymentGatewayLog"}

    internal_extract_res = data_extraction_tool.run({"data_source_config": internal_source_conf, "reconciliation_date_str": test_date_str})
    print(f"  Internal Extract: Status={internal_extract_res['status']}, Count={internal_extract_res.get('records_count')}")

    external_extract_res = data_extraction_tool.run({"data_source_config": external_source_conf, "reconciliation_date_str": test_date_str})
    print(f"  External Extract: Status={external_extract_res['status']}, Count={external_extract_res.get('records_count')}")

    # Ensure data is extracted for comparison tool test
    internal_data_list = internal_extract_res.get("data", [])
    external_data_list = external_extract_res.get("data", [])

    # Simulate some exact matches for primary keys and some differences
    if internal_data_list and external_data_list:
        # Make first few external records match internal ones on the primary key used by comparison mock
        # The mock _generate_mock_recon_data already tries to do this by renaming 'transaction_id' to 'external_session_id'
        # For this test, ensure the matching_rules reflect these field names.
        pass # Data generation already has some overlaps

    # 2. Test DataComparisonTool
    print("\n2. Testing DataComparisonTool:")
    # Rule: match internal 'transaction_id' with external 'external_session_id'
    # And internal 'amount' with external 'transaction_amount'
    sample_matching_rules = [{
        "rule_id": "TestRule001", "description": "Match on ID and amount",
        "primary_keys": [{"internal_field_name": "transaction_id", "external_field_name": "external_session_id"}],
        "amount_field_internal": "amount", "amount_field_external": "transaction_amount",
        "amount_tolerance_absolute": 0.50 # 50 kobo tolerance
    }]

    comparison_res = data_comparison_tool.run({
        "internal_data": internal_data_list,
        "external_data": external_data_list,
        "matching_rules": sample_matching_rules
    })
    print(f"  Comparison: Status={comparison_res['status']}")
    if comparison_res['status'] == 'Success':
        summary = comparison_res['summary_stats']
        print(f"    Summary: Matched={summary.get('matched_count')}, Unmatched Internal={summary.get('unmatched_internal_count')}, Unmatched External={summary.get('unmatched_external_count')}")


    # 3. Test DiscrepancyReportingTool
    print("\n3. Testing DiscrepancyReportingTool:")
    if comparison_res['status'] == 'Success':
        reporting_res = discrepancy_reporting_tool.run({
            "unmatched_internal": comparison_res.get("unmatched_internal", []),
            "unmatched_external": comparison_res.get("unmatched_external", []),
            "comparison_summary": comparison_res.get("summary_stats", {})
        })
        print(f"  Reporting: Status={reporting_res['status']}")
        if reporting_res['status'] == 'Success':
            print(f"    Report Summary Message: {reporting_res['report_sections']['summary_message']}")
    else:
        print("  Skipping DiscrepancyReportingTool test due to prior comparison error.")

    print("\nBack Office Reconciliation Agent tools implemented with mocks.")
