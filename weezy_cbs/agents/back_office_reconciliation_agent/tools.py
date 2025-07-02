# Tools for Back Office Reconciliation Agent
import requests
import pandas as pd # For data comparison and manipulation
from datetime import datetime, timedelta
import json
from . import config
# from weezy_cbs.payments_integration_layer.services import PaystackService, InterswitchService # Ideal
# from weezy_cbs.accounts_ledger_management.services import get_ledger_entries_for_period # Ideal

# --- Data Fetching Tools ---

def fetch_internal_ledger_entries(recon_date: str, relevant_gl_codes: Optional[list[str]] = None) -> list[dict]:
    """
    Fetches ledger entries from the internal Core Banking System for a given date.
    Inputs:
        recon_date: The date for which to fetch entries (YYYY-MM-DD).
        relevant_gl_codes: Optional list of GL account codes to filter by (e.g., settlement GLs for Paystack, Interswitch).
    Output:
        List of ledger entry dictionaries, or empty list if error/no data.
    """
    # This would ideally call a service in accounts_ledger_management.
    # Example: GET_DAILY_LEDGER_SNAPSHOT_ENDPOINT or a more specific query.
    # url = config.GET_DAILY_LEDGER_SNAPSHOT_ENDPOINT.format(date=recon_date)
    # params = {"gl_codes": ",".join(relevant_gl_codes)} if relevant_gl_codes else {}
    try:
        # response = requests.get(url, params=params, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return response.json().get("ledger_entries", [])

        print(f"Mock Internal Ledger Fetch: Date='{recon_date}', GLs='{relevant_gl_codes}'")
        # Simulate some ledger entries
        mock_entries = [
            {"transaction_id": "INT_TXN001", "account_id": "PAYSTACK_SETTLE_GL", "entry_type": "CREDIT", "amount": 10000.00, "currency": "NGN", "narration": "Paystack Settlement Ref PSTK_REF1", "transaction_date": f"{recon_date}T10:00:00Z", "reference_number": "PSTK_REF1"},
            {"transaction_id": "INT_TXN002", "account_id": "INTERSWITCH_FEE_GL", "entry_type": "DEBIT", "amount": 50.00, "currency": "NGN", "narration": "Interswitch Fee for ISW_REF2", "transaction_date": f"{recon_date}T11:00:00Z", "reference_number": "ISW_REF2_FEE"},
            {"transaction_id": "INT_TXN003", "account_id": "INTERSWITCH_SETTLE_GL", "entry_type": "CREDIT", "amount": 25000.00, "currency": "NGN", "narration": "Interswitch Settlement ISW_REF2", "transaction_date": f"{recon_date}T11:00:05Z", "reference_number": "ISW_REF2"},
            {"transaction_id": "INT_TXN004", "account_id": "PAYSTACK_SETTLE_GL", "entry_type": "CREDIT", "amount": 15000.00, "currency": "NGN", "narration": "Paystack Settlement Ref PSTK_REF3_MISMATCH_AMT", "transaction_date": f"{recon_date}T12:00:00Z", "reference_number": "PSTK_REF3_MISMATCH_AMT"},
            {"transaction_id": "INT_TXN005", "account_id": "PAYSTACK_SETTLE_GL", "entry_type": "CREDIT", "amount": 500.00, "currency": "NGN", "narration": "Paystack Unmatched Internal", "transaction_date": f"{recon_date}T14:00:00Z", "reference_number": "INTERNAL_ONLY_001"},

        ]
        if relevant_gl_codes:
            return [e for e in mock_entries if e.get("account_id") in relevant_gl_codes]
        return mock_entries

    except requests.exceptions.RequestException as e:
        print(f"Error fetching internal ledger entries: {str(e)}")
        return []

def fetch_payment_processor_logs(processor_name: str, recon_date: str) -> list[dict]:
    """
    Fetches transaction logs from a specified payment processor for a given date.
    Inputs:
        processor_name: Name of the processor (e.g., "PAYSTACK", "INTERSWITCH").
        recon_date: The date for which to fetch transactions (YYYY-MM-DD).
    Output:
        List of transaction dictionaries from the processor, or empty list if error/no data.
    """
    # This would ideally call a service in payments_integration_layer that uses specific SDKs/APIs.
    headers = {}
    params = {"from": recon_date, "to": recon_date, "status": "success", "perPage": 200} # Common params
    url = ""

    if processor_name.upper() == "PAYSTACK":
        # paystack_service = PaystackService(db_session_placeholder) # Needs DB session for config
        # return paystack_service.list_transactions(from_date=recon_date, to_date=recon_date, status="success")
        url = f"{config.PAYSTACK_TRANSACTIONS_ENDPOINT}"
        headers = {"Authorization": f"Bearer {config.PAYSTACK_SECRET_KEY}"}
        # Paystack API might require pagination handling for many transactions.
    elif processor_name.upper() == "INTERSWITCH_SETTLEMENT": # Assuming this is for settlement files
        # interswitch_service = InterswitchService(db_session_placeholder)
        # return interswitch_service.get_settlement_report(recon_date)
        # This might be a file download and parse, not a direct transaction list API.
        # For mock, simulate API response.
        url = f"{config.INTERSWITCH_TRANSACTIONS_ENDPOINT}" # Conceptual
        headers = {"Authorization": "Bearer mock_interswitch_token"} # Conceptual
        params = {"reportDate": recon_date, "type": "SETTLEMENT"}
    else:
        print(f"Unsupported payment processor: {processor_name}")
        return []

    try:
        # response = requests.get(url, params=params, headers=headers)
        # response.raise_for_status()
        # processor_txns = response.json().get("data", []) # Adapt based on actual API response structure
        # return [_map_processor_txn_to_standard_format(txn, processor_name) for txn in processor_txns]

        print(f"Mock {processor_name} Log Fetch: Date='{recon_date}'")
        if processor_name.upper() == "PAYSTACK":
            return [
                _map_processor_txn_to_standard_format({"id": "PSTK_TXN001", "reference": "PSTK_REF1", "amount": 1000000, "status": "success", "paid_at": f"{recon_date}T10:00:05Z", "currency": "NGN", "fees": 10000}, "PAYSTACK"), # Amount in kobo
                _map_processor_txn_to_standard_format({"id": "PSTK_TXN003", "reference": "PSTK_REF3_MISMATCH_AMT", "amount": 1505000, "status": "success", "paid_at": f"{recon_date}T12:00:05Z", "currency": "NGN", "fees": 15050}, "PAYSTACK"),
                _map_processor_txn_to_standard_format({"id": "PSTK_TXN006", "reference": "PSTK_REF_UNMATCHED_EXTERNAL", "amount": 750000, "status": "success", "paid_at": f"{recon_date}T15:00:00Z", "currency": "NGN", "fees": 7500}, "PAYSTACK"),
            ]
        elif processor_name.upper() == "INTERSWITCH_SETTLEMENT":
            return [
                 _map_processor_txn_to_standard_format({"transactionReference": "ISW_REF2", "amount": 25000.00, "responseCode": "00", "transactionDate": f"{recon_date}T11:00:00Z", "retrievalReferenceNumber": "RRN002"}, "INTERSWITCH"),
                 _map_processor_txn_to_standard_format({"transactionReference": "ISW_REF_UNMATCHED_EXTERNAL", "amount": 3000.00, "responseCode": "00", "transactionDate": f"{recon_date}T16:00:00Z", "retrievalReferenceNumber": "RRN005"}, "INTERSWITCH"),
            ]
        return []

    except requests.exceptions.RequestException as e:
        print(f"Error fetching {processor_name} logs: {str(e)}")
        return []

def _map_processor_txn_to_standard_format(processor_txn: dict, processor_name: str) -> dict:
    """Maps a processor-specific transaction to a standard internal format for reconciliation."""
    if processor_name.upper() == "PAYSTACK":
        return {
            "external_id": processor_txn.get("id"),
            "reference_number": processor_txn.get("reference"), # This is OUR reference sent to Paystack
            "amount": decimal.Decimal(processor_txn.get("amount", 0)) / 100, # Paystack amount is in kobo
            "currency": processor_txn.get("currency"),
            "status": processor_txn.get("status"), # "success", "failed", etc.
            "transaction_date": processor_txn.get("paid_at"), # Or "created_at"
            "fees": decimal.Decimal(processor_txn.get("fees", 0)) / 100,
            "source": processor_name
        }
    elif processor_name.upper() == "INTERSWITCH_SETTLEMENT": # Or just "INTERSWITCH"
        return {
            "external_id": processor_txn.get("retrievalReferenceNumber") or processor_txn.get("transactionReference"), # RRN is often used
            "reference_number": processor_txn.get("transactionReference"), # This might be OUR reference
            "amount": decimal.Decimal(processor_txn.get("amount", 0)),
            "currency": "NGN", # Assume NGN for Interswitch or get from data
            "status": "success" if processor_txn.get("responseCode") == "00" else "failed",
            "transaction_date": processor_txn.get("transactionDate"),
            "fees": decimal.Decimal(processor_txn.get("fee", 0)), # If fee is provided
            "source": processor_name
        }
    # Add mappers for other processors (Flutterwave, Monnify, BankOne etc.)
    else:
        # Generic pass-through or raise error for unmapped processor
        return {**processor_txn, "source": processor_name}


# --- Data Comparison & Reconciliation Logic Tool ---
def compare_and_reconcile_data(internal_df: pd.DataFrame, external_df: pd.DataFrame, match_keys: list[str], amount_field: str = "amount", date_field: str = "transaction_date") -> dict:
    """
    Compares internal ledger data with external processor data using Pandas DataFrames.
    Inputs:
        internal_df: Pandas DataFrame of internal ledger entries.
        external_df: Pandas DataFrame of external processor transactions.
        match_keys: List of column names to use for joining/matching (e.g., ["reference_number"]).
                    The primary match key should be robust (e.g., unique transaction reference).
        amount_field: Name of the column containing transaction amount.
        date_field: Name of the column containing transaction date/timestamp.
    Output:
        Dictionary containing:
            - matched_transactions: DataFrame of perfectly matched transactions.
            - unmatched_internal: DataFrame of internal transactions with no external match.
            - unmatched_external: DataFrame of external transactions with no internal match.
            - discrepancies_amount: DataFrame of transactions matched on keys but with amount differences.
            - discrepancies_timing: DataFrame of transactions matched on keys but with significant timing differences.
    """
    if internal_df.empty and external_df.empty:
        return {"matched_transactions": pd.DataFrame(), "unmatched_internal": pd.DataFrame(), "unmatched_external": pd.DataFrame(), "discrepancies_amount": pd.DataFrame(), "discrepancies_timing": pd.DataFrame(), "summary": "Both datasets are empty."}
    if internal_df.empty:
        return {"matched_transactions": pd.DataFrame(), "unmatched_internal": pd.DataFrame(), "unmatched_external": external_df, "discrepancies_amount": pd.DataFrame(), "discrepancies_timing": pd.DataFrame(), "summary": "Internal dataset empty."}
    if external_df.empty:
        return {"matched_transactions": pd.DataFrame(), "unmatched_internal": internal_df, "unmatched_external": pd.DataFrame(), "discrepancies_amount": pd.DataFrame(), "discrepancies_timing": pd.DataFrame(), "summary": "External dataset empty."}

    # Ensure key columns are of compatible types (e.g. string for references)
    for key in match_keys:
        if key in internal_df.columns: internal_df[key] = internal_df[key].astype(str)
        if key in external_df.columns: external_df[key] = external_df[key].astype(str)

    # Convert amount fields to numeric, coercing errors
    if amount_field in internal_df.columns: internal_df[amount_field] = pd.to_numeric(internal_df[amount_field], errors='coerce')
    if amount_field in external_df.columns: external_df[amount_field] = pd.to_numeric(external_df[amount_field], errors='coerce')

    # Convert date fields to datetime, coercing errors
    if date_field in internal_df.columns: internal_df[date_field] = pd.to_datetime(internal_df[date_field], errors='coerce')
    if date_field in external_df.columns: external_df[date_field] = pd.to_datetime(external_df[date_field], errors='coerce')

    # Perform outer join to find all matches and mismatches
    # Using suffixes to distinguish columns from internal vs external if they have same names (other than match_keys)
    merged_df = pd.merge(internal_df, external_df, on=match_keys, how='outer', suffixes=('_internal', '_external'), indicator=True)

    # Matched transactions (present in both, now check for discrepancies)
    matched_both = merged_df[merged_df['_merge'] == 'both'].copy()

    # Unmatched internal (in internal only)
    unmatched_internal = merged_df[merged_df['_merge'] == 'left_only'][internal_df.columns]

    # Unmatched external (in external only)
    unmatched_external = merged_df[merged_df['_merge'] == 'right_only'][external_df.columns]

    # Identify discrepancies in matched transactions
    discrepancies_amount = pd.DataFrame()
    discrepancies_timing = pd.DataFrame()
    perfectly_matched_indices = []

    if not matched_both.empty:
        # Amount discrepancies (allow for small tolerance)
        amount_internal_col = f"{amount_field}_internal"
        amount_external_col = f"{amount_field}_external"
        if amount_internal_col in matched_both.columns and amount_external_col in matched_both.columns:
            amount_diff = (matched_both[amount_internal_col] - matched_both[amount_external_col]).abs()
            discrepancies_amount = matched_both[amount_diff > config.RECONCILIATION_AMOUNT_TOLERANCE]

        # Timing discrepancies (e.g., transaction date difference > threshold)
        date_internal_col = f"{date_field}_internal"
        date_external_col = f"{date_field}_external"
        if date_internal_col in matched_both.columns and date_external_col in matched_both.columns:
            time_diff = (matched_both[date_internal_col] - matched_both[date_external_col]).abs()
            discrepancies_timing = matched_both[time_diff > timedelta(hours=config.AUTO_RESOLVE_TIME_WINDOW_HOURS)] # Example: 1 hour difference

        # Perfectly matched are those in 'both' but not in any discrepancy list
        discrep_amount_indices = set(discrepancies_amount.index)
        discrep_timing_indices = set(discrepancies_timing.index)
        all_discrep_indices = discrep_amount_indices.union(discrep_timing_indices)

        perfectly_matched_indices = [idx for idx in matched_both.index if idx not in all_discrep_indices]

    matched_transactions = matched_both.loc[perfectly_matched_indices] if perfectly_matched_indices else pd.DataFrame()

    return {
        "matched_transactions": matched_transactions,
        "unmatched_internal": unmatched_internal,
        "unmatched_external": unmatched_external,
        "discrepancies_amount": discrepancies_amount,
        "discrepancies_timing": discrepancies_timing,
        "summary": f"Internal: {len(internal_df)}, External: {len(external_df)}, Matched: {len(matched_transactions)}, Unmatched Internal: {len(unmatched_internal)}, Unmatched External: {len(unmatched_external)}, Amount Disc: {len(discrepancies_amount)}, Timing Disc: {len(discrepancies_timing)}"
    }

# --- Auto-Resolution Tool (Conceptual) ---
def attempt_auto_resolution(unmatched_internal_df: pd.DataFrame, unmatched_external_df: pd.DataFrame) -> dict:
    """
    Attempts to auto-resolve common discrepancies based on predefined rules.
    E.g., minor timing differences, slight variations in reference numbers if amounts match.
    Output: DataFrames of auto-resolved items, and remaining unmatched items.
    """
    # This is a placeholder for complex logic.
    # Could involve fuzzy matching on references, checking amounts within tolerance, dates within window.
    print("Mock Auto-Resolution: Attempting to find matches in unmatched items.")
    auto_resolved_pairs = [] # List of (internal_index, external_index) pairs

    # Example: if amounts match and dates are close, and reference is somewhat similar
    # for i_idx, i_row in unmatched_internal_df.iterrows():
    #     for e_idx, e_row in unmatched_external_df.iterrows():
    #         if abs(i_row['amount'] - e_row['amount']) <= config.RECONCILIATION_AMOUNT_TOLERANCE and \
    #            abs((i_row['transaction_date'] - e_row['transaction_date'])).total_seconds() <= config.AUTO_RESOLVE_TIME_WINDOW_HOURS * 3600 and \
    #            calculate_string_similarity(i_row['reference_number'], e_row['reference_number']) > config.AUTO_RESOLVE_REFERENCE_SIMILARITY_THRESHOLD:
    #             auto_resolved_pairs.append((i_idx, e_idx))
    #             # Mark these as resolved to avoid re-processing
    #             break

    # For mock, let's say we couldn't auto-resolve anything complexly
    return {
        "auto_resolved_transactions": pd.DataFrame(), # DataFrame of newly matched items
        "remaining_unmatched_internal": unmatched_internal_df, # After removing auto-resolved
        "remaining_unmatched_external": unmatched_external_df  # After removing auto-resolved
    }

# --- Reporting Tool ---
def generate_reconciliation_summary_report(recon_results: dict, recon_date: str, processor_name: str) -> str:
    """Generates a human-readable summary report string from reconciliation results."""
    summary = f"--- Reconciliation Report for {processor_name} - Date: {recon_date} ---\n"
    summary += recon_results.get("summary", "No summary available.") + "\n\n"

    if not recon_results.get("matched_transactions", pd.DataFrame()).empty:
        summary += f"Matched Transactions ({len(recon_results['matched_transactions'])}):\n"
        summary += recon_results['matched_transactions'][config.RECONCILIATION_MATCHING_FIELDS + [config.RECONCILIATION_MATCHING_FIELDS[0]+'_internal', config.RECONCILIATION_MATCHING_FIELDS[0]+'_external', 'amount_internal', 'amount_external']].head().to_string() + "\n...\n\n" # Show head

    if not recon_results.get("unmatched_internal", pd.DataFrame()).empty:
        summary += f"Unmatched Internal ({len(recon_results['unmatched_internal'])}):\n"
        summary += recon_results['unmatched_internal'].head().to_string() + "\n...\n\n"

    if not recon_results.get("unmatched_external", pd.DataFrame()).empty:
        summary += f"Unmatched External ({len(recon_results['unmatched_external'])}):\n"
        summary += recon_results['unmatched_external'].head().to_string() + "\n...\n\n"

    if not recon_results.get("discrepancies_amount", pd.DataFrame()).empty:
        summary += f"Amount Discrepancies ({len(recon_results['discrepancies_amount'])}):\n"
        summary += recon_results['discrepancies_amount'].head().to_string() + "\n...\n\n"

    # Save to file (conceptual)
    # file_path = f"{config.RECONCILIATION_REPORT_PATH}recon_{processor_name}_{recon_date.replace('-', '')}.txt"
    # with open(file_path, "w") as f:
    #     f.write(summary)
    # print(f"Reconciliation report saved to {file_path}")
    return summary


if __name__ == '__main__':
    import decimal # For _map_processor_txn_to_standard_format if amounts are decimal
    print("--- Testing Back Office Reconciliation Agent Tools ---")
    test_date = "2023-10-27"

    # 1. Fetch Internal Ledger Data
    print("\n1. Fetching Internal Ledger Data:")
    internal_data_list = fetch_internal_ledger_entries(test_date, relevant_gl_codes=["PAYSTACK_SETTLE_GL"])
    internal_df_test = pd.DataFrame(internal_data_list)
    print(f"Internal Data (first 2 rows):\n{internal_df_test.head(2)}")

    # 2. Fetch Paystack Data
    print("\n2. Fetching Paystack Transaction Data:")
    paystack_data_list = fetch_payment_processor_logs("PAYSTACK", test_date)
    paystack_df_test = pd.DataFrame(paystack_data_list)
    print(f"Paystack Data (first 2 rows):\n{paystack_df_test.head(2)}")

    # 3. Compare and Reconcile
    if not internal_df_test.empty and not paystack_df_test.empty:
        print("\n3. Comparing and Reconciling Data (Internal vs Paystack):")
        # Ensure key 'reference_number' exists and is consistently named for matching
        # Our mock internal data uses 'reference_number'. Paystack mapped data also uses 'reference_number'.
        recon_keys = ["reference_number"]
        results = compare_and_reconcile_data(internal_df_test, paystack_df_test, match_keys=recon_keys)
        print(f"Reconciliation Summary: {results.get('summary')}")

        # print("\nMatched Transactions (sample):")
        # print(results["matched_transactions"].head())
        # print("\nUnmatched Internal (sample):")
        # print(results["unmatched_internal"].head())
        # print("\nUnmatched External (sample):")
        # print(results["unmatched_external"].head())
        # print("\nAmount Discrepancies (sample):")
        # print(results["discrepancies_amount"].head())

        # 4. Attempt Auto-Resolution (conceptual)
        print("\n4. Attempting Auto-Resolution:")
        auto_resolve_res = attempt_auto_resolution(results["unmatched_internal"], results["unmatched_external"])
        print(f"Auto-resolved count: {len(auto_resolve_res['auto_resolved_transactions'])}")

        # 5. Generate Summary Report
        print("\n5. Generating Summary Report:")
        report_str = generate_reconciliation_summary_report(results, test_date, "Paystack")
        print(report_str[:1000] + "\n...") # Print first 1000 chars of report
    else:
        print("\nSkipping comparison due to empty data from fetch steps.")
