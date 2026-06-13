# Coverage matrix — rule ↔ demonstrated win ↔ enforcement

This is the single source of truth linking each value-object rule to (a) the
executable demo in this `rationale/` package that shows the bug it prevents, and
(b) the go-ddd checker that enforces it (if one exists). `coverage_test.go`
fails on a **silent gap** — a checker with no row here, or a row naming a test
that doesn't exist. It tolerates the honest ❌/⚠️ rows by design: the rationale
makes the case for the whole discipline; go-ddd enforces the mechanically
checkable slice.

| Value-object rule | Demonstrated win (test in this package) | Real-world anchor | Enforced by | Status |
|---|---|---|---|---|
| Distinct types instead of bare primitives | `TestTypeConfusion_ValueObjectRejectsWrongUnit` — `Feet` where `Meters` expected won't compile | Mars Climate Orbiter (1999, $327M) | — | ❌ no checker yet |
| Value equality, not representation equality | `TestEquality_ValueObjectIsRight` — `0°C` == `273.15K` | scale/representation collision | `checkequality` (requires a `Test*_Equality`) | ✅ 1:1 |
| Constructors validate invariants | `TestValidation_ValueObjectRejectsBadInput` — sub-absolute-zero rejected | physically impossible state | — | ❌ no checker yet |
| VO constructors get `MustNew*` helpers | `TestMustReimplementation_HandRolledHelpersDiverge` (consistency demo, table below) | without it, authors reinvent divergent must-helpers | `checkmustnew` | ✅ consistency demo |
| `.String()` is for display, not equality | `TestEqualityByString_InconsistentIsWrong` — display-string equality mis-equates `0°C` and `273.15K` | `a.String() == b.String()` mis-equates multi-rep VOs | `checkstring` | ✅ 1:1 |

**Reading the gaps:** the two ❌ rows are wins go-ddd does not yet enforce
(candidate checkers for the `go/analysis` port — not scheduled). Every checker
now has an executable demo (`checkmustnew`'s is in the consistency table below).
Nothing here is a *silent* gap; every checker has a row and every named test
exists.

## Consistency dimension — the case for the *standard*, not just the pattern

The matrix above is arm 1 (primitive) vs arm 3 (consistent value object). But a
value object adopted *inconsistently* buys nothing on the change-speed axis: if
every author holds a different idea of what a VO is, the result leaks
representation and construction the same way a bare primitive does. **Inconsistent
VOs ≈ no VOs.** `rationale/inconsistent/` is arm 2 — a realistic mixture of bare
primitives and non-conforming value objects — and each row below proves it
reopens a silent site the consistent VO closes. This is the rationale for the
*checkers* (and the coming skills): they enforce the one canonical form that
actually delivers the dividend.

| Non-conformance (arm 2) | Silent site it reopens | Demo (test in this package) | Real-world anchor | Checker that plugs it | Status |
|---|---|---|---|---|---|
| **Partial adoption** — some concepts left primitive while others get wrapped | type confusion / wrong unit | `TestPartialAdoption_InconsistentAdmitsWrongUnit` | a slot left a bare string across 43 call sites while its VO existed | — | ❌ no checker yet |
| **Scattered validation** — no single constructor; the invariant copied across builders | bad value admitted at the site that forgot; rule change is an N-site edit | `TestScatteredValidation_InconsistentAdmitsBadValue`, `TestScatteredValidation_RuleLivesInManyPlaces` | pricing primitive-obsession postmortem (parent-validates-child) | — | ❌ no checker yet |
| **Equality via `.String()`** — comparing the display form | scale/representation collision | `TestEqualityByString_InconsistentIsWrong` | `.String()`-as-equality residue (test-VO audit) | `checkstring` | ✅ |
| **Must-helper reimplementation** — no canonical `MustNew`, so authors hand-roll divergent ones | construction behavior diverges (panic vs admit vs clamp) on the same bad input | `TestMustReimplementation_HandRolledHelpersDiverge` | 9 ad-hoc `must*` helpers across 5 files (`e7a470c`) | `checkmustnew` | ✅ |
| **Naming drift** — same value category, inconsistent naming convention | a format/meaning change silently misses the drifted literal | `TestNamingDrift_InconsistentMixesConventions`, `TestNamingDrift_FormatChangeMissesTheOutlier` | `revert_earn` underscore vs hyphen siblings (realized-harm) | — | ❌ no checker yet |

The ❌ rows are the checker backlog, now each grounded in a demonstrated leak:
**partial adoption** and **scattered validation** map to the two roadmap checkers
already named in the matrix above (type-confusion / primitive-should-be-VO, and
constructor-validation — the `go/analysis` port). **Naming drift** is a *new*
candidate the demo surfaced: a separator/format-convention checker. The ✅ rows
show the three existing checkers each plug a real consistency leak.

A further dimension the metric measures but no checker yet gates: the **leak rate
past docs + skills** (how many inconsistencies CI catches when agents write *with*
the skills that say exactly how to build a VO). That is the deepest checker
rationale; it is gated on the skills landing in this repo. See
[`docs/design-three-contender-changeability.md`](../docs/design-three-contender-changeability.md).

## Run

```
go test ./rationale/...                 # the wins + the matrix meta-test
go test -bench=. -benchmem ./rationale/ # the adversarial cost (collection-VO defensive-copy tax)
./rationale/measure-ablation.sh ...     # measure changeability on your own repo
```
