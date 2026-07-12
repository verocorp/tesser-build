import pytest

from expenses.expense import Expense, ExpenseSpec
from expenses.money import MoneySpec


def _spec(amount: str = "42.50", currency: str = "USD",
          category: str = "travel", receipt_number: str = "R-1") -> ExpenseSpec:
    return ExpenseSpec(
        amount=MoneySpec(amount, currency),
        category=category,
        receipt_number=receipt_number,
    )


def test_expense_equality() -> None:
    a = Expense.from_spec(_spec())
    b = Expense.from_spec(_spec())
    assert a == b  # same attributes -> the same expense, no separate identity
    assert hash(a) == hash(b)


def test_expense_inequality_different_receipt() -> None:
    a = Expense.from_spec(_spec(receipt_number="R-1"))
    b = Expense.from_spec(_spec(receipt_number="R-2"))
    assert a != b


def test_expense_rejects_invalid_amount() -> None:
    with pytest.raises(ValueError, match="invalid expense amount"):
        Expense.from_spec(_spec(amount="not-a-number"))


def test_expense_rejects_zero_amount() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        Expense.from_spec(_spec(amount="0.00"))


def test_expense_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        Expense.from_spec(_spec(amount="-5.00"))


def test_expense_rejects_blank_category() -> None:
    with pytest.raises(ValueError, match="invalid expense category"):
        Expense.from_spec(_spec(category=""))


def test_expense_rejects_blank_receipt_number() -> None:
    with pytest.raises(ValueError, match="invalid expense receipt number"):
        Expense.from_spec(_spec(receipt_number=""))
