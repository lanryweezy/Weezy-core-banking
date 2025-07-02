# Agent for Credit Analysis
from . import tools
from . import config # For thresholds, default values

class CreditAnalystAgent:
    def __init__(self, agent_id="credit_analyst_001", memory_storage=None):
        self.agent_id = agent_id
        self.role = "Assesses loan applications and provides approvals/rejections."
        # Memory: Stores application history, decision logs for audit and learning
        # Example: self.memory = {"app_id_XYZ": {"status": "REJECTED", "score": 450, "reason": "Low credit score, high DTI", "timestamp": ...}}
        self.memory = memory_storage if memory_storage is not None else {}

    def _get_application_memory(self, application_id: str):
        if application_id not in self.memory:
            self.memory[application_id] = {"steps_completed": [], "data_collected": {}, "decision_log": []}
        return self.memory[application_id]

    def _update_application_memory(self, application_id: str, step_name: str, data: dict, decision_entry: Optional[str] = None):
        app_mem = self._get_application_memory(application_id)
        if step_name not in app_mem["steps_completed"]:
            app_mem["steps_completed"].append(step_name)
        app_mem["data_collected"][step_name] = data
        if decision_entry:
            app_mem["decision_log"].append({"timestamp": datetime.utcnow().isoformat(), "entry": decision_entry})

    def analyze_loan_application(self, application_id: str, loan_form_data: dict, income_proof_paths: List[str], transaction_history_paths: List[str]) -> dict:
        """
        Workflow to assess a loan application.
        Inputs:
            application_id: Unique ID for the loan application being processed.
            loan_form_data: Dictionary containing data from the loan application form.
                            (e.g., requested_amount, tenor, purpose, customer_bvn, stated_income, existing_debts).
            income_proof_paths: List of file paths to income proof documents (e.g., payslips, employment letter).
            transaction_history_paths: List of file paths to bank statements or transaction histories.
        Output:
            Dictionary with decision ("APPROVED", "REJECTED", "PENDING_FURTHER_REVIEW", "MISSING_DOCUMENTS"),
            reason, and potentially recommended terms.
        """
        app_memory = self._get_application_memory(application_id)
        self._update_application_memory(application_id, "INITIATED_ANALYSIS", {"form_data": loan_form_data})

        # Step 1: Fetch full application details from Loan Management module (if needed, or assume loan_form_data is sufficient)
        # For this example, we assume loan_form_data contains enough, but in reality, might call:
        # app_details_from_core = tools.get_loan_application_details(application_id)
        # if app_details_from_core.get("status") == "error":
        #     return {"decision": "ERROR", "reason": f"Failed to fetch application details: {app_details_from_core.get('message')}"}
        # merged_app_data = {**app_details_from_core, **loan_form_data} # Merge if necessary
        merged_app_data = loan_form_data # Using provided form data directly for mock
        self._update_application_memory(application_id, "FETCHED_APP_DETAILS", merged_app_data)


        # Step 2: Document Analysis (OCR + LLM) for income proofs and bank statements
        extracted_doc_data_aggregated = {}
        for doc_path in income_proof_paths:
            # Determine doc_type based on path or metadata if available
            doc_type = "PAYSLIP" if "payslip" in doc_path.lower() else "INCOME_OTHER"
            analysis_result = tools.analyze_document_with_ocr_llm(doc_path, doc_type)
            self._update_application_memory(application_id, f"DOC_ANALYSIS_{doc_type}_{doc_path.split('/')[-1]}", analysis_result)
            if analysis_result.get("status") == "success":
                extracted_doc_data_aggregated.update(analysis_result.get("extracted_data", {}))
            else: # Handle document analysis failure - e.g. request re-upload
                return {"decision": "MISSING_DOCUMENTS", "reason": f"Failed to analyze document {doc_path}: {analysis_result.get('message')}", "missing_doc_type": doc_type}

        for doc_path in transaction_history_paths:
            doc_type = "BANK_STATEMENT" # Assuming these are bank statements
            analysis_result = tools.analyze_document_with_ocr_llm(doc_path, doc_type)
            self._update_application_memory(application_id, f"DOC_ANALYSIS_{doc_type}_{doc_path.split('/')[-1]}", analysis_result)
            if analysis_result.get("status") == "success":
                extracted_doc_data_aggregated.update(analysis_result.get("extracted_data", {}))
            else:
                return {"decision": "MISSING_DOCUMENTS", "reason": f"Failed to analyze document {doc_path}: {analysis_result.get('message')}", "missing_doc_type": doc_type}

        self._update_application_memory(application_id, "AGGREGATED_DOC_DATA", extracted_doc_data_aggregated)

        # Step 3: Credit Scoring (Internal Model or Third-Party)
        # Prepare features for scoring model. This is crucial and model-dependent.
        # Features might come from merged_app_data, extracted_doc_data_aggregated, or other sources.
        features_for_scoring = {
            "bvn": merged_app_data.get("customer_bvn"),
            "stated_monthly_income": merged_app_data.get("stated_monthly_income"),
            "verified_net_income": extracted_doc_data_aggregated.get("net_income"),
            "average_monthly_inflow_statement": extracted_doc_data_aggregated.get("average_monthly_inflow"),
            "requested_loan_amount": merged_app_data.get("requested_amount"),
            "loan_tenor_months": merged_app_data.get("requested_tenor_months"),
            "existing_debts": merged_app_data.get("existing_monthly_debt_repayments"),
            # ... more features like age, employment_duration, transaction_patterns etc.
        }
        credit_score_result = tools.get_credit_score(application_id, features_for_scoring)
        self._update_application_memory(application_id, "CREDIT_SCORING", credit_score_result)
        if credit_score_result.get("status") == "error": # If scoring service itself fails
            return {"decision": "ERROR", "reason": f"Credit scoring service failed: {credit_score_result.get('message')}"}

        # Step 4: Risk Rules Evaluation
        # Use data from application, scoring, and document analysis
        risk_evaluation_result = tools.evaluate_risk_rules(merged_app_data, credit_score_result, extracted_doc_data_aggregated)
        self._update_application_memory(application_id, "RISK_RULES_EVALUATION", risk_evaluation_result)

        # Step 5: Decision Logic based on scores, rules, and thresholds
        final_decision = "PENDING_FURTHER_REVIEW" # Default if no strong auto-decision
        decision_reason = "Application requires manual underwriter review."

        credit_score_value = credit_score_result.get("credit_score", 0)
        risk_assessment = risk_evaluation_result.get("overall_assessment", "FAIL") # Default to fail if not present

        if risk_assessment == "FAIL":
            final_decision = tools.LoanApplicationStatusEnumSchema.REJECTED
            flags_summary = "; ".join([f"{f['rule']}: {f.get('value', 'N/A')}" for f in risk_evaluation_result.get("flags", [])])
            decision_reason = f"Rejected due to critical risk rule failures: {flags_summary}"
        elif risk_assessment == "PASS": # Only consider approval if basic rules pass
            if credit_score_value >= config.AUTO_APPROVAL_SCORE_THRESHOLD:
                final_decision = tools.LoanApplicationStatusEnumSchema.APPROVED
                decision_reason = f"Auto-approved based on excellent credit score ({credit_score_value}) and passing risk rules."
            elif credit_score_value < config.AUTO_REJECTION_SCORE_THRESHOLD:
                final_decision = tools.LoanApplicationStatusEnumSchema.REJECTED
                decision_reason = f"Rejected due to low credit score ({credit_score_value}) despite passing basic rules."
            else: # Score is in medium range, or rules passed but with medium flags
                final_decision = "PENDING_FURTHER_REVIEW" # Could also be PENDING_DOCUMENTATION if specific docs are weak
                decision_reason = f"Awaiting underwriter review. Score: {credit_score_value}. Risk flags: {risk_evaluation_result.get('flags')}"
        elif "FLAGGED" in risk_assessment: # Medium or High risk flags, but not outright FAIL
             final_decision = "PENDING_FURTHER_REVIEW"
             flags_summary = "; ".join([f"{f['rule']}" for f in risk_evaluation_result.get("flags", [])])
             decision_reason = f"Flagged for underwriter review due to: {flags_summary}. Score: {credit_score_value}."


        # Step 6: Communicate decision (or next steps) by updating Loan Management module
        update_status = tools.update_loan_application_decision(application_id, final_decision, decision_reason)
        self._update_application_memory(application_id, "DECISION_COMMUNICATED_TO_LOAN_MODULE", update_status, decision_entry=f"Final Decision: {final_decision}, Reason: {decision_reason}")

        if update_status.get("status") == "error": # If updating loan module fails
             return {"decision": "ERROR", "reason": f"Failed to update loan application status in core module: {update_status.get('message')}"}

        return {
            "decision": final_decision,
            "reason": decision_reason,
            "credit_score": credit_score_value,
            "risk_assessment_details": risk_evaluation_result,
            "application_id": application_id
        }

    def get_analysis_history(self, application_id: str) -> dict:
        """Returns the stored memory/log for a given application analysis."""
        if application_id in self.memory:
            return self.memory[application_id]
        return {"status": "not_found", "message": "No analysis history found for this application ID."}


# Example Usage (for testing the agent's main workflow)
if __name__ == "__main__":
    from datetime import datetime # For _update_application_memory decision_entry timestamp
    from typing import List, Optional # For type hinting

    credit_agent = CreditAnalystAgent()

    test_app_id = "APP_TEST_001"
    # Mock input data for the agent's main method
    mock_loan_form = {
        "application_id": test_app_id, # Agent might use this or an internal one
        "customer_bvn": "12345678901",
        "stated_monthly_income": 700000.00,
        "requested_amount": 1000000.00,
        "requested_tenor_months": 24,
        "loan_purpose": "Home renovation",
        "existing_monthly_debt_repayments": 30000.00,
        "calculated_requested_emi": 50000.00 # Assume this is pre-calculated for DTI
    }
    mock_income_proofs = ["./dummy_docs/payslip_jan.pdf", "./dummy_docs/payslip_feb.pdf"]
    mock_txn_history = ["./dummy_docs/bank_statement_q3.pdf"]

    # Create dummy files for tools to "read"
    import os
    os.makedirs("./dummy_docs", exist_ok=True)
    for p in mock_income_proofs + mock_txn_history:
        with open(p, "w") as f: f.write("dummy content for " + p)

    print(f"--- Analyzing Loan Application: {test_app_id} ---")
    analysis_outcome = credit_agent.analyze_loan_application(
        test_app_id,
        mock_loan_form,
        mock_income_proofs,
        mock_txn_history
    )

    print("\n--- Analysis Outcome ---")
    print(json.dumps(analysis_outcome, indent=2, default=str)) # Use default=str for decimal/datetime if any

    print("\n--- Agent Memory for Application ---")
    # print(json.dumps(credit_agent.get_analysis_history(test_app_id), indent=2, default=str))

    # Clean up dummy files
    for p in mock_income_proofs + mock_txn_history:
        os.remove(p)
    os.rmdir("./dummy_docs")
