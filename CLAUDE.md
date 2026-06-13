# go-ddd — agent guide

This repo is a **DDD enforcement toolkit for Go**: AST checkers (`cmd/`), a
composite GitHub Action (`actions/`), and an executable rationale layer
(`rationale/`). If you are writing or changing domain objects here — or in a
consumer repo (certus, metron, quanta) — follow the conventions below, because
this repo is what enforces them in CI.

## The conventions (what the checkers enforce)

1. **Value objects get `MustNew*` helpers.** Every `NewX(...) (X, error)` VO
   constructor has a paired `MustNewX(...) X` that panics on error; tests use
   `MustNewX` for inline construction. (`cmd/checkmustnew`.) Aggregates and
   entities are *not* VOs — they carry real construction risk and get no `Must*`.
2. **Every VO has explicit equality test coverage** — a `Test*_Equality` that
   locks equality semantics, so a later field/comparability change is caught.
   (`cmd/checkequality`.)
3. **`.String()` is for display, not equality.** Never compare `a.String() ==
   b.String()`. `.String()` belongs inside a `Test*_String` test.
   (`cmd/checkstring`.)

Build a VO the canonical way: private fields, a single validating constructor as
the only construction path, value equality (not representation equality), and no
representation leak. **Consistency is the point** — a value object built a
different way each time buys nothing on the change-speed axis (see below).

## Where the "why" lives — read before changing the checkers or conventions

- [`rationale/`](rationale/) — the executable case. Three contenders over one
  neutral domain (Mars Climate Orbiter navigation): `primitive/` (arm 1),
  `inconsistent/` (arm 2 — a mixture of primitives and non-conforming VOs), and
  `valueobject/` (arm 3). The tests **assert** the wins; don't narrate them.
- [`rationale/coverage.md`](rationale/coverage.md) — the rule ↔ demo ↔ checker
  matrix. `coverage_test.go` fails on a **silent gap** (a checker with no row, or
  a row naming a test that doesn't exist). When you add a checker or a demo,
  update this matrix in the same change.
- [`docs/design-three-contender-changeability.md`](docs/design-three-contender-changeability.md)
  — the changeability metric (silent-site count) and the docs→skills→CI adoption
  ladder.
- [`docs/case-study.md`](docs/case-study.md) — the magnitudes measured on a real
  ~1,100-commit codebase (anonymized).

Deeper rationale and provenance live in the brain at `~/workspace/brain`
(`originals/changeability-silent-site-cost.md`,
`originals/obligations-conformance-changeability.md`). Use `gbrain search` for
semantic lookups across it.

## Verify

```
go test ./...                          # checkers + the rationale wins + the meta-test
go test -bench=. -benchmem ./rationale/ # the honest cost (collection-VO copy tax)
go vet ./... && gofmt -l .             # both must be clean
```

## Git

After a set of file changes, commit before returning control. Write a
descriptive message. Don't ask permission to commit. Stage files individually —
never `git add -A`/`.`.
