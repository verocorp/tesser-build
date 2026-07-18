# Adversary provenance — decision 3 (no outward representation)

Per `../SCORING.md` §Reproducibility, the adversary run is a one-time design
exercise whose **arms are committed** and whose **provenance is committed** so that
"the adversary tried hard" is verifiable, not asserted. The human role is curating
**realism** of the arms — not judging the winner; the metric judges.

## Provenance history — two passes (the first improved the benchmark)

- **Pass 1 (mismodeled fixture).** The first decision-3 fixture modeled the outward
  layer as a package that imported the domain and gave its DTO a stable accessor
  *method*. Against that, Codex correctly (a) defeated a bogus "import-cycle guard"
  with a shared-leaf DTO, and (b) manufactured a **false tie** by putting a
  `Record.BurnMillis()` compatibility method on the DTO so consumers dodged the raw
  field. That was not a weakness in decision 3 — it was a weakness in the fixture:
  it violated the real architecture. Verified against **certus**: DTOs (specs and
  request/response) are **dumb bags of primitives — no methods, no constructors**;
  domain objects expose **value objects, never primitives**. The fixture was rebuilt
  to that layering and `SCORING.md` gained the DTO/VO type-shape constraint
  (escape-hatch rules) plus the note that decision 3 has **no compile guard** — a
  dumb DTO imports nothing, so a domain importing it is never a cycle; the rule is a
  convention justified by the fan-out. Pass 1 improved the benchmark, the intended
  outcome.

- **Pass 2 (this file).** A fresh, neutral `codex exec -s read-only -c
  model_reasoning_effort=high` run (2026-07-13) against the corrected fixture and the
  frozen `SCORING.md`. No biasing, no mention of pass 1. This is the scored pass.

## The declared change

**D3** (`-tags repv2`): the public response DTO reshapes a field
(`BurnSeconds` → `DurationMillis`). Decoupled = operates on the domain object's
value objects; coupled = reaches the domain-emitted DTO's field.

## The committed arms + verified scoring

Per-package `go build` (SCORING.md's unit), default vs `-tags repv2`:

| Arm | Pattern | pre-migration | `-tags repv2` | forced-edits |
|---|---|---|---|---|
| `coupled/webhookpayload` | outbound adapter builds its own struct from `emit.Maneuver.ToResponse().BurnSeconds` | builds | **fails** | 1 (→ N fanned out) |
| `coupled/burnsort` | reporting/UI sorts `[]emit.Maneuver` by `ToResponse().BurnSeconds` | builds | **fails** | 1 (→ N) |
| `coupled/fanout/*` (generated) | reach `emit.Maneuver.ToResponse().BurnSeconds` | builds | **fails** | N (8/16) |
| `redteam/burnquery` | query-projection facade over `app`/`pub.Client`; owns the single mapping (response_v1/v2) | builds | **builds** | **0** |
| (reference) `decoupled/*` | operate on `domain.Maneuver` value objects | builds | builds | 0 |

Both hand-authored coupled failures are **direct source references** (own source
names `BurnSeconds`), not transitive — `emit` compiles under `-tags repv2` (its DTO
assembly is tag-split), so nothing masks the count. Verified.

**Realism curation (human):** `webhookpayload` (an outbound adapter reusing the
emitted DTO) and `burnsort` (read-side code treating the wire shape as the domain's
inspection API) are patterns real Go codebases contain. The red-team `burnquery` is
a legitimate attempt — a query projection over the application service, using only
sanctioned constructs.

## Ceremony comparison (Codex)

- Decoupled arm (direct domain VO use): a dependent must know `domain.Maneuver`,
  `Maneuver.Burn`, `Burn.Seconds` — 3 symbols; concepts = aggregate + value object +
  VO-owns-conversion; setup = the caller already holds a `domain.Maneuver`.
- `redteam/burnquery`: a scalar-read dependent must know `burnquery.BurnSeconds` — 1
  symbol; concepts = query facade (+ the hidden application client); setup = 0 for
  the simple call.

On the ceremony metric, the facade beats the decoupled arm **for narrow scalar-read
consumers** — but note the comparison is not like-for-like: the facade also does the
fetch-from-id the decoupled consumer assumes already done (Codex's own rejected
variant).

## Rejected variants (Codex)

- **DTO accessor method** (`response.BurnMillis()`): rejected — DTO methods are
  banned by the type-shape rule (this was pass 1's false-tie lever; now excluded).
- **One-line projection `func BurnSeconds(domain.Maneuver) int64`:** lower ceremony,
  but assumes the consumer already holds a domain object outside the service.
- **`map[string]any` / reflection / JSON probing:** banned for coupled arms; weak
  evidence.
- **Generic `Measurement[T]` / interface shims:** more ceremony than the facade, or
  hide coupling rather than improve the architecture.

## Codex's verdict (verbatim conclusion)

> Decision 3 earns its place against the realistic coupled arms: once the domain
> emits `pub.ManeuverResponse`, normal webhook/reporting/sorting code starts naming
> `BurnSeconds`, and D3 forces N direct edits.
>
> The red-team does find a narrower lower-ceremony tie for scalar reads: a query
> facade reaches 0 dependent forced edits with fewer consumer symbols than direct
> domain VO use. Under `SCORING.md`'s finding rule, this should soften the named
> `skills/tesser-build/application-services.md` guidance, not retire D3: keep "domain objects
> do not emit public DTOs," but record "for narrow read consumers, prefer an
> application/query projection facade over exposing the domain VO graph."

## The finding → action

**Decision 3 is validated** (the `coverage.md` row stands): the realistic coupled
arms pay N under the outward-format migration, and the red-team **did not** justify
`emit.Maneuver.ToResponse()` — it explicitly conceded D3 forces N there.

The red-team's facade is the **sanctioned application-layer mapper**, orthogonal to
decision 3 (compatible with it, not a challenge). Its "lower ceremony" is partly the
different job (fetch-from-id vs. already-holding-the-aggregate). What it genuinely
surfaces is a **read-side ergonomics** refinement, consistent with the repo's
existing CQRS-read sanctioning (`repositories.md` read path; decision 4's
"projections OK").

**Action:** apply the *anatomy-of-a-perfect-technical-answer* heuristic to
`skills/tesser-build/application-services.md` (as the anchor's facade finding was folded into
`composition-root.md`): teach not just the rule but the alternatives, which axis each
wins/loses, and the negative —
- **the invariant:** the domain never emits its own DTO (`ToResponse()` on a domain
  object) — a wire reshape then fans out to N dependents (this arm);
- **the good read patterns and when:** domain-side code that already holds the
  aggregate reads its value objects; a narrow read consumer starting from an id is
  better served by a **query/projection facade** over the application service (lower
  ceremony, the CQRS read side);
- **the negative:** exposing the domain VO graph to a scalar-read caller is more
  ceremony than a projection — but is still not a reason to let the domain emit a DTO.
