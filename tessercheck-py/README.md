# tessercheck-py

The Python analog of tesser-build's `tessercheck`: a **zero-dependency, stdlib-`ast`**
conformance analyzer for the DDD construction conventions in
[`skills/tesser-build/python.md`](../skills/tesser-build/python.md). It runs locally and in CI to
enforce conformance instead of relying on adversarial LLM/Codex review to find
gaps.

It targets the **frozen-dataclass** substrate the skill teaches (not pydantic —
pydantic may still be used for runtime/transport validation, which is off the
domain-object check surface). Checks come in three tiers: syntactic shape
checks, **classification-aware** checks keyed on the whole-tree identity-taxonomy
classifier ([`docs/design-python-domain-detection.md`](../docs/design-python-domain-detection.md)),
and whole-tree anatomy checks (context discovery). The type-aware residuals
(alias/NewType/cross-module disguises) are a deferred mypy-plugin decision —
see [`docs/design-python-analyzer.md`](../docs/design-python-analyzer.md).

## Run

```bash
python -m tessercheck path/to/domain          # exit 1 on any finding
python -m tessercheck --app-root path/to/app  # + context discovery / totality guard (exit 2 on an unclassified package)
python -m tessercheck --list-checks           # print the check registry
python -m tessercheck --version
```

Flags:

- `--select CODES` / `--ignore CODES` — comma-separated code lists; the
  ratchet mechanism is two CI jobs with different code lists (a blocking tier
  and an advisory tier), never inline suppressions.
- `--app-root DIR` — treat `DIR` as an app root: discover its bounded contexts
  by their `Client` seam and fail loudly on any root-level package that is
  neither app-level plumbing nor a Client-bearing context (the totality
  guard). With no paths given, `DIR` is also what gets checked.
- `--app-level NAMES` — extend the app-level package set (default: the
  template's `bootstrap`, `srv`, `tests`) by declaration; requires
  `--app-root`.
- `--exclude NAMES` — declare root-level packages out of the totality guard
  *and* out of the checked file set: scratch/demo packages that will never be
  contexts, or contexts not yet adopted (the incremental-adoption ratchet —
  drive the list to zero). Requires `--app-root`. Distinct from `--app-level`:
  that flag asserts a package IS the app's plumbing; an exclusion asserts only
  that you declared it out. The guard's exit-2 teeth stay total over
  everything not declared.

Output is flake8-style `path:line:col: CODE message`. Suppress a single line
with a trailing `# tessercheck:ignore`.

## Checks

Shape checks (TB001–TB004):

| Code | Rule |
|---|---|
| **TB001** | every `@dataclass` must be `frozen=True` — domain values for immutability + value equality; specs/DTOs too, because frozen costs them nothing and a non-frozen dataclass is invisible to the VO classifier (deliberately total; inline-ignore a boundary shape that must mutate) |
| **TB002** | a frozen **value object's** field must not be a mutable collection (`list`/`dict`/`set`) — its `__hash__` raises; use a `tuple`/`frozenset` (classification-aware: a spec/persistence row is exempt) |
| **TB003** | `object.__setattr__`/`__delattr__` must not bypass immutability outside the **construction sites**: `__post_init__` (canonicalization), or `__init__` of a `@dataclass(frozen=True, init=False)` assigning its declared fields (the spec-taking shape has no other way in) |
| **TB004** | compare value objects by value, not by `str()` representation (fires only when **both** sides are `str()`/`__str__()` calls) |

Identity-taxonomy checks (TB010–TB014), keyed on the classifier:

| Code | Rule |
|---|---|
| **TB010** | a value object's primitive must not escape — neither as a public primitive field nor through a passthrough accessor returning it (`@property ... return self._x`); components are exposed as value objects, `__str__` is the sole primitive exit (the spec/VO discriminator; specs expose, VOs don't) |
| **TB011** | an aggregate/entity accessor must not return its backing mutable collection — return a defensive copy |
| **TB012** | an aggregate/entity references another aggregate root by its ID value object, never by holding the root object |
| **TB013** | a structured domain object (entity/aggregate) constructs through its spec — `__init__(self, spec)`; no separate `from_spec` factory |
| **TB014** | equality matches the stereotype: a VO compares by value; an entity defines `__eq__`+`__hash__` together (by ID); an aggregate root blocks accidental equality |

Serialization-norm checks (TB015–TB018), also keyed on the classifier:

| Code | Rule |
|---|---|
| **TB015** | a domain object never serializes itself ([`skills/tesser-build/serialization.md`](../skills/tesser-build/serialization.md) rules 1/3/5): no public method returning a spec-classified type, no emit-a-sink method handing private fields to a parameter, no second or mismatched conversion dunder on a leaf, and no conversion dunder at all on a compound/entity/aggregate (collection VOs included) |
| **TB016** | what a value object may be built from (`serialization.md` rule 5's internal half): a compound (≥2 fields) holds child value objects, not bare wrappable primitives — a raw primitive strands its validation, behavior, and canonical exit at the compound; and `bool`/`complex` are not value-object material at any field count. A single wrappable-primitive field is a leaf, untouched |
| **TB017** | a value object has ONE construction door — its own `__init__`. Any classmethod/staticmethod returning its own type is a second door, name-agnostic (`from_spec`/`parse`/`new`/`require`/`of`), because two doors mean two invariant sets on one type — what the type guarantees would depend on which door the caller picked |
| **TB018** | a leaf's conversion dunder is a one-line delegation to the `canonical_*` policy helper for its backing type (`serialization.md` rule 3), so each canonical form has exactly ONE implementation site; a hand-rolled or wrong-policy exit is a second implementation. `date`/`time` leaves are out of contract until the time-type taxonomy is ruled |

Norm checks:

| Code | Rule |
|---|---|
| **TB020** | the comments norm v0 ([`skills/tesser-build/comments.md`](../skills/tesser-build/comments.md)): no code comments, docstrings, or bare string-literal statements — machine directives exempt; **no test exemption** |
| **TB030** | the fakes-only test-double norm ([`skills/tesser-build/testing.md`](../skills/tesser-build/testing.md)): a test double is a hand-written fake. **Imports** of a mocking library (`unittest.mock` and submodules in any import shape, the `mock` backport, `pytest`/`_pytest.monkeypatch` → `MonkeyPatch`) are flagged **tree-wide, no test exemption**. The `monkeypatch`/`mocker` **fixture-parameter** rule is narrower: it fires only inside a pytest-shaped function (`test_*` or a `@fixture` factory), so a production parameter that happens to share the name stays clean. A test that must patch a seam it cannot inject through carries `# tessercheck:ignore` (matched as a real comment token, over the reported statement's whole line span) |

Scope: TB001–TB003 and the classifier-keyed checks (TB010–TB018) apply to
non-test code — test files are exempt, because they legitimately construct and
exercise domain objects; TB004, TB020, and TB030 fire everywhere. A file is
"test code" when its name is a pytest module
(`test_*.py` / `*_test.py` / `conftest.py`) or any path component is
`tests`/`testdata`. The classifier runs over the **whole tree** in one pass,
so cross-file embedding (an aggregate owning an entity defined in another
module) resolves without import analysis.

## Develop

```bash
pip install -r requirements-dev.txt
mypy            # --strict, configured in pyproject.toml
pytest -q       # unit checks + the examples/python acceptance gate + self-dogfood
```

`testdata/<code>/{good,bad}.py` holds a conformant/violating fixture per
file-scoped check (`good_tree/`/`bad_tree/` directory pairs for tree-scoped
ones); the meta-test (`tests/test_meta.py`) fails if a registered check lacks
its fixtures, if an unregistered code is emitted, or if the analyzer is not
clean on `examples/python` (the canonical conformant tree) or on its own
source (TB020 excluded there by ruling: the comments norm governs
constructed-app code and the example templates, not the toolkit's internals).

One fixture pair is deliberately **unregistered**: `testdata/tb031/` ships
ahead of its checker as the executable specification for the
construction-completeness rule ([`skills/tesser-build/testing.md`](../skills/tesser-build/testing.md)
rule 2) — fixtures first, checker next.

## Distribution

Self-contained and stdlib-only, so a consuming repo vendors the
`tessercheck/` package and runs it as a pre-commit hook + CI step, or installs it
(`pip install tessercheck-py`, exposing the `tessercheck` console script).
