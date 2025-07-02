# Service layer for Accounts & Ledger Management
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError
from . import models, schemas
from .models import AccountTypeEnum, AccountStatusEnum, CurrencyEnum, TransactionTypeEnum # Direct enum access
import decimal
import random
import string
from datetime import datetime, timedelta

# Assuming shared exceptions and NUBAN generation utility
# from weezy_cbs.shared import exceptions, nuban_generator
# from weezy_cbs.customer_identity_management.services import get_customer # To verify customer exists

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

def generate_nuban(bank_code="999999"): # Weezy's mock bank code
    """Generates a NUBAN-like account number. Real NUBAN has specific algorithm."""
    serial_number = ''.join(random.choices(string.digits, k=9))
    # Simplified check digit (sum modulo 10, then 10 - result, or 0 if result is 0)
    # This is NOT the real NUBAN check digit algorithm.
    digits = [int(d) for d in (bank_code[:3] + serial_number)] # Use part of bank code + serial
    s = sum(digits[i] * w for i, w in enumerate([3,7,3,3,7,3,3,7,3,3,7,3])) % 10
    check_digit = str((10 - s) % 10)
    return serial_number + check_digit


# --- Account Services ---
def create_account(db: Session, account_in: schemas.AccountCreate, customer_id: int) -> models.Account:
    """
    Creates a new bank account for a customer.
    Requires customer_id from customer_identity_management.
    """
    # Verify customer exists (ideally call customer service)
    # customer = get_customer(db, customer_id)
    # if not customer:
    #     raise NotFoundException(f"Customer with ID {customer_id} not found.")

    if account_in.account_number:
        existing_acc = get_account_by_number(db, account_in.account_number)
        if existing_acc:
            raise InvalidOperationException(f"Account number {account_in.account_number} already exists.")
        nuban = account_in.account_number
    else:
        # Generate unique NUBAN (simplified)
        while True:
            nuban = generate_nuban()
            if not get_account_by_number(db, nuban):
                break

    db_account = models.Account(
        customer_id=customer_id, # Use the provided customer_id
        account_number=nuban,
        account_type=account_in.account_type,
        currency=account_in.currency,
        ledger_balance=decimal.Decimal('0.0'), # Initial balance is 0 before any deposit
        available_balance=decimal.Decimal('0.0'),
        status=AccountStatusEnum.ACTIVE, # Default status
        fd_maturity_date=account_in.fd_maturity_date,
        fd_interest_rate=account_in.fd_interest_rate,
        fd_principal=account_in.fd_principal,
        last_activity_date=datetime.utcnow()
    )
    db.add(db_account)

    try:
        db.commit()
        db.refresh(db_account)
    except IntegrityError: # Handles race conditions for account_number if not perfectly unique
        db.rollback()
        raise InvalidOperationException("Could not create account due to a conflict. Please try again.")

    # If there's an initial deposit, post it as the first transaction
    if account_in.initial_deposit_amount and account_in.initial_deposit_amount > 0:
        master_tx_id = "TXN_OPEN_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
        # This is a credit to the new account from a conceptual "cash" or "suspense" GL
        _create_ledger_entry_internal(
            db=db,
            account_id=db_account.id,
            transaction_id=master_tx_id,
            entry_type=TransactionTypeEnum.CREDIT,
            amount=account_in.initial_deposit_amount,
            currency=db_account.currency,
            narration=f"Initial deposit for account opening {db_account.account_number}",
            value_date=datetime.utcnow(),
            channel="SYSTEM",
            is_system_tx=True # Flag to bypass some checks like available balance on a GL
        )
        db.commit() # Commit the ledger entry
        db.refresh(db_account)

    return db_account

def get_account(db: Session, account_id: int) -> Optional[models.Account]:
    return db.query(models.Account).filter(models.Account.id == account_id).first()

def get_account_for_update(db: Session, account_id: int) -> Optional[models.Account]:
    """Retrieves an account with a row-level lock for updates."""
    return db.query(models.Account).filter(models.Account.id == account_id).with_for_update().first()

def get_account_by_number(db: Session, account_number: str) -> Optional[models.Account]:
    return db.query(models.Account).filter(models.Account.account_number == account_number).first()

def get_accounts_by_customer_id(db: Session, customer_id: int, skip: int = 0, limit: int = 100) -> List[models.Account]:
    return db.query(models.Account).filter(models.Account.customer_id == customer_id).offset(skip).limit(limit).all()

def update_account_status(db: Session, account_id: int, status_in: schemas.UpdateAccountStatusRequest) -> models.Account:
    account = get_account_for_update(db, account_id)
    if not account:
        raise NotFoundException(f"Account with ID {account_id} not found.")

    # Add logic here for valid status transitions, e.g., cannot move from CLOSED to ACTIVE easily
    account.status = status_in.status
    if status_in.status == AccountStatusEnum.CLOSED:
        account.closed_date = datetime.utcnow()
        # Ensure balance is zero before closing, or handle residual balance
        if account.ledger_balance != decimal.Decimal('0.0'):
            # db.rollback() # Or handle differently
            raise InvalidOperationException("Account balance must be zero before closing.")

    account.last_activity_date = datetime.utcnow()
    db.commit()
    db.refresh(account)
    # TODO: Audit log for status change
    return account

# --- Ledger & Transaction Services ---
def _create_ledger_entry_internal(
    db: Session,
    account_id: int,
    transaction_id: str,
    entry_type: TransactionTypeEnum,
    amount: decimal.Decimal,
    currency: CurrencyEnum,
    narration: str,
    value_date: datetime,
    channel: Optional[str] = "SYSTEM",
    reference_number: Optional[str] = None,
    is_system_tx: bool = False # Special flag for system transactions like interest posting
    ) -> models.LedgerEntry:
    """
    Internal helper to create a single ledger entry and update account balances.
    This function assumes it's part of a larger database transaction managed by the caller.
    Locking (with_for_update) should be handled by the caller on the account object.
    """
    account = db.query(models.Account).filter(models.Account.id == account_id).with_for_update().first() # Lock account row
    if not account:
        raise NotFoundException(f"Account with ID {account_id} not found for ledger posting.")

    if account.status not in [AccountStatusEnum.ACTIVE]: # And potentially other statuses that allow posting
        raise InvalidOperationException(f"Account {account.account_number} is not active. Current status: {account.status.value}")

    if account.currency != currency:
        raise InvalidOperationException(f"Transaction currency {currency.value} does not match account currency {account.currency.value}.")

    balance_before_txn = account.ledger_balance
    available_balance_before_txn = account.available_balance

    if entry_type == TransactionTypeEnum.DEBIT:
        if not is_system_tx and (available_balance_before_txn < amount): # System tx might overdraw a GL account
            raise InsufficientFundsException(f"Insufficient available balance in account {account.account_number}.")
        account.ledger_balance -= amount
        account.available_balance -= amount # Assuming cleared funds for simplicity here
    elif entry_type == TransactionTypeEnum.CREDIT:
        account.ledger_balance += amount
        account.available_balance += amount # Assuming cleared funds
    else:
        raise ValueError("Invalid transaction type")

    account.last_activity_date = datetime.utcnow()

    ledger_entry = models.LedgerEntry(
        transaction_id=transaction_id,
        account_id=account_id,
        entry_type=entry_type,
        amount=amount,
        currency=currency,
        narration=narration,
        transaction_date=datetime.utcnow(), # Booking date
        value_date=value_date,
        balance_before=balance_before_txn,
        balance_after=account.ledger_balance,
        channel=channel,
        reference_number=reference_number
    )
    db.add(ledger_entry)
    # db.commit() # Caller should commit
    # db.refresh(account)
    # db.refresh(ledger_entry)
    return ledger_entry


def post_double_entry_transaction(db: Session, trans_details: schemas.PostTransactionRequest) -> schemas.PostTransactionResponse:
    """
    Posts a double-entry transaction affecting two accounts or an account and a GL.
    Ensures atomicity: both legs succeed or both fail.
    """
    # This is a simplified example. Real GL systems are complex.
    # We'll use account numbers. For GLs, you'd fetch GL model instances.

    debit_account = None
    credit_account = None
    master_transaction_id = "TXN_" + trans_details.transaction_reference # Or generate a new UUID

    if trans_details.from_account_number:
        debit_account = get_account_by_number(db, trans_details.from_account_number)
        if not debit_account:
            raise NotFoundException(f"Debit account {trans_details.from_account_number} not found.")
    # else if trans_details.from_gl_code: fetch GL account
    else:
        raise InvalidOperationException("Debit account or GL must be specified.")

    if trans_details.to_account_number:
        credit_account = get_account_by_number(db, trans_details.to_account_number)
        if not credit_account:
            raise NotFoundException(f"Credit account {trans_details.to_account_number} not found.")
    # else if trans_details.to_gl_code: fetch GL account
    else:
        raise InvalidOperationException("Credit account or GL must be specified.")

    # Value date defaults to now if not provided
    value_date = trans_details.value_date or datetime.utcnow()

    try:
        # Debit Leg
        debit_entry_model = _create_ledger_entry_internal(
            db=db,
            account_id=debit_account.id, # Assuming it's an account-to-account transfer
            transaction_id=master_transaction_id,
            entry_type=TransactionTypeEnum.DEBIT,
            amount=trans_details.amount,
            currency=trans_details.currency, # Ensure currency conversion if accounts differ
            narration=trans_details.narration,
            value_date=value_date,
            channel=trans_details.channel,
            reference_number=trans_details.transaction_reference + "_DR"
        )

        # Credit Leg
        credit_entry_model = _create_ledger_entry_internal(
            db=db,
            account_id=credit_account.id,
            transaction_id=master_transaction_id,
            entry_type=TransactionTypeEnum.CREDIT,
            amount=trans_details.amount,
            currency=trans_details.currency, # Ensure currency conversion if accounts differ
            narration=trans_details.narration,
            value_date=value_date,
            channel=trans_details.channel,
            reference_number=trans_details.transaction_reference + "_CR"
        )

        db.commit()
        db.refresh(debit_entry_model) # Refresh to get committed state
        db.refresh(credit_entry_model)

        return schemas.PostTransactionResponse(
            master_transaction_id=master_transaction_id,
            status="SUCCESSFUL",
            message="Transaction posted successfully.",
            debit_entry=schemas.LedgerEntryResponse.from_orm(debit_entry_model),
            credit_entry=schemas.LedgerEntryResponse.from_orm(credit_entry_model),
            timestamp=datetime.utcnow()
        )

    except (InsufficientFundsException, InvalidOperationException, NotFoundException) as e:
        db.rollback()
        raise e # Re-raise the specific exception
    except Exception as e:
        db.rollback()
        # Log general exception e
        raise InvalidOperationException(f"Transaction failed due to an unexpected error: {str(e)}")


def get_ledger_entries_for_account(db: Session, account_id: int, skip: int = 0, limit: int = 100, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[models.LedgerEntry]:
    query = db.query(models.LedgerEntry).filter(models.LedgerEntry.account_id == account_id)
    if start_date:
        query = query.filter(models.LedgerEntry.transaction_date >= start_date)
    if end_date:
        # Add 1 day to end_date to make it inclusive of the whole day
        query = query.filter(models.LedgerEntry.transaction_date < (end_date + timedelta(days=1)))

    return query.order_by(models.LedgerEntry.transaction_date.desc(), models.LedgerEntry.id.desc()).offset(skip).limit(limit).all()

def get_ledger_entry_count_for_account(db: Session, account_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
    query = db.query(func.count(models.LedgerEntry.id)).filter(models.LedgerEntry.account_id == account_id)
    if start_date:
        query = query.filter(models.LedgerEntry.transaction_date >= start_date)
    if end_date:
        query = query.filter(models.LedgerEntry.transaction_date < (end_date + timedelta(days=1)))
    return query.scalar_one()


# --- Balance Inquiry ---
def get_account_balance(db: Session, account_number: str) -> Optional[schemas.AccountBalanceResponse]:
    account = get_account_by_number(db, account_number)
    if not account:
        return None
    return schemas.AccountBalanceResponse(
        account_number=account.account_number,
        ledger_balance=account.ledger_balance,
        available_balance=account.available_balance,
        currency=account.currency
    )

# --- Lien Management ---
def place_lien(db: Session, account_number: str, lien_request: schemas.PlaceLienRequest) -> models.Account:
    account = db.query(models.Account).filter(models.Account.account_number == account_number).with_for_update().first()
    if not account:
        raise NotFoundException(f"Account {account_number} not found.")
    if account.status != AccountStatusEnum.ACTIVE:
        raise InvalidOperationException("Account is not active.")

    # Check if enough available balance MINUS existing lien to cover new lien.
    # Or, if lien can exceed available balance (depends on bank policy for certain lien types)
    effective_available_for_lien = account.available_balance # Simple model: lien reduces available balance directly
    if effective_available_for_lien < lien_request.amount:
        raise InsufficientFundsException("Not enough available balance to place lien of specified amount.")

    account.lien_amount += lien_request.amount
    account.available_balance -= lien_request.amount # Reduce available balance by lien amount
    account.last_activity_date = datetime.utcnow()

    # TODO: Store individual lien details in a separate LienDetails table for tracking by reason/expiry
    # models.LienDetail(account_id=account.id, amount=lien_request.amount, reason=lien_request.reason, ...)

    db.commit()
    db.refresh(account)
    return account

def release_lien(db: Session, account_number: str, release_request: schemas.ReleaseLienRequest) -> models.Account:
    account = db.query(models.Account).filter(models.Account.account_number == account_number).with_for_update().first()
    if not account:
        raise NotFoundException(f"Account {account_number} not found.")

    # This is simplified. Proper lien release would require identifying specific lien to release.
    # For now, we release a portion of the total lien amount.
    # TODO: Fetch specific LienDetail by reason or ID, release that, and sum remaining active liens.

    amount_to_release = release_request.amount
    if amount_to_release is None or amount_to_release > account.lien_amount: # Release all or up to total lien
        amount_to_release = account.lien_amount

    if amount_to_release <= decimal.Decimal('0.0'):
        raise InvalidOperationException("Lien release amount must be positive.")

    account.lien_amount -= amount_to_release
    account.available_balance += amount_to_release # Increase available balance
    account.last_activity_date = datetime.utcnow()

    db.commit()
    db.refresh(account)
    return account

# --- Interest Accrual & Posting (Simplified) ---
# Real interest calculation is complex (day-basis, compounding rules, product-specific rates)
def calculate_and_accrue_daily_interest_for_account(db: Session, account_id: int, calculation_date: datetime, interest_rate_pa: decimal.Decimal) -> Optional[schemas.AccrueInterestResponse]:
    """Calculates and logs daily accrued interest for a single account."""
    account = db.query(models.Account).filter(models.Account.id == account_id).with_for_update().first()
    if not account or account.status != AccountStatusEnum.ACTIVE or account.account_type != AccountTypeEnum.SAVINGS: # Example: only for savings
        return None # Or log skip

    # Simplified: Use current ledger balance. Real systems use average daily balance or day-end balance.
    # Ensure calculation_date is for a period not yet accrued.
    # last_accrual = account.last_interest_accrual_date
    # if last_accrual and last_accrual.date() >= calculation_date.date():
    #    return None # Already accrued for this date or future

    daily_rate = (interest_rate_pa / decimal.Decimal('100')) / decimal.Decimal('365') # Assuming 365 day year
    balance_for_interest = account.ledger_balance # Simplification

    if balance_for_interest <= decimal.Decimal('0.0'): # No interest on zero or negative balance
        return None

    accrued_amount_today = balance_for_interest * daily_rate
    accrued_amount_today = accrued_amount_today.quantize(decimal.Decimal('0.0001')) # Round to 4 decimal places

    if accrued_amount_today > decimal.Decimal('0.0'):
        account.accrued_interest += accrued_amount_today
        account.last_interest_accrual_date = calculation_date

        # Log this accrual (e.g., in models.InterestAccrualLog)
        # accrual_log = models.InterestAccrualLog(...)
        # db.add(accrual_log)

        db.commit() # Commit changes to account.accrued_interest
        db.refresh(account)
        return schemas.AccrueInterestResponse(
            account_id=account.id,
            amount_accrued=accrued_amount_today,
            new_total_accrued_interest=account.accrued_interest
        )
    return None

def post_accumulated_interest_to_account(db: Session, account_id: int, posting_date: datetime) -> Optional[schemas.PostAccruedInterestResponse]:
    """Posts total accumulated interest to the account's ledger balance."""
    account = db.query(models.Account).filter(models.Account.id == account_id).with_for_update().first()
    if not account or account.accrued_interest <= decimal.Decimal('0.0'):
        return None # No interest to post or account not found

    amount_to_post = account.accrued_interest.quantize(decimal.Decimal('0.01')) # Post rounded to 2 decimal places (currency subunit)

    if amount_to_post <= decimal.Decimal('0.0'):
        return None


    master_tx_id = "TXN_INTPOST_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10)) + f"_{account.id}"
    try:
        # This is a credit to the customer account from an "Interest Expense GL" (not modeled here)
        _create_ledger_entry_internal(
            db=db,
            account_id=account.id,
            transaction_id=master_tx_id,
            entry_type=TransactionTypeEnum.CREDIT,
            amount=amount_to_post,
            currency=account.currency,
            narration=f"Interest posting for period ending {posting_date.strftime('%Y-%m-%d')}",
            value_date=posting_date,
            channel="SYSTEM",
            is_system_tx=True
        )

        account.accrued_interest -= amount_to_post # Reduce accrued interest by amount posted
        if account.accrued_interest < decimal.Decimal('0.0'): # Should not happen with proper quantization
            account.accrued_interest = decimal.Decimal('0.0')

        db.commit()
        db.refresh(account)

        return schemas.PostAccruedInterestResponse(
            account_id=account.id,
            amount_posted=amount_to_post,
            new_ledger_balance=account.ledger_balance
        )
    except Exception as e:
        db.rollback()
        # Log e
        raise InvalidOperationException(f"Failed to post interest for account {account.account_number}: {str(e)}")


# --- Dormancy/Inactivity Handling ---
# A batch job would run this periodically
def process_dormant_accounts(db: Session, dormancy_period_days: int, inactivity_period_days: int):
    """
    Identifies and updates accounts to INACTIVE or DORMANT based on last activity date.
    """
    now = datetime.utcnow()
    dormancy_threshold_date = now - timedelta(days=dormancy_period_days)
    inactivity_threshold_date = now - timedelta(days=inactivity_period_days)

    # Active to Inactive
    accounts_to_make_inactive = db.query(models.Account).filter(
        models.Account.status == AccountStatusEnum.ACTIVE,
        models.Account.last_activity_date < inactivity_threshold_date
    ).all()
    for acc in accounts_to_make_inactive:
        acc.status = AccountStatusEnum.INACTIVE
        # Log this change

    # Inactive to Dormant
    accounts_to_make_dormant = db.query(models.Account).filter(
        models.Account.status == AccountStatusEnum.INACTIVE,
        models.Account.last_activity_date < dormancy_threshold_date
    ).all()
    for acc in accounts_to_make_dormant:
        acc.status = AccountStatusEnum.DORMANT
        # Log this change, potentially move to a different GL pool

    db.commit()
    return {"made_inactive": len(accounts_to_make_inactive), "made_dormant": len(accounts_to_make_dormant)}
