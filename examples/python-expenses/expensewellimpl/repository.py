"""An in-memory ExpenseReportRepository. Satisfies the Protocol structurally.

Genuinely decomposes the aggregate into a row shape on save and reconstructs
through `ExpenseReport.from_spec` on load — never a bare object store, and
never a field-poked rebuild.
"""

from dataclasses import dataclass, field

from expenses.expense import ExpenseSpec
from expenses.identifiers import ReportID
from expenses.money import MoneySpec
from expenses.report import ExpenseReport, ReportSpec


@dataclass(frozen=True)
class _ExpenseRow:
    amount: str
    currency: str
    category: str
    receipt_number: str


@dataclass(frozen=True)
class _ReportRow:  # persistence shape — never leaves this module
    id: str
    title: str
    labels: dict[str, str]
    status: str
    expenses: tuple[_ExpenseRow, ...] = field(default_factory=tuple)


def _decompose(report: ExpenseReport) -> _ReportRow:
    return _ReportRow(
        id=str(report.id),
        title=str(report.title),
        labels=report.labels.as_dict(),
        status=report.status.value,
        expenses=tuple(
            _ExpenseRow(
                amount=str(e.amount.amount),
                currency=e.amount.currency,
                category=str(e.category),
                receipt_number=str(e.receipt_number),
            )
            for e in report.expenses
        ),
    )


def _to_spec(row: _ReportRow) -> ReportSpec:
    return ReportSpec(
        id=row.id,
        title=row.title,
        labels=dict(row.labels),
        expenses=tuple(
            ExpenseSpec(
                amount=MoneySpec(amount=e.amount, currency=e.currency),
                category=e.category,
                receipt_number=e.receipt_number,
            )
            for e in row.expenses
        ),
        status=row.status,
    )


class InMemoryExpenseReportRepository:
    def __init__(self) -> None:
        self._rows: dict[str, _ReportRow] = {}

    def save(self, report: ExpenseReport) -> None:
        self._rows[str(report.id)] = _decompose(report)  # repo decomposes, not the caller

    def load(self, report_id: ReportID) -> ExpenseReport:
        row = self._rows.get(str(report_id))
        if row is None:
            raise LookupError(f"expense report {report_id} not found")
        return ExpenseReport.from_spec(_to_spec(row))  # reconstruct THROUGH the constructor
