# Database models for Fees, Charges & Commission Engine
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLAlchemyEnum, Text, Date
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
    # Add others as needed

class FeeTypeEnum(enum.Enum):
    TRANSACTION_FEE = "TRANSACTION_FEE" # e.g., NIP transfer fee, SMS alert fee
    SERVICE_CHARGE = "SERVICE_CHARGE"   # e.g., Account maintenance, Card issuance
    COMMISSION = "COMMISSION"           # e.g., COT (Commission on Turnover - largely phased out but illustrative)
    PENALTY = "PENALTY"                 # e.g., Late loan repayment penalty
    TAX = "TAX"                         # e.g., VAT, Stamp Duty

class FeeCalculationMethodEnum(enum.Enum):
    FLAT = "FLAT"
    PERCENTAGE = "PERCENTAGE" # Percentage of transaction amount or other base amount
    TIERED_FLAT = "TIERED_FLAT" # Different flat fees based on amount tiers
    TIERED_PERCENTAGE = "TIERED_PERCENTAGE" # Different percentages based on amount tiers
    # Add more complex methods like PER_TRANCHE if needed

class FeeConfig(Base): # Defines a specific fee, charge, or commission
    __tablename__ = "fee_configs"

    id = Column(Integer, primary_key=True, index=True)
    fee_code = Column(String, unique=True, nullable=False, index=True) # e.g., "NIP_OUTWARD_BELOW_5K", "SMS_ALERT", "VAT_ON_FEES"
    description = Column(Text, nullable=False)
    fee_type = Column(SQLAlchemyEnum(FeeTypeEnum), nullable=False)

    # Applicable context (can be broad or very specific)
    # E.g., specific transaction_type, product_code, account_type, channel
    # For simplicity, these can be stored as JSON or made more granular with separate tables
    # applicable_context_json = Column(Text, nullable=True) # {"transaction_type": "NIP_TRANSFER", "channel": "MOBILE_APP"}

    calculation_method = Column(SQLAlchemyEnum(FeeCalculationMethodEnum), nullable=False)

    # Fee values (depending on calculation_method)
    flat_amount = Column(Numeric(precision=18, scale=2), nullable=True) # For FLAT method
    percentage_rate = Column(Numeric(precision=10, scale=4), nullable=True) # For PERCENTAGE method (e.g., 0.005 for 0.5%)

    # For TIERED methods, tiers_json would store the tier definitions
    # e.g., [{"min_amount": 0, "max_amount": 5000, "fee": 10.00}, {"min_amount": 5001, "max_amount": 50000, "fee": 25.00}] for TIERED_FLAT
    # or   [{"min_amount": 0, "max_amount": 100000, "rate": 0.001}, ...] for TIERED_PERCENTAGE
    tiers_json = Column(Text, nullable=True)

    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False) # Currency of the fee itself

    # GL accounts for posting this fee
    # fee_income_gl_code = Column(String, ForeignKey("gl_accounts.gl_code"), nullable=False) # Where the bank books fee income
    # tax_payable_gl_code = Column(String, ForeignKey("gl_accounts.gl_code"), nullable=True) # If this fee includes a tax component to be remitted

    is_active = Column(Boolean, default=True)
    valid_from = Column(Date, default=func.current_date())
    valid_to = Column(Date, nullable=True) # For fees that expire

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<FeeConfig(code='{self.fee_code}', type='{self.fee_type.value}')>"

class AppliedFeeLog(Base): # Record of each time a fee is calculated and applied
    __tablename__ = "applied_fee_logs"

    id = Column(Integer, primary_key=True, index=True)
    # fee_config_id = Column(Integer, ForeignKey("fee_configs.id"), nullable=False, index=True)
    fee_code_applied = Column(String, nullable=False, index=True) # Denormalized for easier query

    # financial_transaction_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True, index=True) # Original transaction that incurred the fee
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    # account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True) # Account from which fee was debited

    # Denormalized references
    source_transaction_reference = Column(String, nullable=True, index=True)
    customer_bvn_or_id = Column(String, nullable=True, index=True)
    account_number_debited = Column(String, nullable=True, index=True)

    base_amount_for_calc = Column(Numeric(precision=18, scale=2), nullable=True) # e.g., transaction amount for percentage fees
    calculated_fee_amount = Column(Numeric(precision=18, scale=2), nullable=False)
    # If fee includes tax (e.g. VAT on fee), this is the main fee part
    # calculated_tax_amount = Column(Numeric(precision=18, scale=2), nullable=True) # e.g. VAT amount
    # total_charged_amount = Column(Numeric(precision=18, scale=2), nullable=False) # fee + tax

    currency = Column(SQLAlchemyEnum(CurrencyEnum), nullable=False)

    status = Column(String, default="APPLIED_SUCCESSFULLY") # APPLIED_SUCCESSFULLY, FAILED_INSUFFICIENT_FUNDS, WAIVED, REVERSED
    # fee_ledger_tx_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True) # FT ID for the fee debit itself
    # tax_ledger_tx_id = Column(String, ForeignKey("financial_transactions.id"), nullable=True) # FT ID for the tax debit/posting

    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    # waiver_id = Column(Integer, ForeignKey("fee_waivers.id"), nullable=True) # If this fee was waived

    # fee_config = relationship("FeeConfig")
    # waiver = relationship("FeeWaiver")

    def __repr__(self):
        return f"<AppliedFeeLog(id={self.id}, fee_code='{self.fee_code_applied}', amount='{self.calculated_fee_amount}')>"

class FeeWaiverPromo(Base): # Configuration for promotional waivers or product discounts
    __tablename__ = "fee_waiver_promos"
    id = Column(Integer, primary_key=True, index=True)
    promo_code = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)

    # fee_config_id_to_waive = Column(Integer, ForeignKey("fee_configs.id"), nullable=True) # If waiving a specific fee
    # fee_code_to_waive = Column(String, nullable=True, index=True) # Or by fee code
    # Can be broader: waive ALL fees of a certain type for certain customers/products
    # applicable_criteria_json = Column(Text) # {"customer_segment": "STUDENT", "product_code": "SAVINGS_LITE"}

    waiver_type = Column(String, default="FULL_WAIVER") # FULL_WAIVER, PERCENTAGE_DISCOUNT, FIXED_AMOUNT_DISCOUNT
    discount_percentage = Column(Numeric(precision=5, scale=2), nullable=True) # e.g. 50.00 for 50% discount
    discount_fixed_amount = Column(Numeric(precision=18, scale=2), nullable=True)

    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)

    # max_waivers_total = Column(Integer, nullable=True) # Max times this promo can be used overall
    # current_waivers_total_count = Column(Integer, default=0)
    # max_waivers_per_customer = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # applied_fees = relationship("AppliedFeeLog", back_populates="waiver") # Link back to applied fees that used this waiver

# Special Nigerian taxes/duties that are rule-based:
# - VAT (currently 7.5%) on certain bank charges. This can be a FeeConfig of type TAX, linked to other fees.
# - Stamp Duty (e.g., NGN 50 on deposits/transfers > NGN 10,000). This is also a FeeConfig.
#   The `applicable_context_json` and `tiers_json` in FeeConfig can handle this.
#   Example Stamp Duty FeeConfig:
#   - fee_code: "STAMP_DUTY_TRANSFER_DEPOSIT"
#   - fee_type: TAX
#   - calculation_method: TIERED_FLAT
#   - tiers_json: [{"min_amount": 0, "max_amount": 9999.99, "fee": 0.00}, {"min_amount": 10000, "max_amount": null, "fee": 50.00}]
#   - currency: NGN
#   - applicable_context_json: {"transaction_types": ["NIP_TRANSFER", "CASH_DEPOSIT", "INTRA_BANK_TRANSFER"], "direction": "CREDIT_TO_CUSTOMER_ACCOUNT_OVER_THRESHOLD"}
#     (The context needs to be interpreted by the fee engine service).

# Commission on Turnover (COT) - largely phased out for current accounts but kept for historical context or specific product types.
# This would be a FeeConfig with PERCENTAGE calculation, applied on total debit turnover on an account over a period.
# The fee engine service would need to query account turnover to calculate this.

# The core of this module is the `FeeConfig` table and the service logic to:
# 1. Identify applicable fees for a given transaction/event context.
# 2. Calculate the fee amount(s) based on config and context.
# 3. Check for waivers/promos.
# 4. Trigger ledger posting for the fee (debit customer, credit fee income GL, credit tax payable GL).
# 5. Log the applied fee.
