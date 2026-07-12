"""The public interface of the expensewell component.

A `Client` Protocol plus its DTOs — the deliberately-exposed contract of the
component, published here and nowhere else. No implementation lives in this
package; the application service satisfies `Client` structurally
(`expensewellimpl/client.py`).
"""

from dataclasses import dataclass, field
from typing import Mapping, Protocol


@dataclass(frozen=True)
class ExpenseInput:  # DTO: primitive-leaved
    amount: str
    currency: str
    category: str
    receipt_number: str


@dataclass(frozen=True)
class ExpenseView:  # DTO: primitive-leaved, never a domain object
    amount: str
    currency: str
    category: str
    receipt_number: str


@dataclass(frozen=True)
class ReportView:
    report_id: str
    title: str
    labels: Mapping[str, str]
    status: str
    expenses: tuple[ExpenseView, ...]
    total_amount: str
    total_currency: str


@dataclass(frozen=True)
class CreateReportRequest:
    title: str
    labels: Mapping[str, str] = field(default_factory=dict)
    expenses: tuple[ExpenseInput, ...] = ()


@dataclass(frozen=True)
class CreateReportResponse:
    report: ReportView


@dataclass(frozen=True)
class AddExpenseRequest:
    report_id: str
    expense: ExpenseInput


@dataclass(frozen=True)
class AddExpenseResponse:
    report: ReportView


@dataclass(frozen=True)
class SubmitReportRequest:
    report_id: str


@dataclass(frozen=True)
class SubmitReportResponse:
    report: ReportView


@dataclass(frozen=True)
class GetReportRequest:
    report_id: str


@dataclass(frozen=True)
class GetReportResponse:
    report: ReportView


class Client(Protocol):
    def create_report(self, req: CreateReportRequest) -> CreateReportResponse: ...

    def add_expense(self, req: AddExpenseRequest) -> AddExpenseResponse: ...

    def submit_report(self, req: SubmitReportRequest) -> SubmitReportResponse: ...

    def get_report(self, req: GetReportRequest) -> GetReportResponse: ...
