import pytest

from expensewell.client import (
    AddExpenseRequest,
    CreateReportRequest,
    CreateReportResponse,
    ExpenseInput,
    GetReportRequest,
    ReportView,
    SubmitReportRequest,
)
from expensewellapp.service import ExpenseReportService
from expensewellimpl.repository import InMemoryExpenseReportRepository


def _service() -> ExpenseReportService:
    return ExpenseReportService(InMemoryExpenseReportRepository())


def test_create_report_assigns_an_id_and_returns_a_dto() -> None:
    svc = _service()
    resp = svc.create_report(CreateReportRequest(title="Trip to NYC"))

    assert isinstance(resp, CreateReportResponse)
    assert isinstance(resp.report, ReportView)  # a DTO, never a domain object
    assert resp.report.report_id  # system-assigned, non-empty
    assert resp.report.title == "Trip to NYC"
    assert resp.report.status == "draft"
    assert resp.report.total_amount == "0.00"


def test_create_report_with_initial_expenses() -> None:
    svc = _service()
    resp = svc.create_report(
        CreateReportRequest(
            title="Trip to NYC",
            labels={"project": "apollo"},
            expenses=(
                ExpenseInput(amount="42.50", currency="USD",
                             category="travel", receipt_number="R-1"),
            ),
        )
    )
    assert resp.report.labels == {"project": "apollo"}
    assert len(resp.report.expenses) == 1
    assert resp.report.total_amount == "42.50"
    assert resp.report.total_currency == "USD"


def test_create_report_rejects_and_propagates_invariant_violation() -> None:
    svc = _service()
    with pytest.raises(ValueError, match="exceeds the"):
        svc.create_report(
            CreateReportRequest(
                title="Too big",
                expenses=(
                    ExpenseInput("1000.01", "USD", "travel", "R-1"),
                ),
            )
        )


def test_add_expense_loads_then_delegates_to_the_aggregate() -> None:
    svc = _service()
    created = svc.create_report(CreateReportRequest(title="Trip"))
    report_id = created.report.report_id

    resp = svc.add_expense(
        AddExpenseRequest(
            report_id=report_id,
            expense=ExpenseInput("15.00", "USD", "meals", "R-1"),
        )
    )
    assert len(resp.report.expenses) == 1
    assert resp.report.total_amount == "15.00"

    fetched = svc.get_report(GetReportRequest(report_id=report_id))
    assert len(fetched.report.expenses) == 1  # the add was persisted


def test_add_expense_propagates_duplicate_receipt_rejection() -> None:
    svc = _service()
    created = svc.create_report(
        CreateReportRequest(
            title="Trip",
            expenses=(ExpenseInput("15.00", "USD", "meals", "R-1"),),
        )
    )
    with pytest.raises(ValueError, match="share a receipt number"):
        svc.add_expense(
            AddExpenseRequest(
                report_id=created.report.report_id,
                expense=ExpenseInput("5.00", "USD", "meals", "R-1"),
            )
        )


def test_submit_then_reject_further_edits() -> None:
    svc = _service()
    created = svc.create_report(CreateReportRequest(title="Trip"))
    report_id = created.report.report_id

    resp = svc.submit_report(SubmitReportRequest(report_id=report_id))
    assert resp.report.status == "submitted"

    with pytest.raises(ValueError):
        svc.add_expense(
            AddExpenseRequest(
                report_id=report_id,
                expense=ExpenseInput("5.00", "USD", "meals", "R-1"),
            )
        )


def test_get_report_unknown_id_raises_lookup_error() -> None:
    svc = _service()
    with pytest.raises(LookupError):
        svc.get_report(GetReportRequest(report_id="does-not-exist"))
