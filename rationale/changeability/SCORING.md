# Changeability scoring — the predeclared contract

This file is the **scoring function for the changeability rationale**, and it is
committed **before any contender arm exists**. That order is the whole point: an
adversary (a red-team model, or a future skeptic) optimizes against a *fixed*
target, so no assertion can be gerrymandered after the arms are seen. If you are
about to author an arm, this file already decided how it will be scored — do not
change the rule to fit a result.

> Design provenance: `~/.gstack/projects/verocorp-go-ddd/chris-main-design-20260712-194513.md`
> (findings F1–F12, both Codex outside-voice passes folded).

## What is being measured

**Changeability = the cost of a representative change, as a function of how many
dependents exist (N).** Not "is there a bug" — *when the code grows, does changing
it get harder.*

The unit is **migration surface**: the number of dependent packages a single
representative change **forces you to touch at all**. It is deliberately *not*
edit-hours. A codemod can rewrite N sites cheaply, but the boundary that yields 0
forced sites means **there is no migration to coordinate across owners** — a
different thing from a cheap migration. We measure "must this change be
coordinated across N dependents," not "how long does each edit take."

Per representative change, the claim under test:

- a **coupled** arm costs `O(dependents)` — every dependent that reached through
  the boundary must change;
- a **decoupled** arm costs `O(1)` — only the thing behind the boundary changes.

The `O(n^2)` systemic figure (lifetime edit-cost under all-pairs coupling) is a
*consequence*, not something this harness measures. Claim only the per-change
fan-out; never report a measured `n^2`.

## Declared changes for the public-interface anchor (C1 + C2)

The anchor for the public-interface decision declares **two** changes, not one —
because the adversary showed one is not enough (see `anchor/adversary_provenance.md`):

- **C1 — backend migration** (`-tags swap`): swap backend A→B. A dependent that
  reached through to a backend-specific type is forced to change; a dependent on
  `orders.Client` is not. **Finding: C1 alone is tied by a lower-ceremony package
  facade** — a facade survives a backend swap too. C1 does not, on its own,
  justify the interface.
- **C2 — substitution** (`-tags subst`): a dependent must be unit-testable against
  a substitute (a fake, or a second impl). A dependent that *receives*
  `orders.Client` swaps a fake in with **0 edits**; a facade dependent bound to a
  global has **no seam**, so gaining substitutability is a forced edit (modelled by
  a `subst`-tagged build that fails to compile — the `swap_bug.go` idiom on the
  substitution axis). C2 is where the interface earns its place, and it scales:
  N facade dependents each pay, N interface dependents pay 0.

A decision may need more than one declared change to be honestly justified. Adding
the change that discriminates (rather than softening the rule) is the standard
resolution when the red-team ties on the first change — that is the red-team
*improving the benchmark*, the intended outcome.

## Declared changes for decision 3 — no outward representation (`nooutward/`)

The decision: **a domain object emits no non-domain representation.** Turning a
domain object into a DTO is the application service's **Respond** step
(`skills/tesser-build/application-services.md`: "a domain object never leaves the service;
returning one is a boundary leak — the service-layer twin of a value object leaking
its representation"), never a method on the domain object. The correct layering,
which the arms model faithfully:

- **DTOs** are the public-interface currency — dumb bags of primitives (and nested
  DTOs), **no methods and no constructors**, importing nothing (a leaf). Clients
  send and receive them.
- **Domain objects** expose **value objects, never primitives**, and import nothing
  outward.
- The **application service** is the only code that knows both: Convert (request DTO
  → domain value objects), Delegate, Persist, Respond (domain object → response DTO).
  The DTO↔domain mapping lives here — the sanctioned "serializer" [F5].

The sanctioned exception stays explicit: a mapper in the application/outward layer
is fine; the rule is "no UNINTENDED representation leak," not "never emit a DTO." So
the coupled arm is a domain object that *itself* emits its DTO (a
`Maneuver.ToResponse()` returning `pub.ManeuverResponse`), not a strawman.

The single declared change:

- **D3 — outward-representation migration (`-tags repv2`).** The public response
  DTO reshapes (`BurnSeconds` → `DurationMillis`). A dependent that operates on the
  **domain object's value objects** (`domain.Maneuver.Burn()`) is untouched; a
  dependent that reached through a **domain that emits its DTO**
  (`emit.Maneuver.ToResponse().BurnSeconds`) is forced. Contrast at matched N:
  decoupled 0 vs coupled N at N=8/16. The single correct mapping site is the
  application service's Respond (package `app`), which the migration forces **once**
  — that O(1) is what the domain-emitting violation trades for O(N).

**There is deliberately NO compile guard for this decision** (this supersedes an
earlier "D3a import-cycle" framing that a first adversary pass correctly defeated).
A properly dumb DTO imports *nothing*, so a domain importing it is **never an import
cycle** — the earlier cycle only appeared because that fixture wrongly put the
domain→DTO mapper inside a package that imported the domain. The no-outward-
representation rule is a **convention the compiler does not enforce**; the D3
fan-out above is what justifies it. (Enforcement, if wanted, is a lint/analyzer —
consistent with why `tessercheck` exists — not the type system.)

## The forced-edit metric (how the count is taken)

For an arm at a given N, apply the arm's **declared change** C, then count the
dependent packages that are *forced* to change.

- **Detection is per-package, never whole-module.** Build each consumer package
  individually (`go build ./rationale/changeability/<arm>/consumer<k>` for every
  k), because `go build ./...` stops early and lets one package's failure mask
  the true count (`measure-ablation.sh` already documents this undercount). [F12a]
- **Dependency-failure filtering.** A package counts as *forced* only if **its own
  source references the changed symbol**. A package that fails merely because a
  package it imports failed is a *transitive* failure and is **not** counted — it
  would double-count the same coupling.
- **"Unchanged" is defined precisely.** A dependent is *unchanged* iff no edit to
  its **source** (imports included) is required to build and pass after C.
  Reformatting and regenerated files do **not** count as changes; a diff limited
  to `gofmt` output or `go:generate` output is "unchanged." [F5]

The compile-detected mechanism above serves the *type-coupling* decisions
(public interface, repository row types). For the *semantic* decisions the count
is **behavior-detected**: apply C, then count dependents that produce observably
wrong output caught by a test — not author-placed markers (which are circular).
Each such decision **also** carries a harm-specific assertion (below).

### The proof is the CONTRAST at matched N — not the coupled count alone

You author N coupled dependents, so "the coupled count rises with N" is true *by
construction* and proves nothing on its own. The assertion is the **delta between
arms at the same N**: [F1]

```
at N = 8:   decoupled forced-edits = 0   |   coupled forced-edits = 8
at N = 16:  decoupled forced-edits = 0   |   coupled forced-edits = 16
```

The decoupled arm staying **flat at 0** across N is the `O(1)` claim (compiler-
verified, structural — it holds at N=1). The coupled arm **tracking N** is the
`O(dependents)` claim. Two N values earn their place only as this contrast: one
arm flat, the other tracking. A single N, or the coupled count in isolation, is
not a proof.

**Positive control (mandatory).** Before applying C, assert **both** arms build
green. Without it, an arm that never compiled would "pass" the failure assertion
trivially. [F6]

## The ceremony metric (for the red-team head-to-head)

When a **red-team** arm reaches the *same* changeability as ours (0 forced-edits
under C) by a *different* route, "did DDD win?" turns on **ceremony**, and
ceremony must be measured, not asserted. [F9] Ceremony of an arm =

1. **Exported symbols** a dependent must know to use the boundary (the public
   surface: exported types + methods + funcs in the boundary package).
2. **Concepts a developer must learn** — the count of named architecture/DDD
   concepts the approach introduces (e.g. "composition root", "public Client",
   "port"). Enumerated explicitly per arm, not guessed.
3. **Wiring / setup steps** — composition-root lines + generate steps + config a
   consumer or the app must perform to obtain the boundary.

Lower ceremony **at equal changeability** wins. This is the only place a
comparison is not a pure integer forced-edit count, so it is defined here up front.

## Escape-hatch rules (which arm may use what)

- **Coupled (realistic-bad) arms** MAY NOT hide coupling behind `interface{}`,
  `map[string]any`, reflection, or stringly-typed contracts — those understate
  real coupling and would rig the count downward. They model what real developers
  actually write that couples more (reach-through to a concrete/backend type,
  shared mutable structs, service-locator), **not** deliberately-worst code. [F5]
- **The red-team arm** MAY use **any real architecture** — protobuf/JSON
  contracts, generated clients, schema-driven adapters, event envelopes, generic
  records. These are legitimate ways to beat our boundary, not gaming, because
  scoring is *forced-edits under C + ceremony*, never "does a dependent name a
  concrete type." [F10]
- **The decoupled (ours) arm** is scored by the same rule as the red-team.
- **Type shapes are fixed by the real architecture (all arms, red-team included).**
  A **DTO** is a dumb bag of primitives (and nested DTOs): **no methods, no
  constructors** on the type. A **domain object** exposes **value objects, never
  primitives**. This is not an escape-hatch ban but a *realism* constraint grounded
  in the reference code (certus: 0 spec/DTO constructors, 0 accessor methods on
  specs or request/response DTOs; the types that carry methods are domain objects
  built from specs). It applies to every arm because a red-team that puts a stable
  accessor **method** on a DTO, or reads a **primitive** straight off a domain
  object, is measuring an architecture the toolkit does not permit — and that
  illegal shape was exactly how a first decision-3 adversary pass manufactured a
  false tie (a `Record.BurnMillis()` shim on a DTO). Curating this is part of the
  human realism role. [added after F12; grounds the DTO/VO boundary]

## The finding → action decision rule (predeclared)

The outcome of an arm set is one of the following, and each **triggers a named
action** — a "logged finding" that changes nothing is not an accepted outcome. [F9]

| Outcome | What it means | Action |
|---|---|---|
| Red-team forced-edits > 0, or = 0 with **more** ceremony than ours | our boundary earns its place for C | assert the win; the `coverage.md` changeability row stands |
| Red-team forced-edits = 0 with **less** ceremony than ours | the boundary is ceremony for C | **soften or retire the named `skills/tesser-build/` rule**; record the simpler approach as the recommended pattern |
| A realistic **coupled** arm matches or beats our forced-edits | the rule doesn't buy what we claimed | **named `skills/tesser-build/` or doc change**, logged with the arm |
| **Negative control**: our decoupled arm also pays N | the harness measures real coupling (not rigged) | control passes — the win elsewhere is credible |
| Negative control: our decoupled arm pays 0 (boundary "helped" where it should not) | the harness is biased | **stop and investigate the harness**, do not report wins |

"Which named rule" must be identifiable *before* running — name the
`skills/tesser-build/*.md` rule each arm is evidence for, in the arm's doc comment.

## Reproducibility & provenance

- The adversary (Codex) run is a **one-time design exercise**. Its produced arms
  are **committed**; CI re-runs the metric on committed code (`go test`), with no
  live agent in CI. [F4]
- Commit the adversary's **provenance** alongside the arms: the prompt, the
  constraints it was given, the transcript, the rejected variants, and the
  selection rationale — so "the adversary tried hard" is verifiable, not asserted. [F12b]
- The **human role** is curating whether a committed arm is a realistic pattern /
  a legitimate red-team attempt — **not** judging the winner. The metric judges.

## Corroboration

The committed synthetic arms are the CI-reproducible proof. They are corroborated
(not replaced) by running `measure-ablation.sh` on **real** code mutations for the
decision under test, cited alongside the synthetic result — the same real-code
approach `docs/case-study.md` already used. Synthetic gives reproducibility; real
ablation answers "is this only true in a fixture." [F7]
