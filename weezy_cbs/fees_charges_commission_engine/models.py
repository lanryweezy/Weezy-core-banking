# Database models for Fees, Charges & Commission Engine
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from weezy_cbs.database import Base # Use the shared Base

import enum

# Assuming CurrencyEnum will be shared
class CurrencyEnum(enum.Enum):
    NGN = "NGN"; USD = "USD" # Add others as needed

class FeeTypeEnum(enum.Enum):
    TRANSACTION_FEE = "TRANSACTION_FEE"
    SERVICE_CHARGE = "SERVICE_CHARGE"
    COMMISSION = "COMMISSION"
    PENALTY = "PENALTY"
    TAX = "TAX" # e.g., VAT, Stamp Duty
    GOVERNMENT_LEVY = "GOVERNMENT_LEVY" # Other specific levies

class FeeCalculationMethodEnum(enum.Enum):
    FLAT = "FLAT"
    PERCENTAGE = "PERCENTAGE"
    TIERED_FLAT = "TIERED_FLAT"
    TIERED_PERCENTAGE = "TIERED_PERCENTAGE"

class FeeConfig(Base):
    __tablename__ = "fee_configs"
    id = Column(Integer, primary_key=True, index=True)
    fee_code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=False) # Changed from Text for brevity
    fee_type = Column(SQLAlchemyEnum(FeeTypeEnum), nullable=False)
    applicable_context_json = Column(Text, nullable=True) # JSON criteria
    calculation_method = Column(SQLAlchemyEnum(FeeCalculationMethodEnum), nullable=False)
    flat_amount = Column(Numeric(precision=18, scale=2), nullable=True)
    percentage_rate = Column(Numeric(precision=10, scale=6), nullable=True) # e.g., 0.005000 for 0.5%
    tiers_json = Column(Text, nullable=True) # Structured tier definitions
    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    fee_income_gl_code = Column(String(20), ForeignKey("gl_accounts.gl_code"), nullable=False)
    tax_payable_gl_code = Column(String(20), ForeignKey("gl_accounts.gl_code"), nullable=True)
    linked_tax_fee_code = Column(String(50), ForeignKey("fee_configs.fee_code"), nullable=True) # For VAT on this fee
    is_active = Column(Boolean, default=True)
    valid_from = Column(Date, default=func.current_date())
    valid_to = Column(Date, nullable=True)
    created_by_user_id = Column(String(50), nullable=True)
    updated_by_user_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    fee_income_gl = relationship("GeneralLedgerAccount", foreign_keys=[fee_income_gl_code])
    tax_payable_gl = relationship("GeneralLedgerAccount", foreign_keys=[tax_payable_gl_code])
    # linked_tax_config = relationship("FeeConfig", remote_side=[fee_code], foreign_keys=[linked_tax_fee_code]) # Check this relationship carefully

    def __repr__(self): return f"<FeeConfig(code='{self.fee_code}', type='{self.fee_type.value}')>"

class AppliedFeeLog(Base):
    __tablename__ = "applied_fee_logs"
    id = Column(Integer, primary_key=True, index=True)
    fee_config_id = Column(Integer, ForeignKey("fee_configs.id"), nullable=False, index=True)
    fee_code_applied = Column(String(50), ForeignKey("fee_configs.fee_code"), nullable=False, index=True)
    financial_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)

    source_transaction_reference = Column(String(100), nullable=True, index=True) # Kept for context
    # customer_bvn_or_id = Column(String, nullable=True, index=True) # Redundant if customer_id present
    # account_number_debited = Column(String, nullable=True, index=True) # Redundant if account_id present

    base_amount_for_calc = Column(Numeric(precision=18, scale=2), nullable=True)
    original_calculated_fee = Column(Numeric(precision=18, scale=2), nullable=False) # Before waiver
    net_fee_charged = Column(Numeric(precision=18, scale=2), nullable=False) # After waiver
    tax_amount_on_fee = Column(Numeric(precision=18, scale=2), nullable=True, default=0.00)
    total_charged_to_customer = Column(Numeric(precision=18, scale=2), nullable=False) # net_fee + tax

    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)
    status = Column(String(30), default="APPLIED_SUCCESSFULLY", index=True)
    fee_ledger_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True)
    tax_ledger_transaction_id = Column(String(40), ForeignKey("financial_transactions.id"), nullable=True)

    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    waiver_promo_id = Column(Integer, ForeignKey("fee_waiver_promos.id"), nullable=True)

    fee_config = relationship("FeeConfig", foreign_keys=[fee_config_id]) # Specify foreign_keys if ambiguous
    # Relationships to FT for fee/tax postings might need distinct names if both point to FinancialTransaction
    fee_posting_transaction = relationship("FinancialTransaction", foreign_keys=[fee_ledger_transaction_id])
    tax_posting_transaction = relationship("FinancialTransaction", foreign_keys=[tax_ledger_transaction_id])
    original_financial_transaction = relationship("FinancialTransaction", foreign_keys=[financial_transaction_id])

    customer = relationship("Customer")
    account = relationship("Account")
    waiver_promo = relationship("FeeWaiverPromo") # Add back_populates in FeeWaiverPromo

    def __repr__(self): return f"<AppliedFeeLog(id={self.id}, fee_code='{self.fee_code_applied}', net_charged='{self.net_fee_charged}')>"

class FeeWaiverPromo(Base):
    __tablename__ = "fee_waiver_promos"
    id = Column(Integer, primary_key=True, index=True)
    promo_code = Column(String(30), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    fee_config_id = Column(Integer, ForeignKey("fee_configs.id"), nullable=True) # Specific fee this promo applies to
    # applicable_criteria_json = Column(Text) # Broader criteria

    waiver_type = Column(String(30), default="FULL_WAIVER")
    discount_percentage = Column(Numeric(precision=5, scale=2), nullable=True)
    discount_fixed_amount = Column(Numeric(precision=18, scale=2), nullable=True)

    is_active = Column(Boolean, default=True, index=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)

    max_waivers_total_limit = Column(Integer, nullable=True)
    current_waivers_total_count = Column(Integer, default=0)
    max_waivers_per_customer_limit = Column(Integer, nullable=True)

    created_by_user_id = Column(String(50), nullable=True)
    updated_by_user_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    fee_config_waived = relationship("FeeConfig") # Relationship to the FeeConfig it waives
    applied_fees = relationship("AppliedFeeLog", back_populates="waiver_promo")
