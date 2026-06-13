# Design: the three-contender changeability metric

**Status:** design — not yet built. Defines the metric *before* it is measured, so
the result can falsify the thesis rather than confirm a foregone conclusion.
**Date:** 2026-06-13
**Origin:** 2026-06-13 Claude Code session in `go-ddd`, building on the landed
`rationale/` layer (`a0dd0ec`) and the silent-site-cost metric
(sessions `91ec0733`, `c8b6be03`). The structural cut here is Chris's.

---

## The gap this closes

The landed `rationale/` proves **value objects beat bare primitives** — on safety
(Mars Climate Orbiter) and on changeability (silent-site count). It does **not**
prove the thing that actually justifies *go-ddd* (the checkers + the coming
skills): that the dividend comes from **consistency**, not from VO-adoption.

The load-bearing claim, stated plainly:

> "Adopt value objects" is a near-no-op if every author holds a different concept
> of what a VO is. A heterogeneous pile of "VOs" leaks representation and
> construction the same way bare primitives do. **Inconsistent VOs ≈ no VOs** on
> the change-speed axis. The dividend is bought by the *standard*, not by the
> pattern.

If that claim is true, the rationale for each layer of the stack follows:

```
                                      what it buys                 measured by
  Layer 0  VOs vs primitives          safety + partial change-speed   landed rationale/
  Layer 1  CONSISTENT vs              the change-speed dividend only   THIS metric
           inconsistent VOs           materializes with one form       (three contenders)
  Layer 2  docs + SKILL.md            how you GET adoption             (skills land soon)
           (coming to this repo)      — goes only so far
  Layer 3  CI / the checkers          the GATE: catches what slipped   leak-rate metric
                                       past docs+skills                 (FUTURE — gated
                                                                        on Layer 2)
```

Layer 3 is the deepest justification for the checkers: they are not redundant
with the skills, they measure the **residual** the skills fail to close.

---

## The metric (defined before measuring)

Reuse the existing unit: **silent-site count** under a change — sites that still
*compile* after the change but are now semantically wrong, so a human must find
them by hand and can miss some. (Compiler-forced sites are cheap and safe; silent
sites are the cost. See `case-study.md`.)

Run the **same change operations** across **three contenders** for the same domain
concept:

```
  silent-site count
  (lower = cheaper, safer to change)
  high ┤  ███████ arm 1            ██████ arm 2
       │  primitives               inconsistent "VOs"
       │
       │
   ~0  ┤                                              ▏ arm 3
       │                                                consistent VOs
       └─────────────────────────────────────────────────────────
```

**The thesis predicts:** `arm 1 ≈ arm 2 ≫ arm 3 ≈ 0`.

**Falsification condition (write it down now):** if `arm 2` lands materially below
`arm 1` — i.e. inconsistent VOs already capture most of the dividend — the thesis
is **wrong**: VO-adoption alone is enough and the consistency argument (and much
of the checker rationale) collapses. We report that honestly if it happens.

### The three arms

| Arm | What it is |
|---|---|
| 1 — primitives | the concept is a bare `string`/`float64`/`map`, as today's `rationale/primitive/` |
| 2 — inconsistent VOs | the concept is "wrapped," but each concept is wrapped a *different non-conforming way* (see modeling rules below) |
| 3 — consistent VOs | the concept is a conforming VO: private field, single validating constructor, value equality, no representation leak — today's `rationale/valueobject/` |

### Change operations (reuse the landed taxonomy)

Per the six-operation / three-tier taxonomy already established: at minimum run
**retype the representation** (string→int), **rename the type**, **add a
validation invariant**, and **change an allowed value/meaning**. Count silent
sites for each operation, each arm.

---

## Modeling arm 2 without rigging it (the grader=builder seam)

Arm 2 is a **fixture we construct**, so we choose how bad to make it. A
deliberately terrible strawman would rig the result and prove nothing. The
discipline: **every non-conforming shape in arm 2 must be anchored to a real
non-conforming shape found in `certus` history** — not invented. Real anchors
already excavated:

| Arm-2 non-conformance (modeled) | Real historical anchor | Silent-site leak it reopens | Checker that catches it |
|---|---|---|---|
| Named type with **exported / leaking representation** (`type X string`, callers do `string(x)` and `X("lit")`) | retype stays expensive when the rep leaks | **retype** is no longer 1-file: every conversion/literal site is silent | (roadmap: no checker yet) |
| **No constructor / no validation** at the boundary | `BaseInput` "data carrier"; nil-check asymmetry (postmortem) | **add-validation** has no single home → scattered or missed | (roadmap: constructor-validation checker) |
| **Equality done two ways** (`==` here, `.String()` compare there) | residual `.String()`-as-equality (test-vo-assertions audit) | **change-meaning / retype** silently breaks the `.String()`-compare sites | `checkstring` |
| **Missing `MustNew`** → callers hand-roll construction | 9 ad-hoc `must*` helpers across 5 files (`e7a470c`) | construction path not single → change to construction is silent at each hand-roll | `checkmustnew` |
| **Partial adoption** (a slot stays raw while the VO exists) | `CreditAmount.CreditType() string` raw across **43 call sites** (`3c4de62`) | every raw slot is a silent site a VO-side change never reaches | (the bidirectional hunter, in certus) |
| **Naming drift** (`revert_earn` underscore vs hyphen elsewhere) | operation-type literals (realized-harm report) | meaning/format change is silent across the drifted literals | (data-level; not a Go-type checker) |

This table is the spine of the deliverable: it simultaneously (a) defines arm 2,
(b) maps each leak to the silent-site class it reopens, and (c) gives
`coverage.md` a new column — *which silent-site leak does this rule plug?* — that
upgrades `checkmustnew`/`checkequality`/`checkstring` from "hygiene" to "each
plugs a measured change-cost leak."

---

## Build plan

1. **`rationale/inconsistent/`** — a third package mirroring the navigation domain
   (Feet/Meters, Temperature, etc.), implemented per the arm-2 modeling rules
   above. Each file comments its real historical anchor.
2. **Extend `changeability_test.go` + `changeability_bench_test.go`** — run the
   change operations across all three arms; assert the predicted ordering
   (`arm1 ≈ arm2 ≫ arm3`). Where an operation can't be expressed as a Go test,
   express it as a build-tag compile check (as `swap_bug.go` already does).
3. **`coverage.md`** — add the *leak-plug* column from the table above; the
   `coverage_test.go` meta-test extends to forbid a silent gap there too.
4. **`case-study.md` (private magnitudes)** — add the `CreditType()`-string
   43-call-site partial-adoption example as the real-world magnitude for arm 2,
   mirroring how the rename/retype magnitudes already anchor arms 1 and 3.

---

## Scope

**In:** Layers 0–1 — the three-contender metric, its fixture, the coverage
leak-plug mapping, and documenting the adoption ladder.

**Out (this round):**
- **Layer 3 leak-rate metric** — "how many inconsistencies does CI catch when
  agents write *with* the skills that tell them exactly how." This is the deepest
  checker rationale, but it is **gated on Layer 2**: the skills aren't in the repo
  yet. Park it; it becomes the next measurement once skills land.
- **New checkers** — the roadmap rows (type-confusion, constructor-validation)
  stay deferred, consistent with the standing decision.

---

## Honesty guardrails (carried from the body of work)

1. **Define before measuring** — this doc commits the predicted ordering and the
   falsification condition *before* any number exists. (`gold-standard-derived-not-assessed`.)
2. **Don't strawman arm 2** — every non-conforming shape cites a real historical
   analogue (the table). The residual builder-seam is *which* shapes to include;
   answer by enumerating the real ones, not inventing.
3. **Exposure is not bugs** — silent-site counts are worst-case exposure, not
   proven escaped bugs. (`no-laundered-quantifiers`.)
4. **Fixture shows the mechanism; history carries the magnitude** — same split the
   landed rationale already uses (neutral public fixture; real certus numbers
   private and anonymized).

---

## Open questions for Chris

1. **Arm-2 breadth:** model *all six* non-conforming shapes (one concept each), or
   the 2–3 highest-signal ones for a tighter fixture? More shapes = stronger claim,
   bigger fixture.
2. **Package name:** `rationale/inconsistent/` vs `rationale/looseobject/` vs other.
3. **Layer-3 framing now:** document the leak-rate metric as a stated *future*
   metric in this round's write-up, or leave it entirely until skills land?
