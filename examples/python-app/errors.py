from __future__ import annotations

import enum
from typing import assert_never


class Kind(enum.Enum):

    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"


class DomainError(Exception):

    def __init__(self, kind: Kind, code: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class InfraError(Exception):
    pass


def invalid(code: str, message: str) -> DomainError:
    return DomainError(Kind.VALIDATION, code, message)


def not_found(code: str, message: str) -> DomainError:
    return DomainError(Kind.NOT_FOUND, code, message)


def conflict(code: str, message: str) -> DomainError:
    return DomainError(Kind.CONFLICT, code, message)


def status_for(kind: Kind) -> int:
    match kind:
        case Kind.VALIDATION:
            return 422
        case Kind.NOT_FOUND:
            return 404
        case Kind.CONFLICT:
            return 409
    assert_never(kind)
