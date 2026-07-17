# ddd-vet-py

The Python analog of go-ddd's `ddd-vet`: a **zero-dependency, stdlib-`ast`**
conformance analyzer for the DDD construction conventions in
[`skills/ddd/python.md`](../skills/ddd/python.md). It runs locally and in CI to
enforce conformance instead of relying on adversarial LLM/Codex review to find
gaps.

It targets the **frozen-dataclass** substrate the skill teaches (not pydantic —
pydantic may still be used for runtime/transport validation, which is off the
domain-object check surface). It enforces the *syntactically decidable* subset;
the type-aware residuals (primitive-obsession field resolution, identity-`__eq__`
fields) are a deferred decision — see
[`docs/design-python-analyzer.md`](../docs/design-python-analyzer.md).

## Run

```bash
python -m ddd_vet path/to/domain        # exit 1 on any finding
python -m ddd_vet --list-checks
```

Output is flake8-style `path:line:col: CODE message`. Suppress a single line
with a trailing `# ddd:ignore`.

## Checks (v1)

| Code | Rule | python.md |
|---|---|---|
| **DDD001** | a domain `@dataclass` must be `frozen=True` | "`frozen=True` always" |
| **DDD002** | a frozen dataclass field must not be a mutable collection (`list`/`dict`/`set`) — its `__hash__` raises; use a `tuple`/`frozenset` | the collection VO backs itself with a sorted tuple |
| **DDD003** | `object.__setattr__`/`__delattr__` must not bypass immutability **outside `__post_init__`** (canonicalization on the construction path is allowed) | "no setters, no mutation" |
| **DDD004** | compare value objects by value, not by `str()` representation (fires only when **both** sides are `str()`/`__str__()` calls) | "Never `str(a) == str(b)`" |

Scope: DDD001–003 are structural and apply to non-test code (test files are
exempt); DDD004 fires everywhere. A file is "test code" when its name is a
pytest module (`test_*.py` / `*_test.py` / `conftest.py`) or any path component
is `tests`/`testdata`.

The checks operate on dataclasses **generically** (value object / spec / DTO
alike) — the rules hold for all three, which sidesteps the one genuinely hard
call (VO vs entity vs aggregate) that v1 does not need.

## Develop

```bash
pip install -r requirements-dev.txt
mypy            # --strict, configured in pyproject.toml
pytest -q       # unit checks + the examples/python acceptance gate + self-dogfood
```

`testdata/<code>/{good,bad}.py` holds a conformant/violating fixture per check;
the meta-test (`tests/test_meta.py`) fails if a registered check lacks a fixture,
if an unregistered code is emitted, or if the analyzer is not clean on
`examples/python` (the canonical conformant tree) or on its own source.

## Distribution

Self-contained and stdlib-only, so a consuming repo (e.g. pilot) vendors the
`ddd_vet/` package and runs it as a pre-commit hook + CI step, or installs it
(`pip install ddd-vet-py`, exposing the `ddd-vet` console script).
