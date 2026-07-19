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

Output is flake8-style `path:line:col: CODE message`. Suppress a single line
with a trailing `# tessercheck:ignore`.

## Checks

Shape checks (TB001–TB004):

| Code | Rule |
|---|---|
| **TB001** | a domain `@dataclass` must be `frozen=True` (immutability + value equality) |
| **TB002** | a frozen **value object's** field must not be a mutable collection (`list`/`dict`/`set`) — its `__hash__` raises; use a `tuple`/`frozenset` (classification-aware: a spec/persistence row is exempt) |
| **TB003** | `object.__setattr__`/`__delattr__` must not bypass immutability **outside `__post_init__`** (canonicalization on the construction path is allowed) |
| **TB004** | compare value objects by value, not by `str()` representation (fires only when **both** sides are `str()`/`__str__()` calls) |

Identity-taxonomy checks (TB010–TB014), keyed on the classifier:

| Code | Rule |
|---|---|
| **TB010** | a value object must not expose a public primitive field — hide the representation (the spec/VO discriminator; specs expose, VOs don't) |
| **TB011** | an aggregate/entity accessor must not return its backing mutable collection — return a defensive copy |
| **TB012** | an aggregate/entity references another aggregate root by its ID value object, never by holding the root object |
| **TB013** | a structured domain object (entity/aggregate) constructs through its spec — `__init__(self, spec)`; no separate `from_spec` factory |
| **TB014** | equality matches the stereotype: a VO compares by value; an entity defines `__eq__`+`__hash__` together (by ID); an aggregate root blocks accidental equality |

Norm checks:

| Code | Rule |
|---|---|
| **TB020** | the comments norm v0 ([`skills/tesser-build/comments.md`](../skills/tesser-build/comments.md)): no code comments, docstrings, or bare string-literal statements — machine directives exempt; **no test exemption** |

Scope: TB001–003 apply to non-test code (test files are exempt); TB004 and
TB020 fire everywhere. A file is "test code" when its name is a pytest module
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

## Distribution

Self-contained and stdlib-only, so a consuming repo vendors the
`tessercheck/` package and runs it as a pre-commit hook + CI step, or installs it
(`pip install tessercheck-py`, exposing the `tessercheck` console script).
