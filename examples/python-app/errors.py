"""Minimal shared error model for the wiring example.

It exists so the fail-closed cross-context call (campaign vetting a destination
via linkpolicy) is *honest* at the boundary — mirroring examples/errorspy's norms
in miniature:

  - ``Kind`` — a CLOSED set (validation / not_found / conflict) mapped to an HTTP
    status by the pure, exhaustive ``status_for``. Add a kind, forget a status,
    and mypy fails at ``assert_never``.
  - ``InfraError`` — an infrastructure failure (a dependency is unavailable). It
    is NOT a domain kind; the boundary maps it to 503. A ``linkpolicy`` outage
    reaches ``campaign`` as an ``InfraError`` so the redirect-creation path fails
    CLOSED (you cannot mint a link to an un-vetted destination) with a 503, never
    a silent success.

Domain code raises only through the named constructors, so a raw kind can never
enter.
"""

from __future__ import annotations

import enum
from typing import assert_never


class Kind(enum.Enum):
    """The closed set of domain error kinds; ``status_for`` is exhaustive over it."""

    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"


class DomainError(Exception):
    """A domain error carrying an intrinsic ``Kind`` (-> status) and a stable
    ``code`` (-> a machine-readable problem type). Construct via ``invalid`` /
    ``not_found`` / ``conflict``, not directly."""

    def __init__(self, kind: Kind, code: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class InfraError(Exception):
    """An infrastructure failure (dependency unavailable, timeout). NOT a domain
    kind — the boundary maps it to 503. Raised by an adapter so nothing
    vendor-shaped crosses into the domain."""


def invalid(code: str, message: str) -> DomainError:
    """Input the domain refuses. Maps to 422."""
    return DomainError(Kind.VALIDATION, code, message)


def not_found(code: str, message: str) -> DomainError:
    """The asked-for thing is absent. Maps to 404."""
    return DomainError(Kind.NOT_FOUND, code, message)


def conflict(code: str, message: str) -> DomainError:
    """Valid input the current state disallows (e.g. a blocked destination, a
    duplicate slug). Maps to 409."""
    return DomainError(Kind.CONFLICT, code, message)


def status_for(kind: Kind) -> int:
    """The pure, typed ``Kind`` -> HTTP status mapper — the ONE place the closed
    set is enforced. Add a kind and forget a case here, and mypy fails on
    ``assert_never``."""
    match kind:
        case Kind.VALIDATION:
            return 422
        case Kind.NOT_FOUND:
            return 404
        case Kind.CONFLICT:
            return 409
    assert_never(kind)
