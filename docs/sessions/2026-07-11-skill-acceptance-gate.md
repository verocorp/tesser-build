# Acceptance-gate record — skills/ddd v1 (2026-07-11)

The gate defined by the approved design (design doc: gstack
`chris-main-design-20260711-093706.md`, Success Criterion 1): a fresh agent
that did not author the skill models a domain from the skill alone; objective
criteria verified independently of the authoring session. Activation is a
required *observed* check, not a gate bit (eng review 8A).

## Go gate — Claude Code host (Sonnet agent) — PASS

**Setup:** fresh subagent, given only (a) a consumer-style routing line
("Creating or modifying domain types → read skills/ddd/SKILL.md and follow its
routing") and (b) a neutral task: flight-boarding domain — seat number,
passenger, manifest with a no-shared-seats invariant. No conventions, no file
list, no mention of VO/entity/aggregate.

**Activation (observed):** followed the routing line unprompted → `SKILL.md`
first → all three concept files (expected: Mode 1 says run the taxonomy tests
per noun, and the task carried three nouns) → `go.md` only (progressive
disclosure held: `python.md` never read).

**Objective criteria (verified independently):**

| Criterion | Result |
|---|---|
| `go test ./examples/ddd/` green incl. agent-written tests (33) | ✅ |
| Gate test checklist (8 items: rejection, MustNew panic, `Test*_Equality`, spec-leaf validation chain, invariant violation, defensive copy, compile-time non-comparability, transition semantics per declared mutability) | ✅ all present |
| `ddd-vet` clean with entity+aggregate excluded (package-local `.go-ddd.yaml`) | ✅ |
| `-gen-excludes` classifies `Passenger` (identity signal: `ID()` method) and `BoardingManifest` (mutation signal) — and none of the four VOs | ✅ machine agrees with doctrine |

**Notable behaviors:**
- Correct judgment calls beyond the letter of the task: wrapped `PassengerName`
  with an explicit primitive-obsession justification; declared `Passenger` a
  *fact* (immutable) and `BoardingManifest` a *lifecycle* (guarded
  `AddPassenger`) with reasons matching the decision guides; no `MustNew` on
  entity/aggregate.
- **Self-discovered the exclude-ratification flow:** ran the repo's own
  `ddd-vet` against its output, hit the VO-heuristic false positives on
  entity/aggregate, traced `internal/voscan/config.go`, and wrote a
  package-local ratified `.go-ddd.yaml` with per-type justifications —
  unprompted.

## Codex host — AGENTS.md routing — PASS

**Setup:** `codex exec` (read-only), given an AGENTS.md-style routing line and
a Python design task (discount code / percentage / redemption), no writes.

**Activation (observed):** followed the routing line → `SKILL.md` → routed to
`value-objects.md`, `entities.md`, `python.md` (not `aggregates.md`,
correctly — no spanning invariant in the task; not `go.md`).

**Doctrine fidelity:** check-then-wrap applied with per-type justification;
identity-must-be-earned applied (defaulted `Redemption` to a fact/value record,
entity + `RedemptionID` only if the domain must distinguish identical
redemptions); Python mechanics correct (`__post_init__` single validation
site, primitive-leaf spec + `from_spec`, no parent re-validation,
`__eq__`/`__hash__` by ID together, no str-equality).

## Corrections harvested (discovery-loop input)

1. **Tool friction, not skill bug:** `ddd-vet -gen-excludes ./examples/ddd/`
   writes `.go-ddd.yaml` to the *current directory*, not next to the analyzed
   package — surprising when generating for a sub-package. Candidate CLI
   improvement for the fast-follow.
2. No resolver misroutes, no convention violations, no FAQ gaps observed in
   either session. The pilot discovery loop (real unassisted sessions on real
   tasks) remains the meaningful test — these two runs are the floor, not the
   ceiling.
