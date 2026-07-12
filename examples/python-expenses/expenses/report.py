"""ExpenseReport — the aggregate root and consistency boundary.

Invariants enforced across the owned Expense collection, in the root's
constructor and re-established after every guarded transition:

  - at most MAX_EXPENSES expenses
  - no two expenses share a receipt number
  - every expense in a report shares one currency
  - the report's total never exceeds MAX_TOTAL (in that currency)

A report is a lifecycle aggregate (draft -> submitted): AddExpense and Submit
are root-guarded transitions, never raw field assignment from the outside.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Mapping, Sequence

from expenses.expense import Expense, ExpenseSpec
from expenses.identifiers import ReportID, ReportTitle
from expenses.labels import Labels
from expenses.money import Money

MAX_EXPENSES = 20
MAX_TOTAL = Decimal("1000.00")


class ReportStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"


class InvalidTransition(ValueError):
    """Raised when an operation is attempted against an illegal report state."""


@dataclass(frozen=True)
class ReportSpec:  # spec: primitive leaves only (nesting mirrors composition)
    id: str
    title: str
    labels: Mapping[str, str] = field(default_factory=dict)
    expenses: Sequence[ExpenseSpec] = field(default_factory=tuple)
    status: str = ReportStatus.DRAFT.value


def _validate_expenses(expenses: Sequence[Expense]) -> None:
    """The cross-object invariant — the aggregate's reason to exist."""
    if len(expenses) > MAX_EXPENSES:
        raise ValueError(f"a report may hold at most {MAX_EXPENSES} expenses")

    receipts = [e.receipt_number for e in expenses]
    if len(set(receipts)) != len(receipts):
        raise ValueError("no two expenses in a report may share a receipt number")

    if not expenses:
        return

    currency = expenses[0].amount.currency
    for e in expenses[1:]:
        if e.amount.currency != currency:
            raise ValueError(
                "all expenses in a report must share one currency "
                f"(got {e.amount.currency}, expected {currency})"
            )

    total = expenses[0].amount
    for e in expenses[1:]:
        total = total.add(e.amount)
    if total.amount > MAX_TOTAL:
        raise ValueError(
            f"report total {total.amount} {total.currency} exceeds the "
            f"{MAX_TOTAL} limit"
        )


class ExpenseReport:
    def __init__(
        self,
        id: ReportID,
        title: ReportTitle,
        labels: Labels,
        expenses: Sequence[Expense],
        status: ReportStatus = ReportStatus.DRAFT,
    ) -> None:
        _validate_expenses(expenses)
        self._id = id
        self._title = title
        self._labels = labels
        self._expenses = list(expenses)
        self._status = status

    @classmethod
    def from_spec(cls, spec: ReportSpec) -> "ExpenseReport":
        try:
            id = ReportID(spec.id)
        except ValueError as e:
            raise ValueError(f"invalid report id: {e}") from e
        try:
            title = ReportTitle(spec.title)
        except ValueError as e:
            raise ValueError(f"invalid report title: {e}") from e
        try:
            status = ReportStatus(spec.status)
        except ValueError as e:
            raise ValueError(f"invalid report status: {spec.status!r}") from e
        expenses = [Expense.from_spec(s) for s in spec.expenses]
        labels = Labels.new(spec.labels)
        return cls(id, title, labels, expenses, status)

    # -- accessors -----------------------------------------------------

    @property
    def id(self) -> ReportID:
        return self._id

    @property
    def title(self) -> ReportTitle:
        return self._title

    @property
    def labels(self) -> Labels:
        return self._labels

    @property
    def status(self) -> ReportStatus:
        return self._status

    @property
    def expenses(self) -> tuple[Expense, ...]:  # defensive copy out
        return tuple(self._expenses)

    def total(self) -> Money | None:
        """The sum of the report's expenses, or None if it holds none."""
        if not self._expenses:
            return None
        total = self._expenses[0].amount
        for e in self._expenses[1:]:
            total = total.add(e.amount)
        return total

    # -- transitions (root-guarded) -------------------------------------

    def add_expense(self, spec: ExpenseSpec) -> None:
        if self._status is not ReportStatus.DRAFT:
            raise InvalidTransition(
                "cannot add an expense to a report that is not a draft"
            )
        expense = Expense.from_spec(spec)
        candidate = self._expenses + [expense]
        _validate_expenses(candidate)  # re-establish invariants, or raise
        self._expenses = candidate

    def submit(self) -> None:
        if self._status is not ReportStatus.DRAFT:
            raise InvalidTransition("only a draft report can be submitted")
        self._status = ReportStatus.SUBMITTED

    # -- equality: identity, not attributes ------------------------------

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ExpenseReport) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)
