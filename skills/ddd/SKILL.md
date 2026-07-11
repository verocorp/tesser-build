---
name: ddd
description: Domain-driven design entry point. Load whenever creating or modifying domain types — adding a field to a struct/class, creating a new type, modeling a new concept, writing a constructor, adding validation, comparing domain objects in tests, or deciding between a value object, entity, or aggregate. Routes the task to the right concept and construction guide.
skill-version: 1
source: https://github.com/verocorp/go-ddd (skills/ddd/)
---

# DDD — Domain Modeling Entry Point

You are about to create or change a domain type. This skill routes you to the
right concept and the right construction mechanics. **Read only what a route
below points you to** — do not read all the files up front.

Languages covered: **Go** (`go.md`) and **Python** (`python.md`).
Concepts covered in v1: **value objects, entities, aggregates**. (Application
services, domain services, repositories, and bounded contexts are coming;
if your task needs one of those, model the domain objects it touches with
this skill and note the gap rather than inventing a convention.)

## The taxonomy in one pass

| Concept | One-question test | Read |
|---|---|---|
| **Value object** | Could I swap this instance for another with the same attributes and nothing would change? | `value-objects.md` |
| **Entity** | Does the system need to track *this specific one* by identity, even if another has identical attributes? | `entities.md` |
| **Aggregate** | Does this type enforce invariants across a group of objects it owns, as their single entry point? | `aggregates.md` |

Identity and consistency scope distinguish them — **not** mutability.

## Mode 1 — Architect: "which building blocks does this feature need?"

Work top-down through the feature's nouns and rules:

1. For each **noun** the feature introduces, run the taxonomy tests above,
   in order (value object → entity → aggregate). Most domain nouns are value
   objects; identity must be earned, not assumed.
2. For each **rule** the feature introduces, place it: a rule about one
   value → the value object's constructor; a rule about one tracked thing →
   the entity; a rule spanning several owned objects → the aggregate root's
   constructor (never in callers).
3. If a noun's rules span objects that *aren't* owned by one root, that's a
   boundary question — v1 of this skill can't settle it; flag it for a human
   rather than forcing an aggregate.
4. Then switch to Mode 2 for each piece.

## Mode 2 — Implement: "construct this piece per convention"

Route on the task:

| Your task | Do this |
|---|---|
| Modeling a brand-new concept | Run the taxonomy tests → read that concept file → then the language section it names |
| Adding a primitive-typed field (string/int/time/...) to a domain type | Read `value-objects.md#is-this-what-im-building` and run the **primitive-obsession check**. Wrap only if the value is domain-meaningful; then follow the spec-leaf + constructor rules in your language file |
| Adding a collection field (slice/map/list/dict) to a domain type | Read `aggregates.md#is-this-what-im-building` — re-evaluate whether the parent just became an aggregate |
| Adding a rule that spans two or more owned objects | Read `aggregates.md#rules` — the invariant lives in the root's constructor/transition, never in callers |
| Writing or changing a constructor | Read your language file: `go.md#the-spec-pattern` / `python.md#the-spec-pattern` |
| Needing mutation / a state transition | Read `entities.md#decisions-you-must-make` (fact vs lifecycle) before writing a setter |
| Comparing two domain objects in a test | Read `value-objects.md#tests-you-must-write` — never compare via `.String()`/`str()` |
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
