# Adversary provenance — the public-interface anchor

Per `SCORING.md` §Reproducibility, the adversary run is a one-time design
exercise whose **arms are committed** and whose **provenance is committed** so
that "the adversary tried hard" is verifiable, not asserted. This file is that
provenance. The human role here is curating **realism** of the arms — not judging
the winner; the metric judges.

## What was commissioned

An outside model (Codex, `codex exec -s read-only -c model_reasoning_effort=high`,
two calls on 2026-07-12) was given the frozen `SCORING.md` plus the full anchor
code and asked to produce, optimizing **against** the fixed contract:

- **Coupled arms** — 2–3 distinct *realistic* coupling patterns real Go devs
  write (not deliberately-worst code), each forced to change by the declared
  change **C = migrate backend A→B** (`go build -tags swap`). Escape-hatch ban
  applied (no `interface{}`/reflection/maps/stringly-typed hiding).
- **Red-team arm** — its best attempt to match the decoupled arm's 0 forced-edits
  under C with **less ceremony**, or to break the O(1) claim. Bans lifted; any
  real architecture allowed.

## The committed arms + verified scoring

Per-package `go build` (SCORING.md's unit), default vs `-tags swap`:

| Arm | Pattern | pre-swap | post-swap (C) | forced-edits |
|---|---|---|---|---|
| `coupled/reachthrough` | calls `backend.FetchRawA`, returns `OrderRowA` (ad-hoc reconciliation) | builds | **fails** | 1 (→ N when fanned out) |
| `coupled/exportrow` | bakes `backend.OrderRowA` into its own exported API type | builds | **fails** | 1 (→ N) |
| `coupled/locator` | package-global returning `backend.OrderRowA` (legacy batch) | builds | **fails** | 1 (→ N) |
| `redteam/portless` | package facade `PlaceOrder`/`GetOrder` over `anchor.Wire()`; imports `anchor`+`orders`, never `backend` | builds | **builds** | **0** |
| (reference) `decoupled/*` | depends only on `orders.Client` | builds | builds | 0 |

All three coupled failures are **direct source references** (own source names
`backend.OrderRowA`/`FetchRawA`), not transitive dependency failures — they pass
SCORING.md's dependency-failure filter.

**Realism curation (human):** all three coupled patterns are realistic — each is
a thing real Go codebases contain (an ops/reconciliation reach-through, a
reporting package reusing the storage row as its exchange type, a legacy global
accessor). The red-team `portless` is a legitimate attempt (a package facade over
a global composition root), not gaming — it uses only real language constructs.

## Ceremony comparison (Codex)

- `orders.Client` (ours): 7 exported boundary symbols (`Client`, 2 methods, 4
  DTOs); concepts = public Client + DTO + composition root + repository port;
  setup = a consumer must receive/hold an `orders.Client`.
- `redteam/portless`: 2 exported symbols (`PlaceOrder`, `GetOrder`) — DTOs shared;
  concepts = package facade + DTO + composition root; setup = none (each call
  invokes `anchor.Wire()`).

On the letter of the ceremony metric, `portless` matches our changeability with
**fewer exported symbols and no consumer setup**.

## Rejected variants (Codex)

- **Generic `Repository[T]`** — 0 forced-edits only if `T` is not
  `backend.OrderRowA`; then it is just another DTO/client boundary with more
  generic ceremony.
- **protobuf / JSON generated contracts** — legitimate 0 forced-edits, but more
  setup and generated surface than `orders.Client`.
- **Returning domain `ordersapp.Order`** — avoids backend coupling, but exposes
  application internals; more conceptual leakage than the facade.
- **`interface{}` / maps / reflection / stringly-typed rows** — disallowed for
  coupled arms, and poor red-team evidence (hides static coupling instead of
  improving the boundary).

## Codex's verdict (verbatim conclusion)

> I cannot cleanly beat the decoupled arm on both changeability and overall
> ceremony without paying elsewhere. `portless` reduces visible consumer setup,
> but it centralizes wiring inside every call and is less testable/injectable than
> accepting an `orders.Client`. The strongest conclusion is that `orders.Client`
> earns its place for this backend migration; the facade is lower setup only by
> giving up dependency injection.

## The finding (what this triggers)

The red-team **ties** the interface on the anchor's single change (migration) with
**less ceremony**. Under SCORING.md's decision rule that reads as "the boundary is
ceremony *for C*." But the tie exists only because the migration change does not
exercise **substitution** — the facade's global `anchor.Wire()` cannot be swapped
for a fake without editing the facade or every call site, whereas an
`orders.Client` dependent substitutes with zero edits.

**Conclusion:** the anchor's migration change **under-justifies** the public
interface — a facade survives a backend swap too. The interface earns its place on
a *second* change: **C2 = substitute the implementation** (a test double / a second
impl). The forced-edit contrast under C2 is where `portless` pays N and
`orders.Client` stays 0. That change, and the matching skill sharpening ("the
public interface earns its place via substitutability, not migration-survival
alone"), is the action this finding triggers — routed to `skills/ddd` per the
decision rule.
