import enum
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from .base import Base
# Potentially link to Account model if cards are tied to specific accounts
# from .account import Account

class CardType(enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    PREPAID = "prepaid"
    VIRTUAL = "virtual"

class CardStatus(enum.Enum):
    REQUESTED = "requested"
    ACTIVE = "active"
    INACTIVE = "inactive" # e.g., not yet activated by user
    SUSPENDED = "suspended" # Temporarily blocked
    EXPIRED = "expired"
    LOST_STOLEN = "lost_stolen"
    CLOSED = "closed"

class CardNetwork(enum.Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"
    OTHER = "other"


class Card(Base):
    __tablename__ = "cards"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # A card might be linked to a specific account (e.g., a debit card to a checking account)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True) # Nullable if it's a standalone credit card not tied to a bank account directly

    card_number_hashed = Column(String(255), unique=True, index=True, nullable=False) # Store only hashed or tokenized card number
    # last_four_digits = Column(String(4), nullable=False) # Storing last 4 for display is common PCI DSS practice
    card_type = Column(Enum(CardType), nullable=False)
    card_network = Column(Enum(CardNetwork), nullable=True)
    expiry_date = Column(String(7), nullable=False) # MM/YYYY format
    cvv_hashed = Column(String(255), nullable=True) # Storing hashed CVV is generally NOT PCI compliant. Usually not stored.
                                                 # If stored, needs extreme security. For this model, it's a placeholder.
    status = Column(Enum(CardStatus), default=CardStatus.REQUESTED, nullable=False)
    issue_date = Column(DateTime, default=datetime.datetime.utcnow)
    activation_date = Column(DateTime, nullable=True)
    credit_limit = Column(Numeric(precision=15, scale=2), nullable=True) # For credit cards
    available_credit = Column(Numeric(precision=15, scale=2), nullable=True) # For credit cards
    billing_address = Column(String(255), nullable=True)
    is_physical = Column(Boolean, default=True) # vs virtual card
    contactless_enabled = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="cards")
    account = relationship("Account", backref="cards") # If linked to an account

    # Transactions made with this card
    # This would require transactions to have a card_id ForeignKey
    # transactions = relationship("Transaction", back_populates="card")


    def __repr__(self):
        # Avoid exposing sensitive info in logs
        return f"<Card(id={self.id}, user_id={self.user_id}, type='{self.card_type.value}', status='{self.status.value}')>"

    def set_card_number(self, card_number: str):
        # Placeholder for hashing. Use a strong, dedicated tokenization/hashing service for real PAN.
        # Storing last 4 digits is common and generally acceptable.
        # self.last_four_digits = card_number[-4:]
        self.card_number_hashed = f"hashed_{card_number}" # NEVER do this in production

    def check_card_number(self, card_number: str) -> bool:
        # Placeholder for checking
        return self.card_number_hashed == f"hashed_{card_number}"

    def set_cvv(self, cvv: str):
        # Placeholder. Storing CVV is highly discouraged and often non-compliant.
        # If absolutely necessary (e.g., for recurring transactions with specific merchant agreements),
        # it must be done with extreme care, strong encryption, and within PCI DSS scope.
        self.cvv_hashed = f"hashed_{cvv}" # NEVER do this in production

    @staticmethod
    def generate_card_number(network: CardNetwork = CardNetwork.VISA):
        # Placeholder for Luhn-valid card number generation
        # Real generation needs to follow network-specific BIN ranges and formats
        import random
        prefix = ""
        length = 16
        if network == CardNetwork.VISA:
            prefix = "4" + "".join(random.choices("0123456789", k=5)) # Visa starts with 4, variable BIN length
        elif network == CardNetwork.MASTERCARD:
            # Mastercard starts with 51-55 or 2221-2720
            prefix_choice = random.choice(["51", "52", "53", "54", "55"])
            prefix = prefix_choice + "".join(random.choices("0123456789", k=4))
        elif network == CardNetwork.AMEX:
            prefix = random.choice(["34", "37"]) + "".join(random.choices("0123456789", k=4)) # Amex 15 digits
            length = 15
        else:
            prefix = "".join(random.choices("0123456789", k=6))

        number = prefix + "".join(random.choices("0123456789", k=length - len(prefix) -1))

        # Calculate Luhn checksum
        digits = [int(d) for d in number]
        for i in range(len(digits) -1, -1, -2): # Iterate from right-to-left, every other digit
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9

        checksum = sum(digits) % 10
        luhn_digit = (10 - checksum) % 10 if checksum != 0 else 0
        return number + str(luhn_digit)


    @staticmethod
    def generate_expiry_date(years_valid: int = 3) -> str:
        now = datetime.datetime.utcnow()
        expiry_year = now.year + years_valid
        expiry_month = now.month
        return f"{expiry_month:02d}/{expiry_year}"

    def activate(self):
        if self.status == CardStatus.INACTIVE or self.status == CardStatus.REQUESTED:
            self.status = CardStatus.ACTIVE
            self.activation_date = datetime.datetime.utcnow()
            print(f"Card {self.id} activated.")
        else:
            print(f"Card {self.id} cannot be activated from status {self.status.value}")

    def is_expired(self) -> bool:
        if not self.expiry_date:
            return True # Or raise error
        month_str, year_str = self.expiry_date.split('/')
        exp_month, exp_year = int(month_str), int(year_str)

        now = datetime.datetime.utcnow()
        # Expires at the end of the expiry month
        if now.year > exp_year:
            return True
        if now.year == exp_year and now.month > exp_month:
            return True
        return False

    def update_status_if_expired(self):
        if self.status not in [CardStatus.EXPIRED, CardStatus.CLOSED] and self.is_expired():
            self.status = CardStatus.EXPIRED
            print(f"Card {self.id} status updated to EXPIRED.")
            return True
        return False
