# Database models for Treasury & Liquidity Management Module
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# from weezy_cbs.database import Base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base() # Local Base for now

import enum

# Re-use from accounts_ledger_management if possible
class CurrencyEnum(enum.Enum):
    NGN = "NGN"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    # Add other relevant currencies for treasury operations

class BankCashPosition(Base): # Overall cash position of the bank
    __tablename__ = "bank_cash_positions"

    id = Column(Integer, primary_key=True, index=True)
    position_date = Column(Date, nullable=False, unique=True, index=True) # End-of-day position

    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    total_cash_at_vault = Column(Numeric(precision=20, scale=4), nullable=False) # Physical cash in bank's vaults
    total_cash_at_cbn = Column(Numeric(precision=20, scale=4), nullable=False) # Balance with Central Bank
    total_cash_at_correspondent_banks = Column(Numeric(precision=20, scale=4), nullable=False) # Nostro balances

    # Other components like cash in transit, ATM cash etc. can be added
    # total_customer_deposits = Column(Numeric(precision=20, scale=4)) # For liquidity ratio calculations
    # total_loans_outstanding = Column(Numeric(precision=20, scale=4)) # For context

    # Liquidity Ratios (calculated, can be stored or computed on demand)
    # liquidity_ratio = Column(Numeric(precision=10, scale=4), nullable=True) # e.g. (Liquid Assets / Total Deposits) * 100

    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(['currency'], ['common.currencies.code'], name='fk_cash_pos_currency'), # Assuming a common currency table
    ) # Example, if currency enum is not used directly but FK to a table

    def __repr__(self):
        return f"<BankCashPosition(date='{self.position_date}', currency='{self.currency.value}')>"

class FXTransactionTypeEnum(enum.Enum):
    SPOT = "SPOT"
    FORWARD = "FORWARD"
    SWAP = "SWAP"
    # Add others like FX Options if applicable

class FXTransaction(Base): # Foreign Exchange deals
    __tablename__ = "fx_transactions"
    id = Column(Integer, primary_key=True, index=True)
    deal_reference = Column(String, unique=True, nullable=False, index=True)
    transaction_type = Column(SQLAlchemyEnum(FXTransactionTypeEnum), nullable=False)

    trade_date = Column(Date, nullable=False)
    value_date = Column(Date, nullable=False) # Settlement date

    currency_pair = Column(String(7), nullable=False) # e.g., "USD/NGN", "EUR/USD"
    rate = Column(Numeric(precision=18, scale=8), nullable=False) # Exchange rate

    buy_currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    buy_amount = Column(Numeric(precision=20, scale=4), nullable=False)

    sell_currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    sell_amount = Column(Numeric(precision=20, scale=4), nullable=False) # Should be buy_amount * rate (or inverse)

    counterparty_name = Column(String, nullable=False) # Could be another bank, corporate client, or CBN
    # counterparty_type = Column(String) # e.g., "BANK", "CORPORATE", "CBN"

    status = Column(String, default="PENDING_SETTLEMENT") # PENDING_SETTLEMENT, SETTLED, CANCELLED
    settled_at = Column(DateTime(timezone=True), nullable=True)

    # For Forwards/Swaps
    # forward_points = Column(Numeric(precision=10, scale_4), nullable=True)
    # maturity_date = Column(Date, nullable=True) # For forward leg

    # Link to ledger entries for settlement
    # buy_leg_ledger_tx_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True)
    # sell_leg_ledger_tx_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True)

    created_by_user_id = Column(String, nullable=True) # Trader ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<FXTransaction(ref='{self.deal_reference}', pair='{self.currency_pair}', rate='{self.rate}')>"


class TreasuryBillInvestment(Base): # Investments in T-Bills
    __tablename__ = "treasury_bill_investments"
    id = Column(Integer, primary_key=True, index=True)
    investment_reference = Column(String, unique=True, nullable=False, index=True)

    # From primary market auction or secondary market purchase
    # source = Column(String) # e.g. "CBN_AUCTION", "SECONDARY_MARKET_PURCHASE"

    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    tenor_days = Column(Integer, nullable=False) # 91, 182, 364 typically

    face_value = Column(Numeric(precision=20, scale=2), nullable=False)
    discount_rate_pa = Column(Numeric(precision=10, scale=4), nullable=False) # Annualized discount rate
    purchase_price = Column(Numeric(precision=20, scale=2), nullable=False) # Calculated: FaceValue / (1 + (DiscountRate * Tenor / 365))
    # Or, if bought at yield:
    # yield_rate_pa = Column(Numeric(precision=10, scale=4), nullable=True)

    currency = Column(SQLAlchemyEnum(CurrencyEnum), default=CurrencyEnum.NGN, nullable=False)

    status = Column(String, default="ACTIVE") # ACTIVE, MATURED, SOLD_BEFORE_MATURITY
    matured_at = Column(DateTime(timezone=True), nullable=True)
    # sold_at = Column(DateTime(timezone=True), nullable=True)
    # sale_price = Column(Numeric(precision=20, scale=2), nullable=True)

    # Link to ledger entries for purchase and maturity/sale
    # purchase_ledger_tx_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True)
    # maturity_ledger_tx_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TreasuryBillInvestment(ref='{self.investment_reference}', face_value='{self.face_value}', maturity='{self.maturity_date}')>"


class InterbankPlacement(Base): # Lending to or Borrowing from other banks
    __tablename__ = "interbank_placements"
    id = Column(Integer, primary_key=True, index=True)
    deal_reference = Column(String, unique=True, nullable=False, index=True)

    placement_type = Column(String, nullable=False) # LENDING (asset) or BORROWING (liability)
    counterparty_bank_code = Column(String, nullable=False) # CBN code of the other bank
    counterparty_bank_name = Column(String, nullable=False)

    principal_amount = Column(Numeric(precision=20, scale=2), nullable=False)
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    interest_rate_pa = Column(Numeric(precision=10, scale=4), nullable=False)

    placement_date = Column(Date, nullable=False) # Start date
    maturity_date = Column(Date, nullable=False) # End date
    tenor_days = Column(Integer, nullable=False)

    # interest_amount_expected = Column(Numeric(precision=20, scale=2), nullable=False) # Calculated
    # total_repayment_expected = Column(Numeric(precision=20, scale=2), nullable=False) # Principal + Interest

    status = Column(String, default="ACTIVE") # ACTIVE, MATURED, DEFAULTED (if counterparty fails)
    matured_at = Column(DateTime(timezone=True), nullable=True)

    # Link to ledger entries for placement and maturity/repayment
    # placement_ledger_tx_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True)
    # repayment_ledger_tx_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<InterbankPlacement(ref='{self.deal_reference}', type='{self.placement_type}', amount='{self.principal_amount}')>"

class CBNRepoOperation(Base): # Repurchase agreements with CBN
    __tablename__ = "cbn_repo_operations"
    id = Column(Integer, primary_key=True, index=True)
    operation_reference = Column(String, unique=True, nullable=False, index=True)
    operation_type = Column(String, nullable=False) # REPO (CBN lends to bank) or REVERSE_REPO (bank lends to CBN)

    # collateral_security_type = Column(String) # e.g. "TREASURY_BILL", "FGN_BOND"
    # collateral_security_id = Column(String) # Reference to the specific security used as collateral
    # collateral_face_value = Column(Numeric(precision=20, scale=2))
    # haircut_percentage = Column(Numeric(precision=5, scale=2)) # e.g. 5%

    loan_amount = Column(Numeric(precision=20, scale=2), nullable=False) # Amount borrowed/lent
    currency = Column(SQLAlchemyEnum(CurrencyEnum), default=CurrencyEnum.NGN, nullable=False)
    interest_rate_pa = Column(Numeric(precision=10, scale=4), nullable=False) # Repo rate

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False) # Repurchase date
    tenor_days = Column(Integer, nullable=False)

    status = Column(String, default="ACTIVE") # ACTIVE, COMPLETED
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Reconciliation with CBN Settlement Accounts:
# This is a process. It would involve:
# 1. Fetching bank's statement from CBN (e.g., RTGS statement, CRR statement).
# 2. Comparing entries with internal ledger records for CBN GL accounts.
# 3. Identifying discrepancies.
# Models like `CBNSettlementStatementEntry` and `CBNReconciliationDiscrepancy` could be used.

# This module is highly dependent on accurate data from accounts_ledger_management for balances
# and transaction_management for flows. It also feeds into regulatory reporting for liquidity ratios etc.
