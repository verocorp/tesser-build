"""Expense — a compound value object.

Two expenses with the same amount, category, and receipt number are the same
expense; there is no identity beyond those attributes (the receipt number is
supplied data, not a system-assigned identity). It has no lifecycle of its
own — it is created once and never edited; only the report that owns it
changes over time.
"""

from dataclasses import dataclass

from expenses.identifiers import Category, ReceiptNumber
from expenses.money import Money, MoneySpec


@dataclass(frozen=True)
class ExpenseSpec:  # spec: primitive leaves only
    amount: MoneySpec
    category: str
    receipt_number: str


@dataclass(frozen=True)
class Expense:
    amount: Money
    category: Category
    receipt_number: ReceiptNumber

    @classmethod
    def from_spec(cls, spec: ExpenseSpec) -> "Expense":
        try:
            amount = Money.from_spec(spec.amount)
        except ValueError as e:
            raise ValueError(f"invalid expense amount: {e}") from e
        try:
            category = Category(spec.category)
        except ValueError as e:
            raise ValueError(f"invalid expense category: {e}") from e
        try:
            receipt_number = ReceiptNumber(spec.receipt_number)
        except ValueError as e:
            raise ValueError(f"invalid expense receipt number: {e}") from e
        return cls(amount=amount, category=category, receipt_number=receipt_number)

    def __post_init__(self) -> None:  # the rules live here, always run
        if self.amount.amount <= 0:
            raise ValueError("expense amount must be positive")
