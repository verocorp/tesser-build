"""The transport layer — a stdlib http.server JSON handler.

The one handler rule: parse/authenticate the request, then call the
application through the injected public `Client` — no domain math, no
repository access here.
"""

import json
import re
from http.server import BaseHTTPRequestHandler
from typing import Any

from expensewell.client import (
    AddExpenseRequest,
    Client,
    CreateReportRequest,
    ExpenseInput,
    GetReportRequest,
    ReportView,
    SubmitReportRequest,
)

_REPORT_ID_RE = re.compile(r"^/reports/([^/]+)$")
_EXPENSES_RE = re.compile(r"^/reports/([^/]+)/expenses$")
_SUBMIT_RE = re.compile(r"^/reports/([^/]+)/submit$")


def _report_view_json(view: ReportView) -> dict[str, Any]:
    return {
        "report_id": view.report_id,
        "title": view.title,
        "labels": dict(view.labels),
        "status": view.status,
        "expenses": [
            {
                "amount": e.amount,
                "currency": e.currency,
                "category": e.category,
                "receipt_number": e.receipt_number,
            }
            for e in view.expenses
        ],
        "total_amount": view.total_amount,
        "total_currency": view.total_currency,
    }


def make_handler(client: Client) -> type[BaseHTTPRequestHandler]:
    """Build a handler class bound to `client` via closure — a stdlib
    BaseHTTPRequestHandler is instantiated by the server, not by us, so the
    Client is injected by capturing it here rather than through __init__."""

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            raw = self.rfile.read(length)
            result: dict[str, Any] = json.loads(raw)
            return result

        def _error(self, status: int, message: str) -> None:
            self._send_json(status, {"error": message})

        def do_GET(self) -> None:  # noqa: N802 (stdlib-mandated name)
            match = _REPORT_ID_RE.match(self.path)
            if match is None:
                self._error(404, "not found")
                return
            try:
                resp = client.get_report(GetReportRequest(report_id=match.group(1)))
            except LookupError as e:
                self._error(404, str(e))
                return
            self._send_json(200, _report_view_json(resp.report))

        def do_POST(self) -> None:  # noqa: N802 (stdlib-mandated name)
            if self.path == "/reports":
                self._handle_create_report()
                return
            match = _EXPENSES_RE.match(self.path)
            if match is not None:
                self._handle_add_expense(match.group(1))
                return
            match = _SUBMIT_RE.match(self.path)
            if match is not None:
                self._handle_submit_report(match.group(1))
                return
            self._error(404, "not found")

        def _handle_create_report(self) -> None:
            try:
                body = self._read_json()
                expenses = tuple(
                    ExpenseInput(
                        amount=item["amount"],
                        currency=item["currency"],
                        category=item["category"],
                        receipt_number=item["receipt_number"],
                    )
                    for item in body.get("expenses", [])
                )
                req = CreateReportRequest(
                    title=body["title"],
                    labels=body.get("labels", {}),
                    expenses=expenses,
                )
                resp = client.create_report(req)
            except (KeyError, ValueError) as e:
                self._error(400, str(e))
                return
            self._send_json(201, _report_view_json(resp.report))

        def _handle_add_expense(self, report_id: str) -> None:
            try:
                body = self._read_json()
                expense = ExpenseInput(
                    amount=body["amount"],
                    currency=body["currency"],
                    category=body["category"],
                    receipt_number=body["receipt_number"],
                )
                resp = client.add_expense(
                    AddExpenseRequest(report_id=report_id, expense=expense)
                )
            except LookupError as e:
                self._error(404, str(e))
                return
            except (KeyError, ValueError) as e:
                self._error(400, str(e))
                return
            self._send_json(200, _report_view_json(resp.report))

        def _handle_submit_report(self, report_id: str) -> None:
            try:
                resp = client.submit_report(SubmitReportRequest(report_id=report_id))
            except LookupError as e:
                self._error(404, str(e))
                return
            except ValueError as e:
                self._error(400, str(e))
                return
            self._send_json(200, _report_view_json(resp.report))

        def log_message(self, format: str, *args: Any) -> None:  # quiet during tests
            pass

    return Handler
