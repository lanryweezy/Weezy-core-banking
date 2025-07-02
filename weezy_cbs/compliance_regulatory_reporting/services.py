# Service layer for Compliance & Regulatory Reporting Module
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from . import models, schemas
from .models import ReportStatusEnum, ReportNameEnum # Direct enum access
from datetime import datetime, date, timedelta
import json
import csv # For CSV report generation
import xml.etree.ElementTree as ET # For XML report generation (basic)
# Potentially use libraries like `openpyxl` for Excel reports.

# Placeholder for other service integrations & data sources
# from weezy_cbs.customer_identity_management.services import get_customer_details_for_reporting
# from weezy_cbs.accounts_ledger_management.services import get_account_data_for_reporting
# from weezy_cbs.transaction_management.services import get_transaction_data_for_reporting
# from weezy_cbs.loan_management_module.services import get_loan_data_for_reporting
# from weezy_cbs.integrations import sanction_list_provider_service # e.g. Refinitiv, Dow Jones
# from weezy_cbs.shared import exceptions, file_storage_service # To store generated reports

class ReportGenerationException(Exception): pass
class SanctionScreeningException(Exception): pass

# --- Report Log Management ---
def create_report_log_entry(db: Session, report_request: schemas.ReportGenerationRequest, user_id: Optional[str] = None) -> models.GeneratedReportLog:
    # Check if a report for this name and period (end date) already exists and is not in a failed state
    existing_report = db.query(models.GeneratedReportLog).filter(
        models.GeneratedReportLog.report_name == report_request.report_name,
        models.GeneratedReportLog.reporting_period_end_date == report_request.reporting_period_end_date,
        models.GeneratedReportLog.status.notin_([ReportStatusEnum.FAILED_GENERATION, ReportStatusEnum.PENDING_GENERATION]) # Allow re-trigger if failed or still pending
    ).first()
    if existing_report:
        # Depending on policy, either return existing or raise error, or allow re-generation if status allows
        # For now, let's prevent duplicate active generation
        if existing_report.status not in [ReportStatusEnum.FAILED_GENERATION, ReportStatusEnum.PENDING_GENERATION]: # Added PENDING_GENERATION here
             raise ReportGenerationException(f"Report {report_request.report_name.value} for period ending {report_request.reporting_period_end_date} already exists with status {existing_report.status.value}.")


    db_log = models.GeneratedReportLog(
        report_name=report_request.report_name,
        reporting_period_start_date=report_request.reporting_period_start_date,
        reporting_period_end_date=report_request.reporting_period_end_date,
        status=ReportStatusEnum.PENDING_GENERATION, # Initial status
        generated_by_user_id=user_id
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def update_report_log_status(
    db: Session, report_log_id: int, new_status: ReportStatusEnum,
    details: Optional[schemas.ReportStatusUpdateRequest] = None
) -> models.GeneratedReportLog:

    report_log = db.query(models.GeneratedReportLog).filter(models.GeneratedReportLog.id == report_log_id).with_for_update().first()
    if not report_log:
        raise ReportGenerationException(f"Report log ID {report_log_id} not found.")

    report_log.status = new_status
    if new_status == ReportStatusEnum.GENERATED and details:
        report_log.generated_at = datetime.utcnow()
        report_log.file_path_or_url = details.file_path_or_url
        # report_log.checksum = calculate_checksum(details.file_path_or_url) # If file path is local
    elif new_status == ReportStatusEnum.SUBMITTED and details:
        report_log.submitted_at = datetime.utcnow()
        report_log.submission_reference = details.submission_reference
    # Add more status-specific updates

    if details and details.notes:
        report_log.notes = (report_log.notes + "; " if report_log.notes else "") + details.notes

    db.commit()
    db.refresh(report_log)
    return report_log

def get_report_log(db: Session, report_log_id: int) -> Optional[models.GeneratedReportLog]:
    return db.query(models.GeneratedReportLog).filter(models.GeneratedReportLog.id == report_log_id).first()

def get_all_report_logs(db: Session, skip: int = 0, limit: int = 100, report_name: Optional[ReportNameEnum]=None, status: Optional[ReportStatusEnum]=None) -> List[models.GeneratedReportLog]:
    query = db.query(models.GeneratedReportLog)
    if report_name:
        query = query.filter(models.GeneratedReportLog.report_name == report_name)
    if status:
        query = query.filter(models.GeneratedReportLog.status == status)
    return query.order_by(models.GeneratedReportLog.reporting_period_end_date.desc(), models.GeneratedReportLog.id.desc()).offset(skip).limit(limit).all()

# --- Report Generation (Conceptual - Specific logic for each report type) ---
def _generate_cbn_crms_report_data(db: Session, start_date: date, end_date: date) -> List[dict]:
    # Query loan_management_module for all relevant loan data (new loans, performing, NPLs, restructures, write-offs)
    # within the reporting period.
    # Format data according to CRMS XML schema specifications.
    # loan_data = get_loan_data_for_reporting(db, start_date, end_date, report_type="CRMS")
    # Example structure (highly simplified):
    return [
        {"loan_id": "L001", "bvn": "11122233344", "amount_disbursed": 100000, "status": "PERFORMING", "npl_since": None},
        {"loan_id": "L002", "bvn": "55566677788", "amount_disbursed": 500000, "status": "NPL", "npl_since": "2023-01-15"},
    ]

def _generate_nfiu_ctr_report_data(db: Session, start_date: date, end_date: date) -> List[schemas.CTRRecordSchema]:
    # Query transaction_management and/or deposit_collection_module for cash transactions
    # exceeding NFIU thresholds (e.g., individuals > 5M, corporates > 10M).
    # Individual transactions or aggregated daily transactions per customer might be needed.
    # cash_transactions = get_cash_transactions_for_ctr(db, start_date, end_date)
    # Example (simplified):
    return [
        schemas.CTRRecordSchema(transaction_date=date(2023,10,3), transaction_amount=decimal.Decimal("6000000.00"), transaction_currency="NGN", customer_bvn="123...", customer_name="John Doe", account_number="012...", transaction_type="CASH_DEPOSIT"),
    ]

def _format_data_as_xml(data: List[dict], root_element_name: str, item_element_name: str) -> str:
    # Basic XML formatter. Real reports need specific schemas and namespaces.
    root = ET.Element(root_element_name)
    for item_data in data:
        item_el = ET.SubElement(root, item_element_name)
        for key, val in item_data.items():
            child = ET.SubElement(item_el, str(key))
            child.text = str(val)
    return ET.tostring(root, encoding='unicode')

def _format_data_as_csv(data: List[dict], fieldnames: List[str]) -> str:
    import io
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def generate_report_file(db: Session, report_log_id: int) -> models.GeneratedReportLog:
    report_log = db.query(models.GeneratedReportLog).filter(models.GeneratedReportLog.id == report_log_id).with_for_update().first()
    if not report_log or report_log.status != ReportStatusEnum.PENDING_GENERATION:
        raise ReportGenerationException("Report log not found or not pending generation.")

    report_log.status = ReportStatusEnum.GENERATING
    db.commit() # Commit status change before long operation

    try:
        data = []
        file_content_str = ""
        file_format = "TXT" # Default

        if report_log.report_name == ReportNameEnum.CBN_CRMS:
            data = _generate_cbn_crms_report_data(db, report_log.reporting_period_start_date, report_log.reporting_period_end_date)
            # CRMS is usually XML, requires specific schema. This is a placeholder.
            file_content_str = _format_data_as_xml(data, "CRMSReport", "LoanRecord")
            file_format = "XML"
        elif report_log.report_name == ReportNameEnum.NFIU_CTR:
            ctr_records_schema = _generate_nfiu_ctr_report_data(db, report_log.reporting_period_start_date, report_log.reporting_period_end_date)
            # Convert Pydantic schema list to list of dicts for CSV
            data_for_csv = [record.dict() for record in ctr_records_schema]
            if data_for_csv:
                 fieldnames = list(data_for_csv[0].keys())
                 file_content_str = _format_data_as_csv(data_for_csv, fieldnames)
            else:
                 file_content_str = "No CTR data for the period."
            file_format = "CSV"
        # Add cases for NFIU_STR, NDIC_RETURNS, CBN_FINA, CBN_OVERSIGHT etc.
        else:
            raise NotImplementedError(f"Report generation for {report_log.report_name.value} not implemented.")

        # Save file_content_str to a file storage (e.g., S3, local disk)
        # file_path = file_storage_service.save_report_file(
        #     report_log.report_name.value,
        #     report_log.reporting_period_end_date,
        #     file_content_str,
        #     file_format
        # )
        mock_file_path = f"/reports_storage/{report_log.report_name.value}_{report_log.reporting_period_end_date}.{file_format.lower()}"

        report_log.status = ReportStatusEnum.GENERATED
        report_log.generated_at = datetime.utcnow()
        report_log.file_path_or_url = mock_file_path
        report_log.file_format = file_format
        # report_log.checksum = calculate_checksum(mock_file_path) # If file is accessible
        db.commit()

    except Exception as e:
        report_log.status = ReportStatusEnum.FAILED_GENERATION
        report_log.notes = f"Generation failed: {str(e)}"
        db.commit()
        raise ReportGenerationException(f"Failed to generate report {report_log_id}: {str(e)}")

    db.refresh(report_log)
    return report_log


# --- AML Rule Management (Admin) ---
def create_aml_rule(db: Session, rule_in: schemas.AMLRuleCreateRequest) -> models.AMLRule:
    existing_rule = db.query(models.AMLRule).filter(models.AMLRule.rule_code == rule_in.rule_code).first()
    if existing_rule:
        raise InvalidOperationException(f"AML Rule with code {rule_in.rule_code} already exists.")

    db_rule = models.AMLRule(
        rule_code=rule_in.rule_code,
        description=rule_in.description,
        parameters_json=json.dumps(rule_in.parameters_json) if rule_in.parameters_json else None,
        severity=rule_in.severity,
        action_to_take=rule_in.action_to_take,
        is_active=rule_in.is_active
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

def update_aml_rule(db: Session, rule_id: int, rule_update: schemas.AMLRuleUpdateRequest) -> models.AMLRule:
    db_rule = db.query(models.AMLRule).filter(models.AMLRule.id == rule_id).first()
    if not db_rule:
        raise NotFoundException(f"AML Rule with ID {rule_id} not found.")

    update_data = rule_update.dict(exclude_unset=True)
    if "parameters_json" in update_data and update_data["parameters_json"] is not None:
        db_rule.parameters_json = json.dumps(update_data["parameters_json"])
        del update_data["parameters_json"] # Avoid trying to set it again via setattr

    for key, value in update_data.items():
        setattr(db_rule, key, value)

    db.commit()
    db.refresh(db_rule)
    return db_rule

def get_aml_rules(db: Session, active_only: bool = True) -> List[models.AMLRule]:
    query = db.query(models.AMLRule)
    if active_only:
        query = query.filter(models.AMLRule.is_active == True)
    return query.all()

# --- AML Transaction Monitoring (Conceptual) ---
# This would be a batch process or real-time stream processor.
def monitor_transactions_for_aml(db: Session, transaction_id: str): # Or process a batch of transactions
    # ft = get_transaction_by_id(db, transaction_id) # Get FinancialTransaction
    # if not ft: return

    # active_rules = get_aml_rules(db, active_only=True)
    # for rule_model in active_rules:
    #     params = json.loads(rule_model.parameters_json) if rule_model.parameters_json else {}
    #     is_breached = False
        # Example: Large Cash Deposit Rule
        # if rule_model.rule_code == "LARGE_CASH_DEPOSIT":
        #     if ft.transaction_type == "CASH_DEPOSIT" and ft.amount > params.get("threshold_amount", 5000000) and ft.currency == params.get("currency", "NGN"):
        #         is_breached = True
        # elif rule_model.rule_code == "HIGH_VELOCITY_TXNS":
            # Query related transactions for the customer/account over params.get("period_days")
            # If count > params.get("txn_count_threshold") or sum_amount > params.get("sum_amount_threshold")
            # is_breached = True

        # if is_breached:
        #     log_suspicious_activity(
        #         db, ft.customer_id, ft.account_id, ft.id, rule_model.rule_code,
        #         f"Rule '{rule_model.description}' breached by transaction {ft.id}."
        #     )
            # Perform action_to_take (e.g. if "BLOCK_TRANSACTION", need to integrate with TransactionManagement)
    pass # Placeholder for complex AML monitoring logic

def log_suspicious_activity(
    db: Session, customer_bvn: Optional[str], account_number: Optional[str],
    transaction_ref: Optional[str], rule_code: str, description: str
) -> models.SuspiciousActivityLog:

    log = models.SuspiciousActivityLog(
        customer_bvn=customer_bvn,
        account_number=account_number,
        transaction_reference_primary=transaction_ref,
        aml_rule_code_triggered=rule_code,
        activity_description=description,
        status="OPEN"
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def update_suspicious_activity_status(db: Session, log_id: int, update_data: schemas.SuspiciousActivityStatusUpdateRequest, user_id: str) -> models.SuspiciousActivityLog:
    log = db.query(models.SuspiciousActivityLog).filter(models.SuspiciousActivityLog.id == log_id).with_for_update().first()
    if not log:
        raise NotFoundException(f"Suspicious Activity Log {log_id} not found.")

    log.status = update_data.new_status
    log.assigned_to_user_id = update_data.assigned_to_user_id or user_id # Assign to current user if not specified
    log.investigation_notes = (log.investigation_notes + "\n---\n" if log.investigation_notes else "") + f"Updated by {user_id} on {datetime.utcnow()}:\n{update_data.investigation_notes or ''}"

    if update_data.new_status in ["CLEARED", "ESCALATED_TO_NFIU"]:
        log.resolution_date = datetime.utcnow()

    # If ESCALATED_TO_NFIU and str_filed_reference provided, link to STR report log
    # if update_data.new_status == "ESCALATED_TO_NFIU" and update_data.str_filed_reference:
    #     str_report = db.query(models.GeneratedReportLog).filter(models.GeneratedReportLog.submission_reference == update_data.str_filed_reference, models.GeneratedReportLog.report_name == ReportNameEnum.NFIU_STR).first()
    #     if str_report: log.str_report_log_id = str_report.id

    db.commit()
    db.refresh(log)
    return log

# --- Sanction Screening Services ---
def perform_sanction_screening(db: Session, screening_request: schemas.SanctionScreeningRequest) -> schemas.SanctionScreeningResult:
    # This would call an external sanction list provider's API
    # matches = sanction_list_provider_service.screen_name(
    #     name=screening_request.name_to_screen,
    #     entity_type=screening_request.entity_type,
    #     # ... other identifiers ...
    # )

    # Mock response
    matches_found_list = []
    if "sanctioned" in screening_request.name_to_screen.lower():
        matches_found_list.append({
            "list_name": "OFAC_SDN_MOCK",
            "matched_name": screening_request.name_to_screen,
            "score": 0.95,
            "details": "Entity found on OFAC SDN list (mock data)."
        })

    log = models.SanctionScreeningLog(
        name_screened=screening_request.name_to_screen,
        bvn_screened=screening_request.bvn_to_screen,
        # entity_type=screening_request.entity_type,
        sanction_lists_checked=json.dumps(["OFAC_SDN_MOCK", "UN_CONSOLIDATED_MOCK"]), # Example lists
        match_found=bool(matches_found_list),
        match_details_json=json.dumps(matches_found_list) if matches_found_list else None
    )
    db.add(log)
    db.commit()

    return schemas.SanctionScreeningResult(
        name_screened=screening_request.name_to_screen,
        screening_date=log.screening_date,
        match_found=log.match_found,
        match_details=matches_found_list
    )

def get_sanction_screening_logs(db: Session, skip: int = 0, limit: int = 100, bvn: Optional[str]=None, name: Optional[str]=None, match_found: Optional[bool]=None) -> List[models.SanctionScreeningLog]:
    query = db.query(models.SanctionScreeningLog)
    if bvn:
        query = query.filter(models.SanctionScreeningLog.bvn_screened == bvn)
    if name:
        query = query.filter(models.SanctionScreeningLog.name_screened.ilike(f"%{name}%")) # Case-insensitive search
    if match_found is not None:
        query = query.filter(models.SanctionScreeningLog.match_found == match_found)
    return query.order_by(models.SanctionScreeningLog.screening_date.desc()).offset(skip).limit(limit).all()

# Note: Actual report file generation and submission often involve complex transformations,
# specific file formats (XML schemas, fixed-width text), and secure transfer protocols or portal interactions.
# This service layer provides the hooks and logging for these processes.
# AML monitoring and Sanction Screening are continuous processes. Sanction lists need frequent updates.
