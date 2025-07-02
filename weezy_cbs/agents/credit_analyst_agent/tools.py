# Tools for Credit Analyst Agent
import requests
import json
from . import config # For API URLs and keys
# from weezy_cbs.ai_automation_layer.schemas import CreditScoringRequest # If calling internal AI service
# from weezy_cbs.loan_management_module.schemas import LoanApplicationStatusEnum # For status updates

# Placeholder for schemas if not importing from main modules
class CreditScoringRequestSchema(dict): pass # Replace with actual Pydantic model
class LoanApplicationStatusEnumSchema(str): # Replace with actual Enum
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING_DOCUMENTATION = "PENDING_DOCUMENTATION"
    UNDER_REVIEW = "UNDER_REVIEW"


def analyze_document_with_ocr_llm(document_path: str, document_type: str) -> dict:
    """
    Uses an OCR + LLM service to extract structured data from a document.
    Inputs:
        document_path: Path to the document file (e.g., payslip, bank statement).
        document_type: Type of document to guide LLM extraction (e.g., "PAYSLIP", "BANK_STATEMENT").
    Output: Dictionary of extracted fields or error.
    """
    # This is a placeholder. Implementation depends on the actual service.
    # It might involve uploading the file and then calling an analysis endpoint.
    try:
        # with open(document_path, 'rb') as f:
        #     files = {'file': (document_path.split('/')[-1], f)}
        #     data = {'document_type': document_type}
        #     response = requests.post(config.DOCUMENT_ANALYSIS_SERVICE_URL, files=files, data=data)
        # response.raise_for_status()
        # return response.json()

        print(f"Mock OCR/LLM Analysis: Analyzing {document_type} at {document_path}")
        if "payslip" in document_type.lower():
            return {
                "status": "success",
                "extracted_data": {
                    "net_income": 500000.00,
                    "employer_name": "WeezyTech Global",
                    "pay_date": "2023-10-28"
                },
                "confidence": 0.92
            }
        elif "bank_statement" in document_type.lower():
             return {
                "status": "success",
                "extracted_data": {
                    "average_monthly_inflow": 750000.00,
                    "closing_balance": 1200000.00,
                    "statement_period": "2023-08-01_to_2023-10-31",
                    "has_bounced_cheques": False
                },
                "confidence": 0.88
            }
        else:
            return {"status": "error", "message": "Unsupported document type for mock analysis."}

    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Document analysis service request failed: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error during document analysis: {str(e)}"}


def get_credit_score(application_id: str, customer_features: dict) -> dict:
    """
    Gets a credit score for a loan application.
    This can call an internal model or a third-party service.
    Inputs:
        application_id: The ID of the loan application.
        customer_features: A dictionary of features required by the scoring model.
                           (e.g., BVN, income, existing debts, transaction patterns).
    Output: Dictionary with score, risk rating, and other details or error.
    """
    # Using the internal AI model endpoint from ai_automation_layer
    payload = CreditScoringRequestSchema(application_id=application_id, features=customer_features)

    try:
        # response = requests.post(config.INTERNAL_CREDIT_SCORING_API_URL, json=payload) # Assuming payload is Pydantic model that serializes
        # response.raise_for_status()
        # return response.json() # This should match CreditScoringResponse from ai_automation_layer.schemas

        print(f"Mock Internal Credit Scoring: Scoring for app {application_id} with features {list(customer_features.keys())}")
        # Simulate score based on some feature
        simulated_score = 650
        if customer_features.get("monthly_income", 0) > 600000:
            simulated_score += 50
        if customer_features.get("existing_loan_count", 0) > 1:
            simulated_score -= 70

        risk_rating = "MEDIUM"
        if simulated_score >= config.AUTO_APPROVAL_SCORE_THRESHOLD: risk_rating = "LOW"
        elif simulated_score < config.AUTO_REJECTION_SCORE_THRESHOLD: risk_rating = "HIGH"

        return {
            "application_id": application_id,
            "credit_score": simulated_score,
            "risk_rating": risk_rating,
            "recommended_action": "MANUAL_REVIEW", # Default, agent logic will refine
            "reason_codes": ["RC01_MOCK_STABLE_INCOME", "RC05_MOCK_MODERATE_DEBT"],
            "prediction_log_id": "mock_pred_log_" + application_id
        }

    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Credit scoring service request failed: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error during credit scoring: {str(e)}"}


def evaluate_risk_rules(application_data: dict, credit_score_data: dict, extracted_doc_data: dict) -> dict:
    """
    Evaluates the application against a predefined set of risk rules.
    Inputs:
        application_data: Data from the loan application form.
        credit_score_data: Output from the get_credit_score tool.
        extracted_doc_data: Aggregated data from analyzed documents.
    Output: Dictionary with rule evaluation results (e.g., pass/fail, flags).
    """
    # This is a placeholder for a more complex rules engine.
    # Rules could be configured in a database or a separate config file.
    print(f"Mock Risk Rules Evaluation: Evaluating for app_id {application_data.get('id')}")

    flags = []
    overall_assessment = "PASS" # Default

    # Rule 1: DTI Ratio (Debt-to-Income)
    # Assumes 'monthly_debt_repayments' is available in application_data or derived,
    # and 'monthly_income' is in extracted_doc_data or application_data.
    monthly_income = extracted_doc_data.get("net_income", application_data.get("stated_monthly_income", 0))
    monthly_debt = application_data.get("existing_monthly_debt_repayments", 0)
    requested_loan_emi = application_data.get("calculated_requested_emi", 0) # EMI for the requested loan

    total_monthly_debt = monthly_debt + requested_loan_emi

    if monthly_income > 0:
        dti_ratio = total_monthly_debt / monthly_income
        if dti_ratio > config.MAX_DTI_RATIO:
            flags.append({"rule": "MAX_DTI_EXCEEDED", "value": dti_ratio, "threshold": config.MAX_DTI_RATIO, "severity": "HIGH"})
            overall_assessment = "FAIL" # Or "FLAGGED_HIGH_RISK"
    else:
        flags.append({"rule": "INCOME_NOT_VERIFIED", "value": None, "severity": "CRITICAL"})
        overall_assessment = "FAIL"

    # Rule 2: Credit Score Threshold
    credit_score = credit_score_data.get("credit_score", 0)
    if credit_score < config.MIN_ACCEPTABLE_CREDIT_SCORE:
        flags.append({"rule": "CREDIT_SCORE_BELOW_MINIMUM", "value": credit_score, "threshold": config.MIN_ACCEPTABLE_CREDIT_SCORE, "severity": "HIGH"})
        if overall_assessment != "FAIL": overall_assessment = "FAIL" # Don't override if already failed critically

    # Rule 3: Document Verification (Conceptual - assumes some flags from doc analysis)
    if extracted_doc_data.get("has_bounced_cheques") is True:
        flags.append({"rule": "BOUNCED_CHEQUES_DETECTED", "value": True, "severity": "MEDIUM"})
        if overall_assessment == "PASS": overall_assessment = "FLAGGED_MEDIUM_RISK"

    # Rule 4: Loan amount vs income (e.g. max loan is 3x annual income - simplified)
    # annual_income = monthly_income * 12
    # if annual_income > 0 and application_data.get("requested_amount",0) > (3 * annual_income):
    #    flags.append({"rule": "LOAN_AMOUNT_TOO_HIGH_FOR_INCOME", "severity": "MEDIUM"})
    #    if overall_assessment == "PASS": overall_assessment = "FLAGGED_MEDIUM_RISK"

    return {
        "overall_assessment": overall_assessment, # PASS, FAIL, FLAGGED_HIGH_RISK, FLAGGED_MEDIUM_RISK
        "flags": flags,
        "dti_ratio_calculated": dti_ratio if monthly_income > 0 else None
    }

def get_loan_application_details(application_id: str) -> dict:
    """Fetches details of a loan application from the Loan Management module."""
    url = config.GET_LOAN_APP_ENDPOINT.format(application_id=application_id)
    try:
        # response = requests.get(url, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"}) # Example auth
        # response.raise_for_status()
        # return response.json() # Should match LoanApplicationResponse schema

        print(f"Mock API Call: GET {url}")
        # Simulate fetching application data
        if application_id == "APP001_FAIL":
            return {"status": "error", "message": "Application not found in mock."}

        return {
            "id": application_id,
            "application_reference": "REF" + application_id,
            "customer_id": "CUST123",
            "loan_product_id": "PROD_PERS_01",
            "requested_amount": 500000.00,
            "requested_tenor_months": 12,
            "loan_purpose": "Personal expenses",
            "status": "SUBMITTED", # Current status from Loan module
            "stated_monthly_income": 600000.00, # Example field
            "existing_monthly_debt_repayments": 50000.00, # Example field
            "calculated_requested_emi": 45000.00 # Example pre-calculated EMI for requested loan
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to fetch loan application {application_id}: {str(e)}"}


def update_loan_application_decision(application_id: str, decision: str, reason: Optional[str]=None, recommended_amount: Optional[float]=None, recommended_tenor: Optional[int]=None) -> dict:
    """Updates the loan application status and decision in the Loan Management module."""
    url = config.UPDATE_LOAN_APP_STATUS_ENDPOINT.format(application_id=application_id)
    payload = {
        "status": decision.upper(), # e.g., "APPROVED", "REJECTED", "PENDING_DOCUMENTATION"
        "decision_reason": reason,
        # Potentially add recommended_amount/tenor if API supports it
        # "approved_amount": recommended_amount,
        # "approved_tenor": recommended_tenor
    }
    try:
        # response = requests.patch(url, json=payload, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return response.json() # Should match LoanApplicationResponse schema

        print(f"Mock API Call: PATCH {url} with payload {payload}")
        return {
            "id": application_id,
            "status": payload["status"],
            "message": f"Application {application_id} status updated to {payload['status']} (mock)."
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to update loan application {application_id}: {str(e)}"}


if __name__ == '__main__':
    print("--- Testing Credit Analyst Agent Tools ---")

    # Test Document Analysis
    print("\n1. Document Analysis (Payslip):")
    payslip_data = analyze_document_with_ocr_llm("dummy_payslip.pdf", "PAYSLIP")
    print(payslip_data)

    print("\n2. Document Analysis (Bank Statement):")
    statement_data = analyze_document_with_ocr_llm("dummy_statement.pdf", "BANK_STATEMENT")
    print(statement_data)

    # Test Get Loan Application Details
    app_id_test = "APP001_GOOD"
    print(f"\n3. Get Loan Application Details (ID: {app_id_test}):")
    app_details = get_loan_application_details(app_id_test)
    print(app_details)

    if app_details.get("status") != "error":
        # Test Credit Scoring
        # Construct mock features based on app_details and payslip_data/statement_data
        mock_features_for_scoring = {
            "bvn": "22200011122", # Example
            "monthly_income": payslip_data.get("extracted_data", {}).get("net_income", app_details.get("stated_monthly_income")),
            "average_monthly_inflow": statement_data.get("extracted_data", {}).get("average_monthly_inflow"),
            "existing_loan_count": 0, # Example
            "requested_loan_amount": app_details.get("requested_amount")
        }
        print(f"\n4. Get Credit Score (ID: {app_id_test}):")
        score_data = get_credit_score(app_id_test, mock_features_for_scoring)
        print(score_data)

        if score_data.get("status") != "error":
            # Test Risk Rules Evaluation
            print(f"\n5. Evaluate Risk Rules (ID: {app_id_test}):")
            # Aggregate extracted data for rules engine
            aggregated_doc_data = {**payslip_data.get("extracted_data",{}), **statement_data.get("extracted_data",{})}
            risk_eval = evaluate_risk_rules(app_details, score_data, aggregated_doc_data)
            print(risk_eval)

            # Test Update Loan Application Decision
            final_decision = LoanApplicationStatusEnumSchema.APPROVED if risk_eval.get("overall_assessment") == "PASS" and score_data.get("credit_score",0) > config.AUTO_APPROVAL_SCORE_THRESHOLD else LoanApplicationStatusEnumSchema.REJECTED
            decision_reason_text = f"Automated decision based on risk assessment: {risk_eval.get('overall_assessment')} and score: {score_data.get('credit_score')}"
            print(f"\n6. Update Loan Application Decision (ID: {app_id_test}, Decision: {final_decision}):")
            update_result = update_loan_application_decision(app_id_test, final_decision, decision_reason_text)
            print(update_result)

    app_id_fail_fetch = "APP001_FAIL"
    print(f"\n7. Get Loan Application Details (ID: {app_id_fail_fetch}) - Expecting failure:")
    app_details_fail = get_loan_application_details(app_id_fail_fetch)
    print(app_details_fail)
