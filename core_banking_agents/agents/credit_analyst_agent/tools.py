# Tools for Credit Analyst Agent

from langchain.tools import tool
from pydantic import HttpUrl
from typing import Dict, Any, List, Optional
import random
import logging

# Assuming schemas might be imported for type hinting if complex objects are passed (not strictly needed for these mocks)
# from .schemas import DocumentCategory # Example if DocumentCategory enum was used as input type

logger = logging.getLogger(__name__)

@tool("DocumentAnalysisTool")
def document_analysis_tool(document_url: HttpUrl, document_category: str) -> Dict[str, Any]:
    """
    Simulates analysis of a single financial document provided by URL.
    Extracts key information based on the document category using mock logic.

    Args:
        document_url (HttpUrl): URL of the document to be analyzed.
        document_category (str): Category of the document
                                 (e.g., "Identification", "IncomeProof", "AddressProof",
                                 "BankStatement", "BusinessDocument").

    Returns:
        Dict[str, Any]: A dictionary with 'status' ("Success", "Failed", "UnsupportedType"),
                        'document_category_processed': actual category processed,
                        'extracted_data': A dictionary of extracted fields, or None if failed.
                        'error_message': Present if status is "Failed".
    """
    logger.info(f"DocumentAnalysisTool: Processing document '{document_url}' of category '{document_category}'")

    if "error" in str(document_url).lower():
        return {"status": "Failed", "document_category_processed": document_category, "extracted_data": None, "error_message": "Simulated error accessing or reading document."}

    extracted_data: Dict[str, Any] = {}
    status = "Success"

    if document_category == "Identification": # e.g., National ID, Passport
        extracted_data = {
            "id_type": "National ID", "id_number": f"NIN{random.randint(10000000000, 99999999999)}",
            "full_name_on_id": "Mock Chiamaka Adeyemi", "date_of_birth_on_id": "1988-07-10",
            "issue_date": "2020-01-15", "expiry_date": "2030-01-14"
        }
    elif document_category == "IncomeProof": # e.g., Payslip, Employment Letter
        extracted_data = {
            "proof_type": "Payslip", "company_name": "Big Corp Inc.",
            "net_monthly_pay_ngn": random.uniform(300000, 1000000),
            "pay_date": "2023-09-28"
        }
    elif document_category == "AddressProof": # e.g., Utility Bill
        extracted_data = {
            "utility_type": "Electricity Bill", "provider_name": "Eko Electric",
            "address_on_bill": "15, Freedom Way, Lekki Phase 1, Lagos", # Should match applicant's
            "bill_date": "2023-09-15", "name_on_bill": "Mock Chiamaka Adeyemi"
        }
    elif document_category == "BankStatement":
        avg_balance = random.uniform(100000, 2000000)
        extracted_data = {
            "bank_name": "First Mock Bank", "account_number_masked": f"xxxxxx{random.randint(1000,9999)}",
            "statement_period": "Jan 2023 - Jun 2023",
            "total_credits_ngn": avg_balance * 6 * random.uniform(0.8, 1.2), # Rough estimate
            "total_debits_ngn": avg_balance * 6 * random.uniform(0.6, 1.0),
            "average_balance_ngn": avg_balance,
            "salary_detected_ngn": random.uniform(300000, 1000000) if random.choice([True, False]) else None,
            "bounced_cheques_count": random.choice([0,0,0,1]),
            "loan_repayments_detected": random.choice([True, False])
        }
    elif document_category == "BusinessDocument": # e.g., CAC Registration
        extracted_data = {
            "document_name": "CAC Certificate of Incorporation", "registration_number": f"RC{random.randint(100000, 999999)}",
            "business_name": "Adeyemi Catering & Events", "registration_date": "2019-05-20",
            "directors": ["Chiamaka Adeyemi", "Bola Tinubu (Mock)"] # Example
        }
    else:
        status = "UnsupportedType"
        logger.warning(f"Unsupported document category: {document_category}")
        return {"status": status, "document_category_processed": document_category, "extracted_data": None, "error_message": f"Document category '{document_category}' is not supported by this mock tool."}

    return {"status": status, "document_category_processed": document_category, "extracted_data": extracted_data}


@tool("CreditScoringTool")
def credit_scoring_tool(applicant_id: str, financial_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates a credit scoring model based on applicant's financial summary.

    Args:
        applicant_id (str): Unique identifier for the applicant.
        financial_summary (Dict[str, Any]): A dictionary containing key financial metrics
                                           (e.g., 'monthly_income_ngn', 'total_existing_debt_ngn',
                                           'credit_history_length_months', 'bureau_score_if_any').

    Returns:
        Dict[str, Any]: A dictionary with 'applicant_id', 'credit_score' (int),
                        'risk_level' ("Low", "Medium", "High"), and 'assessment_details' (str).
    """
    logger.info(f"CreditScoringTool: Scoring applicant ID '{applicant_id}' with summary: {financial_summary}")

    # Mock scoring logic
    score = random.randint(300, 850) # Typical credit score range
    income = financial_summary.get("monthly_income_ngn", 0)
    debt = financial_summary.get("total_existing_debt_ngn", 0)
    bureau_score = financial_summary.get("bureau_score_if_any", score) # Use bureau score if available

    # Adjust score based on some factors (very simplified)
    if income > 500000: score += 50
    if income < 100000: score -= 50
    if debt > income * 0.5 and income > 0 : score -= 70 # High DTI
    if financial_summary.get("credit_history_length_months", 0) < 12: score -= 30

    score = max(300, min(bureau_score, score, 850)) # Ensure score is within bounds and considers bureau score

    risk_level = "Medium"
    if score >= 720: risk_level = "Low"
    elif score < 580: risk_level = "High"

    assessment_details = f"Mock assessment: Score based on income NGN {income:,.0f}, debt NGN {debt:,.0f}. "
    if bureau_score != score and "bureau_score_if_any" in financial_summary:
        assessment_details += f"Initial bureau score was {financial_summary.get('bureau_score_if_any')}. "
    assessment_details += f"Calculated internal score: {score}."


    return {
        "applicant_id": applicant_id,
        "credit_score": score,
        "risk_level": risk_level,
        "assessment_details": assessment_details,
        "model_version": "MockScorer_v1.2"
    }

@tool("RiskRulesTool")
def risk_rules_tool(application_data: Dict[str, Any], credit_score_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates applying predefined bank risk rules to a loan application.

    Args:
        application_data (Dict[str, Any]): The full loan application data.
        credit_score_result (Dict[str, Any]): The output from the CreditScoringTool.

    Returns:
        Dict[str, Any]: With 'passed_rules': List[str], 'failed_rules': List[str],
                        'overall_risk_assessment_from_rules': ("Accept", "Reject", "Refer").
    """
    logger.info(f"RiskRulesTool: Applying rules for application_id '{application_data.get('application_id')}'")

    passed_rules: List[str] = []
    failed_rules: List[str] = []

    # Example Rules:
    # 1. Minimum Credit Score
    min_score_threshold = 600
    applicant_score = credit_score_result.get("credit_score", 0)
    if applicant_score >= min_score_threshold:
        passed_rules.append(f"MinCreditScore: Score {applicant_score} >= {min_score_threshold}")
    else:
        failed_rules.append(f"MinCreditScore: Score {applicant_score} < {min_score_threshold}")

    # 2. Debt-to-Income (DTI) Ratio (Simplified)
    # Assuming DTI is calculated elsewhere or application_data contains income and total debt figures
    monthly_income = application_data.get("applicant_details", {}).get("monthly_income_ngn", 0)
    # Assume total monthly debt payments are estimated or provided
    estimated_monthly_debt_payments = application_data.get("estimated_total_monthly_debt_repayments_ngn", monthly_income * 0.2) # Mock
    requested_loan_monthly_payment = (application_data.get("loan_amount_requested_ngn",0) / application_data.get("requested_loan_tenor_months",12)) * 1.1 # Rough estimate with interest

    total_monthly_payments = estimated_monthly_debt_payments + requested_loan_monthly_payment
    dti_ratio = (total_monthly_payments / monthly_income) if monthly_income > 0 else 1.0 # Default to high if no income
    max_dti_threshold = 0.50 # 50%

    if dti_ratio <= max_dti_threshold:
        passed_rules.append(f"DTIRatio: Ratio {dti_ratio:.2%} <= {max_dti_threshold:.0%}")
    else:
        failed_rules.append(f"DTIRatio: Ratio {dti_ratio:.2%} > {max_dti_threshold:.0%}")

    # 3. Loan Amount vs Income (Affordability)
    max_loan_to_annual_income_ratio = 2.0 # Max loan is 2x annual income
    annual_income = monthly_income * 12
    requested_loan = application_data.get("loan_amount_requested_ngn", 0)
    if annual_income > 0 and (requested_loan / annual_income) <= max_loan_to_annual_income_ratio:
        passed_rules.append(f"LoanToIncomeRatio: Loan {requested_loan:,.0f} vs Annual Income {annual_income:,.0f} is within {max_loan_to_annual_income_ratio}x limit.")
    elif annual_income <=0 and requested_loan > 0:
        failed_rules.append(f"LoanToIncomeRatio: No income provided for requested loan of {requested_loan:,.0f}.")
    elif annual_income > 0 : # Implies ratio was too high
         failed_rules.append(f"LoanToIncomeRatio: Loan {requested_loan:,.0f} vs Annual Income {annual_income:,.0f} exceeds {max_loan_to_annual_income_ratio}x limit.")


    # Determine overall assessment based on rules
    overall_assessment = "Accept"
    if any("MinCreditScore" in rule for rule in failed_rules): # Critical rule
        overall_assessment = "Reject"
    elif failed_rules: # Some non-critical rules failed
        overall_assessment = "Refer" # Refer for manual review

    return {
        "passed_rules": passed_rules,
        "failed_rules": failed_rules,
        "overall_risk_assessment_from_rules": overall_assessment,
        "rules_engine_version": "MockRules_v0.9"
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("--- Testing CreditAnalystAgent Tools ---")

    print("\n1. Testing DocumentAnalysisTool:")
    doc_res1 = document_analysis_tool.run({"document_url": HttpUrl("https://example.com/statement.pdf"), "document_category": "BankStatement"})
    print(f"  BankStatement Analysis: Status {doc_res1['status']}, Avg Balance (mock): {doc_res1.get('extracted_data',{}).get('average_balance_ngn')}")
    doc_res2 = document_analysis_tool.run({"document_url": HttpUrl("https://example.com/cac.jpg"), "document_category": "BusinessDocument"})
    print(f"  BusinessDocument Analysis: Status {doc_res2['status']}, Biz Name (mock): {doc_res2.get('extracted_data',{}).get('business_name')}")
    doc_res_err = document_analysis_tool.run({"document_url": HttpUrl("https://example.com/error.pdf"), "document_category": "IncomeProof"})
    print(f"  Error Doc Analysis: Status {doc_res_err['status']}")
    doc_res_unsupported = document_analysis_tool.run({"document_url": HttpUrl("https://example.com/unknown.docx"), "document_category": "UnknownType"})
    print(f"  Unsupported Doc Analysis: Status {doc_res_unsupported['status']}")


    print("\n2. Testing CreditScoringTool:")
    fin_summary_good = {"monthly_income_ngn": 800000, "total_existing_debt_ngn": 100000, "credit_history_length_months": 36, "bureau_score_if_any": 750}
    score_res_good = credit_scoring_tool.run({"applicant_id": "APP001", "financial_summary": fin_summary_good})
    print(f"  Good Applicant Score: {score_res_good['credit_score']}, Risk: {score_res_good['risk_level']}")

    fin_summary_avg = {"monthly_income_ngn": 250000, "total_existing_debt_ngn": 150000, "credit_history_length_months": 10} # No bureau score
    score_res_avg = credit_scoring_tool.run({"applicant_id": "APP002", "financial_summary": fin_summary_avg})
    print(f"  Average Applicant Score: {score_res_avg['credit_score']}, Risk: {score_res_avg['risk_level']}")

    fin_summary_poor = {"monthly_income_ngn": 80000, "total_existing_debt_ngn": 50000, "credit_history_length_months": 5, "bureau_score_if_any": 450}
    score_res_poor = credit_scoring_tool.run({"applicant_id": "APP003", "financial_summary": fin_summary_poor})
    print(f"  Poor Applicant Score: {score_res_poor['credit_score']}, Risk: {score_res_poor['risk_level']}")


    print("\n3. Testing RiskRulesTool:")
    app_data_pass = {
        "application_id": "LOAN001",
        "applicant_details": {"monthly_income_ngn": 700000},
        "loan_amount_requested_ngn": 1000000,
        "requested_loan_tenor_months": 24,
        "estimated_total_monthly_debt_repayments_ngn": 50000
    }
    score_data_pass = {"credit_score": 720}
    rules_res_pass = risk_rules_tool.run({"application_data": app_data_pass, "credit_score_result": score_data_pass})
    print(f"  Rules Pass: Assessment '{rules_res_pass['overall_risk_assessment_from_rules']}', Failed: {rules_res_pass['failed_rules']}")

    app_data_fail_score = app_data_pass.copy()
    score_data_fail_score = {"credit_score": 550} # Fails min score
    rules_res_fail_score = risk_rules_tool.run({"application_data": app_data_fail_score, "credit_score_result": score_data_fail_score})
    print(f"  Rules Fail (Score): Assessment '{rules_res_fail_score['overall_risk_assessment_from_rules']}', Failed: {rules_res_fail_score['failed_rules']}")

    app_data_fail_dti = {
        "application_id": "LOAN002",
        "applicant_details": {"monthly_income_ngn": 300000},
        "loan_amount_requested_ngn": 2000000, # High loan amount
        "requested_loan_tenor_months": 36,
        "estimated_total_monthly_debt_repayments_ngn": 100000 # High existing debt
    }
    score_data_ok_dti = {"credit_score": 680}
    rules_res_fail_dti = risk_rules_tool.run({"application_data": app_data_fail_dti, "credit_score_result": score_data_ok_dti})
    print(f"  Rules Fail (DTI): Assessment '{rules_res_fail_dti['overall_risk_assessment_from_rules']}', Failed: {rules_res_fail_dti['failed_rules']}")

    print("\nCredit Analyst Agent tools implemented with mocks.")
