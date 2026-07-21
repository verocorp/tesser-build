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
        "every dataclass must be frozen=True — domain values for immutability "
        "+ value equality; specs/DTOs too, because frozen costs them nothing "
        "and a non-frozen dataclass is invisible to the VO classifier "
        "(deliberately total; inline-ignore a boundary shape that must mutate)",
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
        "the construction sites: __post_init__, or __init__ of a "
        "@dataclass(frozen=True, init=False) assigning its declared fields",
    ),
    CheckMeta(
        "TB004",
        "no-string-equality",
        "compare value objects by value, not by str() representation",
    ),
    CheckMeta(
        "TB010",
        "no-primitive-exposure",
        "a value object's primitive must not escape — neither as a public "
        "primitive field nor through a passthrough accessor returning it; "
        "components are exposed as value objects, a leaf's canonical "
        "conversion exit is the sole primitive door "
        "(the spec/VO discriminator; specs expose, VOs don't)",
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
        "TB015",
        "public-decompiler",
        "a domain object never serializes itself: no public method returning a "
        "spec, no emit-a-sink, no second or mismatched conversion dunder on a "
        "leaf, and no conversion dunder at all on a compound/entity/aggregate "
        "(skills/tesser-build/serialization.md rules 1, 3, 5)",
    ),
    CheckMeta(
        "TB016",
        "value-object-primitives",
        "what a value object is built from: a compound holds child value "
        "objects, not bare primitives (a raw primitive strands its validation, "
        "behavior and canonical exit at the compound); and bool/complex are not "
        "value-object material at all — a bool is atomic (model it raw or an "
        "enum), complex has no domain wire form",
    ),
    CheckMeta(
        "TB017",
        "single-construction-door",
        "a value object has ONE construction door — its own __init__; a "
        "classmethod or staticmethod returning its own type is a second door "
        "(from_spec/parse/new/require alike), and two doors let two callers "
        "build the same type under different invariants",
    ),
    CheckMeta(
        "TB018",
        "canonical-exit-routing",
        "a leaf value object's conversion dunder is a one-line delegation to "
        "the canonical_* policy helper matching its backing type; a "
        "hand-rolled exit is a second implementation of a canonical form "
        "(skills/tesser-build/serialization.md rule 3)",
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
    CheckMeta(
        "TB030",
        "no-mock-libraries",
        "the fakes-only test-double norm: a test double is a hand-written fake "
        "implementing the collaborator's interface — mocking libraries "
        "(unittest.mock in any import shape, the mock backport, pytest-mock's "
        "mocker) and pytest's monkeypatch/MonkeyPatch are banned tree-wide; a "
        "wiring test that must patch a process seam carries "
        "'# tessercheck:ignore' (skills/tesser-build/testing.md)",
    ),
)


def codes() -> frozenset[str]:
    """Every registered check code."""
    return frozenset(c.code for c in CHECKS)
