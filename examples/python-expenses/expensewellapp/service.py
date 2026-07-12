"""ExpenseReportService — the coordination layer. No business logic.

Every method is the four-step shape: convert -> delegate -> persist -> respond.
The rules (max expenses, unique receipts, one currency, the 1000.00 cap,
draft-only editing) all live on `ExpenseReport` / `Expense` / `Money`; this
service only sequences calls into them.
"""

from expensewell.client import (
    AddExpenseRequest,
    AddExpenseResponse,
    CreateReportRequest,
    CreateReportResponse,
    ExpenseInput,
    ExpenseView,
    GetReportRequest,
    GetReportResponse,
    ReportView,
    SubmitReportRequest,
    SubmitReportResponse,
)
from expenses.expense import Expense, ExpenseSpec
from expenses.identifiers import ReportID
from expenses.money import MoneySpec
from expenses.report import ExpenseReport, ReportSpec, ReportStatus
from expensewellapp.repository import ExpenseReportRepository


def _to_expense_spec(item: ExpenseInput) -> ExpenseSpec:
    return ExpenseSpec(
        amount=MoneySpec(amount=item.amount, currency=item.currency),
        category=item.category,
        receipt_number=item.receipt_number,
    )


def _to_expense_view(expense: Expense) -> ExpenseView:
    return ExpenseView(
        amount=str(expense.amount.amount),
        currency=expense.amount.currency,
        category=str(expense.category),
        receipt_number=str(expense.receipt_number),
    )


def _to_report_view(report: ExpenseReport) -> ReportView:
    total = report.total()
    total_amount = str(total.amount) if total is not None else "0.00"
    total_currency = total.currency if total is not None else ""
    return ReportView(
        report_id=str(report.id),
        title=str(report.title),
        labels=report.labels.as_dict(),
        status=report.status.value,
        expenses=tuple(_to_expense_view(e) for e in report.expenses),
        total_amount=total_amount,
        total_currency=total_currency,
    )


class ExpenseReportService:
    def __init__(self, repo: ExpenseReportRepository) -> None:  # injected, never built here
        self._repo = repo

    def create_report(self, req: CreateReportRequest) -> CreateReportResponse:
        spec = ReportSpec(  # 1. Convert
            id=ReportID.generate().value,
            title=req.title,
            labels=dict(req.labels),
            expenses=tuple(_to_expense_spec(e) for e in req.expenses),
            status=ReportStatus.DRAFT.value,
        )
        report = ExpenseReport.from_spec(spec)  # 2. Delegate (construct)
        self._repo.save(report)  # 3. Persist (whole aggregate)
        return CreateReportResponse(report=_to_report_view(report))  # 4. Respond

    def add_expense(self, req: AddExpenseRequest) -> AddExpenseResponse:
        report_id = ReportID(req.report_id)  # 1. Convert
        report = self._repo.load(report_id)  # 2a. Delegate: load
        report.add_expense(_to_expense_spec(req.expense))  # 2b. guarded transition
        self._repo.save(report)  # 3. Persist
        return AddExpenseResponse(report=_to_report_view(report))  # 4. Respond

    def submit_report(self, req: SubmitReportRequest) -> SubmitReportResponse:
        report_id = ReportID(req.report_id)  # 1. Convert
        report = self._repo.load(report_id)  # 2a. Delegate: load
        report.submit()  # 2b. guarded transition
        self._repo.save(report)  # 3. Persist
        return SubmitReportResponse(report=_to_report_view(report))  # 4. Respond

    def get_report(self, req: GetReportRequest) -> GetReportResponse:
        report_id = ReportID(req.report_id)  # 1. Convert
        report = self._repo.load(report_id)  # 2. Delegate: load
        return GetReportResponse(report=_to_report_view(report))  # 4. Respond (no persist)
