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
    """Static description of a check, for the registry and the meta-test.

    ``scope`` declares the fixture shape the meta-test enforces: ``"file"``
    checks are proven by a ``good.py``/``bad.py`` pair; ``"tree"`` checks
    (whole-tree anatomy properties: discovery, env-edge, exits) are proven by
    a ``good_tree/``/``bad_tree/`` directory pair.
    """

    code: str
    name: str
    summary: str
    scope: str = "file"


# The registry. One entry per check; the meta-test fails if a code appears in
# the checker but not here, or a registered code has no good/bad fixture.
CHECKS: tuple[CheckMeta, ...] = (
    CheckMeta(
        "TB001",
        "frozen-dataclass",
        "a domain dataclass must be frozen=True (immutability + value equality)",
    ),
    CheckMeta(
        "TB002",
        "hashable-fields",
        "a frozen dataclass field must not be a mutable collection "
        "(list/dict/set) — its __hash__ raises; use tuple/frozenset",
    ),
    CheckMeta(
        "TB003",
        "no-setattr-bypass",
        "object.__setattr__/__delattr__ must not bypass immutability outside "
        "__post_init__",
    ),
    CheckMeta(
        "TB004",
        "no-string-equality",
        "compare value objects by value, not by str() representation",
    ),
    CheckMeta(
        "TB010",
        "no-primitive-exposure",
        "a value object must not expose a public primitive field — hide the "
        "representation (the spec/VO discriminator; specs expose, VOs don't)",
    ),
    CheckMeta(
        "TB011",
        "no-collection-leak",
        "an aggregate/entity accessor must not return its backing mutable "
        "collection directly — return a defensive copy",
    ),
    CheckMeta(
        "TB012",
        "reference-roots-by-id",
        "an aggregate/entity must reference another aggregate root by its ID "
        "value object, not hold the root object across the boundary",
    ),
    CheckMeta(
        "TB013",
        "construct-through-spec",
        "a structured domain object (entity/aggregate) constructs through its "
        "spec — __init__(self, spec); no separate from_spec factory",
    ),
    CheckMeta(
        "TB014",
        "equality-by-type",
        "equality must match the stereotype: a value object compares by value; "
        "an entity defines __eq__ and __hash__ together (by ID); an aggregate "
        "root blocks accidental equality (__eq__ = None / __hash__ = None)",
    ),
    CheckMeta(
        "TB020",
        "no-comments",
        "the comments norm v0: no code comments and no docstrings — machine "
        "directives (shebang, coding, type: ignore, noqa, tessercheck:ignore, "
        "tb-* markers, pragma, formatter/linter controls) are exempt; "
        "carve-outs are added only from discovered evidence "
        "(skills/tesser-build/comments.md)",
    ),
)


def codes() -> frozenset[str]:
    """Every registered check code."""
    return frozenset(c.code for c in CHECKS)
