# Agent for Compliance Operations (AML/KYC Monitoring, Regulatory Reporting)
import json # For pretty printing dicts if needed
from . import tools
from . import config # For thresholds, default values
from datetime import datetime, date # For date operations

class ComplianceAgent:
    def __init__(self, agent_id="compliance_agent_001", memory_storage=None):
        self.agent_id = agent_id
        self.role = "Enforces AML/KYC rules and regulatory monitoring."
        # Memory: Stores regulatory rules (or references them), flagged cases, SAR/STR preparation status.
        # Example: self.memory = {
        #    "flagged_case_SAL001": {"customer_id": "CUST123", "transaction_id": "TXNABC", "status": "PENDING_STR_DRAFT", ...},
        #    "active_aml_rules": [{"rule_code": "LARGE_CASH", "params": {...}}],
        #    "sanction_list_last_checked": "2023-10-28T10:00:00Z"
        # }
        self.memory = memory_storage if memory_storage is not None else {}
        self._load_initial_memory()

    def _load_initial_memory(self):
        # Placeholder: Load active AML rules, last sanction list update info, etc.
        # self.memory["active_aml_rules"] = tools.get_active_aml_rules_config()
        # self.memory["sanction_list_last_checked"] = tools.get_sanction_list_last_update_time()
        pass

    def _update_case_memory(self, case_id: str, step_name: str, data: dict, status_update: Optional[str] = None):
        if case_id not in self.memory:
            self.memory[case_id] = {"steps_completed": [], "data_collected": {}, "current_status": "NEW"}

        case_mem = self.memory[case_id]
        if step_name not in case_mem["steps_completed"]:
            case_mem["steps_completed"].append(step_name)
        case_mem["data_collected"][step_name] = data
        if status_update:
            case_mem["current_status"] = status_update
            case_mem["last_status_update_at"] = datetime.utcnow().isoformat()

    # --- Workflow: Onboard New Customer Compliance Check ---
    def perform_new_customer_compliance_checks(self, customer_id: str, customer_data: dict) -> dict:
        """
        Workflow for compliance checks during new customer onboarding.
        Inputs:
            customer_id: Internal ID of the new customer.
            customer_data: Dictionary of customer details (name, BVN, NIN, DOB, address, etc.).
        Output:
            Dictionary with overall compliance status for onboarding (e.g., "CLEARED", "FLAGGED_SANCTION_MATCH", "HIGH_RISK_PROFILE").
        """
        case_id = f"ONBOARDING_{customer_id}"
        self._update_case_memory(case_id, "INITIATED_ONBOARDING_CHECKS", customer_data, "CHECKS_STARTED")

        overall_status = "CLEARED_FOR_ONBOARDING"
        issues_found = []

        # 1. Sanctions Screening
        sanction_result = tools.screen_entity_against_sanctions_lists(
            entity_name=f"{customer_data.get('first_name','')} {customer_data.get('last_name','')}".strip(),
            entity_type="INDIVIDUAL",
            bvn=customer_data.get('bvn'),
            other_identifiers={
                "date_of_birth": customer_data.get('date_of_birth'),
                "nationality": customer_data.get('nationality', 'NG') # Assume Nigerian if not specified
            }
        )
        self._update_case_memory(case_id, "SANCTION_SCREENING", sanction_result)
        if sanction_result.get("status") == "error":
            overall_status = "ERROR_DURING_CHECKS"
            issues_found.append(f"Sanction screening service error: {sanction_result.get('message')}")
        elif sanction_result.get("match_found") is True:
            overall_status = "FLAGGED_SANCTION_MATCH"
            issues_found.append(f"Potential sanction match found: {sanction_result.get('match_details')}")
            # Log this critical action
            tools.log_compliance_action_to_audit_trail(
                action_type="ONBOARDING_SANCTION_MATCH", entity_type="CUSTOMER", entity_id=customer_id,
                summary=f"Sanction match found during onboarding for {customer_id}.",
                details_after=sanction_result
            )

        # 2. Initial AML Risk Assessment (Simplified - based on profile)
        # In a real system, this would use a more sophisticated customer risk scoring model.
        # For mock: Flag if customer is from a high-risk country or is a PEP (Politically Exposed Person)
        # (Assuming 'country_of_residence' and 'is_pep' are in customer_data)
        if customer_data.get("country_of_residence", "NG").upper() in config.HIGH_RISK_COUNTRY_LIST:
            issues_found.append("Customer from designated high-risk country.")
            if overall_status == "CLEARED_FOR_ONBOARDING": overall_status = "FLAGGED_HIGH_RISK_PROFILE"

        if customer_data.get("is_pep") is True:
            issues_found.append("Customer identified as a Politically Exposed Person (PEP). Requires enhanced due diligence.")
            if overall_status == "CLEARED_FOR_ONBOARDING": overall_status = "FLAGGED_PEP_REQUIRES_EDD"

        self._update_case_memory(case_id, "INITIAL_AML_RISK_ASSESSMENT", {"issues": issues_found}, overall_status)

        # Log overall check completion
        tools.log_compliance_action_to_audit_trail(
            action_type="ONBOARDING_COMPLIANCE_CHECK_COMPLETED", entity_type="CUSTOMER", entity_id=customer_id,
            summary=f"Onboarding compliance check for {customer_id} resulted in status: {overall_status}.",
            details_after={"status": overall_status, "issues": issues_found}
        )

        return {"customer_id": customer_id, "onboarding_compliance_status": overall_status, "issues": issues_found}

    # --- Workflow: Monitor Transaction for Compliance ---
    def monitor_transaction_for_compliance(self, transaction_id: str) -> dict:
        """
        Workflow to monitor a specific financial transaction for compliance issues (AML, Sanctions on counterparties).
        This might be triggered after fraud detection or as part of ongoing monitoring.
        Inputs:
            transaction_id: The ID of the financial transaction to monitor.
        Output:
            Dictionary with compliance assessment (e.g., "CLEARED", "FLAGGED_AML_RULE", "FLAGGED_COUNTERPARTY_SANCTION").
        """
        case_id = f"TXN_MONITOR_{transaction_id}"

        # 1. Fetch transaction details
        transaction_data = tools.get_transaction_details_for_compliance(transaction_id)
        if transaction_data.get("status") == "error":
            self._update_case_memory(case_id, "FETCH_TX_DETAILS_FAILED", transaction_data, "ERROR_FETCHING_DATA")
            return {"transaction_id": transaction_id, "compliance_status": "ERROR_FETCHING_DATA", "reason": transaction_data.get("message")}
        self._update_case_memory(case_id, "FETCHED_TX_DETAILS", transaction_data, "MONITORING_STARTED")

        overall_status = "CLEARED_COMPLIANCE_MONITORING"
        issues_found = []

        # 2. AML Rule Evaluation (if not already done by a dedicated AML monitoring system)
        # This might be a more focused set of rules than real-time fraud detection.
        # customer_id_debit = transaction_data.get("debit_customer_id") # Assuming these are available
        # customer_profile_debit = tools.get_customer_details_for_compliance(customer_id_debit) if customer_id_debit else None
        aml_eval_result = tools.evaluate_transaction_against_aml_rules(transaction_data, customer_profile=None) # Pass profile if available
        self._update_case_memory(case_id, "AML_RULE_EVALUATION", aml_eval_result)
        if aml_eval_result.get("flags"):
            issues_found.extend(aml_eval_result.get("flags"))
            if aml_eval_result.get("aml_risk_level") in ["HIGH", "CRITICAL"]:
                overall_status = "FLAGGED_AML_CONCERN"

        # 3. Sanctions Screening of Counterparties (if interbank or to known external entity)
        # Example: Screen beneficiary if it's an outgoing NIP transfer
        if transaction_data.get("type") == "NIP_TRANSFER" and transaction_data.get("credit_account_name"):
            counterparty_name = transaction_data.get("credit_account_name")
            # BVN might not be available for counterparty in NIP, use name and bank.
            counterparty_sanction_result = tools.screen_entity_against_sanctions_lists(entity_name=counterparty_name, entity_type="INDIVIDUAL_OR_ORGANIZATION") # Generic type
            self._update_case_memory(case_id, f"COUNTERPARTY_SANCTION_SCREEN_{counterparty_name}", counterparty_sanction_result)
            if counterparty_sanction_result.get("match_found") is True:
                issues_found.append(f"Counterparty '{counterparty_name}' has potential sanction match: {counterparty_sanction_result.get('match_details')}")
                overall_status = "FLAGGED_COUNTERPARTY_SANCTION_MATCH"
                # This is a serious flag, might need to block/reverse transaction if possible, or file STR.

        self._update_case_memory(case_id, "COMPLETED_MONITORING", {"issues": issues_found}, overall_status)

        # 4. Log action and potentially prepare/submit STR if issues are severe
        log_summary = f"Compliance monitoring for TXN {transaction_id} resulted in: {overall_status}."
        tools.log_compliance_action_to_audit_trail(
            action_type="TRANSACTION_COMPLIANCE_MONITOR", entity_type="FINANCIAL_TRANSACTION", entity_id=transaction_id,
            summary=log_summary, details_after={"status": overall_status, "issues": issues_found}
        )

        if "FLAGGED" in overall_status: # If any serious flag
            # This might trigger a SuspiciousActivityLog entry in compliance_regulatory_reporting module
            # or directly proceed to STR preparation if criteria met.
            self.prepare_and_submit_str_if_needed(
                case_id,
                suspicion_reason=log_summary,
                transaction_data=transaction_data,
                # customer_data=customer_profile_debit # Or fetch involved customer(s) data
                customer_data=tools.get_customer_details_for_compliance(transaction_data.get("debit_customer_id")) if transaction_data.get("debit_customer_id") else None
            )

        return {"transaction_id": transaction_id, "compliance_status": overall_status, "issues_found": issues_found}

    # --- Workflow: Prepare and Submit Suspicious Transaction Report (STR) ---
    def prepare_and_submit_str_if_needed(self, case_id_or_sal_id: str, suspicion_reason: str, transaction_data: dict, customer_data: Optional[dict]) -> dict:
        """
        Prepares data for an STR and "submits" it (logs for regulatory reporting module).
        Inputs:
            case_id_or_sal_id: Reference to the internal case or Suspicious Activity Log ID.
            suspicion_reason: Detailed grounds for suspicion.
            transaction_data: Data of the suspicious transaction(s).
            customer_data: Data of the customer(s) involved.
        Output:
            Dictionary with submission status and reference.
        """
        self._update_case_memory(case_id_or_sal_id, "STR_PREPARATION_INITIATED", {"reason": suspicion_reason}, "STR_PREP_IN_PROGRESS")

        # 1. Gather all necessary data (this is often the most complex part)
        # This tool is a simplified representation.
        str_data_payload = tools.prepare_suspicious_transaction_report_data(
            suspicious_activity_log_id=case_id_or_sal_id, # Use case ID as reference
            transaction_details=transaction_data,
            customer_details=customer_data or {},
            reason_for_suspicion=suspicion_reason
        )
        self._update_case_memory(case_id_or_sal_id, "STR_DATA_PREPARED", str_data_payload)

        # 2. "Submit" the report data (e.g. to internal regulatory reporting queue/service)
        # For NFIU, this usually means generating a file for goAML or using their API if available.
        submission_result = tools.submit_regulatory_report(
            report_type="STR",
            report_data=str_data_payload,
            report_period_end_date=date.today().isoformat() # STR is usually event-driven, not period-based for end date
        )
        self._update_case_memory(case_id_or_sal_id, "STR_SUBMISSION_ATTEMPTED", submission_result, f"STR_{submission_result.get('status','UNKNOWN')}")

        # 3. Log this critical action
        tools.log_compliance_action_to_audit_trail(
            action_type="STR_SUBMITTED" if submission_result.get("status") == "success" else "STR_SUBMISSION_FAILED",
            entity_type="SUSPICIOUS_ACTIVITY_CASE", entity_id=case_id_or_sal_id,
            summary=f"STR submission attempt for {case_id_or_sal_id}. Result: {submission_result.get('message')}",
            details_after=submission_result
        )

        return submission_result

    def get_case_memory(self, case_id: str) -> dict:
        if case_id in self.memory:
            return self.memory[case_id]
        return {"status": "not_found", "message": "No compliance case memory found for this ID."}


# Example Usage
if __name__ == "__main__":
    compliance_agent = ComplianceAgent()

    # --- Test New Customer Onboarding Compliance ---
    print("\n--- Testing New Customer Onboarding Compliance ---")
    customer_clean_data = {
        "customer_id": "CUST_NEW_CLEAN", "first_name": "Clean", "last_name": "User",
        "bvn": "22299988877", "date_of_birth": "1990-01-01", "nationality": "NG", "is_pep": False
    }
    onboarding_res_clean = compliance_agent.perform_new_customer_compliance_checks("CUST_NEW_CLEAN", customer_clean_data)
    print("Clean Customer Onboarding Result:")
    print(json.dumps(onboarding_res_clean, indent=2))
    # print("Memory for CUST_NEW_CLEAN:")
    # print(json.dumps(compliance_agent.get_case_memory("ONBOARDING_CUST_NEW_CLEAN"), indent=2, default=str))


    customer_sanctioned_data = {
        "customer_id": "CUST_NEW_SANCTIONED", "first_name": "Sanctioned Person", "last_name": "International",
        "bvn": "22277766655", "date_of_birth": "1975-06-20", "nationality": "COUNTRY_X", "is_pep": True
    }
    onboarding_res_sanctioned = compliance_agent.perform_new_customer_compliance_checks("CUST_NEW_SANCTIONED", customer_sanctioned_data)
    print("\nSanctioned/PEP Customer Onboarding Result:")
    print(json.dumps(onboarding_res_sanctioned, indent=2))

    # --- Test Transaction Monitoring ---
    print("\n--- Testing Transaction Compliance Monitoring ---")
    # Assume transaction TXN_COMPLY_CLEAN is already fetched and normal
    # For TXN_COMPLY_FLAGGED, let's assume it triggered an AML rule (e.g. large cash, high risk country if data was there)
    # or its counterparty is sanctioned.

    # To make this testable, we need mock transaction data that tools.get_transaction_details_for_compliance would return.
    # Let's assume TXN_AML_FLAG is a large cash deposit that will be flagged by our mock AML rule tool.
    # (The tool `evaluate_transaction_against_aml_rules` currently has a mock for large cash)

    # First, ensure get_transaction_details_for_compliance can be called by the agent's workflow
    # This tool is mocked in tools.py to return some data.

    print("\nMonitoring a potentially suspicious transaction (TXN_AML_FLAG):")
    # The agent's monitor_transaction_for_compliance will call the mocked tools.
    # tools.get_transaction_details_for_compliance is mocked to return data for any TXN_ID not "TXN_UNKNOWN"
    # tools.evaluate_transaction_against_aml_rules is mocked to flag large cash
    # tools.screen_entity_against_sanctions_lists is mocked to flag "Sanctioned Person X"

    # The agent's workflow will call these. We need to ensure the mock data from get_transaction_details_for_compliance
    # is sufficient for the other tools if they depend on its output.
    # For example, if counterparty screening needs `credit_account_name` from transaction_data.

    # A transaction that might trigger AML rule (large cash) but not sanction on counterparty
    # (because the mocked get_transaction_details_for_compliance doesn't return a "Sanctioned Person X" as counterparty)
    monitoring_res_aml = compliance_agent.monitor_transaction_for_compliance("TXN_AML_FLAG")
    print("Transaction (TXN_AML_FLAG) Monitoring Result:")
    print(json.dumps(monitoring_res_aml, indent=2, default=str))
    # print("Memory for TXN_AML_FLAG case:")
    # print(json.dumps(compliance_agent.get_case_memory("TXN_MONITOR_TXN_AML_FLAG"), indent=2, default=str))


    # To test STR submission part, we'd need a case that was flagged.
    # If monitoring_res_aml was flagged, the agent's workflow would have called prepare_and_submit_str_if_needed.
    # We can check the memory for that case.
    if "FLAGGED" in monitoring_res_aml.get("compliance_status", ""):
        print("\nSTR related memory for TXN_AML_FLAG (if any STR prep steps ran):")
        case_mem = compliance_agent.get_case_memory("TXN_MONITOR_TXN_AML_FLAG")
        if "STR_DATA_PREPARED" in case_mem.get("steps_completed",[]):
            print("STR Data was prepared. Submission status:", case_mem.get("current_status"))
            # print(json.dumps(case_mem["data_collected"]["STR_SUBMISSION_ATTEMPTED"], indent=2, default=str))
        else:
            print("STR preparation was not triggered for this case based on mock logic.")

    print("\n--- Compliance Agent Memory Dump ---")
    # print(json.dumps(compliance_agent.memory, indent=2, default=str)) # Might be large
    for k, v_case in compliance_agent.memory.items():
        if isinstance(v_case, dict) and "current_status" in v_case: # Print only case memories
            print(f"Case: {k}, Status: {v_case['current_status']}")
