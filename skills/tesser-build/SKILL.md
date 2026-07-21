---
name: tesser-build
description: Application-construction entry point (DDD). Load whenever creating or modifying domain types OR the code around them — adding a field to a struct/class, creating a new type, modeling a new concept, writing a constructor, adding validation, comparing domain objects in tests, deciding between a value object/entity/aggregate, AND whenever writing a handler/endpoint, a use-case or application/domain service, or persistence/repository code (where to put business logic, how to load or save an aggregate, keeping domain math out of controllers), AND whenever wiring an application together — writing an entry point / `main` / composition root / host, exposing a component behind a public interface (a `Client` + DTOs), connecting two bounded contexts (a cross-context call or read), or placing a web UI / frontend / SPA (where presentation code lives), AND whenever reasoning about strategic design — subdomains, bounded contexts, or ubiquitous language. Routes the task through the decomposition procedure to the right component doc.
skill-version: 17
source: https://github.com/verocorp/tesser-build (skills/tesser-build/)
---

# Application construction — entry point

You are about to build or change a piece of an application. This skill routes
you to the right concept and the right construction mechanics. **Read only what
a route below points you to** — do not read all the files up front.

**Reasoning about boundaries, not building a piece?** Deciding where a **bounded
context** goes, whether two areas are one model or two, classifying a **subdomain**
(Core / Supporting / Generic), or naming the **ubiquitous language** is *strategic
design* — read `strategic-design.md`. The rest of this file routes the tactical
work that fills a boundary once it is drawn.

Languages covered: **Go** (`go.md`) and **Python** (`python.md`).
The anatomy — what the pieces of an application are and how they connect — is
`map.md`; each piece has its own component doc (listed there). Some component
docs are **stubs**: they carry a status note naming the verified implementation
to imitate — follow the note, don't invent a convention.

**Deliberately out of scope (static code only):** operational concerns — safe
change/migration sequencing, deploys, runbooks, production observability — are
deferred, not missing. **Named, thinner areas:** domain events (the event shape
in `map.md#adapters` is a symmetry default, not settled doctrine) and the
vendor/ACL gateway (no verified impl anywhere — note the gap, don't invent a
convention).

## The taxonomy in one pass

| Concept | One-question test | Read |
|---|---|---|
| **Value object** | Could I swap this instance for another with the same attributes and nothing would change? | `value-objects.md` |
| **Entity** | Does the system need to track *this specific one* by identity, even if another has identical attributes? | `entities.md` |
| **Aggregate** | Does this type enforce invariants across a group of objects it owns, as their single entry point? | `aggregates.md` |

Identity and consistency scope distinguish them — **not** mutability.

## Mode 1 — Decompose: "which pieces does this job need?"

Jobs are too many to catalog ("hook up my database", "add an endpoint", "make
these two features talk") — decompose instead. The full procedure and the
anatomy it walks are in `map.md`; the three steps:

1. **Name the pieces the job touches.** Which context(s), and within them which
   roles — domain, application, adapters (handlers/gateways), wiring, or the
   app-level bootstrap/srv (`map.md#the-anatomy`). For the *domain* pieces,
   work through the feature's nouns, rules, and use cases:
   - For each **noun**, run the taxonomy tests above, in order (value object →
     entity → aggregate). Most domain nouns are value objects; identity must be
     earned, not assumed.
   - For each **rule**, place it by what it's about: one value → the value
     object's constructor; one tracked thing → the entity; several owned
     objects → the aggregate root (constructor / guarded transition), never in
     callers; a genuine domain operation owned by **no single object** → a
     domain service (rare — `domain-services.md`; check for a missing type
     first). A rule spanning objects *not* owned by one root is a
     **cross-aggregate boundary** question — ask whether those objects even
     belong in the same context (`strategic-design.md#bounded-contexts`); if
     that isn't clear, flag it for a human.
   - For each **use case**, you need an **application service** to coordinate
     it (`application-services.md`), a **repository** for its load/save
     (`repositories.md`), and — if it is reachable from outside — a **handler**
     (`handlers.md`) behind the context's **`Client`** (`public-interface.md`).
2. **Survey the codebase for which pieces already exist.** Find the context by
   its `Client`; check each named piece against what is there. What exists is
   the convention to follow — imitate before inventing.
3. **Build only the gap**, each piece per its component doc (Mode 2).

**Behavior placement — "where does this line go?"** Most agent spaghetti is a
placement failure, not a mis-picked noun:
- parse/authenticate the request → **handler** (`handlers.md` — the one handler rule)
- orchestrate the use case → **application service**
- a rule about one object, or a set it owns → that **object / aggregate root**
- an operation owned by no single object → **domain service** (rare)
- load or save an aggregate → **repository**
- reach a peer context → **cross-context gateway** (`gateway-cross-context.md`)
- choose a concrete impl / build the object graph → **wiring / bootstrap**
- read the environment, exit the process → **host** (`srv.md`) — nowhere else
- computing a domain result (sum/decision) in a handler or service → it's
  misplaced; move it onto a domain type
  (`application-services.md#domain-logic-leakage-checks`)

## Mode 2 — Implement: "construct this piece per convention"

Route on the task:

| Your task | Do this |
|---|---|
| Understanding how the pieces of an app fit together, or where a new piece belongs | Read `map.md` — the anatomy, the adapter taxonomy, how contexts connect, app vs library |
| Deciding where a context boundary goes, whether two areas are one model or two, classifying a subdomain, or naming the domain language | Read `strategic-design.md` — subdomains (Core/Supporting/Generic), bounded contexts (own model, `Client` seam, integration patterns), ubiquitous language (one term, one meaning) |
| Modeling a brand-new concept | Run the taxonomy tests → read that concept file → then the language section it names |
| Adding a primitive-typed field (string/int/time/...) to a domain type | Read `value-objects.md#is-this-what-im-building` and run the **primitive-obsession check**. Wrap only if the value is domain-meaningful; then follow the spec-leaf + constructor rules in your language file |
| Adding a collection field (slice/map/list/dict) to a domain type | Read `aggregates.md#is-this-what-im-building` — re-evaluate whether the parent just became an aggregate |
| Adding a rule that spans two or more owned objects | Read `aggregates.md#rules` — the invariant lives in the root's constructor/transition, never in callers |
| Writing or changing a constructor | Read your language file: `go.md#the-spec-pattern` / `python.md#the-spec-pattern` |
| Needing mutation / a state transition | Read `entities.md#decisions-you-must-make` (fact vs lifecycle) before writing a setter |
| Comparing two domain objects in a test | Read `value-objects.md#tests-you-must-write` — never compare via `.String()`/`str()` |
| Writing a use-case / orchestration / a service method | Read `application-services.md` — the four-step shape (convert → delegate → persist → respond), no business logic |
| Writing a handler / endpoint / controller | Read `handlers.md` — the one handler rule: parse/auth → call the app service through the public `Client`, injected; no domain math, no repository |
| Loading or saving an aggregate, or writing a repository | Read `repositories.md` — whole aggregate in, reconstructed out, no business logic; query object ≠ spec |
| Making one context call or read another | Read `gateway-cross-context.md` (the caller owns the port; fail-closed) and `map.md#how-contexts-connect` (a read composing two peers becomes its own context) |
| Exposing a component/service behind a public interface (a `Client` + DTOs) | Read `public-interface.md` — a decoupling boundary, satisfied by embedding the service; speaks DTOs, never domain objects |
| Wiring a context's own construction / its config | Read `wiring.md` — coordinate-driven impl selection, config in the wiring, cross-context deps injected |
| Writing the app's composition root / `main` / app config / lifecycle | Read `bootstrap.md` — service-owned `new(cfg) → App`, builds the graph once, never reads the environment |
| Writing an entry point / server / CLI host, or reading the environment | Read `srv.md` — one host per delivery mechanism; the host is the env edge; only the edge exits |
| Placing a web UI / frontend / SPA / admin console — where presentation code lives | Read `map.md#presentation` — a driving actor at the edge; server-rendered HTML is an inbound handler, a client-side app is an app-level `web/<app>` deployable |
| Business logic that "wants" to live in a service or handler | Read `application-services.md#domain-logic-leakage-checks` — move it onto the owning domain type |
| Domain logic that fits no single object | Read `domain-services.md` — the rare case; confirm no missing type owns it first |
| Serializing a domain object — a repo row, a wire payload, a workflow-engine payload, or "how do I get the value out of this VO?" | Read `serialization.md` — domain objects never serialize themselves; leaf VOs have one canonical conversion exit; compounds/entities/aggregates decompose through the context's parts module (application layer); edges own their shape |
| Writing or changing a test — how to write it, what to assert, what a test double may be | Read `testing.md` — hand-written doubles only (never a mocking library), one completeness test per spec-constructed type, assert only what you set or what was computed, trust your layers |
| Tempted to write a comment or docstring | Read `comments.md` — v0 is zero (machine directives exempt); the explanation moves to a name, type, test, commit, or doc, never inline |
| Adding logging, or wanting a domain object to "print nicely" in a log | Read `logging.md` — a stub: don't invent a convention; `repr` is the interim debug surface (domain types define no display dunders) |
| Unsure after the tests | Read `value-objects.md` first — it defines the default; identity is the exception |

## Non-negotiables (all concepts, all languages)

1. **One validating constructor** is the only construction path.
2. **Private/protected fields**; accessors, no setters unless the concept has
   a declared lifecycle.
3. **Validation lives in the constructor** of the type that owns the value —
   parents never re-validate children.
4. **Display is not equality** — never compare domain objects by their string
   form.
5. **Tests are part of the object**: constructor rejection, equality
   semantics, and every invariant get tests when the type is born, not later.
6. **Dependencies point inward and one way** — adapters depend on the domain,
   contexts talk only through `Client`s, and the graph stays acyclic
   (`map.md#how-contexts-connect`).

Humans learning the why: see `docs/start-here.md` and `docs/faq.md` in the
source repo (or https://github.com/verocorp/tesser-build).
