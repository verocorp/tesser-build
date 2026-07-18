"""The public contract for the reports context — the entire surface callers
depend on. ``Client`` Protocol + primitive-leaved DTOs only; no domain type
crosses this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LinkVerdictView:
    """One report row, primitive-leaved — never a domain object."""

    slug: str
    target_url: str
    allowed: bool
    reason: str


class Client(Protocol):
    """The entire public surface of the reports context."""

    def links_by_verdict(self) -> tuple[LinkVerdictView, ...]: ...
