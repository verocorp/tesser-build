# Coverage matrix — rule ↔ demonstrated win ↔ enforcement

This is the single source of truth linking each value-object rule to (a) the
executable demo in this `rationale/` package that shows the bug it prevents, and
(b) the `ddd-vet` analyzer that enforces it (if one exists). `coverage_test.go`
fails on a **silent gap** — a shipping analyzer (`internal/analyzers.All`) with no
row here, or a row naming a test that doesn't exist. It tolerates the honest ❌/⚠️
rows by design: the rationale makes the case for the whole discipline, and some
analyzers enforce a rubric rule that has no demo *yet* — both directions are
tracked openly, neither is allowed to be silent.

> Enforcement moved from the standalone `cmd/check*` directory-walkers to the
> `go/analysis` analyzers in `ddd-vet` (see
> [`docs/design-ddd-vet-migration.md`](../docs/design-ddd-vet-migration.md)). The
> rows below name the analyzers; the guard keys off the `analyzers.All` registry
> so it stays live after the old walkers are deleted.

| Value-object rule | Demonstrated win (test in this package) | Real-world anchor | Enforced by | Status |
|---|---|---|---|---|
| Distinct types instead of bare primitives | `TestTypeConfusion_ValueObjectRejectsWrongUnit` — `Feet` where `Meters` expected won't compile | Mars Climate Orbiter (1999, $327M) | — | ❌ no analyzer yet |
| Value equality, not representation equality | `TestEquality_ValueObjectIsRight` — `0°C` == `273.15K` | scale/representation collision | — (`equalitytest` parked; `comparability` guards the structural `==` hazard — separate row — but no analyzer locks the equality *test*) | ⚠️ enforcer dropped |
| Constructors validate invariants | `TestValidation_ValueObjectRejectsBadInput` — sub-absolute-zero rejected | physically impossible state | `voconstructor` (enforces the validating constructor *exists* as the single path; that the body validates stays the test's job) | ⚠️ structural, not semantic |
| VO constructors get `MustNew*` helpers | `TestMustReimplementation_HandRolledHelpersDiverge` (consistency demo, table below) | without it, authors reinvent divergent must-helpers | `mustnew` | ✅ consistency demo |
| `.String()` is for display, not equality | `TestEqualityByString_InconsistentIsWrong` — display-string equality mis-equates `0°C` and `273.15K` | `a.String() == b.String()` mis-equates multi-rep VOs | `stringequality` | ✅ 1:1 |

**Reading the gaps:** the ❌ row (distinct types) is a win go-ddd does not yet
enforce. The two ⚠️ rows are honest partials worth naming: **value equality** lost
its enforcer when `equalitytest` (the `Test*_Equality` existence tripwire) was
parked — `comparability` now guards the structural `==` hazard (pointer/interface
fields, see the rubric table) but nothing locks the equality *test* itself, the
parked equality-correctness gap in the design doc; **constructor validation** is
enforced only structurally (`voconstructor` checks the constructor exists as the
single path, not that its body validates). Nothing here is a *silent* gap.

## VO-construction rubric — enforced, demo pending

These analyzers ship in `ddd-vet` and enforce value-object rubric rules, but the
`rationale/` package does not yet carry an executable demo of the leak each
prevents. They are the inverse of the ❌ rows above (a demonstrated win with no
checker): here the checker leads its demo. Tracked openly so the gap is not
silent; the demos are backlog, not a blocker.

| Rubric rule | Analyzer | Demo (test in this package) | Status |
|---|---|---|---|
| #1 no exported fields (encapsulate representation) | `vofields` | — | ❌ demo pending |
| #6 a value object has a `String() string` display form | `stringer` | — | ❌ demo pending |
| #6a/6b no primitive accessors (`ToString` / `To<builtin>`) | `primitiveaccessor` | — | ❌ demo pending |
| #7 `Equal` exists when `==` is unavailable or unsafe (slice/map/func, or pointer/interface field) | `comparability` | — | ❌ demo pending |

## Consistency dimension — the case for the *standard*, not just the pattern

The matrix above is arm 1 (primitive) vs arm 3 (consistent value object). But a
value object adopted *inconsistently* buys nothing on the change-speed axis: if
every author holds a different idea of what a VO is, the result leaks
representation and construction the same way a bare primitive does. **Inconsistent
VOs ≈ no VOs.** `rationale/inconsistent/` is arm 2 — a realistic mixture of bare
primitives and non-conforming value objects — and each row below proves it
reopens a silent site the consistent VO closes. This is the rationale for the
*analyzers* (and the coming skills): they enforce the one canonical form that
actually delivers the dividend.

| Non-conformance (arm 2) | Silent site it reopens | Demo (test in this package) | Real-world anchor | Analyzer that plugs it | Status |
|---|---|---|---|---|---|
| **Partial adoption** — some concepts left primitive while others get wrapped | type confusion / wrong unit | `TestPartialAdoption_InconsistentAdmitsWrongUnit` | a slot left a bare string across 43 call sites while its VO existed | — | ❌ no analyzer yet |
| **Scattered validation** — no single constructor; the invariant copied across builders | bad value admitted at the site that forgot; rule change is an N-site edit | `TestScatteredValidation_InconsistentAdmitsBadValue`, `TestScatteredValidation_RuleLivesInManyPlaces` | pricing primitive-obsession postmortem (parent-validates-child) | `voconstructor` (forces a single constructor path; does not check the body validates) | ⚠️ structural |
| **Equality via `.String()`** — comparing the display form | scale/representation collision | `TestEqualityByString_InconsistentIsWrong` | `.String()`-as-equality residue (test-VO audit) | `stringequality` | ✅ |
| **Must-helper reimplementation** — no canonical `MustNew`, so authors hand-roll divergent ones | construction behavior diverges (panic vs admit vs clamp) on the same bad input | `TestMustReimplementation_HandRolledHelpersDiverge` | 9 ad-hoc `must*` helpers across 5 files (`e7a470c`) | `mustnew` | ✅ |
| **Naming drift** — same value category, inconsistent naming convention | a format/meaning change silently misses the drifted literal | `TestNamingDrift_InconsistentMixesConventions`, `TestNamingDrift_FormatChangeMissesTheOutlier` | `revert_earn` underscore vs hyphen siblings (realized-harm) | — | ❌ no analyzer yet |

The ❌ rows are the analyzer backlog, now each grounded in a demonstrated leak:
**partial adoption** maps to the distinct-types checker (type-confusion /
primitive-should-be-VO) still unbuilt. **Naming drift** is a *new* candidate the
demo surfaced: a separator/format-convention checker. The ✅ rows show `mustnew`
and `stringequality` each plug a real consistency leak, and the ⚠️ row shows
`voconstructor` plugs scattered validation structurally (single path) without
yet checking the validation body.

A further dimension the metric measures but no analyzer yet gates: the **leak rate
past docs + skills** (how many inconsistencies CI catches when agents write *with*
the skills that say exactly how to build a VO). That is the deepest analyzer
rationale; it is gated on the skills landing in this repo. See
[`docs/design-three-contender-changeability.md`](../docs/design-three-contender-changeability.md).

## Run

```
go test ./rationale/...                 # the wins + the matrix meta-test
go test -bench=. -benchmem ./rationale/ # the adversarial cost (collection-VO defensive-copy tax)
./rationale/measure-ablation.sh ...     # measure changeability on your own repo
```
