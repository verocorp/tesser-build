"""Findings and the check registry.

``CHECKS`` is the single registry of every check the analyzer runs — the Python
analog of ``internal/analyzers.All``. The meta-test iterates it to guarantee no
check ships without a good/bad testdata pair, so this tuple is the one place a
check is enrolled.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """One conformance violation at one source location."""

    path: str
    line: int
    col: int
    code: str
    message: str

    def render(self) -> str:
        """flake8-style ``path:line:col: CODE message`` — editor and CI friendly."""
        return f"{self.path}:{self.line}:{self.col}: {self.code} {self.message}"


@dataclass(frozen=True)
class CheckMeta:
    """Static description of a check, for the registry and the meta-test."""

    code: str
    name: str
    summary: str


# The registry. One entry per check; the meta-test fails if a code appears in
# the checker but not here, or a registered code has no good/bad fixture.
CHECKS: tuple[CheckMeta, ...] = (
    CheckMeta(
        "DDD001",
        "frozen-dataclass",
        "a domain dataclass must be frozen=True (immutability + value equality)",
    ),
    CheckMeta(
        "DDD002",
        "hashable-fields",
        "a frozen dataclass field must not be a mutable collection "
        "(list/dict/set) — its __hash__ raises; use tuple/frozenset",
    ),
    CheckMeta(
        "DDD003",
        "no-setattr-bypass",
        "object.__setattr__/__delattr__ must not bypass immutability outside "
        "__post_init__",
    ),
    CheckMeta(
        "DDD004",
        "no-string-equality",
        "compare value objects by value, not by str() representation",
    ),
    CheckMeta(
        "DDD010",
        "no-primitive-exposure",
        "a value object must not expose a public primitive field — hide the "
        "representation (the spec/VO discriminator; specs expose, VOs don't)",
    ),
    CheckMeta(
        "DDD011",
        "no-collection-leak",
        "an aggregate/entity accessor must not return its backing mutable "
        "collection directly — return a defensive copy",
    ),
    CheckMeta(
        "DDD012",
        "reference-roots-by-id",
        "an aggregate/entity must reference another aggregate root by its ID "
        "value object, not hold the root object across the boundary",
    ),
)


def codes() -> frozenset[str]:
    """Every registered check code."""
    return frozenset(c.code for c in CHECKS)
