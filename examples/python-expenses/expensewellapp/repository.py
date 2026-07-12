"""The repository interface — defined with its caller, the application service.

Exactly two jobs: save an aggregate (decompose it into rows) and retrieve one
(reconstruct it through its constructor). No business logic.
"""

from typing import Protocol

from expenses.identifiers import ReportID
from expenses.report import ExpenseReport


class ExpenseReportRepository(Protocol):
    def save(self, report: ExpenseReport) -> None: ...

    def load(self, report_id: ReportID) -> ExpenseReport:
        """Raise LookupError if no report with this id exists."""
        ...
