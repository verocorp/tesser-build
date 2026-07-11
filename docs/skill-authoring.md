# Authoring the `skills/ddd/` files

This is the repo-side contract for writing and revising the agent skill. It is
not copied into consumer repos. The design it implements is the 2026-07-11
approved design (office-hours + eng review); the rules below are the ones a
future author must not silently break.

## The two templates

Every **concept doc** (`value-objects.md`, `entities.md`, `aggregates.md`, and
future ones: application services, repositories, bounded contexts, ...) follows
one structure; every **mechanics doc** (`go.md`, `python.md`) follows another.
The structures are designed for how an agent consumes them mid-task — routed in
with a specific question, needing the answer near the top and the depth below —
not for how the source material happened to be organized. Do not copy source
docs' structure; fill these templates from them.

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
# Building domain objects in <Language>
Scope line: construction mechanics only; concepts live in the concept docs.

## Value objects        ← one section per concept, same order everywhere
## Entities
## Aggregates
## The Spec pattern     ← cross-cutting construction pattern(s)
## Testing patterns
```

Each section is complete for its concept: full worked code, naming rules,
error handling, test skeletons. Section headings are stable anchors — the
resolver and the coverage matrix link to them; renaming a heading is a
breaking change to both.

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
