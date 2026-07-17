"""Domain error model for the error-norms worked example.

Two-level identity:
  - Kind: a CLOSED set (validation / not_found / conflict) that the transport
    boundary maps to an HTTP status. Exhaustiveness of that mapping is checked
    by mypy via ``assert_never`` over this enum — add a kind, forget a status,
    and the type checker fails at ``status_for``.
  - Code: an OPEN, stable, machine-readable identifier for the SPECIFIC problem
    (e.g. "duplicate_slug"). Two codes may share one kind. Becomes RFC 9457
    ``type``. Product semantics live here so callers never parse messages and
    never need to grow the closed Kind set.

Domain code raises ``DomainError`` only through the named constructors
(``invalid`` / ``not_found`` / ``conflict``) — never by passing a raw kind — so
an arbitrary kind can never enter. Infrastructure failures use ``InfraError``,
which is NOT a domain kind: the boundary maps it to 503, distinct from an
unexpected 500. The adapter raises it so nothing vendor-shaped crosses inward.
"""

from __future__ import annotations

import enum
from typing import assert_never


class DomainKind(enum.Enum):
    """The closed set of domain error kinds. Closed on purpose: the transport
    boundary's status mapping is exhaustive over exactly these members."""

    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"


class DomainError(Exception):
    """A domain error carrying an intrinsic Kind (-> status) and a stable Code
    (-> RFC 9457 ``type``). Construct via ``invalid`` / ``not_found`` /
    ``conflict``, not directly, so a raw kind can never enter."""

    def __init__(
        self,
        kind: DomainKind,
        code: str,
        message: str,
        *,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.code = code
        self.field = field

    def __str__(self) -> str:
        where = f" ({self.field})" if self.field is not None else ""
        return f"[{self.code}]{where} {super().__str__()}"


class InfraError(Exception):
    """An infrastructure failure (storage unavailable, timeout, driver error).
    NOT a domain kind — the boundary maps it to 503. The adapter raises this so
    nothing vendor-shaped crosses into the domain."""


def invalid(code: str, message: str, *, field: str | None = None) -> DomainError:
    """A validation failure: input the domain refuses. Maps to 422."""
    return DomainError(DomainKind.VALIDATION, code, message, field=field)


def not_found(code: str, message: str) -> DomainError:
    """The asked-for thing is absent. Maps to 404. Detected at the adapter but
    a domain-meaningful outcome."""
    return DomainError(DomainKind.NOT_FOUND, code, message)


def conflict(code: str, message: str) -> DomainError:
    """Valid input the current state disallows (illegal transition, duplicate,
    lost update). Maps to 409."""
    return DomainError(DomainKind.CONFLICT, code, message)


def wrap(err: DomainError, message: str, *, field: str | None = None) -> DomainError:
    """Re-raise a child domain error with added positional/path context,
    PRESERVING its kind and code — so the boundary still maps it correctly and
    the client still sees the specific problem. Use when a parent knows context
    a child cannot (e.g. which collection index failed). This is the only way to
    build a DomainError from an existing one; it never invents a new kind."""
    return DomainError(
        err.kind, err.code, message, field=field if field is not None else err.field
    )


def status_for(kind: DomainKind) -> int:
    """The pure, typed Kind -> HTTP status mapper. This is the ONE place the
    closed set is enforced: add a kind and forget a case here, and mypy fails on
    ``assert_never``. Runtime error recovery (``except`` / ``errors.As``) happens
    elsewhere; exhaustiveness fires HERE, on the typed enum, not on the recovery.
    """
    match kind:
        case DomainKind.VALIDATION:
            return 422
        case DomainKind.NOT_FOUND:
            return 404
        case DomainKind.CONFLICT:
            return 409
    assert_never(kind)
