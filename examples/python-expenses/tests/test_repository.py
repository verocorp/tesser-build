import pytest

from expenses.expense import ExpenseSpec
from expenses.identifiers import ReportID
from expenses.money import MoneySpec
from expenses.report import ExpenseReport, ReportSpec, ReportStatus
from expensewellimpl.repository import InMemoryExpenseReportRepository


def test_round_trip_preserves_the_report() -> None:
    repo = InMemoryExpenseReportRepository()
    spec = ReportSpec(
        id=ReportID.generate().value,
        title="Trip to NYC",
        labels={"project": "apollo"},
        expenses=(
            ExpenseSpec(MoneySpec("42.50", "USD"), "travel", "R-1"),
        ),
    )
    report = ExpenseReport.from_spec(spec)

    repo.save(report)
    loaded = repo.load(report.id)

    assert loaded == report  # same identity
    assert str(loaded.title) == "Trip to NYC"
    assert loaded.labels.as_dict() == {"project": "apollo"}
    assert loaded.status is ReportStatus.DRAFT
    assert len(loaded.expenses) == 1
    assert str(loaded.expenses[0].amount.amount) == "42.50"


def test_round_trip_preserves_submitted_status() -> None:
    repo = InMemoryExpenseReportRepository()
    report = ExpenseReport.from_spec(
        ReportSpec(id=ReportID.generate().value, title="Trip", expenses=())
    )
    report.submit()
    repo.save(report)

    loaded = repo.load(report.id)
    assert loaded.status is ReportStatus.SUBMITTED


def test_load_missing_report_raises_lookup_error() -> None:
    repo = InMemoryExpenseReportRepository()
    with pytest.raises(LookupError):
        repo.load(ReportID.generate())
