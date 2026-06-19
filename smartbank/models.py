"""
SmartBank – Domain Models (OOP)
Demonstrates: Encapsulation · Inheritance · Polymorphism
"""

from datetime import datetime
from decimal import Decimal


# ══════════════════════════════════════════════════════════════════════════════
# Base Account
# ══════════════════════════════════════════════════════════════════════════════

class Account:
    """
    Abstract base class for all SmartBank account types.

    Encapsulation  → balance is private (_balance); accessed through get_balance()
    Polymorphism   → subclasses override withdraw() to apply their own rules
    """

    def __init__(self, account_number: str, account_holder: str, initial_balance: float = 0.0):
        self.account_number   = account_number
        self.account_holder   = account_holder
        self._balance         = Decimal(str(initial_balance))   # private
        self._transaction_history: list[dict] = []

    # ── Public interface ───────────────────────────────────────────────────────

    def get_balance(self) -> Decimal:
        """Return the current balance (read-only access to private _balance)."""
        return self._balance

    def deposit(self, amount: float, description: str = "Deposit") -> dict:
        """
        Add funds to the account.
        Raises ValueError for non-positive amounts.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")

        self._balance += amount
        record = self._record_transaction("deposit", amount, description)
        return record

    def withdraw(self, amount: float, description: str = "Withdrawal") -> dict:
        """
        Remove funds from the account.
        Base rule: cannot exceed current balance.
        Overridden by CurrentAccount to allow overdraft.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if amount > self._balance:
            raise ValueError("Insufficient funds.")

        self._balance -= amount
        record = self._record_transaction("withdrawal", amount, description)
        return record

    def transfer(self, amount: float, receiver_account_number: str) -> dict:
        """Debit this account for a transfer."""
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Transfer amount must be positive.")
        if amount > self._balance:
            raise ValueError("Insufficient funds for transfer.")

        self._balance -= amount
        record = self._record_transaction(
            "transfer_out", amount,
            f"Transfer to {receiver_account_number}"
        )
        record["receiver_account"] = receiver_account_number
        return record

    def display_details(self) -> dict:
        """Return a dict of account summary info."""
        return {
            "account_number": self.account_number,
            "account_holder": self.account_holder,
            "balance":        float(self._balance),
            "account_type":   self.__class__.__name__,
        }

    def show_transactions(self) -> list[dict]:
        """Return a copy of the in-memory transaction history."""
        return list(self._transaction_history)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _record_transaction(self, tx_type: str, amount: Decimal, description: str) -> dict:
        record = {
            "type":          tx_type,
            "amount":        float(amount),
            "balance_after": float(self._balance),
            "description":   description,
            "timestamp":     datetime.now().isoformat(),
        }
        self._transaction_history.append(record)
        return record

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} #{self.account_number} balance={self._balance}>"


# ══════════════════════════════════════════════════════════════════════════════
# SavingsAccount  (Inheritance)
# ══════════════════════════════════════════════════════════════════════════════

class SavingsAccount(Account):
    """
    Savings account with an annual interest rate.
    Inherits deposit/withdraw rules from Account (no overdraft).
    Adds:  calculate_interest(), apply_interest()
    """

    DEFAULT_INTEREST_RATE = Decimal("3.50")   # 3.50 % per annum

    def __init__(self, account_number: str, account_holder: str,
                 initial_balance: float = 0.0,
                 interest_rate: float = None):
        super().__init__(account_number, account_holder, initial_balance)
        self.interest_rate = (
            Decimal(str(interest_rate))
            if interest_rate is not None
            else self.DEFAULT_INTEREST_RATE
        )

    def calculate_interest(self) -> Decimal:
        """Calculate monthly interest on current balance."""
        monthly_rate = self.interest_rate / Decimal("100") / Decimal("12")
        return (self._balance * monthly_rate).quantize(Decimal("0.01"))

    def apply_interest(self) -> dict:
        """Deposit the calculated monthly interest into the account."""
        interest = self.calculate_interest()
        return self.deposit(float(interest), description=f"Monthly interest @ {self.interest_rate}%")

    def display_details(self) -> dict:
        details = super().display_details()
        details["interest_rate"] = float(self.interest_rate)
        return details


# ══════════════════════════════════════════════════════════════════════════════
# CurrentAccount  (Inheritance + Polymorphism)
# ══════════════════════════════════════════════════════════════════════════════

class CurrentAccount(Account):
    """
    Current (checking) account with an overdraft facility.
    Polymorphism → overrides withdraw() to allow balance to go negative
    up to the overdraft limit.
    """

    DEFAULT_OVERDRAFT = Decimal("10000.00")

    def __init__(self, account_number: str, account_holder: str,
                 initial_balance: float = 0.0,
                 overdraft_limit: float = None):
        super().__init__(account_number, account_holder, initial_balance)
        self.overdraft_limit = (
            Decimal(str(overdraft_limit))
            if overdraft_limit is not None
            else self.DEFAULT_OVERDRAFT
        )

    # Polymorphic override ─────────────────────────────────────────────────────
    def withdraw(self, amount: float, description: str = "Withdrawal") -> dict:
        """
        Allow withdrawal up to balance + overdraft_limit.
        Raises ValueError if the combined limit is exceeded.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if amount > (self._balance + self.overdraft_limit):
            raise ValueError(
                f"Exceeds overdraft limit (available: ₹{self._balance + self.overdraft_limit:.2f})."
            )

        self._balance -= amount
        record = self._record_transaction("withdrawal", amount, description)
        return record

    def display_details(self) -> dict:
        details = super().display_details()
        details["overdraft_limit"] = float(self.overdraft_limit)
        return details


# ══════════════════════════════════════════════════════════════════════════════
# Factory helper
# ══════════════════════════════════════════════════════════════════════════════

def account_factory(account_type: str, account_number: str, account_holder: str,
                    balance: float = 0.0, **kwargs) -> Account:
    """Return the appropriate Account subclass instance."""
    if account_type == "savings":
        return SavingsAccount(account_number, account_holder, balance,
                              interest_rate=kwargs.get("interest_rate"))
    elif account_type == "current":
        return CurrentAccount(account_number, account_holder, balance,
                              overdraft_limit=kwargs.get("overdraft_limit"))
    else:
        raise ValueError(f"Unknown account type: {account_type}")
