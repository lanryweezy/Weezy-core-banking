# Service layer for Loan Management Module
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from .models import LoanApplicationStatusEnum, LoanAccountStatusEnum, CurrencyEnum # Direct enum access
import decimal
import random
import string
from datetime import datetime, date
from dateutil.relativedelta import relativedelta # For adding months to dates

# Placeholder for shared exceptions, other services, and utilities
# from weezy_cbs.shared import exceptions
# from weezy_cbs.customer_identity_management.services import get_customer
# from weezy_cbs.accounts_ledger_management.services import post_double_entry_transaction, generate_nuban as generate_loan_account_number, get_account_by_number as get_deposit_account
# from weezy_cbs.integrations import credit_bureau # For CRC, FirstCentral, etc.

class NotFoundException(Exception): pass
class InvalidOperationException(Exception): pass
class CreditRiskException(Exception): pass

def generate_reference(prefix="APP"):
    return f"{prefix}-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))

def generate_loan_account_number_placeholder():
    return "LACC" + "".join(random.choices(string.digits, k=8))

# --- Loan Product Services ---
def create_loan_product(db: Session, product_in: schemas.LoanProductCreate) -> models.LoanProduct:
    db_product = models.LoanProduct(**product_in.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def get_loan_product(db: Session, product_id: int) -> Optional[models.LoanProduct]:
    return db.query(models.LoanProduct).filter(models.LoanProduct.id == product_id).first()

def get_loan_products(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[models.LoanProduct]:
    query = db.query(models.LoanProduct)
    if active_only:
        query = query.filter(models.LoanProduct.is_active == True)
    return query.offset(skip).limit(limit).all()

# --- Loan Application Services ---
def create_loan_application(db: Session, application_in: schemas.LoanApplicationCreate) -> models.LoanApplication:
    # Validate customer exists
    # customer = get_customer(db, application_in.customer_id)
    # if not customer:
    #     raise NotFoundException(f"Customer with ID {application_in.customer_id} not found.")

    loan_product = get_loan_product(db, application_in.loan_product_id)
    if not loan_product or not loan_product.is_active:
        raise NotFoundException(f"Active loan product with ID {application_in.loan_product_id} not found.")

    # Validate requested amount and tenor against product limits
    if not (loan_product.min_amount <= application_in.requested_amount <= loan_product.max_amount):
        raise InvalidOperationException(f"Requested amount {application_in.requested_amount} is outside product limits ({loan_product.min_amount}-{loan_product.max_amount}).")
    if not (loan_product.min_tenor_months <= application_in.requested_tenor_months <= loan_product.max_tenor_months):
        raise InvalidOperationException(f"Requested tenor {application_in.requested_tenor_months} months is outside product limits ({loan_product.min_tenor_months}-{loan_product.max_tenor_months} months).")

    app_ref = generate_reference("LOANAPP")
    db_application = models.LoanApplication(
        **application_in.dict(),
        application_reference=app_ref,
        status=LoanApplicationStatusEnum.SUBMITTED # Initial status
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application

def get_loan_application(db: Session, application_id: int) -> Optional[models.LoanApplication]:
    return db.query(models.LoanApplication).filter(models.LoanApplication.id == application_id).first()

def get_loan_application_by_reference(db: Session, reference: str) -> Optional[models.LoanApplication]:
    return db.query(models.LoanApplication).filter(models.LoanApplication.application_reference == reference).first()

def get_loan_applications_by_customer(db: Session, customer_id: int, skip: int = 0, limit: int = 100) -> List[models.LoanApplication]:
    return db.query(models.LoanApplication).filter(models.LoanApplication.customer_id == customer_id).order_by(models.LoanApplication.submitted_at.desc()).offset(skip).limit(limit).all()

def update_loan_application_status(db: Session, application_id: int, new_status: LoanApplicationStatusEnum, reason: Optional[str] = None) -> models.LoanApplication:
    application = get_loan_application(db, application_id)
    if not application:
        raise NotFoundException(f"Loan application with ID {application_id} not found.")

    # TODO: Add state transition validation (e.g., cannot go from REJECTED to APPROVED directly)
    application.status = new_status
    application.decision_reason = reason or application.decision_reason # Keep old reason if new one not provided

    if new_status == LoanApplicationStatusEnum.APPROVED:
        application.approved_at = datetime.utcnow()
    elif new_status == LoanApplicationStatusEnum.REJECTED:
        application.rejected_at = datetime.utcnow()
    elif new_status == LoanApplicationStatusEnum.DISBURSED: # Should be set by disbursement function
        application.disbursed_at = datetime.utcnow()

    db.commit()
    db.refresh(application)
    return application

def perform_credit_assessment(db: Session, application_id: int) -> schemas.CreditRiskAssessmentResponse:
    """
    Performs credit risk assessment. Integrates with credit bureaus and internal scoring models.
    This is a placeholder for a more complex process.
    """
    application = get_loan_application(db, application_id)
    if not application:
        raise NotFoundException(f"Loan application {application_id} not found.")

    if application.status != LoanApplicationStatusEnum.SUBMITTED and application.status != LoanApplicationStatusEnum.UNDER_REVIEW:
        raise InvalidOperationException(f"Application status {application.status} not valid for credit assessment.")

    application.status = LoanApplicationStatusEnum.UNDER_REVIEW
    db.commit()
    db.refresh(application)

    # Mocked credit bureau check & internal scoring
    # bureau_report = credit_bureau.get_report(bvn=application.customer.bvn) # Assuming customer relationship loaded
    # credit_score = bureau_report.score if bureau_report else 600 # Default score
    # internal_score = _calculate_internal_score(application_data)
    # final_score = (credit_score * 0.6) + (internal_score * 0.4) # Weighted average

    # For mock:
    mock_credit_score = random.randint(300, 850)
    risk_rating = "HIGH"
    if mock_credit_score > 700: risk_rating = "LOW"
    elif mock_credit_score > 550: risk_rating = "MEDIUM"

    application.credit_score = mock_credit_score
    application.risk_rating = risk_rating
    # Based on score, decide if auto-approve, auto-reject, or needs manual review
    if mock_credit_score < 450:
        update_loan_application_status(db, application_id, LoanApplicationStatusEnum.REJECTED, "Credit score too low.")
        raise CreditRiskException("Loan rejected due to low credit score.")
    elif mock_credit_score > 720 and application.requested_amount < decimal.Decimal("500000"): # Example auto-approval criteria
        update_loan_application_status(db, application_id, LoanApplicationStatusEnum.APPROVED, "Auto-approved based on credit score and amount.")
    else:
        application.status = LoanApplicationStatusEnum.PENDING_DOCUMENTATION # Or PENDING_APPROVAL for manual review
        application.decision_reason = "Further review or documentation required."

    db.commit()
    db.refresh(application)

    return schemas.CreditRiskAssessmentResponse(
        application_id=application_id,
        credit_score=mock_credit_score,
        risk_rating=risk_rating,
        assessment_details={"message": application.decision_reason}
    )

# --- Loan Disbursement & Account Creation ---
def disburse_loan(db: Session, disbursement_request: schemas.LoanDisbursementRequest) -> models.LoanAccount:
    application = get_loan_application(db, disbursement_request.application_id)
    if not application:
        raise NotFoundException(f"Loan application {disbursement_request.application_id} not found.")
    if application.status != LoanApplicationStatusEnum.APPROVED and application.status != LoanApplicationStatusEnum.PENDING_DISBURSEMENT:
        raise InvalidOperationException(f"Loan application status ({application.status}) is not valid for disbursement.")

    loan_product = get_loan_product(db, application.loan_product_id) # Should exist if application was made
    if not loan_product:
        raise NotFoundException("Associated loan product not found, data integrity issue.")

    # Check if disbursement account exists and is active (using accounts_ledger_management service)
    # disbursement_deposit_account = get_deposit_account(db, disbursement_request.disbursement_account_number)
    # if not disbursement_deposit_account or disbursement_deposit_account.status != 'ACTIVE': # Assuming status is string
    #     raise InvalidOperationException(f"Disbursement account {disbursement_request.disbursement_account_number} is not valid or active.")

    # Create Loan Account
    loan_acc_number = generate_loan_account_number_placeholder() # Use actual NUBAN-like generator
    disbursement_date = datetime.utcnow()
    maturity_date_calc = disbursement_date + relativedelta(months=application.requested_tenor_months)
    first_repayment_date_calc = disbursement_date + relativedelta(months=1) # Simplified: first payment one month from disbursement

    db_loan_account = models.LoanAccount(
        loan_account_number=loan_acc_number,
        application_id=application.id,
        customer_id=application.customer_id,
        # disbursement_account_id=disbursement_deposit_account.id,
        principal_disbursed=application.requested_amount, # Assuming full amount approved
        interest_rate_pa=loan_product.interest_rate_pa, # Or from application if adjusted
        tenor_months=application.requested_tenor_months,
        principal_outstanding=application.requested_amount, # Initially full principal is outstanding
        status=LoanAccountStatusEnum.ACTIVE,
        disbursement_date=disbursement_date,
        first_repayment_date=first_repayment_date_calc,
        next_repayment_date=first_repayment_date_calc,
        maturity_date=maturity_date_calc
    )
    db.add(db_loan_account)

    # Actual fund transfer (posting to ledger)
    # This needs integration with accounts_ledger_management
    # Example: Debit Bank's Loan GL, Credit Customer's Deposit Account
    # transaction_ref = generate_reference("LNDSB")
    # post_double_entry_transaction(
    #     db,
    #     schemas.PostTransactionRequest(
    #         from_gl_code="BANK_LOAN_ASSET_GL", # Bank's asset GL for loans
    #         to_account_number=disbursement_request.disbursement_account_number,
    #         amount=db_loan_account.principal_disbursed,
    #         currency=CurrencyEnum.NGN, # Assuming NGN for now
    #         narration=f"Loan disbursement for {loan_acc_number}",
    #         transaction_reference=transaction_ref
    #     )
    # )

    # Update application status
    application.status = LoanApplicationStatusEnum.DISBURSED
    application.disbursed_at = disbursement_date

    db.commit()
    db.refresh(db_loan_account)
    db.refresh(application)

    # Generate Repayment Schedule
    generate_repayment_schedule(db, db_loan_account.id)

    return db_loan_account

def get_loan_account(db: Session, loan_account_id: int) -> Optional[models.LoanAccount]:
    return db.query(models.LoanAccount).filter(models.LoanAccount.id == loan_account_id).first()

def get_loan_account_by_number(db: Session, loan_account_number: str) -> Optional[models.LoanAccount]:
    return db.query(models.LoanAccount).filter(models.LoanAccount.loan_account_number == loan_account_number).first()


# --- Repayment Schedule Generation ---
def generate_repayment_schedule(db: Session, loan_account_id: int):
    """
    Generates a repayment schedule (e.g., Equal Monthly Installments - EMI).
    This is a simplified version. Real EMI calculation can be complex.
    """
    loan_account = get_loan_account(db, loan_account_id)
    if not loan_account:
        raise NotFoundException(f"Loan account {loan_account_id} not found for schedule generation.")

    # Simplified EMI calculation (Reducing Balance) - this is illustrative, not financially precise for all scenarios
    P = loan_account.principal_disbursed
    r_pa = loan_account.interest_rate_pa / decimal.Decimal('100') # annual rate as decimal
    r_monthly = r_pa / decimal.Decimal('12') # monthly rate
    n = loan_account.tenor_months # number of installments

    if r_monthly == 0: # Interest-free loan
        emi = P / decimal.Decimal(n)
    else:
        # EMI = P * r * (1+r)^n / ((1+r)^n - 1)
        try:
            emi_numerator = P * r_monthly * ((decimal.Decimal('1') + r_monthly) ** n)
            emi_denominator = ((decimal.Decimal('1') + r_monthly) ** n) - decimal.Decimal('1')
            if emi_denominator == 0: # Avoid division by zero, can happen if r_monthly is tiny and n is small
                 raise InvalidOperationException("Cannot calculate EMI due to denominator being zero. Check rate and tenor.")
            emi = emi_numerator / emi_denominator
            emi = emi.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP) # Round to 2 decimal places
        except (OverflowError, decimal.InvalidOperation) as e:
            raise InvalidOperationException(f"Error calculating EMI: {str(e)}. Check loan parameters (high amount/tenor with high rate).")


    current_balance = P
    for i in range(1, n + 1):
        interest_for_month = (current_balance * r_monthly).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
        principal_for_month = emi - interest_for_month

        # Adjust last installment for any rounding differences
        if i == n:
            principal_for_month = current_balance # Ensure last principal payment clears the balance
            emi = principal_for_month + interest_for_month # Recalculate EMI for last payment

        if principal_for_month < 0: # Should not happen if EMI is calculated correctly
            principal_for_month = decimal.Decimal('0.00') # Or handle error
            # This might mean the EMI is too low to cover interest, which is an issue

        schedule_entry = models.LoanRepaymentSchedule(
            loan_account_id=loan_account.id,
            due_date=loan_account.first_repayment_date + relativedelta(months=i-1),
            installment_number=i,
            principal_due=principal_for_month,
            interest_due=interest_for_month,
            total_due=emi, # Or principal_for_month + interest_for_month
        )
        db.add(schedule_entry)
        current_balance -= principal_for_month

    db.commit()

def get_repayment_schedule(db: Session, loan_account_id: int) -> List[models.LoanRepaymentSchedule]:
    return db.query(models.LoanRepaymentSchedule).filter(models.LoanRepaymentSchedule.loan_account_id == loan_account_id).order_by(models.LoanRepaymentSchedule.installment_number).all()

# --- Loan Repayment Processing ---
def process_loan_repayment(db: Session, repayment_in: schemas.LoanRepaymentCreate) -> models.LoanRepayment:
    loan_account = get_loan_account_by_number(db, repayment_in.loan_account_number)
    if not loan_account:
        raise NotFoundException(f"Loan account {repayment_in.loan_account_number} not found.")
    if loan_account.status == LoanAccountStatusEnum.PAID_OFF or loan_account.status == LoanAccountStatusEnum.WRITTEN_OFF:
        raise InvalidOperationException(f"Loan account is already {loan_account.status.value}.")

    # Allocation logic (simplified: Penalties -> Fees -> Interest -> Principal)
    # This is a critical part and often complex based on bank policy
    amount_to_allocate = repayment_in.amount_paid
    alloc_penalties = min(amount_to_allocate, loan_account.penalties_outstanding)
    amount_to_allocate -= alloc_penalties

    alloc_fees = min(amount_to_allocate, loan_account.fees_outstanding)
    amount_to_allocate -= alloc_fees

    alloc_interest = min(amount_to_allocate, loan_account.interest_outstanding)
    amount_to_allocate -= alloc_interest

    alloc_principal = min(amount_to_allocate, loan_account.principal_outstanding)
    # Any remaining amount could be overpayment, handle as per policy (e.g., refund, hold, apply to future)

    # Create Repayment Record
    db_repayment = models.LoanRepayment(
        loan_account_id=loan_account.id,
        # transaction_id=repayment_in.transaction_id, # If payment comes via master transaction
        payment_date=repayment_in.payment_date,
        amount_paid=repayment_in.amount_paid,
        currency=repayment_in.currency,
        allocated_to_penalties=alloc_penalties,
        allocated_to_fees=alloc_fees,
        allocated_to_interest=alloc_interest,
        allocated_to_principal=alloc_principal,
        payment_method=repayment_in.payment_method,
        reference=repayment_in.reference
    )
    db.add(db_repayment)

    # Update Loan Account Balances
    loan_account.penalties_outstanding -= alloc_penalties
    loan_account.fees_outstanding -= alloc_fees
    loan_account.interest_outstanding -= alloc_interest
    loan_account.principal_outstanding -= alloc_principal

    loan_account.total_repaid_principal += alloc_principal
    loan_account.total_repaid_interest += alloc_interest

    loan_account.last_repayment_date = repayment_in.payment_date
    loan_account.last_repayment_amount = repayment_in.amount_paid

    # Update schedule entries (find relevant due schedule items and mark as paid/partially paid)
    # This is complex: payment might cover multiple installments or partial.
    # For simplicity, not fully implemented here.

    # Check if loan is fully paid off
    if loan_account.principal_outstanding <= decimal.Decimal('0.0') and \
       loan_account.interest_outstanding <= decimal.Decimal('0.0') and \
       loan_account.fees_outstanding <= decimal.Decimal('0.0') and \
       loan_account.penalties_outstanding <= decimal.Decimal('0.0'):
        loan_account.status = LoanAccountStatusEnum.PAID_OFF
        loan_account.next_repayment_date = None # No more repayments
    else:
        # Update DPD, next repayment date, etc. (batch job might handle this)
        pass

    db.commit()
    db.refresh(db_repayment)
    db.refresh(loan_account)
    return db_repayment

# --- Guarantors and Collaterals ---
def add_guarantor(db: Session, guarantor_in: schemas.GuarantorCreate) -> models.Guarantor:
    # Check if application exists
    app = get_loan_application(db, guarantor_in.loan_application_id)
    if not app:
        raise NotFoundException(f"Loan application {guarantor_in.loan_application_id} not found.")

    db_guarantor = models.Guarantor(**guarantor_in.dict())
    db.add(db_guarantor)
    db.commit()
    db.refresh(db_guarantor)
    return db_guarantor

def add_collateral(db: Session, collateral_in: schemas.CollateralCreate) -> models.Collateral:
    app = get_loan_application(db, collateral_in.loan_application_id)
    if not app:
        raise NotFoundException(f"Loan application {collateral_in.loan_application_id} not found.")

    db_collateral = models.Collateral(**collateral_in.dict())
    db.add(db_collateral)
    db.commit()
    db.refresh(db_collateral)
    return db_collateral

# TODO: Services for Loan Restructuring, Top-up, Write-off, CBN CRMS Reporting data extraction.
# TODO: Batch jobs for updating DPD, interest accrual on loans, penalty calculation.
