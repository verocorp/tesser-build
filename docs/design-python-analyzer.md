# Design — the Python DDD analyzer (`ddd-vet-py`) and its sequencing (2026-07-15)

Planning record from a `/office-hours` sequencing session. Driver: a new Python
app for **pilot** is being built now (VOs, entities, aggregates, repositories,
application services, composition root), and the goal is an **automated
conformance gate that runs locally and in CI** — to replace the current
adversarial-LLM/Codex review loop for catching DDD-convention gaps.

## Findings that set the plan

1. **The Go tree is green.** `go test ./...`, `go vet`, `gofmt` all clean on
   `main`. The "VO checker/vet failures after entities+aggregates" are **not in
   the toolkit** — the last commits (`307367a`, `9fc1a52`) are "pass ddd-vet"
   fixes. Any remaining failures live in a **consumer repo** (certus / metron /
   quanta / pilot) whose code predates the entities/aggregates conventions.
   That is a consumer migration, not a go-ddd fix, and does not block pilot.

2. **Python guidance already ships; enforcement does not.** `skills/ddd/python.md`
   + `examples/python/` cover the whole stack pilot is building (VO simple/
   compound/collection, entity, aggregate fact+lifecycle, application service,
   repository, public-interface client, composition root, thin handler), gated
   by mypy-strict + pytest on the examples. There is **zero machine enforcement**
   for arbitrary Python domain code — no ast/flake8/mypy analyzer. `ddd-vet` and
   `gclplugin` are `go/analysis` and cannot run on Python.

3. **"Enforced/checked" is two things.** (a) guidance available for Python — done;
   (b) automated CI enforcement — the gap, and the subject of this doc.

4. **Substrate shift vs the prior port design.** The only prior port exploration
   (session `7164f852`, 2026-07-08, no code written) designed the analyzer around
   **pydantic** (`ValueObject(BaseModel)`, `model_construct`/`model_copy` bypass
   detection) because the framing question was "python with mypy/**pydantic**."
   But the skill/examples that shipped afterward use **stdlib frozen dataclasses**
   (no pydantic anywhere; `requirements-dev.txt` = mypy + pytest only). Decision:
   the analyzer targets the **frozen-dataclass** substrate the skill teaches.
   pydantic may still appear in pilot for runtime/transport validation — that is a
   separate concern, outside the domain-object check surface.

## Why the dataclass substrate is simpler and higher-coverage than the pydantic design

The Go analyzers all sit on one heuristic (`internal/voscan`): a VO is a type
`X` with a constructor `NewX(...) (X, error)` whose suffix matches the return
type. **That has no Python analog** — but on dataclasses it is replaced by
something better and fully syntactic:

- **VO identification** = the `@dataclass(frozen=True)` decorator, visible in the
  AST. No import resolution, no marker base to invent, no `voscan`, no
  exclude-config. Entities/aggregates are `@dataclass` (non-frozen) or
  `__eq__ = None`, also AST-visible.
- **comparability's real residual** — a frozen VO with a `list`/`dict`/`set`
  field that makes `__hash__` raise when used as a set/dict key — is readable
  from the **field annotation** in the AST. No mypy needed. (This is exactly why
  `examples/python/catalog/labels.py` backs itself with a `tuple`.)

So the mypy-plugin need shrinks close to zero for v1.

## Rule-by-rule fate (7 Go analyzers → reconciled Python check-set)

| Go analyzer | Python fate on the dataclass substrate |
|---|---|
| `vofields` (#1 no exported fields) | **→ "must be frozen"**: VO decorator must carry `frozen=True`. Pure AST. |
| `voconstructor` (#2 validating ctor) | **→ "no-bypass construction"** (highest value): flag `object.__setattr__(vo, …)` in non-test code. `dataclasses.replace()` is allowed — it re-runs `__post_init__`. Pure AST. |
| `mustnew` (#4 paired MustNewX) | **Dissolves** — Python constructors raise; no error/panic two-channel. |
| `stringequality` (#6use) | **Ports verbatim** — flag `str(a) == str(b)` / `assert str(a)==str(b)` in tests where both sides are `str()`. Pure AST, easiest. |
| `stringer` (#6 String() exists) | **Weak** — VO should define `__str__`; low value, optional. |
| `primitiveaccessor` (#6a/6b no leak) | **Dropped** — dataclass fields are public by idiom; banning accessors would be theater. |
| `comparability` (#7 needs Equal) | **→ hash-hazard**: frozen VO with a `list`/`dict`/`set` field. Readable from annotation, pure AST. |

## v1 scope (the build)

Standalone stdlib-`ast` CLI, zero deps: `python -m ddd_vet <paths>`. Lives in
go-ddd, distributed to consumers like the skill (copy-in / pre-commit), consumed
by pilot.

Four checks: (1) VO must be frozen, (2) no `object.__setattr__` bypass in
non-test code, (3) no `str==str` equality in tests, (4) frozen VO with a
`list`/`dict`/`set` field.

Plus: (5) testdata good/bad fixtures per check (mirror `passes/*/testdata`);
(6) acceptance-gate on `examples/python/` — must pass clean, as `ddd-vet` gates
`examples/ddd`; (7) a `coverage.md` Python-enforcement column and a meta-test
that every check is tested (mirror `TestEveryAnalyzerIsTested`).

Effort: hours. Editor-inline (flake8 entry-point adapter) and the mypy-plugin
residuals are **out of v1**.

## Sequencing

- **P0 — `ddd-vet-py` v1, now.** The one workstream that serves pilot and is the
  stated goal. Step 1 (pin the check-set against `python.md`) absorbs most of the
  Python-side skill-reconciliation worry.
- **P1 — fast-follow, after pilot has real domain code.** Decide the two
  type-aware residuals (identity-`__eq__` field; deeper hash hazards) →
  mypy-plugin vs drop, based on whether they actually bite. Optional flake8 adapter.
- **P2 — rationale decisions 1 & 4** (app-service SRP; repo speaks domain
  objects). Not blocking pilot. Strongest as **real-code corroboration against
  pilot's own app-services/repos** (the `anchor/CORROBORATION.md` pattern), which
  is another reason it sits after pilot has that code.
- **Triage — the Go "failures."** Locate them (which consumer repo). Toolkit is
  green; this is a consumer migration, decoupled from the analyzer.

## Open question

Where were the Go checker/vet failures observed? `main` is green, so they are in
a consumer repo — which one, and is its CI currently red on `ddd-vet`?

## The assignment

Start P0 step 1: pin the four-check set against `skills/ddd/python.md` and note
any drift, before writing the tool. That is the cheapest step that de-risks the
whole build (it guarantees the analyzer enforces exactly what the skill teaches).
