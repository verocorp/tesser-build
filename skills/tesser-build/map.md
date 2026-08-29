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

**The tree declares itself.** A checkable app tree carries a `.tesser-root`
file at its root — that one file is what makes the directory a tessercheck
subject. The file has a total grammar — a first line `app`, then only
`skip <dir>`, `export <dir>`, `import <package>`, and `stdlib <module>` lines
(`kernels.md`; tree-specific configuration goes in this file, never in the
analyzer's code); anything else is a finding. A missing, unreadable, or wrong `.tesser-root`, or one
nested inside another tree, is a `TB044` finding; a symlinked directory
inside the tree is `TB045` (the walk never follows symlinks and must say what
it could not see). When one of these fires it is the only finding reported,
and no inline debt marker can silence it: the analyzer says what the directory is
(or isn't) before saying anything about its contents. When you create a
new app tree, the declaration file comes first. And everything is an app —
there is no library kind; a "library" is an app that does no IO but still
exposes a client and coordinates its domain through an application service.

**A bounded context has four roles — all present in an app context; internal
nesting and layout are free** (presence is required, organization is not
prescribed):

| Role | What it holds | Component docs |
|---|---|---|
| **domain** | VOs / entities / aggregates | `value-objects.md`, `entities.md`, `aggregates.md`, `domain-services.md` |
| **application** | use-case services (Convert → Delegate → Persist → Respond); no business logic — plus the **outbound ports the context owns**, in an `application/ports/` package (one port per module, with the request/response DTOs it speaks), and the domain ↔ port-DTO mapping | `application-services.md`, `repositories.md` |
| **adapters** | inbound `handlers` + outbound `gateways` (taxonomy below) | `handlers.md`, `repositories.md`, `gateway-cross-context.md` |
| **component** | the context's own construction + its `Config` | `component.md` |

The context's **`client` role is its public interface**: the `Client` interface +
primitive DTOs in `client.py` (or a `client/` package as it grows), with the
context's `__init__.py` empty (`public-interface.md`). There is no separate
"contract" role — the client role *is* the context's public face. A context is
**discovered by its public interface**: anything whose `client` module exposes a
`Client` is a context (the verified impl's discovery check keys on exactly this).

**App-level, not per-context** — three roles:

- **`app`** — the composition root: `new(cfg) → App`, builds the graph
  once (`app.md`).
- **`srv/`** — the hosts, one per *in-process* delivery mechanism; the host is
  the env edge and owns the process lifecycle (`srv.md`). A platform-required
  health/metrics listener is part of the host it reports on, not a second host.
- **`web/`** — the *out-of-process* presentation deployables (an SPA, an admin
  console, a native client): each a separately built, separately deployed
  frontend that reaches the app only over a host's API. The `srv/`↔`web/` split
  *is* the in-process↔out-of-process split. Anatomy and placement below
  (`#presentation`); no verified impl yet — doctrine, imitate when built.

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
- **Jobs (inbound, engine)** — where a durable-execution engine hands work
  back: a job calls an application client (a class of actions) or constructs
  an orchestrator over the invocation's job context. A handler calls the
  context client; a job never does. → `python.md#orchestrators-actions-jobs`
- **Gateways (outbound)** — satisfy a port the context owns, by reaching
  something outside it. The port and its DTOs live in the context's
  `application/ports/`; the gateway imports that ports module and **nothing
  else** from the context:
  - **repository** — the gateway to persistence → `repositories.md`
  - **cross-context** — the gateway to a peer context's `Client` →
    `gateway-cross-context.md`
  - **vendor/ACL** — the gateway to a model you *don't* own (a third-party SDK
    or schema). **No file and no verified impl exists yet** — note the gap,
    don't invent a convention. Anti-corruption is a *purpose* a gateway can
    have, not a separate role: it is built as port + adapter like any other.

Enforced layout (TB041/TB052): `adapters/handlers`, `adapters/gateways`,
`adapters/repositories`, and `adapters/jobs` are the adapter kind packages;
every adapters module lives in one and holds the kind its package names,
because the package is what carries the module's reach (TB060). Each
implementation module is named for its backing (`file_repository.py`,
`repo_memory.py`). **Events are not a new role**: publish = an outbound
gateway over an `EventPublisher` port; consume = an inbound handler plus a
worker host (`srv/wrk`). (The event shape is reasoned by symmetry with the
well-evidenced HTTP path — the prior art is thin here; treat it as the default
shape, not settled doctrine.)

## How contexts connect {#how-contexts-connect}

**Dependency direction is the load-bearing rule.** Within a context, adapters
and component depend inward on application and domain, never the reverse. Between
contexts, every edge points one way, and the graph stays acyclic:

```
srv/* hosts ──▶ handlers ──▶ Client ──▶ application ──▶ domain
app ──▶ each context's component          (constructs, never the reverse)
gateways ──implement──▶ ports in each context's application/ports
```

**Of `application`, an adapter reaches only the ports package** — alongside
peer `Client`s, and (for handlers only) the app shell's `protocol`: the
transport vocabulary is spoken by srv and handlers, never by a gateway or a
repository, which read `application/ports` and nothing else of the shell. That is what
moving the ports out of the service module bought: a gateway can no longer
import the service it exists to be decoupled from. Sibling adapters remain
importable, since every role may import itself, so the claim is about the
`application` seam and not about adapters in general (measured across seven
encodings in `docs/design-application-ports.md`).

Declare this, don't review it. The direction is a `forbidden` contract per edge
in import-linter — verified in-example at `examples/python-app/.importlinter`,
including the one config decision that matters: `allow_indirect_imports = true`,
because the default is transitive and a composition root legitimately reaches
every context. The same file holds the host to a context's `adapters.handlers`.

**A cross-context CALL** (one context needs a peer's answer, synchronously):
the caller owns a port in its own vocabulary, in its own
`application/ports/`; a gateway in the caller's
`adapters/gateways` adapts the peer's `Client` to it; the composition root
constructs and injects the adapter. Synchronous calls are **fail-closed** — a
peer outage fails the use case honestly. → `gateway-cross-context.md`

**A cross-context READ** (a result composes data from two peers and belongs to
neither): it becomes **its own small bounded context, above both**, composing
their public `Client`s. Its domain owns the join/ordering semantics; it needs
no *gateways* (it reaches peers only through injected `Client`s) but owns a
*handler* the moment a host serves it; no special "orchestrator" role exists —
it has the same anatomy as its siblings.
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
a component bug, not a cycle break.

## App vs library {#app-vs-library}

Which roles a context carries is decided by **application vs library**
(settled ruling):

- **domain + the public interface (`Client` + DTOs) — always required.** They define
  a context and key discovery.
- **application — required when the context has use cases.**
- **adapters — optional** (present where the context touches the outside).
- **component — required for app contexts, absent for library contexts.** A
  library ships the roles but no component and no hosts — the consumer supplies
  them; an app has `app` + `srv` too.

## Presentation — web and other out-of-process clients {#presentation}

A **presentation surface** — a web SPA, an admin console, an ops dashboard, a
marketing site, a native mobile app — is a *driving actor*, the same category as
a handler or a CLI: it sits to the left of the dependency arrow
(`#how-contexts-connect`) and the domain never knows it exists. "Presentation"
is a subset of the wider *inbound* category; being visual, or human-facing, is
architecturally irrelevant. The one decision that fixes where its code lives is
**in-process vs. out-of-process**:

- **Server-rendered HTML** (templates, htmx, form posts) runs *in* the app
  process, so it is an **inbound handler** — a `web.*` sibling of the JSON
  handler in a context's `adapters/handlers` (`handlers.md`). It renders from
  `Client` DTOs and never calls methods on domain objects (the presentation
  twin of "no outward representation"). It does **not** get a top-level dir; it
  is backend code and lives inside its context like any other handler.
- **A client-side app** (SPA, native, desktop) is a **separate deployable**:
  its own build, its own dependency graph, its own onion, reaching the app only
  over a host's API. It is **not in the app's dependency graph** — so it lives
  **app-level, at the top, never inside a context and never in Go `internal/`**.

**Where the out-of-process clients live.** They are an app-level role beside
`srv/`. One frontend → a flat `web/`. Several — `admin`, `ops`, `landingpage`,
`app` — → one per subdir under the grouping dir: `web/admin`, `web/ops`,
`web/landingpage`, `web/app`, each its own deployable. Don't build the grouping
dir for a single occupant (promoting `web/` → `web/<app>/` later is a rename);
do use it the moment a second frontend is real.

- **Serving a built bundle** (if the app hosts the static files itself) is a
  **`srv/` concern** — served either as routes on the existing HTTP host, or by
  its own static-file host in its own process, never a second long-running
  server folded into the API's process (`srv.md` rule 6). The frontend *source*
  lives in `web/<app>`; its compiled output is what a host serves.
- **A view that composes two contexts for one screen** is a **cross-context
  read**, so it is its own small context above both, not a fat frontend or a
  fat handler (`#how-contexts-connect`). A backend-for-frontend is that pattern
  wearing a UI-shaped name — reach for it only when one client needs a bespoke
  aggregate shape.
- **Monorepo vs. its own repo** is decided by shared API types and release
  cadence, not by this anatomy. When `web/` is a sibling of the backend in one
  repo the toolchains stay disjoint (Go/Python ignores `web/`, the JS build
  owns it); a broader `clients/` grouping is the generalization once a
  non-web deployable (an SDK, a bot) joins the web ones.

**Status: doctrine, no verified impl yet.** Unlike the rest of this map, no
`examples/` tree backs the `web/` shape — note the gap and imitate this section,
don't invent a variant. The totality guard already recognizes `web/` as an
app-level role (not a malformed, `Client`-less context).

## The gap survey — the decomposition procedure

You arrive with a job ("hook up my database", "add an endpoint", "make these
two features talk"). Jobs are too many to catalog; decompose instead:

1. **Name the pieces the job touches.** Walk the anatomy above and list the
   components involved — which context(s), and within them which roles: a new
   domain type? a use case? a handler? a gateway? component? a host?
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
| Handler | `handlers.md` | full |
| Outbound port (`application/ports/`) | `repositories.md#rules`, mechanics in `python.md#ports` | full (Python; Go mirror pending) |
| Gateway: repository | `repositories.md` | full |
| Gateway: cross-context | `gateway-cross-context.md` | core rules settled; rest stub |
| Gateway: vendor/ACL | — no file | gap: no verified impl anywhere |
| Context component | `component.md` | full |
| app + app config + lifecycle | `app.md` | full |
| srv hosts | `srv.md` | full |
| Presentation: web / out-of-process clients | `map.md#presentation` | doctrine only; no verified impl yet |
| Strategic design (subdomains, contexts, language) | `strategic-design.md` | full |
| Language mechanics | `go.md`, `python.md` | full for the domain + interface concepts; app-level anatomy mechanics (component/app/handlers/hosts) in `python.md` only — the Go mirror is pending |
