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
| `stringequality` | A test never compares two value objects by their `.String()` form (`a.String() == b.String()`, or `assert.Equal(a.String(), b.String())`) — compare by value, not by string. |
| `stringer` | A value object has a `String() string` display form. |
| `primitiveaccessor` | A value object exposes no primitive accessors (`ToString` / `To<builtin>`). |
| `comparability` | A value object defines `Equal` when `==` is unavailable (slice/map/func field) or unsafe (pointer/interface field). |

Configuration is a single `.go-ddd.yaml` `exclude:` list at the consumer repo
root, read by every analyzer — the aggregate/entity types that match the
value-object heuristic but aren't value objects. Generate a starter with
`ddd-vet -gen-excludes ./...`, then review and curate it. The list is per-consumer
config — every repo has its own aggregates.

### Using it in CI — the `go tool` directive

go-ddd ships a tool, not a CI pipeline. You pin `ddd-vet` in your own module and
run it in your own workflow — the same way you'd consume staticcheck or NilAway.
There is no go-ddd-owned GitHub Action; CI wiring stays yours, so you keep control
of your Go version, package scoping, and caching.

**1. Pin the tool** (records a `tool` directive in your `go.mod`; Renovate/
Dependabot bump it like any dependency):

```sh
go get -tool github.com/chrisconley/go-ddd/cmd/ddd-vet@latest
```

**2. Run it** as a step in your existing workflow:

```sh
go tool ddd-vet ./...        # exits non-zero on any violation
```

In GitHub Actions that's one line in *your* `test.yml`, not an owned action:

```yaml
- run: go tool ddd-vet ./...
```

**Config:** a single `.go-ddd.yaml` `exclude:` list at your repo root (generate a
starter with `go tool ddd-vet -gen-excludes ./...`, then curate). The standalone
run reads it fresh every time, so an exclude edit always takes effect.

**Editors / large repos (secondary):** `ddd-vet` is also a `go vet` tool —
`go vet -vettool=<path-to-ddd-vet> ./...`. That path is the more scalable one on
large modules (per-package, file-based intermediates) and is what lights the
diagnostics up in editors through gopls.

**Know before you adopt:**
- **Your packages must compile.** The analyzers are type-aware; an unrelated build
  error also reds the check. (For a real module that already builds in CI, a
  non-event.)
- **Go version:** this module is `go 1.25`, and the `tool` directive itself needs
  Go ≥ 1.24. Consumers on an older toolchain can't use the directive.
- **`go.mod` footprint:** the directive pulls `golang.org/x/tools` + `gopkg.in/
  yaml.v3` (and their transitive deps) into your `go.mod`/`go.sum` via MVS.
- **A malformed `.go-ddd.yaml` fails the run loud** (a missing one is fine). It
  never silently falls back to "no excludes" — that would silently change
  enforcement.

## The conventions, briefly

This toolkit encodes three rules from a broader DDD approach for Go:

1. **Value objects get `MustNew*` helpers.** VOs are cheap to construct; tests should be able to write `MustNewCustomerID("cust-1")` inline without error-handling noise. Aggregates and entities are not VOs — they carry real construction risk and don't get `Must*` constructors.

2. **Every VO has explicit equality test coverage.** Equality is a load-bearing property of value objects; behavior changes (adding a field, changing comparability) should be caught by a `Test*_Equality` test that exists specifically to lock that behavior.

3. **`.String()` is for display, not for equality.** If you find yourself comparing `a.String() == b.String()` (or `assert.Equal(a.String(), b.String())`), you're doing value-object equality the wrong way — it silently mis-equates value objects that have more than one valid representation. The `stringequality` analyzer flags exactly that comparison; a lone `.String()` (display, a discarded call, a compare against a string literal) is left alone. Exercising stringification belongs in a `Test*_String` test.

## Consumers

- [verocorp/certus](https://github.com/verocorp/certus) — reference implementation
- [verocorp/metron](https://github.com/verocorp/metron)
- [verocorp/quanta](https://github.com/verocorp/quanta)

## Status

This repo is new. The checkers were extracted from certus's `ci/` directory; porting them to the `go/analysis` framework (enabling `go vet -vettool`, `multichecker`, editor integration) is a follow-up.
