# The map — application anatomy, connections, and the gap survey

<!-- tb-status: full -->

This is the **general map**: what the pieces of an application are, how they
connect, and the survey procedure for finding which pieces your task actually
needs (`SKILL.md` routes here from Mode 1). It is anatomy + procedure, not a
component doc — each piece's construction rules live in its own file, listed at
the bottom. Evidence base: the settled model excavated from the vero prior art
(`docs/prior-art-anatomy.md` in the source repo); the verified impl is
`examples/python-app/`.

## The anatomy

An application is a set of **bounded contexts** (`strategic-design.md`) plus a
thin app-level layer that wires and hosts them.

**A bounded context has four roles — all present in an app context; internal
nesting and layout are free** (presence is required, organization is not
prescribed):

| Role | What it holds | Component docs |
|---|---|---|
| **domain** | VOs / entities / aggregates + the outbound port interfaces the context owns, defined beside their consumer | `value-objects.md`, `entities.md`, `aggregates.md`, `domain-services.md` |
| **application** | use-case services (Convert → Delegate → Persist → Respond); no business logic | `application-services.md` |
| **adapters** | inbound `handlers` + outbound `gateways` (taxonomy below) | `handlers.md`, `repositories.md`, `gateway-cross-context.md` |
| **wiring** | the context's own construction + its `Config` | `wiring.md` |

The context's **top level is its public seam**: the `Client` interface +
primitive DTOs (`public-interface.md`). There is no separate "contract" role —
the seam *is* the top of the context. A context is **discovered by its seam**:
anything that exposes a `Client` is a context (the verified impl's discovery
check keys on exactly this).

**App-level, not per-context** — two things only:

- **`bootstrap`** — the composition root: `new(cfg) → App`, builds the graph
  once (`bootstrap.md`).
- **`srv/`** — the hosts, one per delivery mechanism; the host is the env edge
  (`srv.md`).

**Boundary enforcement is optional, the boundary is not.** The public-vs-impl
split stands on private fields + constructor-only construction; Go's
`internal/` or Python's `_internal` + import-linter are optional hardening over
it, not the boundary itself.

## Adapters: handlers and gateways {#adapters}

**Adapters** is the umbrella: everything that touches the outside world on a
context's behalf. Two types, split by direction — **inbound needs a server
(something calls *in*); outbound doesn't (it calls out).**

- **Handlers (inbound)** — translate one delivery mechanism's wire format to and
  from the context's `Client`: HTTP, CLI, event-consumer. → `handlers.md`
- **Gateways (outbound)** — satisfy a port the context owns, by reaching
  something outside it:
  - **repository** — the gateway to persistence → `repositories.md`
  - **cross-context** — the gateway to a peer context's `Client` →
    `gateway-cross-context.md`
  - **vendor/ACL** — the gateway to a model you *don't* own (a third-party SDK
    or schema). **No file and no verified impl exists yet** — note the gap,
    don't invent a convention. Anti-corruption is a *purpose* a gateway can
    have, not a separate role: it is built as port + adapter like any other.

Recommended (not enforced) layout: `adapters/handlers` and `adapters/gateways`
as the sole adapter dirs. **Events are not a new role**: publish = an outbound
gateway over an `EventPublisher` port; consume = an inbound handler plus a
worker host (`srv/wrk`). (The event shape is reasoned by symmetry with the
well-evidenced HTTP path — the prior art is thin here; treat it as the default
shape, not settled doctrine.)

## How contexts connect {#how-contexts-connect}

**Dependency direction is the load-bearing rule.** Within a context, adapters
and wiring depend inward on application and domain, never the reverse. Between
contexts, every edge points one way, and the graph stays acyclic:

```
srv/* hosts ──▶ handlers ──▶ Client ──▶ application ──▶ domain
bootstrap ──▶ each context's wiring          (constructs, never the reverse)
gateways ──implement──▶ ports the domain/application own
```

**A cross-context CALL** (one context needs a peer's answer, synchronously):
the caller owns a port in its own vocabulary; a gateway in the caller's
`adapters/gateways` adapts the peer's `Client` to it; the composition root
constructs and injects the adapter. Synchronous calls are **fail-closed** — a
peer outage fails the use case honestly. → `gateway-cross-context.md`

**A cross-context READ** (a result composes data from two peers and belongs to
neither): it becomes **its own small bounded context, above both**, composing
their public `Client`s. Its domain owns the join/ordering semantics; its
adapters are optional (it reaches peers only through injected `Client`s); no
special "orchestrator" role exists — it has the same anatomy as its siblings.
The guardrails that keep this honest:
- A read that belongs to **one** peer stays *in* that peer — spawning a context
  is for composition that belongs to neither, not for every query.
- Putting the read *in* a peer would force a peer → peer import and close a
  cycle; putting it in a handler or host would leak domain semantics (the join
  *is* domain logic) into an adapter. The dependency direction — the new
  context reads both, nothing imports it — is what avoids the cycle.

**Cycle resolution.** Two contexts that import each other are not two contexts
(`strategic-design.md#bounded-contexts`). Break a would-be cycle by dependency
direction first (as above); hoist into a real orchestrating context **only when
it is a genuine cross-context workflow**; N-context cycles need events, not a
third service. **Never nil-then-setter** — passing `nil` and mutating later is
a wiring bug, not a cycle break.

## App vs library {#app-vs-library}

Which roles a context carries is decided by **application vs library**
(settled ruling):

- **domain + the public seam (`Client` + DTOs) — always required.** They define
  a context and key discovery.
- **application — required when the context has use cases.**
- **adapters — optional** (present where the context touches the outside).
- **wiring — required for app contexts, absent for library contexts.** A
  library ships the roles but no wiring and no hosts — the consumer supplies
  them; an app has `bootstrap` + `srv` too.

## The gap survey — the decomposition procedure

You arrive with a job ("hook up my database", "add an endpoint", "make these
two features talk"). Jobs are too many to catalog; decompose instead:

1. **Name the pieces the job touches.** Walk the anatomy above and list the
   components involved — which context(s), and within them which roles: a new
   domain type? a use case? a handler? a gateway? wiring? a host?
2. **Survey the codebase for which already exist.** Find the context by its
   `Client`; check each named piece against what is already there. What exists
   is the convention to follow — imitate before inventing.
3. **Build only the gap, each piece per its component doc.** Route by the table
   below; where a doc is a stub, note the gap and imitate the verified impl it
   names — don't invent a convention.

## Where each piece is taught

| Piece | Doc | Status |
|---|---|---|
| Value object | `value-objects.md` | full |
| Entity | `entities.md` | full |
| Aggregate | `aggregates.md` | full |
| Domain service | `domain-services.md` | stub (deliberately shallow) |
| Application service | `application-services.md` | full |
| Public interface (`Client` + DTOs) | `public-interface.md` | full |
| Handler | `handlers.md` | one-handler rule settled; rest stub |
| Gateway: repository | `repositories.md` | full |
| Gateway: cross-context | `gateway-cross-context.md` | core rules settled; rest stub |
| Gateway: vendor/ACL | — no file | gap: no verified impl anywhere |
| Context wiring | `wiring.md` | stub |
| bootstrap + app config + lifecycle | `bootstrap.md` | composition root full; config/lifecycle stub |
| srv hosts | `srv.md` | stub |
| Strategic design (subdomains, contexts, language) | `strategic-design.md` | full |
| Language mechanics | `go.md`, `python.md` | full for the domain + seam concepts |
