import pytest

from expenses.expense import ExpenseSpec
from expenses.identifiers import ReportID
from expenses.money import MoneySpec
from expenses.report import (
    InvalidTransition,
    ExpenseReport,
    ReportSpec,
    ReportStatus,
)


def _expense(amount: str = "10.00", currency: str = "USD",
             category: str = "travel", receipt_number: str = "R-1") -> ExpenseSpec:
    return ExpenseSpec(
        amount=MoneySpec(amount, currency),
        category=category,
        receipt_number=receipt_number,
    )


def _spec(expenses: tuple[ExpenseSpec, ...] = (),
          status: str = ReportStatus.DRAFT.value) -> ReportSpec:
    return ReportSpec(
        id=ReportID.generate().value,
        title="Trip to NYC",
        labels={"project": "apollo"},
        expenses=expenses,
        status=status,
    )


def test_report_constructs_with_valid_expenses() -> None:
    report = ExpenseReport.from_spec(
        _spec(expenses=(_expense(receipt_number="R-1"), _expense(receipt_number="R-2")))
    )
    total = report.total()
    assert total is not None
    assert str(total.amount) == "20.00"
    assert report.status is ReportStatus.DRAFT


def test_report_constructs_empty_with_no_total() -> None:
    report = ExpenseReport.from_spec(_spec())
    assert report.total() is None
    assert report.expenses == ()


def test_report_rejects_more_than_twenty_expenses() -> None:
    expenses = tuple(
        _expense(amount="1.00", receipt_number=f"R-{i}") for i in range(21)
    )
    with pytest.raises(ValueError, match="at most 20 expenses"):
        ExpenseReport.from_spec(_spec(expenses=expenses))


def test_report_accepts_exactly_twenty_expenses() -> None:
    expenses = tuple(
        _expense(amount="1.00", receipt_number=f"R-{i}") for i in range(20)
    )
    report = ExpenseReport.from_spec(_spec(expenses=expenses))
    assert len(report.expenses) == 20


def test_report_rejects_duplicate_receipt_numbers() -> None:
    expenses = (_expense(receipt_number="R-1"), _expense(receipt_number="R-1"))
    with pytest.raises(ValueError, match="share a receipt number"):
        ExpenseReport.from_spec(_spec(expenses=expenses))


def test_report_rejects_mixed_currencies() -> None:
    expenses = (
        _expense(currency="USD", receipt_number="R-1"),
        _expense(currency="EUR", receipt_number="R-2"),
    )
    with pytest.raises(ValueError, match="must share one currency"):
        ExpenseReport.from_spec(_spec(expenses=expenses))


def test_report_rejects_total_over_the_cap() -> None:
    expenses = (
        _expense(amount="999.00", receipt_number="R-1"),
        _expense(amount="1.01", receipt_number="R-2"),
    )
    with pytest.raises(ValueError, match="exceeds the"):
        ExpenseReport.from_spec(_spec(expenses=expenses))


def test_report_accepts_total_exactly_at_the_cap() -> None:
    expenses = (
        _expense(amount="999.00", receipt_number="R-1"),
        _expense(amount="1.00", receipt_number="R-2"),
    )
    report = ExpenseReport.from_spec(_spec(expenses=expenses))
    total = report.total()
    assert total is not None
    assert str(total.amount) == "1000.00"


def test_report_expenses_accessor_is_defensive() -> None:
    report = ExpenseReport.from_spec(_spec(expenses=(_expense(receipt_number="R-1"),)))
    snapshot = report.expenses
    assert isinstance(snapshot, tuple)
    report.add_expense(_expense(receipt_number="R-2"))
    assert len(snapshot) == 1  # the earlier accessor result is unaffected
    assert len(report.expenses) == 2


def test_add_expense_to_draft_report_succeeds() -> None:
    report = ExpenseReport.from_spec(_spec())
    report.add_expense(_expense(receipt_number="R-1"))
    assert len(report.expenses) == 1
    total = report.total()
    assert total is not None
    assert str(total.amount) == "10.00"


def test_add_expense_rejects_duplicate_receipt_against_existing() -> None:
    report = ExpenseReport.from_spec(_spec(expenses=(_expense(receipt_number="R-1"),)))
    with pytest.raises(ValueError, match="share a receipt number"):
        report.add_expense(_expense(receipt_number="R-1"))
    assert len(report.expenses) == 1  # no partial mutation


def test_add_expense_rejects_over_the_cap() -> None:
    report = ExpenseReport.from_spec(
        _spec(expenses=(_expense(amount="999.00", receipt_number="R-1"),))
    )
    with pytest.raises(ValueError, match="exceeds the"):
        report.add_expense(_expense(amount="1.01", receipt_number="R-2"))
    assert len(report.expenses) == 1  # no partial mutation


def test_add_expense_rejects_currency_mismatch_against_existing() -> None:
    report = ExpenseReport.from_spec(
        _spec(expenses=(_expense(currency="USD", receipt_number="R-1"),))
    )
    with pytest.raises(ValueError, match="must share one currency"):
        report.add_expense(_expense(currency="EUR", receipt_number="R-2"))


def test_add_expense_rejects_when_report_at_twenty() -> None:
    expenses = tuple(
        _expense(amount="1.00", receipt_number=f"R-{i}") for i in range(20)
    )
    report = ExpenseReport.from_spec(_spec(expenses=expenses))
    with pytest.raises(ValueError, match="at most 20 expenses"):
        report.add_expense(_expense(amount="1.00", receipt_number="R-20"))


def test_add_expense_rejects_once_submitted() -> None:
    report = ExpenseReport.from_spec(_spec())
    report.submit()
    with pytest.raises(InvalidTransition, match="not a draft"):
        report.add_expense(_expense(receipt_number="R-1"))


def test_submit_transitions_draft_to_submitted() -> None:
    report = ExpenseReport.from_spec(_spec())
    report.submit()
    assert report.status is ReportStatus.SUBMITTED


def test_submit_rejects_a_second_submission() -> None:
    report = ExpenseReport.from_spec(_spec())
    report.submit()
    with pytest.raises(InvalidTransition, match="only a draft report"):
        report.submit()


def test_report_equality_is_by_identity() -> None:
    id_str = ReportID.generate().value
    a = ExpenseReport.from_spec(ReportSpec(id=id_str, title="Trip A", expenses=()))
    b = ExpenseReport.from_spec(ReportSpec(id=id_str, title="Trip B", expenses=()))
    assert a == b  # same id, different title -> still the same report

    c = ExpenseReport.from_spec(_spec())
    assert a != c  # different id -> different report, even with similar shape
