# Service layer for Deposit & Collection Module
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from .models import DepositStatusEnum # Direct enum access
import decimal
from datetime import datetime, timedelta

# Placeholder for other service integrations
# from weezy_cbs.accounts_ledger_management.services import get_account_by_number, post_double_entry_transaction
# from weezy_cbs.accounts_ledger_management.schemas import PostTransactionRequest as LedgerPostRequest
# from weezy_cbs.transaction_management.services import initiate_transaction # For creating master FT record
# from weezy_cbs.transaction_management.schemas import TransactionCreateRequest as MasterTxCreateRequest
# from weezy_cbs.shared import exceptions

class NotFoundException(Exception): pass
class InvalidOperationException(Exception): pass

# --- Cash Deposit Services ---
def log_cash_deposit(db: Session, deposit_in: schemas.CashDepositCreateRequest, teller_id: str, branch_code: str) -> models.CashDepositLog:
    # Validate account exists and is active
    # target_account = get_account_by_number(db, deposit_in.account_number)
    # if not target_account:
    #     raise NotFoundException(f"Account {deposit_in.account_number} not found.")
    # if target_account.status != "ACTIVE": # Assuming status is string
    #     raise InvalidOperationException(f"Account {deposit_in.account_number} is not active.")
    # if target_account.currency != deposit_in.currency:
    #     raise InvalidOperationException("Currency mismatch between deposit and account.")

    # Create a master financial transaction record for this deposit
    # master_tx_ref = "DEP_" + datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    # ft_request = MasterTxCreateRequest(
    #     transaction_type="CASH_DEPOSIT",
    #     channel=models.TransactionChannelEnum.BRANCH_TELLER if not deposit_in.agent_id_external else models.TransactionChannelEnum.AGENT_BANKING,
    #     amount=deposit_in.amount,
    #     currency=deposit_in.currency,
    #     # No debit account for cash deposit from bank's perspective (it's cash GL)
    #     credit_account_number=deposit_in.account_number,
    #     credit_bank_code="OUR_BANK_CODE", # Assuming our bank code
    #     narration=f"Cash deposit by {deposit_in.depositor_name or 'Customer'}"
    # )
    # master_ft = initiate_transaction(db, ft_request) # This would set it to PENDING

    db_log = models.CashDepositLog(
        # financial_transaction_id=master_ft.id, # Link to the master FT
        account_number=deposit_in.account_number,
        amount=deposit_in.amount,
        currency=deposit_in.currency,
        depositor_name=deposit_in.depositor_name,
        depositor_phone=deposit_in.depositor_phone,
        teller_id=teller_id,
        branch_code=branch_code,
        status=DepositStatusEnum.COMPLETED, # Assume immediate completion for cash unless large/flagged
        notes=deposit_in.notes,
        agent_id_external=deposit_in.agent_id_external,
        agent_terminal_id=deposit_in.agent_terminal_id
    )
    db.add(db_log)

    # Post to ledger (credit customer account, debit teller/branch cash GL)
    # ledger_post = LedgerPostRequest(
    #     # from_gl_code=f"CASH_GL_{branch_code}_{teller_id}", # Teller's cash GL
    #     from_gl_code="TELLER_CASH_GL", # Simplified
    #     to_account_number=deposit_in.account_number,
    #     amount=deposit_in.amount,
    #     currency=deposit_in.currency,
    #     narration=f"Cash Deposit ref {db_log.id} by {deposit_in.depositor_name or 'N/A'}",
    #     transaction_reference=master_ft.id, # Link to master FT
    #     channel="TELLER" # Or AGENT
    # )
    # try:
    #     post_double_entry_transaction(db, ledger_post)
    #     # Update master_ft status to SUCCESSFUL
    #     # update_transaction_status(db, master_ft.id, TransactionStatusEnum.SUCCESSFUL, "00", "Cash Deposit Successful")
    # except Exception as e:
    #     # Rollback or mark deposit log as FAILED, update master_ft status
    #     db_log.status = DepositStatusEnum.FAILED
    #     db_log.notes = (db_log.notes or "") + f"; Ledger posting failed: {str(e)}"
    #     # update_transaction_status(db, master_ft.id, TransactionStatusEnum.FAILED, "96", f"Ledger Posting Failed: {str(e)}")
    #     # db.commit() # Commit the failure status
    #     raise InvalidOperationException(f"Ledger posting failed for cash deposit: {str(e)}")

    db.commit()
    db.refresh(db_log)
    return db_log

def get_cash_deposit_log(db: Session, log_id: int) -> Optional[models.CashDepositLog]:
    return db.query(models.CashDepositLog).filter(models.CashDepositLog.id == log_id).first()

# --- Cheque Deposit Services ---
def log_cheque_deposit(db: Session, deposit_in: schemas.ChequeDepositCreateRequest, teller_id: str, branch_code: str) -> models.ChequeDepositLog:
    # Validate beneficiary account
    # target_account = get_account_by_number(db, deposit_in.account_number)
    # if not target_account:
    #     raise NotFoundException(f"Beneficiary account {deposit_in.account_number} not found.")
    # if target_account.currency != deposit_in.currency: # Usually NGN for local cheques
    #     raise InvalidOperationException("Currency mismatch for cheque deposit.")

    # Create a master financial transaction record (optional, or handle status within ChequeDepositLog)
    # master_tx_ref = "CHQD_" + datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    # ... initiate_transaction ... (status PENDING_CLEARANCE)

    # Expected clearing date (e.g., T+1 for local cheques - simplified)
    expected_clearing = datetime.utcnow().date() + timedelta(days=1) # This needs proper business day logic
    # For simplicity, using datetime, though date might be more appropriate for clearing_date_expected
    expected_clearing_dt = datetime.combine(expected_clearing, datetime.min.time())


    db_log = models.ChequeDepositLog(
        # financial_transaction_id=master_ft.id if master_ft else None,
        account_number=deposit_in.account_number,
        cheque_number=deposit_in.cheque_number,
        drawee_bank_code=deposit_in.drawee_bank_code,
        drawee_account_number=deposit_in.drawee_account_number,
        drawer_name=deposit_in.drawer_name,
        amount=deposit_in.amount,
        currency=deposit_in.currency,
        depositor_name=deposit_in.depositor_name,
        teller_id=teller_id,
        branch_code=branch_code,
        status=DepositStatusEnum.PENDING_CLEARANCE,
        clearing_date_expected=expected_clearing_dt,
        # cheque_image_front_url=deposit_in.cheque_image_front_url,
        # cheque_image_back_url=deposit_in.cheque_image_back_url,
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)

    # Send to clearing house (integration with NIBSS Cheque Truncation System)
    # clearing_service.submit_cheque_for_clearing(db_log)

    return db_log

def update_cheque_deposit_status(db: Session, log_id: int, status_update: schemas.ChequeStatusUpdateRequest) -> models.ChequeDepositLog:
    cheque_log = db.query(models.ChequeDepositLog).filter(models.ChequeDepositLog.id == log_id).with_for_update().first()
    if not cheque_log:
        raise NotFoundException(f"Cheque deposit log {log_id} not found.")

    cheque_log.status = status_update.new_status
    if status_update.new_status == DepositStatusEnum.FAILED:
        cheque_log.reason_for_failure = status_update.reason_for_failure
        # Update master FT if linked
        # update_transaction_status(db, cheque_log.financial_transaction_id, TransactionStatusEnum.FAILED, "XX", status_update.reason_for_failure)
    elif status_update.new_status == DepositStatusEnum.COMPLETED:
        cheque_log.cleared_date_actual = status_update.actual_cleared_date or datetime.utcnow()
        # Post to ledger: Credit customer (remove uncleared hold), Debit NIBSS settlement GL
        # ledger_post = LedgerPostRequest(
        #     from_gl_code="NIBSS_CHEQUE_SETTLEMENT_GL",
        #     to_account_number=cheque_log.account_number,
        #     amount=cheque_log.amount,
        #     currency=cheque_log.currency,
        #     narration=f"Cleared Cheque {cheque_log.cheque_number}",
        #     transaction_reference=cheque_log.financial_transaction_id,
        #     channel="CLEARING"
        # )
        # try:
        #     post_double_entry_transaction(db, ledger_post)
        #     # update_transaction_status(db, cheque_log.financial_transaction_id, TransactionStatusEnum.SUCCESSFUL, "00", "Cheque Cleared")
        # except Exception as e:
        #     cheque_log.status = DepositStatusEnum.FAILED # Or a specific "POSTING_FAILED" status
        #     cheque_log.reason_for_failure = f"Ledger posting failed after clearing: {str(e)}"
        #     # update_transaction_status(db, cheque_log.financial_transaction_id, TransactionStatusEnum.FLAGGED, "96", cheque_log.reason_for_failure) # Flag for investigation
        #     # db.commit()
        #     raise InvalidOperationException(f"Ledger posting failed for cleared cheque: {str(e)}")

    db.commit()
    db.refresh(cheque_log)
    return cheque_log

# --- Collection Services (Admin/Setup) ---
def create_collection_service(db: Session, service_in: schemas.CollectionServiceCreateRequest) -> models.CollectionService:
    # Validate merchant_account_id exists and is suitable for settlement
    # merchant_account = get_account_by_id(db, service_in.merchant_account_id)
    # if not merchant_account:
    #     raise NotFoundException(f"Merchant settlement account {service_in.merchant_account_id} not found.")

    db_service = models.CollectionService(**service_in.dict())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

def get_collection_service(db: Session, service_id: int) -> Optional[models.CollectionService]:
    return db.query(models.CollectionService).filter(models.CollectionService.id == service_id).first()

# --- Collection Payment Logging ---
def log_collection_payment(db: Session, payment_in: schemas.CollectionPaymentCreateRequest, collection_service_id: int) -> models.CollectionPaymentLog:
    collection_service = get_collection_service(db, collection_service_id)
    if not collection_service or not collection_service.is_active:
        raise NotFoundException(f"Active collection service with ID {collection_service_id} not found.")

    # Potentially validate customer_identifier_at_merchant if service has validation_endpoint
    # if collection_service.validation_endpoint:
    #     is_valid, customer_details = external_validator.validate(collection_service.validation_endpoint, payment_in.customer_identifier_at_merchant)
    #     if not is_valid:
    #         raise InvalidOperationException("Customer identifier validation failed with merchant.")
    #     # payment_in.payer_name = customer_details.get("name") or payment_in.payer_name # Populate if available

    # Create a master financial transaction for this collection (debit payer, credit merchant's collection GL)
    # This is complex: Payer could be paying via cash, card, transfer.
    # For now, assume payment is confirmed and we are just logging it for settlement.
    # master_ft = ...

    db_log = models.CollectionPaymentLog(
        collection_service_id=collection_service_id,
        # financial_transaction_id = master_ft.id if master_ft else None,
        **payment_in.dict()
        # status will be SUCCESSFUL if payment is confirmed by channel
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)

    # Trigger settlement process to merchant's account (could be batch)
    # settle_to_merchant_account(db, db_log.id, collection_service.merchant_account_id)
    return db_log


# --- POS Reconciliation Services (Placeholder) ---
def initiate_pos_reconciliation_batch(db: Session, batch_create: schemas.POSReconciliationBatchCreate) -> models.POSReconciliationBatch:
    # Check if batch for this date already exists
    existing_batch = db.query(models.POSReconciliationBatch).filter(models.POSReconciliationBatch.batch_date == batch_create.batch_date).first()
    if existing_batch:
        raise InvalidOperationException(f"Reconciliation batch for date {batch_create.batch_date} already exists or initiated.")

    db_batch = models.POSReconciliationBatch(
        batch_date=datetime.combine(batch_create.batch_date, datetime.min.time()), # Store as datetime
        source_file_name=batch_create.source_file_name,
        status="PENDING"
    )
    db.add(db_batch)
    db.commit()
    db.refresh(db_batch)

    # Async task: process_pos_reconciliation_file(db_batch.id, uploaded_file_path)
    return db_batch

def process_pos_reconciliation_file(db: Session, batch_id: int, file_data: List[dict]): # file_data parsed from acquirer's file
    """
    Processes the transactions from the acquirer's file against internal records.
    This is a highly simplified placeholder.
    """
    batch = db.query(models.POSReconciliationBatch).filter(models.POSReconciliationBatch.id == batch_id).with_for_update().first()
    if not batch or batch.status != "PENDING":
        raise InvalidOperationException("Batch not found or not in pending state for processing.")

    batch.status = "PROCESSING"
    batch.total_transactions_in_file = len(file_data)
    batch.total_amount_in_file = sum(decimal.Decimal(item.get("amount", 0)) for item in file_data)
    db.commit()

    matched_count = 0
    unmatched_count = 0
    total_discrepancy_amount = decimal.Decimal("0.0")

    for item in file_data:
        external_ref = item.get("rrn") or item.get("stan") # Common external references
        external_amount = decimal.Decimal(item.get("amount",0))

        # Try to find matching internal transaction (e.g., in FinancialTransaction or CardTransaction)
        # internal_tx = db.query(models.FinancialTransaction).filter(models.FinancialTransaction.external_transaction_id == external_ref).first()
        # Mock find:
        internal_tx_found = random.choice([True, True, False]) if external_ref else False
        mock_internal_amount = external_amount if random.random() > 0.1 else external_amount - decimal.Decimal("10.00") # Simulate amount mismatch

        if internal_tx_found:
            # if internal_tx.amount == external_amount:
            if mock_internal_amount == external_amount:
                matched_count +=1
            else: # Amount mismatch
                unmatched_count += 1
                discrepancy = mock_internal_amount - external_amount
                total_discrepancy_amount += discrepancy
                # Log discrepancy: models.POSReconciliationDiscrepancy(...)
                db.add(models.POSReconciliationDiscrepancy(
                    batch_id=batch.id, external_transaction_reference=external_ref,
                    discrepancy_type="AMOUNT_MISMATCH", details=f"Internal: {mock_internal_amount}, External: {external_amount}", status="OPEN"
                ))
        else: # Missing internal
            unmatched_count +=1
            total_discrepancy_amount -= external_amount # External has it, we don't (negative discrepancy for us)
            # Log discrepancy: models.POSReconciliationDiscrepancy(...)
            db.add(models.POSReconciliationDiscrepancy(
                batch_id=batch.id, external_transaction_reference=external_ref,
                discrepancy_type="MISSING_INTERNAL", details=f"External txn {external_ref} not found internally.", status="OPEN"
            ))

    batch.matched_transactions_count = matched_count
    batch.unmatched_transactions_count = unmatched_count
    batch.discrepancy_amount = total_discrepancy_amount
    batch.status = "COMPLETED" # Or "COMPLETED_WITH_DISCREPANCIES"
    batch.processed_at = datetime.utcnow()
    db.commit()
    # Further actions: generate reports, trigger alerts for large discrepancies.

# Helper to get paginated results
def get_paginated_deposits(db: Session, model_class, skip: int, limit: int, account_number: Optional[str] = None) -> List[Any]:
    query = db.query(model_class)
    if account_number:
        query = query.filter(model_class.account_number == account_number)
    return query.order_by(model_class.deposit_date.desc()).offset(skip).limit(limit).all()

def count_deposits(db: Session, model_class, account_number: Optional[str] = None) -> int:
    query = db.query(func.count(model_class.id))
    if account_number:
        query = query.filter(model_class.account_number == account_number)
    return query.scalar_one()
