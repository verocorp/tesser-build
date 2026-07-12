"""Composes the application service behind the public `Client`.

`ExpenseReportService` already has exactly `Client`'s methods, taking and
returning `expensewell.client`'s DTO types — so it *is* a Client structurally.
The `-> Client` return annotation is the compile-time (mypy) proof.
"""

from expensewell.client import Client
from expensewellapp.service import ExpenseReportService


def new_client(svc: ExpenseReportService) -> Client:
    return svc  # the service satisfies the Protocol structurally
