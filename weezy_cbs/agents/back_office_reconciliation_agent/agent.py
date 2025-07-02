# Agent for Back Office Reconciliation
import pandas as pd
from datetime import datetime, timedelta
from . import tools
from . import config # For default date ranges, supported sources

class BackOfficeReconciliationAgent:
    def __init__(self, agent_id="back_office_recon_agent_001", memory_storage=None):
        self.agent_id = agent_id
        self.role = "Matches internal ledger with external transaction logs (e.g., Paystack, Interswitch)."
        # Memory: Stores status of past reconciliations, unresolved discrepancies, configurations.
        # Example: self.memory = {
        #    "recon_PAYSTACK_20231027": {"status": "COMPLETED", "unresolved_count": 2, "report_path": "..."},
        #    "unresolved_discrepancies": [ {"type": "UNMATCHED_EXTERNAL", "processor": "PAYSTACK", "details": {...}}, ... ]
        # }
        self.memory = memory_storage if memory_storage is not None else {}
        self._load_initial_config()

    def _load_initial_config(self):
        self.supported_sources = config.SUPPORTED_RECON_SOURCES
        # Potentially load GL codes relevant for each source
        self.source_gl_map = {
            "PAYSTACK": ["PAYSTACK_SETTLEMENT_GL", "PAYSTACK_FEE_GL"], # Example GL codes
            "INTERSWITCH_SETTLEMENT": ["INTERSWITCH_SETTLEMENT_GL", "INTERSWITCH_FEE_GL"]
        }

    def _update_recon_memory(self, recon_key: str, status: str, summary: Optional[str]=None, report_data: Optional[dict]=None, unresolved_items: Optional[list]=None):
        if recon_key not in self.memory:
            self.memory[recon_key] = {}

        self.memory[recon_key]["status"] = status
        self.memory[recon_key]["last_updated"] = datetime.utcnow().isoformat()
        if summary: self.memory[recon_key]["summary"] = summary
        if report_data: self.memory[recon_key]["report_preview"] = report_data # Store a preview or path

        # Manage overall list of unresolved discrepancies
        if "unresolved_discrepancies" not in self.memory: self.memory["unresolved_discrepancies"] = []

        # Naive update: clear previous unresolved for this key and add new ones
        # A more robust system would track individual discrepancies by unique ID.
        self.memory["unresolved_discrepancies"] = [
            item for item in self.memory["unresolved_discrepancies"] if item.get("recon_key") != recon_key
        ]
        if unresolved_items:
            for item in unresolved_items:
                item["recon_key"] = recon_key # Add context
                self.memory["unresolved_discrepancies"].append(item)


    def perform_daily_reconciliation(self, recon_date_str: Optional[str] = None, processor_name: Optional[str] = None) -> List[dict]:
        """
        Main workflow to perform daily reconciliation for one or all supported processors.
        Inputs:
            recon_date_str: The date for reconciliation (YYYY-MM-DD). Defaults to yesterday.
            processor_name: Specific processor to reconcile (e.g., "PAYSTACK"). If None, tries all supported.
        Output:
            List of result dictionaries, one for each processor reconciled. Each dict includes
            status, summary, and path to detailed report.
        """
        if recon_date_str:
            try:
                run_date = datetime.strptime(recon_date_str, "%Y-%m-%d").date()
            except ValueError:
                return [{"processor": processor_name or "ALL", "status": "ERROR", "summary": "Invalid date format. Use YYYY-MM-DD."}]
        else:
            run_date = datetime.utcnow().date() - timedelta(days=config.DEFAULT_RECONCILIATION_DATE_RANGE_DAYS)

        recon_date_to_fetch = run_date.strftime("%Y-%m-%d")

        processors_to_run = [processor_name.upper()] if processor_name else self.supported_sources
        all_results = []

        for proc_name in processors_to_run:
            if proc_name not in self.supported_sources:
                all_results.append({"processor": proc_name, "status": "SKIPPED", "summary": "Processor not supported by this agent."})
                continue

            recon_key = f"RECON_{proc_name}_{run_date.strftime('%Y%m%d')}"
            self._update_recon_memory(recon_key, "STARTED", summary=f"Reconciliation started for {proc_name} on {recon_date_to_fetch}.")

            # 1. Fetch Internal Ledger Entries
            relevant_gls = self.source_gl_map.get(proc_name)
            internal_entries_list = tools.fetch_internal_ledger_entries(recon_date_to_fetch, relevant_gl_codes=relevant_gls)
            if not internal_entries_list and proc_name in ["PAYSTACK", "INTERSWITCH_SETTLEMENT"]: # Expect some data
                 # Log warning, but continue if external data might exist (e.g. to find missing internal)
                 print(f"Warning: No internal ledger entries found for {proc_name} GLs on {recon_date_to_fetch}.")
            internal_df = pd.DataFrame(internal_entries_list)

            # 2. Fetch Payment Processor Logs
            external_entries_list = tools.fetch_payment_processor_logs(proc_name, recon_date_to_fetch)
            if not external_entries_list and proc_name in ["PAYSTACK", "INTERSWITCH_SETTLEMENT"]:
                 print(f"Warning: No external transaction logs found for {proc_name} on {recon_date_to_fetch}.")
            external_df = pd.DataFrame(external_entries_list)

            # 3. Compare and Reconcile Data
            # Define match keys based on processor - this is crucial and needs careful setup.
            # Common keys: transaction_reference, amount, date (normalized).
            # For Paystack, OUR reference is `reference_number` in mapped external, and `reference_number` in internal.
            # For Interswitch, it might be `retrievalReferenceNumber` or a custom transaction ID.
            # This needs to align with how `_map_processor_txn_to_standard_format` names them.
            match_keys_for_proc = ["reference_number"] # Default, may need to be processor-specific

            # Ensure DataFrames are not completely empty before proceeding, to avoid errors with .columns access
            if internal_df.empty and external_df.empty:
                summary = f"Both internal and external datasets for {proc_name} are empty for {recon_date_to_fetch}."
                self._update_recon_memory(recon_key, "COMPLETED_EMPTY", summary=summary)
                all_results.append({"processor": proc_name, "status": "COMPLETED_EMPTY", "summary": summary})
                continue

            recon_results = tools.compare_and_reconcile_data(internal_df, external_df, match_keys=match_keys_for_proc)

            # 4. Attempt Auto-Resolution (Conceptual - can be expanded)
            # auto_resolved_info = tools.attempt_auto_resolution(
            #     recon_results["unmatched_internal"],
            #     recon_results["unmatched_external"]
            # )
            # Update recon_results with items moved from unmatched to matched by auto-resolution.
            # For now, this step is mostly a pass-through in the mock tool.

            # 5. Prepare Summary Report and Log Unresolved Items
            summary_report_str = tools.generate_reconciliation_summary_report(recon_results, recon_date_to_fetch, proc_name)

            unresolved_for_memory = []
            for _, row in recon_results["unmatched_internal"].iterrows():
                unresolved_for_memory.append({"type": "UNMATCHED_INTERNAL", "processor": proc_name, "date": recon_date_to_fetch, "details": row.to_dict()})
            for _, row in recon_results["unmatched_external"].iterrows():
                unresolved_for_memory.append({"type": "UNMATCHED_EXTERNAL", "processor": proc_name, "date": recon_date_to_fetch, "details": row.to_dict()})
            for _, row in recon_results["discrepancies_amount"].iterrows():
                 unresolved_for_memory.append({"type": "AMOUNT_DISCREPANCY", "processor": proc_name, "date": recon_date_to_fetch, "details": row.to_dict()})
            # Add timing discrepancies too if needed for manual review

            self._update_recon_memory(recon_key, "COMPLETED", summary=recon_results.get("summary"), report_data={"preview": summary_report_str[:500]}, unresolved_items=unresolved_for_memory)

            all_results.append({
                "processor": proc_name,
                "status": "COMPLETED",
                "summary": recon_results.get("summary"),
                "report_preview": summary_report_str[:500] + "..." # Or path to full report file
            })

        return all_results

    def get_unresolved_discrepancies(self, processor_name: Optional[str] = None, max_age_days: Optional[int] = None) -> list:
        """Retrieves currently unresolved discrepancies, optionally filtered."""
        unresolved = self.memory.get("unresolved_discrepancies", [])
        filtered_discrepancies = unresolved
        if processor_name:
            filtered_discrepancies = [d for d in filtered_discrepancies if d.get("processor", "").upper() == processor_name.upper()]
        if max_age_days:
            cutoff_date = datetime.utcnow().date() - timedelta(days=max_age_days)
            filtered_discrepancies = [d for d in filtered_discrepancies if datetime.strptime(d.get("date"), "%Y-%m-%d").date() >= cutoff_date]
        return filtered_discrepancies

    def get_reconciliation_status(self, recon_date_str: str, processor_name: str) -> dict:
        """Gets the status and summary of a specific past reconciliation."""
        try:
            run_date = datetime.strptime(recon_date_str, "%Y-%m-%d").date()
        except ValueError:
            return {"status": "ERROR", "message": "Invalid date format. Use YYYY-MM-DD."}

        recon_key = f"RECON_{processor_name.upper()}_{run_date.strftime('%Y%m%d')}"
        if recon_key in self.memory:
            return self.memory[recon_key]
        return {"status": "NOT_FOUND", "message": f"No reconciliation record found for {processor_name} on {recon_date_str}."}

# Example Usage
if __name__ == "__main__":
    recon_agent = BackOfficeReconciliationAgent()

    print("--- Performing Daily Reconciliation for Paystack (Yesterday) ---")
    yesterday_str = (datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")
    paystack_results = recon_agent.perform_daily_reconciliation(recon_date_str=yesterday_str, processor_name="PAYSTACK")

    for res in paystack_results:
        print(f"\nProcessor: {res['processor']}")
        print(f"Status: {res['status']}")
        print(f"Summary: {res['summary']}")
        # print(f"Report Preview:\n{res.get('report_preview')}")

    print("\n--- Performing Daily Reconciliation for ALL Supported Sources (2 days ago) ---")
    two_days_ago_str = (datetime.utcnow().date() - timedelta(days=2)).strftime("%Y-%m-%d")
    all_src_results = recon_agent.perform_daily_reconciliation(recon_date_str=two_days_ago_str)
    for res in all_src_results:
        print(f"\nProcessor: {res['processor']}")
        print(f"Status: {res['status']}")
        print(f"Summary: {res['summary']}")

    print("\n--- Getting Unresolved Discrepancies (All) ---")
    unresolved = recon_agent.get_unresolved_discrepancies()
    print(f"Total unresolved items: {len(unresolved)}")
    if unresolved:
        print("Sample unresolved item:")
        print(json.dumps(unresolved[0], indent=2, default=str)) # default=str for datetime/decimal

    print("\n--- Getting Status for a Specific Reconciliation ---")
    status_check = recon_agent.get_reconciliation_status(yesterday_str, "PAYSTACK")
    print(f"Status for Paystack on {yesterday_str}:")
    print(json.dumps(status_check, indent=2, default=str))

    # print("\n--- Agent Memory Dump (selected parts) ---")
    # for k, v in recon_agent.memory.items():
    #     if k.startswith("RECON_"):
    #         print(f"Key: {k}, Status: {v.get('status')}, Summary: {v.get('summary')}")
    # print(f"Total Unresolved Discrepancies in memory: {len(recon_agent.memory.get('unresolved_discrepancies',[]))}")
