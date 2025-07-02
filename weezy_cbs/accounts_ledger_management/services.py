# Service layer for Accounts & Ledger Management
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any
import json # For audit logging if storing dicts as JSON strings

from . import models, schemas
from .models import AccountTypeEnum, AccountStatusEnum, CurrencyEnum, TransactionTypeEnum # Direct enum access
# from ..customer_identity_management.services import get_customer # To verify customer exists - cross-module import
# from ..core_infrastructure_config_engine.services import get_product_config # For product details
# from ..core_infrastructure_config_engine.models import ProductConfig # For type hinting

import decimal
import random
import string
from datetime import datetime, timedelta, date


# Placeholder for shared exceptions (should be in a shared module)
class NotFoundException(Exception):
    def __init__(self, message="Resource not found"):
        self.message = message
        super().__init__(self.message)

class InvalidOperationException(Exception):
    def __init__(self, message="Invalid operation"):
        self.message = message
        super().__init__(self.message)

class InsufficientFundsException(InvalidOperationException):
    def __init__(self, message="Insufficient funds"):
        super().__init__(message)

# NUBAN Generation Utility (Simplified - Real NUBAN has specific CBN algorithm)
def _generate_nuban(bank_code: str = "999999", serial_length: int = 9) -> str:
    """Generates a NUBAN-like account number. Bank code is usually fixed for the institution."""
    serial_number = ''.join(random.choices(string.digits, k=serial_length))
    check_digit = random.choice(string.digits)
    return serial_number + check_digit

def _log_account_event(db: Session, account_id: int, event_type: str, details: Optional[Dict[str, Any]] = None, changed_by_user_id: str = "SYSTEM"):
    # print(f"AUDIT LOG (Account: {account_id}): Event='{event_type}', Details='{details}', By='{changed_by_user_id}'")
    pass # Placeholder for actual audit logging


# --- Account Services (Part 1: Account Management) ---
# (create_account, get_account_by_id_internal, get_account_by_number, get_accounts_by_customer_id, update_account_status, place_lien_on_account, release_lien_on_account - already implemented in previous step)
# ... (previous Part 1 code from above) ...
# --- Account Services (Part 1: Account Management) ---
def create_account(db: Session, account_in: schemas.AccountCreateRequest, created_by_user_id: str = "SYSTEM") -> models.Account:
    """
    Creates a new bank account for a customer, linked to a product_code.
    """
    # 1. Validate Customer
    # customer = get_customer(db, account_in.customer_id) # Assumes get_customer is available
    # if not customer:
    #     raise NotFoundException(f"Customer with ID {account_in.customer_id} not found.")
    # if not customer.is_active:
    #     raise InvalidOperationException(f"Customer {account_in.customer_id} is not active.")
    # TODO: Check if customer's KYC tier allows opening this type of account/product.

    # 2. Validate Product Code and get product details
    # product_config_model = get_product_config(db, account_in.product_code) # Assumes service from core_infra
    # if not product_config_model or not product_config_model.is_active:
    #     raise NotFoundException(f"Active Product Configuration with code '{account_in.product_code}' not found.")
    # product_params = json.loads(product_config_model.config_parameters_json)

    # Mock product config fetching:
    mock_product_params = {}
    if "SAV" in account_in.product_code.upper():
        mock_product_params = {"account_type": "SAVINGS", "currency": "NGN", "min_opening_balance": 0}
    elif "CUR" in account_in.product_code.upper():
        mock_product_params = {"account_type": "CURRENT", "currency": "NGN", "min_opening_balance": 1000}
    elif "DOM" in account_in.product_code.upper():
        mock_product_params = {"account_type": "DOMICILIARY", "currency": "USD", "min_opening_balance": 100}
    else:
        raise NotFoundException(f"Mock Product Configuration for code '{account_in.product_code}' not found.")

    account_type_from_product = AccountTypeEnum[mock_product_params["account_type"]]
    currency_from_product = CurrencyEnum[mock_product_params["currency"]]

    # 3. Check initial deposit against product minimum (if any)
    min_opening_balance = decimal.Decimal(str(mock_product_params.get("min_opening_balance", 0)))
    if account_in.initial_deposit_amount < min_opening_balance:
        raise InvalidOperationException(f"Initial deposit {account_in.initial_deposit_amount} is less than minimum {min_opening_balance} for product {account_in.product_code}.")

    # 4. Generate unique NUBAN account number
    cbn_bank_code = "999999"
    while True:
        nuban = _generate_nuban(bank_code=cbn_bank_code)
        if not db.query(models.Account).filter(models.Account.account_number == nuban).first():
            break

    db_account = models.Account(
        customer_id=account_in.customer_id,
        product_code=account_in.product_code,
        account_number=nuban,
        account_type=account_type_from_product,
        currency=currency_from_product,
        ledger_balance=decimal.Decimal('0.00'),
        available_balance=decimal.Decimal('0.00'),
        status=AccountStatusEnum.ACTIVE,
        opened_date=date.today(),
        last_customer_initiated_activity_date=datetime.utcnow(),
        fd_maturity_date=account_in.fd_maturity_date if account_type_from_product == AccountTypeEnum.FIXED_DEPOSIT else None,
        fd_interest_rate_pa=account_in.fd_interest_rate_pa if account_type_from_product == AccountTypeEnum.FIXED_DEPOSIT else None,
        fd_principal_amount=account_in.fd_principal_amount if account_type_from_product == AccountTypeEnum.FIXED_DEPOSIT else None,
    )
    db.add(db_account)

    try:
        db.commit()
        db.refresh(db_account)
    except IntegrityError as e:
        db.rollback()
        if "accounts_account_number_key" in str(e.orig):
             raise InvalidOperationException("Generated account number conflict. Please try again.")
        raise InvalidOperationException(f"Could not create account due to a database conflict: {str(e)}")

    _log_account_event(db, db_account.id, "ACCOUNT_CREATED", {"product_code": account_in.product_code, "initial_deposit": account_in.initial_deposit_amount}, created_by_user_id)

    if account_in.initial_deposit_amount > 0:
        # For initial deposit, directly update balances after account creation is committed.
        # A full ledger entry will also be created by the calling service (e.g. deposit module)
        # or a system transaction if this is purely an internal opening balance.
        # Here we simulate the balance update that would result from such a posting.
        # This step is simplified for now; a full ledger posting would be preferred.
        financial_transaction_id_opening = f"SYS_OPEN_{db_account.account_number}"
        _create_ledger_entry_internal(
            db=db,
            account_id=db_account.id,
            financial_transaction_id=financial_transaction_id_opening,
            entry_type=TransactionTypeEnum.CREDIT,
            amount=account_in.initial_deposit_amount,
            currency=db_account.currency,
            narration=f"Initial opening deposit for {db_account.account_number}",
            value_date=datetime.utcnow(),
            channel="SYSTEM",
            is_system_tx=True # Bypass some checks for system-generated entries
        )
        # _create_ledger_entry_internal handles balance update and commit within itself now.
        db.refresh(db_account) # Refresh to get updated balances from ledger posting
    return db_account

def get_account_by_id_internal(db: Session, account_id: int, for_update: bool = False) -> Optional[models.Account]:
    query = db.query(models.Account)
    if for_update:
        query = query.with_for_update()
    return query.filter(models.Account.id == account_id).first()

def get_account_by_number(db: Session, account_number: str, for_update: bool = False) -> Optional[models.Account]:
    query = db.query(models.Account)
    if for_update:
        query = query.with_for_update()
    return query.filter(models.Account.account_number == account_number).first()

def get_accounts_by_customer_id(db: Session, customer_id: int, skip: int = 0, limit: int = 100) -> List[models.Account]:
    return db.query(models.Account).filter(models.Account.customer_id == customer_id).order_by(models.Account.opened_date.desc()).offset(skip).limit(limit).all()

def update_account_status(db: Session, account_number: str, status_request: schemas.UpdateAccountStatusRequest, updated_by_user_id: str) -> models.Account:
    account = get_account_by_number(db, account_number, for_update=True)
    if not account:
        raise NotFoundException(f"Account {account_number} not found.")
    details_before = {"status": account.status.value, "is_post_no_debit": account.is_post_no_debit, "block_reason": account.block_reason}
    new_status_enum = AccountStatusEnum[status_request.status.value]
    if new_status_enum == AccountStatusEnum.CLOSED:
        if account.ledger_balance != decimal.Decimal('0.00'):
            raise InvalidOperationException(f"Account {account_number} cannot be closed with non-zero balance ({account.ledger_balance}).")
        if not status_request.closure_reason:
            raise InvalidOperationException("Closure reason is required to close an account.")
        account.closed_date = date.today()
        account.block_reason = None
        account.is_post_no_debit = False
    elif new_status_enum == AccountStatusEnum.BLOCKED:
        if not status_request.block_reason:
            raise InvalidOperationException("Block reason is required to block an account.")
        account.block_reason = status_request.block_reason
    else:
        account.block_reason = None
    account.status = new_status_enum
    if status_request.is_post_no_debit is not None:
        account.is_post_no_debit = status_request.is_post_no_debit
    account.last_customer_initiated_activity_date = datetime.utcnow()
    details_after = {"status": account.status.value, "is_post_no_debit": account.is_post_no_debit, "block_reason": account.block_reason, "closed_date": account.closed_date}
    _log_account_event(db, account.id, "ACCOUNT_STATUS_UPDATED", {"before": details_before, "after": details_after, "reason_for_change": status_request.reason_for_change}, updated_by_user_id)
    db.commit()
    db.refresh(account)
    return account

def place_lien_on_account(db: Session, account_number: str, lien_request: schemas.PlaceLienRequest, placed_by_user_id: str) -> models.Account:
    account = get_account_by_number(db, account_number, for_update=True)
    if not account:
        raise NotFoundException(f"Account {account_number} not found.")
    if account.status != AccountStatusEnum.ACTIVE:
        raise InvalidOperationException(f"Account {account_number} is not active, cannot place lien.")
    if account.is_post_no_debit:
        raise InvalidOperationException(f"Account {account_number} has Post-No-Debit, cannot place lien.")
    if account.available_balance < lien_request.amount:
        raise InsufficientFundsException(f"Insufficient available balance ({account.available_balance}) in account {account_number} to place lien of {lien_request.amount}.")
    details_before = {"lien_amount": account.lien_amount, "available_balance": account.available_balance}
    account.lien_amount += lien_request.amount
    account.available_balance -= lien_request.amount
    details_after = {"lien_amount": account.lien_amount, "available_balance": account.available_balance}
    _log_account_event(db, account.id, "LIEN_PLACED", {"before": details_before, "after": details_after, "lien_details": lien_request.dict()}, placed_by_user_id)
    db.commit()
    db.refresh(account)
    return account

def release_lien_on_account(db: Session, account_number: str, release_request: schemas.ReleaseLienRequest, released_by_user_id: str) -> models.Account:
    account = get_account_by_number(db, account_number, for_update=True)
    if not account:
        raise NotFoundException(f"Account {account_number} not found.")
    amount_to_actually_release = min(release_request.amount_to_release, account.lien_amount)
    if amount_to_actually_release <= decimal.Decimal('0.00'):
        raise InvalidOperationException("Amount to release must be positive or no lien to release.")
    details_before = {"lien_amount": account.lien_amount, "available_balance": account.available_balance}
    account.lien_amount -= amount_to_actually_release
    account.available_balance += amount_to_actually_release
    details_after = {"lien_amount": account.lien_amount, "available_balance": account.available_balance}
    _log_account_event(db, account.id, "LIEN_RELEASED", {"before": details_before, "after": details_after, "release_details": release_request.dict(), "amount_released": amount_to_actually_release}, released_by_user_id)
    db.commit()
    db.refresh(account)
    return account

# --- Part 2: Ledger & Transaction Posting Services ---

def _create_ledger_entry_internal(
    db: Session,
    account_id: int,
    financial_transaction_id: str,
    entry_type: TransactionTypeEnum,
    amount: decimal.Decimal,
    currency: CurrencyEnum,
    narration: str,
    value_date: datetime, # Should be datetime for value_date
    channel: Optional[str] = "SYSTEM",
    external_reference_number: Optional[str] = None,
    is_system_tx: bool = False # Flag for system transactions like interest, initial deposit
) -> models.LedgerEntry:
    """
    Internal helper to create a single ledger entry and update account balances.
    This function forms part of a larger database transaction, commit is handled by caller.
    It assumes the Account row is already locked if necessary (e.g. by `get_account_by_number(for_update=True)`).
    """
    account = db.query(models.Account).filter(models.Account.id == account_id).first() # No need for_update here if caller handles it
    if not account:
        # This should ideally not happen if caller validates account before calling
        raise NotFoundException(f"Account with ID {account_id} not found for ledger posting.")

    if account.status not in [AccountStatusEnum.ACTIVE] and not is_system_tx:
        # Allow system transactions (like interest on dormant) on non-ACTIVE accounts if business rules permit.
        # For typical customer/teller transactions, account must be ACTIVE.
        raise InvalidOperationException(f"Account {account.account_number} is not active. Current status: {account.status.value}")

    if account.currency != currency: # Ensure currency matches
        raise InvalidOperationException(f"Transaction currency {currency.value} does not match account currency {account.currency.value}.")

    balance_before_txn = account.ledger_balance

    if entry_type == TransactionTypeEnum.DEBIT:
        if not is_system_tx and account.is_post_no_debit:
            raise InvalidOperationException(f"Account {account.account_number} has Post-No-Debit restriction.")
        if not is_system_tx and (account.available_balance < amount):
            raise InsufficientFundsException(f"Insufficient available balance in account {account.account_number} for debit of {amount}.")
        account.ledger_balance -= amount
        account.available_balance -= amount # Simplification: assumes all debits affect available balance immediately
    elif entry_type == TransactionTypeEnum.CREDIT:
        account.ledger_balance += amount
        account.available_balance += amount # Simplification: assumes all credits affect available balance immediately
    else:
        raise ValueError("Invalid ledger entry type specified.") # Should not happen with Enum

    account.last_customer_initiated_activity_date = datetime.utcnow() # Update activity date

    ledger_entry = models.LedgerEntry(
        financial_transaction_id=financial_transaction_id,
        account_id=account_id,
        entry_type=entry_type,
        amount=amount, # Already decimal.Decimal
        currency=currency,
        narration=narration,
        transaction_date=datetime.utcnow(), # Booking date/time
        value_date=value_date, # Value date/time
        balance_before=balance_before_txn,
        balance_after=account.ledger_balance,
        channel=channel,
        external_reference_number=external_reference_number
    )
    db.add(ledger_entry)
    db.flush() # Flush to assign ID to ledger_entry if needed by caller before commit
    # db.commit() # COMMIT IS HANDLED BY THE CALLING SERVICE WRAPPING THE TRANSACTION
    # db.refresh(account) # Caller should refresh if needed after its commit
    # db.refresh(ledger_entry) # Caller should refresh if needed after its commit
    return ledger_entry


def post_internal_transaction(db: Session, request: schemas.InternalTransactionPostingRequest) -> schemas.InternalTransactionPostingResponse:
    """
    Handles posting for internal transfers (Account-to-Account, Account-to-GL, GL-to-Account, GL-to-GL).
    This is the primary service for moving funds within the bank's own books.
    It ensures atomicity for double-entry postings.
    """
    debit_entry_model: Optional[models.LedgerEntry] = None
    credit_entry_model: Optional[models.LedgerEntry] = None

    # Determine debit and credit entities (Account or GL)
    # This section needs robust logic to fetch account/GL models and check their status/validity.
    # For brevity, assuming helper functions like _get_entity_for_posting(db, leg_details) exist.

    # For example, if debit_leg specifies account_number:
    # debit_target_account = get_account_by_number(db, request.debit_leg['account_number'], for_update=True)
    # if not debit_target_account: raise NotFoundException("Debit account not found.")
    # ... similar for credit_target_account or GLs ...

    # For mock purposes, assume accounts are valid and fetched.
    # In a real system, you'd lock rows for accounts involved.
    mock_debit_account_id = 1 # Placeholder
    mock_credit_account_id = 2 # Placeholder

    try:
        if request.debit_leg: # Assuming it's an account for simplicity
            debit_entry_model = _create_ledger_entry_internal(
                db=db, account_id=mock_debit_account_id, # Replace with actual fetched account ID
                financial_transaction_id=request.financial_transaction_id,
                entry_type=TransactionTypeEnum.DEBIT,
                amount=request.amount, currency=request.currency,
                narration=request.debit_leg.get('narration', request.narration_overall),
                value_date=request.value_date or datetime.utcnow(), channel=request.channel,
                external_reference_number=request.external_reference
            )

        if request.credit_leg: # Assuming it's an account for simplicity
             credit_entry_model = _create_ledger_entry_internal(
                db=db, account_id=mock_credit_account_id, # Replace with actual fetched account ID
                financial_transaction_id=request.financial_transaction_id,
                entry_type=TransactionTypeEnum.CREDIT,
                amount=request.amount, currency=request.currency,
                narration=request.credit_leg.get('narration', request.narration_overall),
                value_date=request.value_date or datetime.utcnow(), channel=request.channel,
                external_reference_number=request.external_reference
            )

        # If only single leg info provided (e.g. system posting to one customer account from/to a GL)
        # ... handle single leg posting logic ...

        db.commit() # Commit all ledger entries and account balance updates together

        # Refresh models after commit if their IDs or computed values are needed
        if debit_entry_model: db.refresh(debit_entry_model)
        if credit_entry_model: db.refresh(credit_entry_model)

        # _log_account_event for both accounts involved if applicable.

        return schemas.InternalTransactionPostingResponse(
            financial_transaction_id=request.financial_transaction_id,
            status="SUCCESSFUL_POSTING",
            message="Transaction posted successfully to ledger.",
            debit_ledger_entry_id=debit_entry_model.id if debit_entry_model else None,
            credit_ledger_entry_id=credit_entry_model.id if credit_entry_model else None,
            timestamp=datetime.utcnow()
        )
    except (InsufficientFundsException, InvalidOperationException, NotFoundException) as e:
        db.rollback()
        # Log the specific error for the financial_transaction_id in TransactionManagement system
        raise e # Re-raise for TransactionManagement to handle the master FT status
    except Exception as e:
        db.rollback()
        # Log generic error
        raise InvalidOperationException(f"Ledger posting failed unexpectedly for FT ID {request.financial_transaction_id}: {str(e)}")


def post_cash_deposit_to_account(db: Session, account_number: str, amount: decimal.Decimal, currency: CurrencyEnum,
                                 narration: str, channel: str, financial_transaction_id: str,
                                 value_date: Optional[datetime] = None, posted_by_user_id: str = "SYSTEM",
                                 teller_gl_code: str = "TELLER_CASH_GL_MAIN") -> models.LedgerEntry: # Teller's cash GL
    """Posts a cash deposit: Credits customer account, Debits Teller/Branch Cash GL."""
    target_account = get_account_by_number(db, account_number, for_update=True)
    if not target_account:
        raise NotFoundException(f"Account {account_number} for cash deposit not found.")

    # This is a simplified call to post_internal_transaction.
    # A more direct approach would be to use _create_ledger_entry_internal for customer leg,
    # and another _create_ledger_entry_internal for the GL leg (if GLs are also 'Account' like entities in ledger).
    # For now, conceptualizing the double entry:

    # 1. Credit Customer Account
    customer_credit_entry = _create_ledger_entry_internal(
        db=db, account_id=target_account.id,
        financial_transaction_id=financial_transaction_id,
        entry_type=TransactionTypeEnum.CREDIT, amount=amount, currency=currency,
        narration=narration, value_date=value_date or datetime.utcnow(), channel=channel
    )

    # 2. Debit Teller/Branch Cash GL (conceptual - GL posting needs full implementation)
    # This assumes a function `post_to_gl_account(db, gl_code, amount, type, ft_id, ...)` exists.
    # For now, this leg is implicit or handled by accounting reconciliation.
    # _log_account_event(db, target_account.id, "CASH_DEPOSIT_POSTED", {"amount": amount, "ft_id": financial_transaction_id}, posted_by_user_id)

    db.commit()
    db.refresh(customer_credit_entry)
    db.refresh(target_account) # Refresh account to get updated balances
    return customer_credit_entry


def post_cash_withdrawal_from_account(db: Session, account_number: str, amount: decimal.Decimal, currency: CurrencyEnum,
                                      narration: str, channel: str, financial_transaction_id: str,
                                      value_date: Optional[datetime] = None, posted_by_user_id: str = "SYSTEM",
                                      teller_gl_code: str = "TELLER_CASH_GL_MAIN") -> models.LedgerEntry:
    """Posts a cash withdrawal: Debits customer account, Credits Teller/Branch Cash GL."""
    target_account = get_account_by_number(db, account_number, for_update=True)
    if not target_account:
        raise NotFoundException(f"Account {account_number} for cash withdrawal not found.")

    # 1. Debit Customer Account
    customer_debit_entry = _create_ledger_entry_internal(
        db=db, account_id=target_account.id,
        financial_transaction_id=financial_transaction_id,
        entry_type=TransactionTypeEnum.DEBIT, amount=amount, currency=currency,
        narration=narration, value_date=value_date or datetime.utcnow(), channel=channel
    )

    # 2. Credit Teller/Branch Cash GL (conceptual)
    # _log_account_event(db, target_account.id, "CASH_WITHDRAWAL_POSTED", {"amount": amount, "ft_id": financial_transaction_id}, posted_by_user_id)

    db.commit()
    db.refresh(customer_debit_entry)
    db.refresh(target_account)
    return customer_debit_entry


# --- Balance Inquiry & Transaction History ---
def get_account_balance(db: Session, account_number: str) -> Optional[schemas.AccountBalanceResponse]:
    account = get_account_by_number(db, account_number)
    if not account:
        return None
    return schemas.AccountBalanceResponse(
        account_number=account.account_number,
        ledger_balance=account.ledger_balance,
        available_balance=account.available_balance,
        currency=schemas.CurrencySchema(account.currency.value) # Ensure schema enum used
    )

def get_transaction_history_for_account(
    db: Session, account_number: str,
    skip: int = 0, limit: int = 100,
    start_date: Optional[date] = None, end_date: Optional[date] = None
) -> List[models.LedgerEntry]:
    account = get_account_by_number(db, account_number)
    if not account:
        # Optionally raise NotFoundException or return empty list based on API contract
        raise NotFoundException(f"Account {account_number} not found.")

    query = db.query(models.LedgerEntry).filter(models.LedgerEntry.account_id == account.id)
    if start_date:
        query = query.filter(models.LedgerEntry.value_date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(models.LedgerEntry.value_date <= datetime.combine(end_date, datetime.max.time())) # Inclusive of end date

    return query.order_by(models.LedgerEntry.value_date.desc(), models.LedgerEntry.id.desc()).offset(skip).limit(limit).all()

# --- Interest & Dormancy services would be here (Part 3 - Batch Processes, if split further) ---
# For now, keeping them in Part 2 as they involve ledger interactions.

def accrue_daily_interest_for_account(db: Session, account_id: int, calculation_date: date, interest_rate_pa: decimal.Decimal, product_interest_config: Dict) -> Optional[models.InterestAccrualLog]:
    """Calculates and logs daily accrued interest for a single account."""
    account = get_account_by_id_internal(db, account_id, for_update=True)
    if not account or account.status != AccountStatusEnum.ACTIVE or account.account_type not in [AccountTypeEnum.SAVINGS, AccountTypeEnum.FIXED_DEPOSIT]: # Example eligibility
        return None

    # Check if already accrued for this date
    # if account.last_interest_accrual_run_date and account.last_interest_accrual_run_date >= calculation_date:
    #    return None # Already accrued

    # Determine balance for interest (e.g., minimum daily balance, average balance - simplified to current ledger for now)
    balance_for_interest = account.ledger_balance
    min_bal_for_interest = decimal.Decimal(str(product_interest_config.get("min_balance_for_interest", 0)))

    if balance_for_interest < min_bal_for_interest:
        return None # Below minimum balance to earn interest

    # day_count_convention = product_interest_config.get("day_count_convention", 365) # e.g. 365, 360, Actual/Actual
    daily_rate = (interest_rate_pa / decimal.Decimal('100')) / decimal.Decimal('365')

    accrued_amount_today = (balance_for_interest * daily_rate).quantize(decimal.Decimal('0.0001')) # 4DP for accrual

    if accrued_amount_today > decimal.Decimal('0.0000'):
        accrual_log = models.InterestAccrualLog(
            account_id=account.id,
            accrual_date=calculation_date,
            amount_accrued=accrued_amount_today,
            interest_rate_pa_used=interest_rate_pa,
            balance_subject_to_interest=balance_for_interest
        )
        db.add(accrual_log)

        account.accrued_interest_payable += accrued_amount_today # Add to the running total of accrued interest
        account.last_interest_accrual_run_date = calculation_date

        # db.commit() # Commit should be handled by the batch process orchestrating this.
        # db.refresh(account)
        # db.refresh(accrual_log)
        return accrual_log
    return None

def post_accrued_interest_to_ledger(db: Session, account_id: int, posting_date: date, financial_transaction_id_base: str, posted_by_user_id: str = "SYSTEM_INTEREST_POST") -> Optional[models.LedgerEntry]:
    """Posts total accumulated interest to the account's ledger balance."""
    account = get_account_by_id_internal(db, account_id, for_update=True)
    if not account or account.accrued_interest_payable <= decimal.Decimal('0.00'):
        return None

    amount_to_post = account.accrued_interest_payable.quantize(decimal.Decimal('0.01')) # Post rounded to 2DP

    if amount_to_post <= decimal.Decimal('0.00'):
        # Clear tiny residual accrued interest if it rounds to zero for posting
        account.accrued_interest_payable = decimal.Decimal('0.00')
        # db.commit()
        return None

    ft_id_interest = f"{financial_transaction_id_base}_ACC{account.id}"

    # Credit Customer Account, Debit Bank's Interest Expense GL
    customer_credit_entry = _create_ledger_entry_internal(
        db=db, account_id=account.id,
        financial_transaction_id=ft_id_interest,
        entry_type=TransactionTypeEnum.CREDIT, amount=amount_to_post, currency=account.currency,
        narration=f"Interest Credit for period ending {posting_date.strftime('%Y-%m-%d')}",
        value_date=datetime.combine(posting_date, datetime.min.time()), channel="SYSTEM_INTEREST",
        is_system_tx=True
    )

    # Debit Interest Expense GL (conceptual)
    # _create_ledger_entry_internal(db, gl_account_id_interest_expense, ft_id_interest, TransactionTypeEnum.DEBIT, ...)

    account.accrued_interest_payable -= amount_to_post # Reduce the accumulated accrued interest
    _log_account_event(db, account.id, "INTEREST_POSTED", {"amount": amount_to_post, "ft_id": ft_id_interest}, posted_by_user_id)

    # Update InterestAccrualLog records for this account to mark them as posted
    # db.query(models.InterestAccrualLog).filter(
    #     models.InterestAccrualLog.account_id == account.id,
    #     models.InterestAccrualLog.is_posted_to_account_ledger == False,
    #     models.InterestAccrualLog.accrual_date <= posting_date
    # ).update({"is_posted_to_account_ledger": True, "posting_date": posting_date, "related_ledger_entry_id": customer_credit_entry.id})

    # db.commit() # Handled by caller
    # db.refresh(customer_credit_entry)
    # db.refresh(account)
    return customer_credit_entry

def process_account_dormancy(db: Session, account_id: int, inactivity_days_config: int, dormancy_days_config: int, system_user_id: str = "SYSTEM_DORMANCY") -> Optional[str]:
    """Checks and updates dormancy status for a single account."""
    account = get_account_by_id_internal(db, account_id, for_update=True)
    if not account or account.status in [AccountStatusEnum.CLOSED, AccountStatusEnum.DORMANT]: # Already closed or dormant
        return None

    now_dt = datetime.utcnow()
    last_activity_dt = account.last_customer_initiated_activity_date

    days_inactive = (now_dt - last_activity_dt).days
    new_status = None

    if account.status == AccountStatusEnum.ACTIVE and days_inactive >= inactivity_days_config:
        new_status = AccountStatusEnum.INACTIVE
    elif account.status == AccountStatusEnum.INACTIVE and days_inactive >= dormancy_days_config:
        new_status = AccountStatusEnum.DORMANT
        # TODO: Additional actions for dormancy (e.g., move to dormant ledger, stop certain charges)

    if new_status and new_status != account.status:
        details_before = {"status": account.status.value}
        account.status = new_status
        details_after = {"status": account.status.value}
        _log_account_event(db, account.id, f"ACCOUNT_STATUS_CHANGED_TO_{new_status.value}", {"before": details_before, "after": details_after, "days_inactive": days_inactive}, system_user_id)
        # db.commit() # Handled by batch caller
        # db.refresh(account)
        return new_status.value
    return None
