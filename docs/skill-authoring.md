# Authoring the `skills/tesser-build/` files

This is the repo-side contract for writing and revising the agent skill. It is
not copied into consumer repos. The design it implements is the 2026-07-11
approved design (office-hours + eng review); the rules below are the ones a
future author must not silently break.

## The three templates

Every **component doc** (`value-objects.md`, `entities.md`, `aggregates.md`,
`application-services.md`, `public-interface.md`, `bootstrap.md`, the gateway
family `repositories.md` / `gateway-cross-context.md`, `handlers.md`,
`wiring.md`, `srv.md`, and the grouped `strategic-design.md`) follows one
structure; every **mechanics doc** (`go.md`, `python.md`) follows another; the
**map doc** (`map.md`) is a third shape of its own (below).
The structures are designed for how an agent consumes them mid-task — routed in
with a specific question, needing the answer near the top and the depth below —
not for how the source material happened to be organized. Do not copy source
docs' structure; fill these templates from them.

One concept doc groups three concepts: `strategic-design.md` (skill-version 6) covers
subdomains, bounded contexts, and ubiquitous language as three sections — each
following the concept-doc shape (is-this / rules / decisions / common mistakes) under
a shared strategic-taxonomy table. They are grouped, not split into three files,
because the trio is interlocked (a bounded context is defined by its ubiquitous
language; a subdomain maps to a context) and none carries language mechanics. It
obeys the shared rules below; there are no `go.md`/`python.md` sections for it.

### Concept-doc template

```
# <Concept>
One-paragraph definition. Concept authority: Evans (DDD) / Vernon (IDDD),
paraphrased and cited — never verbatim passages.

## Is this what I'm building?        ← the classification TEST, first
The one-question test + the near-misses (what matches superficially but
is NOT this concept: DTOs, specs, persistence models...).

## Rules
Numbered, language-agnostic conventions. Each rule carries a one-line why.

## Shape
Minimal type shape only (fields + one signature). NO construction
mechanics — those live in the mechanics docs (code-ownership rule below).

## Decisions you must make
The genuine judgment calls (mutability, equality path, simple vs compound)
with the decision guide for each.

## How the machine sees it
The structural signals analyzers key on, stated as HEURISTICS the human
ratifies, never as the definition.

## Tests you must write
The concept's test checklist.

## Common mistakes
Named anti-patterns with the corrective rule.

## Now build it
Route to the mechanics doc anchors (go.md#..., python.md#...).
```

### Mechanics-doc template

```
# Building domain code in <Language>
Scope line: construction mechanics only; concepts live in the concept docs.
Covers the domain building blocks AND the seams that serve them (application
services, repositories are not domain objects, but their mechanics live here).

## Value objects        ← one section per concept, same order everywhere
## Entities
## Aggregates
## Application services  ← seam sections follow the object sections
## Repositories
## The Spec pattern     ← cross-cutting construction pattern(s)
## Testing patterns
```

The title is **"Building domain code"**, not "domain objects" — application
services and repositories are not domain objects (they orchestrate and persist
them), so a "domain objects" title is a category error once the seams land.
Domain services, when deepened past their stub, get a `## Domain services`
section between Aggregates and Application services.

### Map-doc template (the third shape)

`map.md` is a **procedure + anatomy**, not a concept: it teaches what the
pieces of an application are, how they connect, and the gap-survey
decomposition procedure — and routes each piece to its component doc. Sections:
the anatomy (roles + app level) → the adapter taxonomy → how contexts connect
(direction, call/read patterns, cycle resolution) → app vs library → the gap
survey → the piece-to-doc routing table. **No per-scenario guides** — tricky
cases that recur go to `docs/faq.md`, not new map sections. The
adapters/handlers/gateways *umbrella* concepts live here (OQ1 ruling,
2026-07-18), not in a taxonomy-only routing file.

### Stub contract (eng review 2A)

A component doc may ship before its content is materialized, but **every
not-yet-materialized doc (or section) carries the disclaimer inside itself**:
not yet materialized; note the gap, don't invent a convention; the verified
impl is `examples/python-app/<path>` (naming the exact path). Disclaimers
retire **per-file** as content lands — never wholesale at the SKILL.md level.
A stub still names the rules that *are* settled and machine-verified (locked by
an enforcement test in the verified impl); it stubs only what isn't.

Each section is complete for its concept: full worked code, naming rules,
error handling, test skeletons. Section headings are stable anchors — the
resolver and the coverage matrix link to them; renaming a heading is a
breaking change to both.

## Roadmap annotation schema (eng review 1A)

The roadmap matrix (`roadmap/ROADMAP.md`) is **generated, never hand-edited**:
`roadmap/generate.py` derives every cell from the repo. The row taxonomy lives
in `roadmap/registry.json` (one canonical registry file — adding a component
is a registry edit, not a generator edit, eng review D11b). Mechanically
derivable cells are computed; **judgment cells are annotated at the source they
describe** with ONE uniform marker grammar — the same line grammar in every
file type, wrapped in that file's comment syntax (`<!-- -->` in Markdown, `//`
in Go, `#` in Python). No per-file variants.

```
tb-status: full|partial|stub
tb-cell: <row-key> <column> <symbol> [-- <free text>]
tb-allow-missing: <path>
```

- **`tb-status`** — required in every skill doc a registry row names; drives
  the Skill-doc column (`full` → ✅, `partial`/`stub` → 🟡 + label). A file
  marked `partial` or `stub` **must contain the 2A disclaimer phrases**
  ("not yet materialized", "don't invent a convention") — machine-checked by
  the generator.
- **`tb-cell`** — a judgment override for one cell. `<row-key>` is a registry
  key; `<column>` is one of `py-example | go-example | skill | checker |
  rationale`; `<symbol>` is exactly one of `✅ 🟡 ❌ —` (the machine value);
  the `-- text` suffix is free commentary carried into the rendered cell. One
  marker per cell repo-wide (a duplicate is an error); a malformed marker is a
  named error with file:line.
- **`tb-allow-missing`** — suppresses the generator's dead-path check for one
  intentional forward reference (e.g. a planned example) in that file.

Registry rows are **typed** (eng review 5A): `"kind": "component"` (the
default when absent) renders in the component × materialization matrix;
`"kind": "rule"` — one row per pay-now rule, added fused with its
enforcement — renders in a second "Pay-now rules" table
(rule / taught in / enforced by / status), so an external enforcer like
import-linter renders honestly instead of bending the component columns.
A rule row carries `taught_in` (a repo path, optionally `#anchor`,
existence-checked) and `enforced_by` (free text naming the enforcer); a
malformed `kind` is a named file:line error. `tb-cell` overrides apply to
component rows only.

Markers are scanned in `skills/`, `examples/`, `rationale/`, `passes/`,
`tessercheck-py/` (`.md`/`.go`/`.py`; `testdata/` excluded). `docs/` and
`roadmap/` are deliberately out of scan scope so this section and the
generator's fixtures can quote the grammar.

## Delta-only norm sections (eng review 5A — review-enforced, not machine-checked)

Cross-cutting norms (error handling, testing, comments) get a general layer
plus **per-component deltas inline in component docs**. A delta must be
delta-only: the review procedure is the **delete-the-inline-bit test** — delete
the inline section; if no information was lost, it was a restatement, and
restatements are banned (they are silent sites: the general layer changes and
the copy silently diverges). This rule is **explicitly review-enforced** — no
analyzer checks it; the reviewer runs the delete test on every inline norm
section a change touches. This is the repo's honest-gap idiom: the enforcement
gap is named, not hidden.

## Code-ownership rule (eng review 5A)

Concept docs may show a minimal type SHAPE to teach the idea. ALL construction
mechanics — Spec pattern, validation placement, `MustNew*`, non-comparability,
frozen dataclasses, factory functions — live only in the mechanics docs. If
you're pasting a constructor body into a concept doc, you're breaking the rule.

## Source authority (eng review 9A)

- **Concept authority:** Evans (Domain-Driven Design) and Vernon (Implementing
  Domain-Driven Design). Paraphrase and cite. Brief attributed quotes (a
  sentence, clearly marked) only where original phrasing is load-bearing.
  Never reproduce book passages — this is a public MIT repo.
- **Implementation authority:** the ported vero doctrine (genericized) and
  this repo's analyzers. Battle-tested, but imperfect — where books and
  practice tension, say so in the doc rather than silently picking one.

## Machine alignment (eng review 1A)

The structural conventions must match `internal/genexclude`'s signals exactly:
identity (an `ID()` method, or a field named `id`/`ID`/`<Type>ID`), mutability
(pointer-receiver setter), child collections (slice/map of a named domain
struct type). If genexclude's signals change, the skill text changes in the
same commit. Signals are heuristics the human ratifies — never definitions
(eng review 10A). The signal *vocabulary* is v1 and flagged for revisit
(design doc Open Question 6).

## Progressive disclosure (eng review 7A)

`SKILL.md` is the only file a session auto-loads. It stays small: taxonomy +
two-mode resolver + routes. Every route names the exact file and heading
anchor. Never instruct the agent to "read all the files first."

## Sync (P5)

`rationale/coverage.md`'s skill matrix has one column per materialized file.
When you change a rule, walk its row and update every rendering in the same
commit; bump `skill-version` in `SKILL.md` frontmatter and note the changed
sections in the release notes.
