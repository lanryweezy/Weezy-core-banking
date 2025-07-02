# Tools for Compliance Agent
import requests
import json
from datetime import datetime
from . import config
# from weezy_cbs.compliance_regulatory_reporting.schemas import SanctionScreeningRequest # If calling internal service
# from weezy_cbs.core_infrastructure_config_engine.schemas import AuditLogCreateRequest # Conceptual

# Placeholder for schemas if not importing
class SanctionScreeningRequestSchema(dict): pass
class AuditLogCreateRequestSchema(dict): pass

# --- Sanctions List Screening Tool ---
def screen_entity_against_sanctions_lists(entity_name: str, entity_type: str = "INDIVIDUAL", bvn: Optional[str] = None, other_identifiers: Optional[dict] = None) -> dict:
    """
    Screens an entity (customer, counterparty) against configured sanctions lists.
    Inputs:
        entity_name: Name of the individual or organization.
        entity_type: "INDIVIDUAL" or "ORGANIZATION".
        bvn: BVN if available.
        other_identifiers: Dictionary of other relevant data (e.g., DOB, nationality, address).
    Output:
        Dictionary with screening result (e.g., match_found: True/False, match_details, lists_checked).
    """
    # This tool would call the SANCTIONS_SCREENING_SERVICE_URL (internal wrapper)
    # or directly call a third-party sanctions API provider.

    payload = SanctionScreeningRequestSchema(
        name_to_screen=entity_name,
        entity_type=entity_type.upper(),
        bvn_to_screen=bvn,
        # Pass other_identifiers if the internal service or external API supports them
        # Example: date_of_birth=other_identifiers.get('dob')
    )

    try:
        # response = requests.post(config.SANCTIONS_SCREENING_SERVICE_URL, json=payload)
        # response.raise_for_status()
        # return response.json() # Should match SanctionScreeningResult schema

        print(f"Mock Sanctions Screening: Screening '{entity_name}' (BVN: {bvn})")
        # Simulate a match for specific names for testing
        match_found = False
        match_details_list = []
        if "sanctioned_person" in entity_name.lower():
            match_found = True
            match_details_list.append({
                "list_name": "OFAC_SDN_MOCK",
                "matched_name": entity_name,
                "score": 0.98,
                "details": "Entity listed on OFAC SDN (Mock Data). Reason: Terrorism Financing."
            })

        return {
            "name_screened": entity_name,
            "screening_date": datetime.utcnow().isoformat(),
            "match_found": match_found,
            "match_details": match_details_list,
            "sanction_lists_checked": ["OFAC_SDN_MOCK", "UN_CONSOLIDATED_MOCK", "EU_CFSP_MOCK"]
        }

    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Sanctions screening service request failed: {str(e)}", "match_found": None} # Indicate error clearly
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error during sanctions screening: {str(e)}", "match_found": None}

# --- AML Rules Evaluation Tool (Conceptual) ---
def evaluate_transaction_against_aml_rules(transaction_data: dict, customer_profile: Optional[dict] = None) -> dict:
    """
    Evaluates a transaction against AML rules (e.g., large cash, high velocity, high-risk country).
    This is a simplified version. A real system might use a dedicated rules engine or call
    a service in the compliance_regulatory_reporting module.
    Inputs:
        transaction_data: Dictionary of transaction details.
        customer_profile: Optional dictionary of customer risk profile / history.
    Output:
        Dictionary with flags raised, risk assessment.
    """
    print(f"Mock AML Rules Evaluation: Evaluating transaction {transaction_data.get('transaction_id')}")
    flags = []
    aml_risk_level = "LOW"

    # Example Rule 1: Large Cash Transaction (different from CTR, this is for general AML scrutiny)
    if transaction_data.get("type") in ["CASH_DEPOSIT", "CASH_WITHDRAWAL"] and \
       transaction_data.get("amount", 0) > config.LARGE_TRANSACTION_AML_THRESHOLD_NGN and \
       transaction_data.get("currency") == "NGN":
        flags.append({
            "rule_code": "AML_LARGE_CASH",
            "description": f"Large cash transaction of {transaction_data['amount']} NGN.",
            "severity": "MEDIUM"
        })
        aml_risk_level = "MEDIUM"

    # Example Rule 2: Transaction involving a high-risk country (from customer or counterparty data)
    # This requires customer_profile or counterparty details within transaction_data
    # involved_country = customer_profile.get("country_of_residence") or transaction_data.get("counterparty_country")
    # if involved_country and involved_country.upper() in config.HIGH_RISK_COUNTRY_LIST:
    #    flags.append({"rule_code": "AML_HIGH_RISK_COUNTRY", "description": f"Transaction involves high-risk country: {involved_country}.", "severity": "HIGH"})
    #    aml_risk_level = "HIGH" if aml_risk_level != "CRITICAL" else "CRITICAL"

    # Example Rule 3: Structuring (multiple smaller transactions to avoid thresholds)
    # This requires looking at recent transaction history for the customer.
    # if customer_profile and customer_profile.get("recent_cash_tx_pattern") == "SUSPICIOUS_STRUCTURING":
    #    flags.append({"rule_code": "AML_POSSIBLE_STRUCTURING", "description": "Pattern of transactions suggests potential structuring.", "severity": "HIGH"})
    #    aml_risk_level = "HIGH"

    return {
        "transaction_id": transaction_data.get("transaction_id"),
        "aml_risk_level": aml_risk_level, # LOW, MEDIUM, HIGH, CRITICAL
        "flags": flags # List of dictionaries, each describing a triggered rule/flag
    }

# --- Audit Trail Generation Tool ---
def log_compliance_action_to_audit_trail(
    action_type: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    summary: Optional[str] = None,
    details_before: Optional[dict] = None,
    details_after: Optional[dict] = None,
    status: str = "SUCCESS",
    performed_by_agent_id: str = "ComplianceAgent" # Or pass specific user ID
    ) -> dict:
    """
    Logs a compliance-related action to the central audit trail.
    This would call an API of the core_infrastructure_config_engine.
    """
    payload = AuditLogCreateRequestSchema(
        username_performing_action=performed_by_agent_id,
        action_type=f"COMPLIANCE_{action_type.upper()}", # Prefix to denote source
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        details_before_json=details_before, # Pydantic will handle dict to JSON string if model expects string
        details_after_json=details_after,
        status=status.upper(),
        # ip_address might be system's IP for agent actions
    )
    try:
        # response = requests.post(config.AUDIT_LOG_API_URL, json=payload)
        # response.raise_for_status()
        # return {"status": "success", "audit_log_id": response.json().get("id"), "message": "Action logged to audit trail."}

        print(f"Mock Audit Log: Action='{payload['action_type']}', Entity='{entity_type}:{entity_id}', Summary='{summary}'")
        return {"status": "success", "audit_log_id": "mock_audit_" + str(random.randint(1000,9999)), "message": "Action logged to audit trail (mock)."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to log action to audit trail: {str(e)}"}


# --- Regulatory Report Preparation/Submission Tools (Conceptual) ---
def prepare_suspicious_transaction_report_data(suspicious_activity_log_id: str, transaction_details: dict, customer_details: dict, reason_for_suspicion: str) -> dict:
    """
    Gathers and formats data required for an STR (NFIU).
    This would involve fetching comprehensive data from various modules.
    Output: A dictionary structured according to STR requirements.
    """
    # This is highly complex and specific to NFIU's goAML format or other submission methods.
    # For mock, just structure the inputs.
    print(f"Mock STR Data Prep: For SAL ID {suspicious_activity_log_id}")
    str_data = {
        "report_type": "STR",
        "suspicious_activity_ref": suspicious_activity_log_id,
        "transaction_info": transaction_details,
        "customer_info": customer_details,
        "grounds_for_suspicion": reason_for_suspicion,
        "reporting_institution_details": {"name": "Weezy Bank Plc", "rc_number": "RC123456"},
        "submission_date": datetime.utcnow().isoformat()
    }
    return str_data

def submit_regulatory_report(report_type: str, report_data: dict, report_period_end_date: str) -> dict:
    """
    "Submits" a regulatory report (e.g., STR, CTR data for aggregation).
    In reality, this might mean:
    - Generating an XML/CSV file and flagging it for manual upload.
    - Calling a specific API of the compliance_regulatory_reporting module to queue generation.
    - Directly calling a regulator's API if available.
    """
    endpoint = None
    if report_type.upper() == "STR":
        endpoint = config.SUBMIT_SAR_ENDPOINT # Conceptual: might take structured data
    elif report_type.upper() == "CTR_TRANSACTION": # Logging a single transaction for CTR aggregation
        endpoint = config.LOG_CTR_ENDPOINT

    if not endpoint:
        return {"status": "error", "message": f"No submission endpoint configured for report type: {report_type}"}

    payload = {
        "report_data": report_data,
        "reporting_period_end": report_period_end_date # If applicable for the report type
    }
    try:
        # response = requests.post(endpoint, json=payload, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return {"status": "success", "submission_reference": response.json().get("submission_id"), "message": f"{report_type} data submitted for processing."}

        print(f"Mock Regulatory Submission: Type='{report_type}', Endpoint='{endpoint}'")
        return {"status": "success", "submission_reference": "MOCK_REG_SUB_" + str(random.randint(1000,9999)), "message": f"{report_type} data submitted (mock)."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to submit {report_type} data: {str(e)}"}

# --- Data Fetching Tools (from other CBS modules) ---
def get_customer_details_for_compliance(customer_id: str) -> dict:
    """Fetches customer data relevant for compliance checks."""
    url = f"{config.CUSTOMER_DATA_API_URL}/{customer_id}/profile360" # Example endpoint
    try:
        # response = requests.get(url, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return response.json() # Should match CustomerProfileResponse or similar

        print(f"Mock API Call: GET {url}")
        if customer_id == "CUST_UNKNOWN": return {"status": "error", "message": "Customer not found (mock)."}
        return {
            "id": customer_id, "bvn": f"222{customer_id[-3:]}00011", "nin": f"111{customer_id[-3:]}99922",
            "first_name": "Compliance", "last_name": f"User_{customer_id[-3:]}", "email": f"compliance{customer_id[-3:]}@example.com",
            "phone_number": f"080123{customer_id[-3:]}45", "date_of_birth": "1985-05-15", "address": "123 Compliance Street",
            "account_tier": "Tier 2", "is_verified_bvn": True, "is_pep": False, "risk_rating_manual": "MEDIUM"
            # ... other fields from CustomerProfileResponse
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to fetch customer details for {customer_id}: {str(e)}"}

def get_transaction_details_for_compliance(transaction_id: str) -> dict:
    """Fetches transaction data relevant for compliance checks."""
    url = f"{config.TRANSACTION_DATA_API_URL}/{transaction_id}" # Example endpoint
    try:
        # response = requests.get(url, headers={"Authorization": f"Bearer {config.WEEZY_API_KEY}"})
        # response.raise_for_status()
        # return response.json() # Should match TransactionDetailResponse

        print(f"Mock API Call: GET {url}")
        if transaction_id == "TXN_UNKNOWN": return {"status": "error", "message": "Transaction not found (mock)."}
        return {
            "id": transaction_id, "transaction_type": "NIP_TRANSFER", "channel": "MOBILE_APP",
            "status": "SUCCESSFUL", "amount": 1500000.00, "currency": "NGN",
            "debit_account_number": "0123456789", "debit_customer_id": "CUST123",
            "credit_account_number": "9876543210", "credit_account_name": "Beneficiary Name", "credit_bank_code": "058",
            "narration": "Payment for goods", "initiated_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            "external_transaction_id": "NIP_SESS_" + transaction_id
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to fetch transaction details for {transaction_id}: {str(e)}"}


if __name__ == '__main__':
    from typing import Optional # For type hinting in main block
    print("--- Testing Compliance Agent Tools ---")

    # 1. Test Sanctions Screening
    print("\n1. Sanctions Screening (Clean Name):")
    clean_screening = screen_entity_against_sanctions_lists("John Doe", "INDIVIDUAL", "22211100099")
    print(json.dumps(clean_screening, indent=2))

    print("\n2. Sanctions Screening (Sanctioned Name):")
    sanctioned_screening = screen_entity_against_sanctions_lists("Sanctioned Person X", "INDIVIDUAL", "22211100088")
    print(json.dumps(sanctioned_screening, indent=2))

    # 2. Test AML Rules Evaluation (conceptual)
    mock_normal_tx = {"transaction_id": "TXN_NORM_COMPLY", "type": "NIP", "amount": 50000.00, "currency": "NGN"}
    print("\n3. AML Rules Evaluation (Normal Transaction):")
    aml_eval_normal = evaluate_transaction_against_aml_rules(mock_normal_tx)
    print(json.dumps(aml_eval_normal, indent=2))

    mock_large_cash_tx = {"transaction_id": "TXN_LCASH_COMPLY", "type": "CASH_DEPOSIT", "amount": 3000000.00, "currency": "NGN"}
    print("\n4. AML Rules Evaluation (Large Cash Transaction):")
    aml_eval_large_cash = evaluate_transaction_against_aml_rules(mock_large_cash_tx)
    print(json.dumps(aml_eval_large_cash, indent=2))

    # 3. Test Audit Log
    print("\n5. Log Compliance Action to Audit Trail:")
    audit_log_result = log_compliance_action_to_audit_trail(
        action_type="SANCTION_SCREEN_PERFORMED",
        entity_type="CUSTOMER_BVN",
        entity_id="22211100099",
        summary="Sanction screening performed for John Doe.",
        details_after=clean_screening # Example of storing result as 'after' state
    )
    print(json.dumps(audit_log_result, indent=2))

    # 4. Test Regulatory Report Prep/Submission (conceptual)
    mock_cust_details_for_str = get_customer_details_for_compliance("CUST_FLAGGED")
    mock_tx_details_for_str = get_transaction_details_for_compliance("TXN_FLAGGED_FOR_STR")

    if mock_cust_details_for_str.get("status") != "error" and mock_tx_details_for_str.get("status") != "error":
        print("\n6. Prepare STR Data:")
        str_data = prepare_suspicious_transaction_report_data(
            "SAL_001", mock_tx_details_for_str, mock_cust_details_for_str,
            "Unusual transaction pattern inconsistent with customer profile and large sum to new beneficiary."
        )
        print(json.dumps(str_data, indent=2, default=str)) # Use default=str for datetime

        print("\n7. Submit STR Data (Conceptual):")
        str_submit_result = submit_regulatory_report("STR", str_data, date.today().isoformat())
        print(json.dumps(str_submit_result, indent=2))
    else:
        print("\n6 & 7. STR Prep/Submission skipped due to mock data fetch error.")

    print("\n8. Fetch Customer Details:")
    cust_data = get_customer_details_for_compliance("CUST123")
    print(json.dumps(cust_data, indent=2))

    print("\n9. Fetch Transaction Details:")
    tx_data = get_transaction_details_for_compliance("TXNABC")
    print(json.dumps(tx_data, indent=2))
