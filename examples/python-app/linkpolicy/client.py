"""The public contract for the linkpolicy context — the entire surface callers
depend on. ``Client`` Protocol + primitive-leaved DTOs only; no domain type
crosses this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CheckRequest:
    target_url: str


@dataclass(frozen=True)
class CheckResponse:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class VerdictView:
    """A recorded verdict, primitive-leaved — never a domain object."""

    target_url: str
    allowed: bool
    reason: str


class Client(Protocol):
    """The entire public surface of the linkpolicy context."""

    def check(self, req: CheckRequest) -> CheckResponse: ...

    def list_verdicts(self) -> tuple[VerdictView, ...]: ...
