# Service layer for Transaction Management
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from . import models, schemas
from .models import TransactionStatusEnum, TransactionChannelEnum, CurrencyEnum # Direct enum access
import decimal
import uuid # For generating unique transaction IDs
from datetime import datetime, timedelta

# Placeholder for other service integrations
# from weezy_cbs.accounts_ledger_management.services import (
#     get_account_by_number as get_deposit_account,
#     post_double_entry_transaction
# )
# from weezy_cbs.accounts_ledger_management.schemas import PostTransactionRequest as LedgerPostRequest
# from weezy_cbs.integrations import nibss_service, ussd_aggregator_service # etc.
# from weezy_cbs.fees_charges_commission_engine.services import calculate_and_apply_fees
# from weezy_cbs.shared import exceptions

class NotFoundException(Exception): pass
class InvalidOperationException(Exception): pass
class InsufficientFundsException(InvalidOperationException): pass
class ExternalServiceException(Exception): pass

def _generate_transaction_id(prefix="WZYTXN"):
    return f"{prefix}{uuid.uuid4().hex[:16].upper()}"

# --- Core Transaction Processing ---
def initiate_transaction(db: Session, transaction_in: schemas.TransactionCreateRequest, initiated_by_customer_id: Optional[int] = None) -> models.FinancialTransaction:
    """
    Initiates a new financial transaction.
    This function creates the master transaction record and sets it to PENDING.
    Actual processing (NIP call, ledger posting) happens in subsequent steps or async tasks.
    """
    # Validate debit account if it's one of ours
    if transaction_in.debit_account_number and (transaction_in.debit_bank_code is None or transaction_in.debit_bank_code == "OUR_BANK_CODE"): # Replace "OUR_BANK_CODE"
        # debit_account = get_deposit_account(db, transaction_in.debit_account_number)
        # if not debit_account:
        #     raise NotFoundException(f"Debit account {transaction_in.debit_account_number} not found.")
        # if debit_account.status != "ACTIVE": # Assuming status is string
        #     raise InvalidOperationException(f"Debit account {transaction_in.debit_account_number} is not active.")
        # if debit_account.available_balance < transaction_in.amount: # Basic pre-check
        #     raise InsufficientFundsException("Insufficient funds in debit account.")
        # transaction_in.debit_account_name = debit_account.customer.name # Assuming customer relation and name field
        pass # Placeholder for above validation

    # For interbank, name enquiry might be done first (see NIP services)
    # For now, assume credit_account_name is provided or will be handled by NIP flow

    txn_id = _generate_transaction_id()
    db_transaction = models.FinancialTransaction(
        id=txn_id,
        transaction_type=transaction_in.transaction_type,
        channel=transaction_in.channel,
        status=TransactionStatusEnum.PENDING, # Initial status
        amount=transaction_in.amount,
        currency=transaction_in.currency,
        debit_account_number=transaction_in.debit_account_number,
        debit_account_name=transaction_in.debit_account_name, # May need to fetch if our account
        debit_bank_code=transaction_in.debit_bank_code,
        # debit_customer_id=initiated_by_customer_id, # Or fetched from debit_account if internal
        credit_account_number=transaction_in.credit_account_number,
        credit_account_name=transaction_in.credit_account_name,
        credit_bank_code=transaction_in.credit_bank_code,
        narration=transaction_in.narration,
        initiated_at=datetime.utcnow()
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # Depending on channel, trigger next step (e.g., NIP call, USSD handler, ledger posting)
    # This could be an async task:
    # process_pending_transaction_async(db_transaction.id)

    return db_transaction

def get_transaction_by_id(db: Session, transaction_id: str) -> Optional[models.FinancialTransaction]:
    return db.query(models.FinancialTransaction).filter(models.FinancialTransaction.id == transaction_id).first()

def get_transactions_by_status(db: Session, status: TransactionStatusEnum, limit: int = 100) -> List[models.FinancialTransaction]:
    return db.query(models.FinancialTransaction).filter(models.FinancialTransaction.status == status).limit(limit).all()

def get_transactions_for_account(db: Session, account_number: str, skip: int = 0, limit: int = 20, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[models.FinancialTransaction]:
    query = db.query(models.FinancialTransaction).filter(
        or_(
            models.FinancialTransaction.debit_account_number == account_number,
            models.FinancialTransaction.credit_account_number == account_number
        )
    )
    if start_date:
        query = query.filter(models.FinancialTransaction.initiated_at >= start_date)
    if end_date:
        query = query.filter(models.FinancialTransaction.initiated_at < (end_date + timedelta(days=1)))

    return query.order_by(models.FinancialTransaction.initiated_at.desc()).offset(skip).limit(limit).all()

def get_transaction_count_for_account(db: Session, account_number: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
    query = db.query(func.count(models.FinancialTransaction.id)).filter(
        or_(
            models.FinancialTransaction.debit_account_number == account_number,
            models.FinancialTransaction.credit_account_number == account_number
        )
    )
    if start_date:
        query = query.filter(models.FinancialTransaction.initiated_at >= start_date)
    if end_date:
        query = query.filter(models.FinancialTransaction.initiated_at < (end_date + timedelta(days=1)))
    return query.scalar_one()


def update_transaction_status(
    db: Session,
    transaction_id: str,
    new_status: TransactionStatusEnum,
    response_code: Optional[str] = None,
    response_message: Optional[str] = None,
    external_transaction_id: Optional[str] = None,
    system_remarks: Optional[str] = None
) -> models.FinancialTransaction:

    transaction = get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise NotFoundException(f"Transaction {transaction_id} not found for status update.")

    transaction.status = new_status
    if response_code: transaction.response_code = response_code
    if response_message: transaction.response_message = response_message
    if external_transaction_id: transaction.external_transaction_id = external_transaction_id
    if system_remarks:
        transaction.system_remarks = (transaction.system_remarks + "; " if transaction.system_remarks else "") + system_remarks

    if new_status in [TransactionStatusEnum.SUCCESSFUL, TransactionStatusEnum.FAILED, TransactionStatusEnum.REVERSED, TransactionStatusEnum.TIMEOUT]:
        transaction.processed_at = datetime.utcnow()
        if external_transaction_id: # If external system involved, use its timestamp if available
             transaction.external_system_at = datetime.utcnow() # Or parse from external system response

    db.commit()
    db.refresh(transaction)
    return transaction

# --- NIP Services (Illustrative & Conceptual) ---
# These would typically call an external NIBSS integration service/client using GenericExternalAPICaller.
# For now, we mock the NIBSS interaction part.

# Import necessary services for conceptual calls
from weezy_cbs.third_party_fintech_integration.services import GenericExternalAPICaller, api_service_config_service, external_service_log_service
# from weezy_cbs.accounts_ledger_management.services import post_transaction_to_ledger # Conceptual ledger posting
# from weezy_cbs.digital_channels_modules.services import notification_service # Conceptual notification

NIBSS_NIP_SERVICE_NAME = "NIBSS_NIP_SERVICE" # Matches APIServiceConfig.service_name

async def perform_nip_name_enquiry(
    db: Session,
    request: schemas.NIPNameEnquiryRequest,
    correlation_id: Optional[str] = None
) -> schemas.NIPNameEnquiryResponse:
    """
    Performs a NIP Name Enquiry.
    Conceptually calls NIBSS via GenericExternalAPICaller.
    """
    # api_caller = GenericExternalAPICaller(db, api_service_config_service, external_service_log_service)
    # nibss_payload = { ... map request to NIBSS NE payload ... }
    # try:
    #     response = await api_caller.make_request(
    #         service_name=NIBSS_NIP_SERVICE_NAME,
    #         method="POST", # Or whatever NIBSS uses
    #         endpoint_path="/nameenquiry", # NIBSS specific endpoint
    #         json_payload=nibss_payload,
    #         correlation_id=correlation_id
    #     )
    #     response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
    #     response_data = response.json()
    #     if response_data.get("responseCode") == "00": # NIBSS success code
    #         return schemas.NIPNameEnquiryResponse(
    #             session_id=response_data.get("sessionId"), # Map fields
    #             destination_institution_code=response_data.get("destinationInstitutionCode"),
    #             account_number=response_data.get("accountNumber"),
    #             account_name=response_data.get("accountName"),
    #             bank_verification_number=response_data.get("bankVerificationNumber"),
    #             kyc_level=response_data.get("kycLevel"),
    #             response_code="00"
    #         )
    #     else:
    #         raise ExternalServiceException(f"NIP Name Enquiry failed at NIBSS: {response_data.get('responseMessage')}")
    # except httpx.HTTPStatusError as e:
    #     raise ExternalServiceException(f"NIP Name Enquiry HTTP error: {e.response.status_code} - {e.response.text}")
    # except Exception as e:
    #     raise ExternalServiceException(f"NIP Name Enquiry unexpected error: {str(e)}")

    # Mocked response:
    print(f"SERVICE: Simulating NIP Name Enquiry for Acc: {request.account_number}, Bank: {request.destination_institution_code}")
    if request.account_number == "0000000000": # Simulate failure
        raise ExternalServiceException("NIP Name Enquiry failed: Invalid account (mock).")

    return schemas.NIPNameEnquiryResponse(
        session_id=uuid.uuid4().hex[:20],
        destination_institution_code=request.destination_institution_code,
        account_number=request.account_number,
        account_name="Mock Beneficiary Name (NIP)",
        bank_verification_number="22211100099", # Example
        kyc_level="2", # Example
        response_code="00"
    )

async def process_outgoing_nip_funds_transfer(
    db: Session,
    transaction_id: str,
    nip_request_details: schemas.NIPFundsTransferRequest # Contains all NIBSS required fields
) -> models.FinancialTransaction:
    """
    Processes an initiated NIP transaction by calling NIBSS.
    """
    transaction = get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise NotFoundException(f"Transaction {transaction_id} not found for NIP processing.")

    transaction = update_transaction_status(db, transaction_id, TransactionStatusEnum.PROCESSING, system_remarks="NIP FT: Sent to NIBSS")

    # api_caller = GenericExternalAPICaller(db, api_service_config_service, external_service_log_service)
    # nibss_ft_payload = { ... map nip_request_details to NIBSS FT payload ... }
    # nibss_session_id_from_call = "NIPFT_MOCK_" + uuid.uuid4().hex[:10] # Placeholder
    # mock_response_code = "00"
    # mock_response_message = "Transfer Successful"

    # try:
    #     response = await api_caller.make_request(
    #         service_name=NIBSS_NIP_SERVICE_NAME, method="POST", endpoint_path="/fundstransfer",
    #         json_payload=nibss_ft_payload, correlation_id=transaction.id
    #     )
    #     response.raise_for_status()
    #     response_data = response.json()
    #     nibss_session_id_from_call = response_data.get("sessionId", nibss_session_id_from_call)
    #     mock_response_code = response_data.get("responseCode", "96") # Default to system error
    #     mock_response_message = response_data.get("responseMessage", "Error processing at NIBSS")

    # except Exception as e:
    #     mock_response_code = "96" # System error
    #     mock_response_message = f"Error calling NIBSS for FT: {str(e)}"
    #     # Log this critical failure in ExternalServiceLog via api_caller or directly

    # Mock NIBSS FT call response
    nibss_session_id_from_call = "NIPFT_MOCK_" + uuid.uuid4().hex[:10].upper()
    mock_response_code = "00"
    mock_response_message = "Transaction Successful (NIP Mock)"
    if transaction.amount > decimal.Decimal("5000000"): # Simulate a failure for large amounts
        mock_response_code = "Z0" # Example NIBSS failure code (e.g., "Transaction Limit Exceeded")
        mock_response_message = "Transaction amount exceeds NIP limit (mock)."

    # Store/Update NIP specific details
    nip_tx_record = db.query(models.NIPTransaction).filter(models.NIPTransaction.financial_transaction_id == transaction.id).first()
    if not nip_tx_record:
        nip_tx_record = models.NIPTransaction(financial_transaction_id=transaction.id)
        db.add(nip_tx_record)

    nip_tx_record.nibss_session_id = nibss_session_id_from_call
    nip_tx_record.name_enquiry_ref = nip_request_details.name_enquiry_ref
    # nip_tx_record.request_payload_json = json.dumps(nibss_ft_payload) # If logging payload
    # nip_tx_record.response_payload_json = json.dumps(response_data) if 'response_data' in locals() else None


    if mock_response_code == "00": # NIBSS Successful
        # Conceptual: Trigger debit ledger posting for the sender
        # from_account = transaction.debit_account_number
        # to_gl_account = "NIBSS_SETTLEMENT_GL" # Or appropriate GL
        # try:
        #     post_transaction_to_ledger(db, from_account, to_gl_account, transaction.amount, transaction.currency,
        #                                f"NIP Out: {transaction.narration}", transaction.id, "DEBIT_CUSTOMER_CREDIT_GL")
        #     transaction = update_transaction_status(db, transaction.id, TransactionStatusEnum.SUCCESSFUL,
        #                                 mock_response_code, mock_response_message, nibss_session_id_from_call,
        #                                 "NIP successful, local debit ledger posted.")
        # except Exception as ledger_error:
        #     # CRITICAL: NIP was successful, but local debit failed. Requires urgent reconciliation.
        #     transaction = update_transaction_status(db, transaction.id, TransactionStatusEnum.FLAGGED_SUSPICION,
        #                                 mock_response_code, mock_response_message, nibss_session_id_from_call,
        #                                 f"NIP successful but local debit ledger failed: {str(ledger_error)}. Needs reconciliation.")
        #     # TODO: Trigger alert for reconciliation team

        # Simplified mock for successful ledger posting
        transaction = update_transaction_status(db, transaction.id, TransactionStatusEnum.SUCCESSFUL,
                                    mock_response_code, mock_response_message, nibss_session_id_from_call,
                                    "NIP successful, local debit ledger posted (mock).")
    else: # NIBSS Failed
        transaction = update_transaction_status(db, transaction.id, TransactionStatusEnum.FAILED,
                                    mock_response_code, mock_response_message, nibss_session_id_from_call,
                                    f"NIP transfer failed at NIBSS: {mock_response_message}")

    db.commit()
    db.refresh(transaction)
    if nip_tx_record: db.refresh(nip_tx_record)
    return transaction

async def handle_incoming_nip_credit_notification(
    db: Session,
    notification_data: schemas.NIPIncomingCreditNotification # Schema for parsed webhook data
) -> models.FinancialTransaction:
    """
    Handles an incoming NIP credit notification (e.g., from a webhook).
    """
    # 1. Validate notification (basic checks, e.g. required fields)
    # (Pydantic schema validation already does some of this)

    # 2. Check for duplicate processing using NIBSS Session ID
    existing_ft_by_external_id = db.query(models.FinancialTransaction).filter(
        models.FinancialTransaction.external_transaction_id == notification_data.nibss_session_id,
        models.FinancialTransaction.transaction_type == "NIP_INWARD_CREDIT" # Be specific
    ).first()
    if existing_ft_by_external_id and existing_ft_by_external_id.status == TransactionStatusEnum.SUCCESSFUL:
        print(f"SERVICE: Duplicate NIP credit notification received and ignored: {notification_data.nibss_session_id}")
        # Potentially return the existing transaction or a specific "duplicate" response
        return existing_ft_by_external_id

    # 3. Identify beneficiary customer and account
    # beneficiary_account_orm = get_deposit_account(db, notification_data.beneficiary_account_number)
    # if not beneficiary_account_orm:
    #     # Log this critical failure: account not found for incoming NIP.
    #     # This might require manual intervention or return to NIBSS.
    #     raise NotFoundException(f"Beneficiary account {notification_data.beneficiary_account_number} not found for NIP credit.")
    # if beneficiary_account_orm.status != "ACTIVE": # Assuming status is string
    #     raise InvalidOperationException(f"Beneficiary account {notification_data.beneficiary_account_number} is not active.")

    # Mock beneficiary account lookup:
    mock_beneficiary_customer_id = 123 # Placeholder
    print(f"SERVICE: Identified beneficiary account {notification_data.beneficiary_account_number} (mock).")


    # 4. Create FinancialTransaction record
    txn_id = _generate_transaction_id("NIPIN")
    db_transaction = models.FinancialTransaction(
        id=txn_id,
        transaction_type="NIP_INWARD_CREDIT", # Specific type
        channel=TransactionChannelEnum.NIP,
        status=TransactionStatusEnum.PROCESSING, # Start as processing while attempting ledger
        amount=notification_data.amount,
        currency=CurrencyEnum[notification_data.currency.upper()] if notification_data.currency else CurrencyEnum.NGN,

        debit_account_number=notification_data.originator_account_number,
        debit_account_name=notification_data.originator_account_name,
        debit_bank_code=notification_data.originator_bank_code,

        credit_account_number=notification_data.beneficiary_account_number,
        credit_account_name=notification_data.beneficiary_account_name, # Should be our customer's name
        credit_bank_code="OUR_BANK_CODE", # Weezy CBS's bank code
        credit_customer_id=mock_beneficiary_customer_id, # Linked to our customer

        narration=notification_data.narration or f"NIP Credit from {notification_data.originator_account_name}",
        initiated_at=datetime.utcnow(), # When we received it or use NIBSS timestamp if reliable
        external_transaction_id=notification_data.nibss_session_id,
        response_code="00", # Assuming NIBSS sent it because it was successful there
        response_message="Inward NIP Received"
    )
    db.add(db_transaction)

    # 5. Create NIPTransaction record
    nip_tx_record = models.NIPTransaction(
        financial_transaction_id=txn_id,
        nibss_session_id=notification_data.nibss_session_id,
        name_enquiry_ref=notification_data.name_enquiry_ref, # If available in notification
        nip_channel_code=notification_data.channel_code
    )
    db.add(nip_tx_record)

    # 6. Trigger credit ledger posting
    # try:
    #     post_transaction_to_ledger(db,
    #                                from_gl_account="NIBSS_INWARD_CLEARING_GL",
    #                                to_account=notification_data.beneficiary_account_number,
    #                                amount=db_transaction.amount, currency=db_transaction.currency,
    #                                narration=db_transaction.narration, transaction_reference=txn_id,
    #                                posting_type="DEBIT_GL_CREDIT_CUSTOMER")
    #     db_transaction = update_transaction_status(db, txn_id, TransactionStatusEnum.SUCCESSFUL, system_remarks="NIP Inward credit posted to customer account.")

    #     # 7. (Conceptual) Send customer notification
    #     # notification_service.send_credit_alert(db, customer_id=mock_beneficiary_customer_id, amount=db_transaction.amount, ...)

    # except Exception as e:
    #     # CRITICAL: Failed to credit customer after receiving NIP value. Requires urgent reconciliation.
    #     db_transaction = update_transaction_status(db, txn_id, TransactionStatusEnum.FLAGGED_SUSPICION,
    #                                     system_remarks=f"NIP Inward received ({notification_data.nibss_session_id}) but failed to credit customer: {str(e)}. Needs reconciliation.")
    #     # TODO: Trigger alert for reconciliation team

    # Simplified mock for successful ledger posting
    db_transaction = update_transaction_status(db, txn_id, TransactionStatusEnum.SUCCESSFUL, system_remarks="NIP Inward credit posted to customer account (mock).")

    db.commit()
    db.refresh(db_transaction)
    if nip_tx_record: db.refresh(nip_tx_record)

    print(f"SERVICE: Processed incoming NIP credit {notification_data.nibss_session_id} for Acc: {notification_data.beneficiary_account_number}, Amount: {notification_data.amount}")
    return db_transaction


# --- Intra-bank Transfer ---
def process_intrabank_transfer(db: Session, transaction_id: str) -> models.FinancialTransaction:
    """
    Processes an initiated intra-bank transfer.
    1. Update transaction status to PROCESSING.
    2. Perform ledger posting between the two internal accounts.
    3. Update transaction status to SUCCESSFUL/FAILED.
    """
    transaction = update_transaction_status(db, transaction_id, TransactionStatusEnum.PROCESSING, system_remarks="Processing intra-bank transfer")

    # ledger_post_request = LedgerPostRequest(
    #     from_account_number=transaction.debit_account_number,
    #     to_account_number=transaction.credit_account_number,
    #     amount=transaction.amount,
    #     currency=transaction.currency,
    #     narration=transaction.narration,
    #     transaction_reference=transaction.id,
    #     channel=transaction.channel.value
    # )
    try:
        # post_double_entry_transaction(db, ledger_post_request)
        # Mock successful ledger posting
        update_transaction_status(db, transaction_id, TransactionStatusEnum.SUCCESSFUL, "00", "Transfer Successful", system_remarks="Intra-bank ledger posting successful (mock).")
    except InsufficientFundsException as e:
        update_transaction_status(db, transaction_id, TransactionStatusEnum.FAILED, "51", "Insufficient Funds", system_remarks=str(e))
    except NotFoundException as e: # e.g. one of the accounts not found
        update_transaction_status(db, transaction_id, TransactionStatusEnum.FAILED, "07", "Account Not Found", system_remarks=str(e))
    except InvalidOperationException as e: # e.g. account not active
        update_transaction_status(db, transaction_id, TransactionStatusEnum.FAILED, "12", "Invalid Transaction", system_remarks=str(e))
    except Exception as e:
        # Log actual exception e
        update_transaction_status(db, transaction_id, TransactionStatusEnum.FAILED, "96", "System Malfunction", system_remarks=f"Unexpected error during ledger posting: {str(e)}")

    db.commit()
    db.refresh(transaction)
    return transaction

# --- Transaction Reversal ---
def reverse_transaction(db: Session, reversal_request: schemas.TransactionReversalRequest, reversed_by_user_id: Optional[int] = None) -> models.FinancialTransaction:
    original_txn = get_transaction_by_id(db, reversal_request.original_transaction_id)
    if not original_txn:
        raise NotFoundException(f"Original transaction {reversal_request.original_transaction_id} not found.")
    if original_txn.status != TransactionStatusEnum.SUCCESSFUL:
        raise InvalidOperationException(f"Original transaction status is {original_txn.status.value}, cannot reverse unless successful.")
    if original_txn.is_reversal or db.query(models.FinancialTransaction).filter(models.FinancialTransaction.original_transaction_id == original_txn.id).first():
        raise InvalidOperationException("Original transaction has already been reversed.")

    reversal_txn_id = _generate_transaction_id("WZYREV")
    # Create a new FinancialTransaction record for the reversal
    # Swap debit and credit parties, amount remains the same
    db_reversal_txn = models.FinancialTransaction(
        id=reversal_txn_id,
        transaction_type=f"REVERSAL_{original_txn.transaction_type}",
        channel=original_txn.channel, # Or a specific REVERSAL channel
        status=TransactionStatusEnum.PENDING, # Reversal also needs processing
        amount=original_txn.amount,
        currency=original_txn.currency,
        debit_account_number=original_txn.credit_account_number, # Swapped
        debit_account_name=original_txn.credit_account_name,
        debit_bank_code=original_txn.credit_bank_code,
        credit_account_number=original_txn.debit_account_number, # Swapped
        credit_account_name=original_txn.debit_account_name,
        credit_bank_code=original_txn.debit_bank_code,
        narration=f"Reversal of {original_txn.id}: {reversal_request.reason}",
        system_remarks=f"Reversing transaction {original_txn.id} due to: {reversal_request.reason}",
        initiated_at=datetime.utcnow(),
        is_reversal=True,
        original_transaction_id=original_txn.id
    )
    db.add(db_reversal_txn)

    # Process this reversal transaction (e.g., post to ledger)
    # This is simplified. Real reversals might involve NIBSS reversal calls for NIP.
    # For intra-bank, it's a reverse ledger posting.
    # ledger_post_request = LedgerPostRequest(
    #     from_account_number=db_reversal_txn.debit_account_number, # Original creditor is now debitor
    #     to_account_number=db_reversal_txn.credit_account_number,   # Original debitor is now creditor
    #     amount=db_reversal_txn.amount,
    #     currency=db_reversal_txn.currency,
    #     narration=db_reversal_txn.narration,
    #     transaction_reference=db_reversal_txn.id,
    #     channel=db_reversal_txn.channel.value
    # )
    try:
        # post_double_entry_transaction(db, ledger_post_request)
        # Mock successful reversal ledger posting
        db_reversal_txn = update_transaction_status(db, reversal_txn_id, TransactionStatusEnum.SUCCESSFUL, "00", "Reversal Successful", system_remarks="Reversal ledger posting successful (mock).")
        original_txn.status = TransactionStatusEnum.REVERSED # Mark original as reversed
        original_txn.system_remarks = (original_txn.system_remarks + "; " if original_txn.system_remarks else "") + f"Reversed by {reversal_txn_id}"

    except Exception as e:
        # Log e
        update_transaction_status(db, reversal_txn_id, TransactionStatusEnum.FAILED, "96", "Reversal Failed", system_remarks=f"Reversal failed: {str(e)}")
        # Original transaction status remains SUCCESSFUL if reversal fails
        raise InvalidOperationException(f"Could not process reversal: {str(e)}")

    db.commit()
    db.refresh(db_reversal_txn)
    db.refresh(original_txn)
    return db_reversal_txn


# --- Standing Order Services ---
def create_standing_order(db: Session, so_in: schemas.StandingOrderCreate) -> models.StandingOrder:
    # Validate accounts, frequency, dates etc.
    # debit_account = get_deposit_account(db, so_in.debit_account_number)
    # if not debit_account or debit_account.customer_id != so_in.customer_id:
    #     raise InvalidOperationException("Invalid debit account or customer mismatch.")

    # Ensure start_date is not in the past for new orders (or handle appropriately)
    if so_in.start_date < datetime.utcnow() and not (so_in.start_date.date() == datetime.utcnow().date()): # Allow same day start
         raise InvalidOperationException("Standing order start date cannot be in the past.")
    if so_in.end_date and so_in.end_date < so_in.start_date:
        raise InvalidOperationException("End date cannot be before start date.")

    db_so = models.StandingOrder(
        **so_in.dict(),
        next_execution_date=so_in.start_date # First execution is on start_date
    )
    db.add(db_so)
    db.commit()
    db.refresh(db_so)
    return db_so

def get_standing_orders_for_customer(db: Session, customer_id: int, active_only: bool = True) -> List[models.StandingOrder]:
    query = db.query(models.StandingOrder).filter(models.StandingOrder.customer_id == customer_id)
    if active_only:
        query = query.filter(models.StandingOrder.is_active == True)
    return query.order_by(models.StandingOrder.next_execution_date).all()

def get_due_standing_orders(db: Session, execution_date: Optional[datetime] = None) -> List[models.StandingOrder]:
    """Fetches standing orders due for execution on or before the given date."""
    if execution_date is None:
        execution_date = datetime.utcnow()

    return db.query(models.StandingOrder).filter(
        models.StandingOrder.is_active == True,
        models.StandingOrder.next_execution_date <= execution_date,
        or_(
            models.StandingOrder.end_date == None,
            models.StandingOrder.next_execution_date <= models.StandingOrder.end_date
        )
    ).all()

def _calculate_next_so_execution_date(current_next_date: datetime, frequency: str) -> datetime:
    # Simplified calculation
    if frequency == "DAILY": return current_next_date + timedelta(days=1)
    if frequency == "WEEKLY": return current_next_date + timedelta(weeks=1)
    if frequency == "MONTHLY": return current_next_date + relativedelta(months=1) # from dateutil
    if frequency == "QUARTERLY": return current_next_date + relativedelta(months=3)
    if frequency == "ANNUALLY": return current_next_date + relativedelta(years=1)
    raise ValueError(f"Unsupported standing order frequency: {frequency}")


def process_standing_order_execution(db: Session, standing_order_id: int) -> Optional[models.FinancialTransaction]:
    """Executes a single standing order if due."""
    so = db.query(models.StandingOrder).filter(models.StandingOrder.id == standing_order_id).with_for_update().first()
    if not so or not so.is_active: return None

    # Check if it's time to execute (already done by get_due_standing_orders, but good for direct call)
    # if so.next_execution_date > datetime.utcnow(): return None
    # if so.end_date and so.next_execution_date > so.end_date:
    #     so.is_active = False # Deactivate if past end date
    #     db.commit()
    #     return None

    # Create transaction details from SO
    txn_details = schemas.TransactionCreateRequest(
        transaction_type="STANDING_ORDER_PAYMENT",
        channel=TransactionChannelEnum.STANDING_ORDER,
        amount=so.amount,
        currency=so.currency,
        debit_account_number=so.debit_account_number,
        credit_account_number=so.credit_account_number,
        credit_bank_code=so.credit_bank_code or "OUR_BANK_CODE", # Default to own bank if not specified
        narration=so.narration
    )

    financial_txn = None
    try:
        # Initiate and process the transaction
        financial_txn = initiate_transaction(db, txn_details, initiated_by_customer_id=so.customer_id)

        # This is simplified; real processing depends on if it's intra or interbank
        if so.credit_bank_code and so.credit_bank_code != "OUR_BANK_CODE":
            # Simulate NIP processing for interbank SO
            # nip_req = schemas.NIPFundsTransferRequest(...) # build from so and financial_txn
            # process_nip_funds_transfer(db, financial_txn.id, nip_req)
            update_transaction_status(db, financial_txn.id, TransactionStatusEnum.SUCCESSFUL, "00", "SO Interbank Mock Success", system_remarks="Mock SO NIP")
        else:
            process_intrabank_transfer(db, financial_txn.id) # Re-uses the intra-bank logic

        # If transaction was successful (check financial_txn.status after processing)
        financial_txn_final = get_transaction_by_id(db, financial_txn.id) # Get updated status
        if financial_txn_final.status == TransactionStatusEnum.SUCCESSFUL:
            so.last_execution_date = so.next_execution_date
            so.next_execution_date = _calculate_next_so_execution_date(so.next_execution_date, so.frequency)
            so.failure_count = 0
            # Deactivate if next execution is past end date
            if so.end_date and so.next_execution_date > so.end_date:
                so.is_active = False
        else:
            so.failure_count += 1
            # Potentially deactivate after max failures
            # if so.failure_count >= so.max_failures: so.is_active = False

    except (InsufficientFundsException, InvalidOperationException) as e:
        so.failure_count += 1
        if financial_txn: # Update the specific financial transaction to FAILED
             update_transaction_status(db, financial_txn.id, TransactionStatusEnum.FAILED, system_remarks=f"SO Failed: {str(e)}")
    except Exception as e:
        # Log generic error
        so.failure_count += 1
        if financial_txn:
             update_transaction_status(db, financial_txn.id, TransactionStatusEnum.FAILED, system_remarks=f"SO Failed unexpectedly: {str(e)}")

    db.commit()
    db.refresh(so)
    if financial_txn: db.refresh(financial_txn)
    return financial_txn


# --- Bulk Payment Services (Simplified) ---
def create_bulk_payment_batch(db: Session, batch_request: schemas.BulkPaymentBatchRequest) -> models.BulkPaymentBatch:
    batch_id = "BULK_" + uuid.uuid4().hex[:10].upper()
    total_amount = sum(item.amount for item in batch_request.items)

    db_batch = models.BulkPaymentBatch(
        id=batch_id,
        batch_name=batch_request.batch_name,
        total_amount=total_amount,
        total_transactions=len(batch_request.items),
        status="PENDING_PROCESSING" # Initial status
    )
    db.add(db_batch)

    # Create individual FinancialTransaction records for each item, linked to this batch
    # These will be in PENDING state initially
    for item in batch_request.items:
        txn_id = _generate_transaction_id("BLKITEM")
        db_item_txn = models.FinancialTransaction(
            id=txn_id,
            transaction_type="BULK_PAYMENT_ITEM",
            channel=TransactionChannelEnum.BULK_PAYMENT,
            status=TransactionStatusEnum.PENDING,
            amount=item.amount,
            currency=CurrencyEnum.NGN, # Assuming from debit account currency
            debit_account_number=batch_request.debit_account_number,
            # debit_account_name, debit_bank_code (for debit account)
            credit_account_number=item.credit_account_number,
            credit_account_name=item.credit_account_name,
            credit_bank_code=item.credit_bank_code,
            narration=item.narration,
            initiated_at=datetime.utcnow(),
            # bulk_payment_batch_id=batch_id # This needs the relationship defined on FinancialTransaction model
        )
        # Temporary: Add batch_id to system remarks if direct FK not set up yet.
        db_item_txn.system_remarks = f"Bulk Batch ID: {batch_id}"
        db.add(db_item_txn)

    db.commit()
    db.refresh(db_batch)
    # Async task to process the batch: process_bulk_payment_batch_async(batch_id)
    return db_batch

# --- Transaction Dispute Services ---
def log_transaction_dispute(db: Session, dispute_in: schemas.TransactionDisputeCreate, customer_id: int) -> models.TransactionDispute:
    # Check if transaction exists
    txn = get_transaction_by_id(db, dispute_in.financial_transaction_id)
    if not txn:
        raise NotFoundException(f"Transaction {dispute_in.financial_transaction_id} not found.")

    db_dispute = models.TransactionDispute(
        financial_transaction_id=dispute_in.financial_transaction_id,
        # customer_id=customer_id, # Assuming customer_id is from authenticated user context
        dispute_reason=dispute_in.dispute_reason,
        status="OPEN" # Initial status
    )
    db.add(db_dispute)
    db.commit()
    db.refresh(db_dispute)
    return db_dispute

def get_transaction_dispute(db: Session, dispute_id: int) -> Optional[models.TransactionDispute]:
    return db.query(models.TransactionDispute).filter(models.TransactionDispute.id == dispute_id).first()

# TODO: Add services for USSD, RTGS, POS, ATM transaction processing. These will involve specific integrations.
# TODO: Add fee calculation and application by calling the fees_charges_commission_engine.
