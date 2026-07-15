# Design — the Python DDD analyzer (`ddd-vet-py`) and its sequencing (2026-07-15)

Planning record from a `/office-hours` sequencing session. Driver: a new Python
app for **rhema** is being built now (VOs, entities, aggregates, repositories,
application services, composition root), and the goal is an **automated
conformance gate that runs locally and in CI** — to replace the current
adversarial-LLM/Codex review loop for catching DDD-convention gaps.

## Findings that set the plan

1. **The Go tree is green.** `go test ./...`, `go vet`, `gofmt` all clean on
   `main`. The "VO checker/vet failures after entities+aggregates" were **already
   fixed in this repo** — the last commits (`307367a`, `9fc1a52`) are the "pass
   ddd-vet" fixes. Confirmed dropped; there is no toolkit or consumer item to
   chase, and nothing here blocks rhema.

2. **Python guidance already ships; enforcement does not.** `skills/ddd/python.md`
   + `examples/python/` cover the whole stack rhema is building (VO simple/
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
   pydantic may still appear in rhema for runtime/transport validation — that is a
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
by rhema.

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

- **P0 — `ddd-vet-py` v1, now.** The one workstream that serves rhema and is the
  stated goal. Step 1 (pin the check-set against `python.md`) absorbs most of the
  Python-side skill-reconciliation worry.
- **P1 — mypy-plugin, decided by a parallel spike run *during* P0.** Not gated on
  rhema having real code — Chris spikes the mypy-plugin approach in parallel with
  the P0 build so a decision is ready by the time P0 ships. What the plugin buys:
  the syntactic v1 checks approximate the primitive-obsession field rule ("VO
  fields are value objects, not raw primitives") by reading annotation *text* —
  spoofable by aliases / `NewType` / imported names. A mypy plugin resolves it
  honestly, and reaches the two comparability residuals AST can't (a field whose
  class lacks `__eq__` and compares by identity; a hash hazard from a non-literal
  unhashable field type). Cost: mypy's plugin API is unstable + thinly documented
  and pins a version range — which is exactly what the spike measures. Freebie
  (not the plugin): `NewType`/`Annotated` VOs make plain mypy catch unit-swap bugs
  for free. Optional flake8 adapter for editor-inline here too.
- **P1↔P2 order is contingent, not fixed.** Which of the mypy-plugin work and the
  decisions-1&4 checks goes first depends on what the parallel mypy spike finds.
- **P2 — decisions 1 & 4 as a second wave of checks (NOT rhema-gated).** These
  have enforceable surfaces writable now, right after the v1 ports ship:
  decision 4 (repo speaks domain objects) → flag a repository method signature
  that takes/returns primitives or DTOs instead of domain types; decision 1
  (app-service SRP) → the domain-logic-leakage check (`for`-loop over domain
  objects / arithmetic inside an app service) `application-services.md` already
  describes. Testdata fixtures like v1. This is independent of the pending
  **rationale arms** for decisions 1 & 4 (the changeability *proof*, synthetic,
  also not rhema-gated) — enforcement does not wait on the proof.

_(Dropped: Go-checker-failure triage — the toolkit tree is green and the failures
were already fixed in this repo; there was no consumer-repo item to chase.)_

## Status

**P0 v1 shipped.** `ddd-vet-py/` — a zero-dependency stdlib-`ast` analyzer with
the four checks (DDD001 frozen-dataclass, DDD002 hashable-fields, DDD003
no-setattr-bypass, DDD004 no-string-equality), good/bad testdata fixtures, a
meta-test (registry ↔ fixtures, no unregistered code, clean on `examples/python`,
self-dogfood), a `coverage.md` Python-enforcement section, and a CI job
(`ddd-vet-py`: mypy --strict + pytest + the explicit `examples/python` CLI gate).
mypy --strict and pytest are clean; the analyzer passes clean on `examples/python`
and on its own source. P1 (mypy-plugin spike) and P2 (decisions 1 & 4 as
second-wave checks) are unstarted.

## The assignment

Start P0 step 1: pin the four-check set against `skills/ddd/python.md` and note
any drift, before writing the tool. That is the cheapest step that de-risks the
whole build (it guarantees the analyzer enforces exactly what the skill teaches).
