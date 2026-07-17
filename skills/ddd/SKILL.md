---
name: ddd
description: Domain-driven design entry point. Load whenever creating or modifying domain types OR the code around them — adding a field to a struct/class, creating a new type, modeling a new concept, writing a constructor, adding validation, comparing domain objects in tests, deciding between a value object/entity/aggregate, AND whenever writing a handler/endpoint, a use-case or application/domain service, or persistence/repository code (where to put business logic, how to load or save an aggregate, keeping domain math out of controllers), AND whenever wiring an application together — writing an entry point / `main` / composition root, or exposing a component behind a public interface (a `Client` + DTOs), AND whenever reasoning about strategic design — subdomains, bounded contexts, or ubiquitous language (where to draw a model boundary, whether two areas are one model or two, what to name the domain language). Routes the task to the right concept and construction guide.
skill-version: 7
source: https://github.com/verocorp/go-ddd (skills/ddd/)
---

# DDD — Domain Modeling Entry Point

You are about to create or change a domain type. This skill routes you to the
right concept and the right construction mechanics. **Read only what a route
below points you to** — do not read all the files up front.

**Reasoning about boundaries, not building a type?** Deciding where a **bounded
context** goes, whether two areas are one model or two, classifying a **subdomain**
(Core / Supporting / Generic), or naming the **ubiquitous language** is *strategic
design* — read `strategic-design.md`. The rest of this file is the tactical building
blocks that fill a boundary once it is drawn.

Languages covered: **Go** (`go.md`) and **Python** (`python.md`).
Concepts covered: **value objects, entities, aggregates** (the domain building
blocks), **application services, repositories** (the seams around them), the
**public interface + composition root** (how the app is wired together —
`composition-root.md`), a **domain-service stub** (`domain-services.md` — the rare
no-single-owner case, deliberately shallow), and **strategic design** — subdomains,
bounded contexts, ubiquitous language (`strategic-design.md` — where model boundaries
go and what language holds inside them). Not yet covered: the transport/HTTP layer
beyond the one handler rule below, domain events, the run/lifecycle layer beyond
wiring (config, pools, shutdown, health, workers), and context *mapping* beyond the
integration-pattern names in `strategic-design.md`. If your task needs one of those,
model the pieces it touches with this skill and note the gap rather than inventing a
convention.

**The one handler rule (transport layer, until it gets its own guide):** a
handler/endpoint parses and authenticates the request, then calls an application
service **through the component's public `Client` interface**
(`composition-root.md`) where one exists — depending on that contract, never a
concrete service or repository it constructed itself. It does **no domain math and touches no repository** — if you're writing
a `for`-loop over domain objects or a DB call in a handler, that logic belongs in
the application service or the domain (see the placement guide below).

## The taxonomy in one pass

| Concept | One-question test | Read |
|---|---|---|
| **Value object** | Could I swap this instance for another with the same attributes and nothing would change? | `value-objects.md` |
| **Entity** | Does the system need to track *this specific one* by identity, even if another has identical attributes? | `entities.md` |
| **Aggregate** | Does this type enforce invariants across a group of objects it owns, as their single entry point? | `aggregates.md` |

Identity and consistency scope distinguish them — **not** mutability.

## Mode 1 — Architect: "which building blocks does this feature need?"

Work top-down through the feature's nouns, rules, **and where each line of
behavior goes** — most agent spaghetti is a placement failure (domain math in a
handler, persistence in the domain, a fat service over an anemic domain), not a
mis-picked noun.

1. For each **noun** the feature introduces, run the taxonomy tests above,
   in order (value object → entity → aggregate). Most domain nouns are value
   objects; identity must be earned, not assumed.
2. For each **rule**, place it by what it's about: one value → the value
   object's constructor; one tracked thing → the entity; several owned objects
   → the aggregate root (constructor / guarded transition), never in callers; a
   genuine domain operation owned by **no single object** → a domain service
   (rare — `domain-services.md`; check for a missing type first).
3. For each **use case** the feature handles, you need an **application
   service** to coordinate it (`application-services.md`): convert → delegate →
   persist → respond, with **no business logic**. Its load/save goes through a
   **repository** (`repositories.md`): whole aggregate in, reconstructed out.
4. **Behavior placement — "where does this line go?"**
   - parse/authenticate the request → **handler** (thin; the one handler rule)
   - orchestrate the use case → **application service**
   - a rule about one object, or a set it owns → that **object / aggregate root**
   - an operation owned by no single object → **domain service** (rare)
   - load or save an aggregate → **repository**
   - computing a domain result (sum/decision) anywhere in a handler or service →
     it's misplaced; move it onto a domain type
     (`application-services.md#domain-logic-leakage-checks`)
5. A rule spanning objects that *aren't* owned by one root is a **cross-aggregate
   boundary** question — before forcing a god-aggregate, ask whether those objects
   even belong in the same context (`strategic-design.md#bounded-contexts`); if that
   isn't clear, flag it for a human.
6. Then switch to Mode 2 for each piece.

## Mode 2 — Implement: "construct this piece per convention"

Route on the task:

| Your task | Do this |
|---|---|
| Deciding where a context boundary goes, whether two areas are one model or two, classifying a subdomain, or naming the domain language | Read `strategic-design.md` — subdomains (Core/Supporting/Generic), bounded contexts (own model, `Client` seam, integration patterns), ubiquitous language (one term, one meaning) |
| Modeling a brand-new concept | Run the taxonomy tests → read that concept file → then the language section it names |
| Adding a primitive-typed field (string/int/time/...) to a domain type | Read `value-objects.md#is-this-what-im-building` and run the **primitive-obsession check**. Wrap only if the value is domain-meaningful; then follow the spec-leaf + constructor rules in your language file |
| Adding a collection field (slice/map/list/dict) to a domain type | Read `aggregates.md#is-this-what-im-building` — re-evaluate whether the parent just became an aggregate |
| Adding a rule that spans two or more owned objects | Read `aggregates.md#rules` — the invariant lives in the root's constructor/transition, never in callers |
| Writing or changing a constructor | Read your language file: `go.md#the-spec-pattern` / `python.md#the-spec-pattern` |
| Needing mutation / a state transition | Read `entities.md#decisions-you-must-make` (fact vs lifecycle) before writing a setter |
| Comparing two domain objects in a test | Read `value-objects.md#tests-you-must-write` — never compare via `.String()`/`str()` |
| Writing a use-case / orchestration / a service method | Read `application-services.md` — the four-step shape (convert → delegate → persist → respond), no business logic |
| Writing a handler / endpoint / controller | Read `application-services.md#is-this-what-im-building` (keep domain math and repositories out) **and `composition-root.md#the-public-interface`** — depend on the component's public `Client`, injected; never a concrete service or repository |
| Loading or saving an aggregate, or writing a repository | Read `repositories.md` — whole aggregate in, reconstructed out, no business logic; query object ≠ spec |
| Exposing a component/service behind a public interface (a `Client` + DTOs) | Read `composition-root.md#the-public-interface` — a decoupling boundary, satisfied by embedding the service; speaks DTOs, never domain objects |
| Wiring the app / writing an entry point / `main` / a composition root | Read `composition-root.md#the-composition-root` — the one place that chooses the concrete impls, composes them behind the `Client`, and injects it into the handler |
| Business logic that "wants" to live in a service or handler | Read `application-services.md#domain-logic-leakage-checks` — move it onto the owning domain type |
| Domain logic that fits no single object | Read `domain-services.md` — the rare case; confirm no missing type owns it first |
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

Humans learning the why: see `docs/start-here.md` and `docs/faq.md` in the
source repo (or https://github.com/verocorp/go-ddd).
