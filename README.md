# go-ddd

Go DDD enforcement toolkit: analyzers, workflows, and CI actions for Go repos following domain-driven design conventions.

## Why — the rationale layer

Enforcement without a demonstrated reason gets ignored. [`rationale/`](rationale/)
is the executable case: a neutral fixture (spaceflight navigation, anchored on
the Mars Climate Orbiter unit-confusion loss) whose tests **assert** the wins —
a `Feet`-where-`Meters` call that won't compile, `0°C == 273.15K` under value
equality, a sub-absolute-zero temperature rejected at construction — plus
benchmarks showing the honest cost (collection value objects pay a defensive-copy
allocation a raw map doesn't). [`rationale/coverage.md`](rationale/coverage.md)
maps each rule to its demo and its checker, with a meta-test that forbids silent
gaps. [`docs/case-study.md`](docs/case-study.md) carries the magnitude measured on
a real ~1,100-commit codebase.

The fixture runs **three contenders** over the same domain — bare primitives
([`rationale/primitive/`](rationale/primitive/)), a realistic *mixture* of
primitives and inconsistently-built value objects
([`rationale/inconsistent/`](rationale/inconsistent/)), and consistent value
objects ([`rationale/valueobject/`](rationale/valueobject/)). The arm-2 tests
prove the point that justifies the checkers: a value object adopted
*inconsistently* reopens the same silent sites a bare primitive does. The
dividend is bought by the **standard**, not by the pattern. See
[`docs/design-three-contender-changeability.md`](docs/design-three-contender-changeability.md).

## What's here

### `cmd/ddd-vet` — the DDD analyzers

`ddd-vet` is a [`go/analysis`](https://pkg.go.dev/golang.org/x/tools/go/analysis)
multichecker. Run it standalone (`ddd-vet ./...`) or as a `go vet` tool
(`go vet -vettool=$(command -v ddd-vet) ./...`), which also lights the diagnostics
up in editors through gopls. The analyzers (each independently adoptable — a menu,
not all-or-nothing):

| Analyzer | What it enforces |
|---|---|
| `mustnew` | Every value-object constructor `NewX(...) (X, error)` has a paired `MustNewX(...) X` that panics on error. |
| `vofields` | A value object has no exported fields (representation stays encapsulated). |
| `voconstructor` | A value object has a validating constructor `NewX(...) (X, error)` as the single construction path. |
| `stringequality` | `.String()` is only called inside `Test*_String` accessor tests — not as a shortcut for value comparison elsewhere. |
| `stringer` | A value object has a `String() string` display form. |
| `primitiveaccessor` | A value object exposes no primitive accessors (`ToString` / `To<builtin>`). |
| `comparability` | A value object defines `Equal` when `==` is unavailable (slice/map/func field) or unsafe (pointer/interface field). |

Configuration is a single `.go-ddd.yaml` `exclude:` list at the consumer repo
root, read by every analyzer — the aggregate/entity types that match the
value-object heuristic but aren't value objects. Generate a starter with
`ddd-vet -gen-excludes ./...`, then review and curate it. The list is per-consumer
config — every repo has its own aggregates.

### `actions/run-ddd-checks` — composite GitHub Action

Runs the `ddd-vet` analyzers against the caller's repo via `go vet`. Used from
consumer workflows:

```yaml
- uses: verocorp/go-ddd/actions/run-ddd-checks@v1
```

No inputs — configuration is file-only via a `.go-ddd.yaml` at the consumer repo
root (one shared `exclude:` list, generated with `ddd-vet -gen-excludes` then
human-curated). See [`actions/run-ddd-checks/README.md`](actions/run-ddd-checks/README.md)
for the exclude format and the two consequences (packages must compile; the check
runs with a cold cache so config edits always take effect).

## The conventions, briefly

This toolkit encodes three rules from a broader DDD approach for Go:

1. **Value objects get `MustNew*` helpers.** VOs are cheap to construct; tests should be able to write `MustNewCustomerID("cust-1")` inline without error-handling noise. Aggregates and entities are not VOs — they carry real construction risk and don't get `Must*` constructors.

2. **Every VO has explicit equality test coverage.** Equality is a load-bearing property of value objects; behavior changes (adding a field, changing comparability) should be caught by a `Test*_Equality` test that exists specifically to lock that behavior.

3. **`.String()` is for display, not for equality.** If you find yourself comparing `a.String() == b.String()`, you're doing value-object equality the wrong way. `.String()` belongs inside a `Test*_String` test that exercises stringification.

## Consumers

- [verocorp/certus](https://github.com/verocorp/certus) — reference implementation
- [verocorp/metron](https://github.com/verocorp/metron)
- [verocorp/quanta](https://github.com/verocorp/quanta)

## Status

This repo is new. The checkers were extracted from certus's `ci/` directory; porting them to the `go/analysis` framework (enabling `go vet -vettool`, `multichecker`, editor integration) is a follow-up.
