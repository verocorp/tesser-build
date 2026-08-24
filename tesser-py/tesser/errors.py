import enum
import collections.abc as abc
import typing


class Kind(enum.Enum):

    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"


class NeedsDesignFieldProblem:

    code: str
    field: str | None
    message: str

    def __init__(self, code: str, field: str | None, message: str) -> None:
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "field", field)
        object.__setattr__(self, "message", message)

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash((type(self), self.code, self.field, self.message))

    def __repr__(self) -> str:
        return (
            f"NeedsDesignFieldProblem(code={self.code!r}, "
            f"field={self.field!r}, message={self.message!r})"
        )

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is frozen: cannot set {name!r}")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{type(self).__name__} is frozen: cannot delete {name!r}")


class DomainError(Exception):

    def __init__(
        self,
        kind: Kind,
        code: str,
        message: str,
        *,
        field: str | None = None,
        problems: tuple[NeedsDesignFieldProblem, ...] = (),
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
    return DomainError(Kind.VALIDATION, code, message, field=field)


def not_found(code: str, message: str) -> DomainError:
    return DomainError(Kind.NOT_FOUND, code, message)


def conflict(code: str, message: str) -> DomainError:
    return DomainError(Kind.CONFLICT, code, message)


def wrap(err: DomainError, message: str, *, field: str | None = None) -> DomainError:
    return DomainError(
        err.kind, err.code, message, field=field if field is not None else err.field
    )


def collect(**fields: abc.Callable[[], object]) -> None:
    problems: list[NeedsDesignFieldProblem] = []
    for name, thunk in fields.items():
        try:
            thunk()
        except DomainError as e:
            if e.kind is not Kind.VALIDATION:
                raise
            problems.append(NeedsDesignFieldProblem(e.code, e.field or name, e.message))
    if problems:
        raise DomainError(
            Kind.VALIDATION,
            "validation_failed",
            "one or more fields are invalid",
            problems=tuple(problems),
        )


def status_for(kind: Kind) -> int:
    match kind:
        case Kind.VALIDATION:
            return 422
        case Kind.NOT_FOUND:
            return 404
        case Kind.CONFLICT:
            return 409
    typing.assert_never(kind)


def exit_code_for(kind: Kind) -> int:
    match kind:
        case Kind.VALIDATION:
            return 2
        case Kind.NOT_FOUND:
            return 1
        case Kind.CONFLICT:
            return 1
    typing.assert_never(kind)
