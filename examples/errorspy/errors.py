from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass
from typing import assert_never


class DomainKind(enum.Enum):

    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class FieldProblem:

    code: str
    field: str | None
    message: str


class DomainError(Exception):

    def __init__(
        self,
        kind: DomainKind,
        code: str,
        message: str,
        *,
        field: str | None = None,
        problems: tuple[FieldProblem, ...] = (),
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.code = code
        self.message = message
        self.field = field
        self.problems = problems

    def __str__(self) -> str:
        where = f" ({self.field})" if self.field is not None else ""
        return f"[{self.code}]{where} {self.message}"


class InfraError(Exception):
    pass


def invalid(code: str, message: str, *, field: str | None = None) -> DomainError:
    return DomainError(DomainKind.VALIDATION, code, message, field=field)


def not_found(code: str, message: str) -> DomainError:
    return DomainError(DomainKind.NOT_FOUND, code, message)


def conflict(code: str, message: str) -> DomainError:
    return DomainError(DomainKind.CONFLICT, code, message)


def wrap(err: DomainError, message: str, *, field: str | None = None) -> DomainError:
    return DomainError(
        err.kind, err.code, message, field=field if field is not None else err.field
    )


def collect(**fields: Callable[[], object]) -> None:
    problems: list[FieldProblem] = []
    for name, thunk in fields.items():
        try:
            thunk()
        except DomainError as e:
            if e.kind is not DomainKind.VALIDATION:
                raise
            problems.append(FieldProblem(e.code, e.field or name, e.message))
    if problems:
        raise DomainError(
            DomainKind.VALIDATION,
            "validation_failed",
            "one or more fields are invalid",
            problems=tuple(problems),
        )


def status_for(kind: DomainKind) -> int:
    match kind:
        case DomainKind.VALIDATION:
            return 422
        case DomainKind.NOT_FOUND:
            return 404
        case DomainKind.CONFLICT:
            return 409
    assert_never(kind)
