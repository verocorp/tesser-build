# Domain service (stub)

<!-- tb-status: stub -->

> **Stub — read this first.** A domain service is the **rare** case, and it is
> the most-abused concept in DDD. Most logic that feels like it needs a "service"
> actually belongs on a *type*. This file is deliberately shallow: it gives you
> the one honest test and sends you back to look harder. It is **net-new
> guidance** (the vero corpus has no domain-service doctrine) and **unvalidated**
> in both Go and Python — treat it as a starting point, not settled convention.
> It deepens (mechanics, worked examples) only when real usage proves the need.
> Mechanics are not yet materialized; note the gap, don't invent a convention —
> there is no verified impl to imitate yet.

## Before you reach for a domain service

Almost every "I need a service for this" is misplaced domain logic that has an
owning type you haven't found yet. **Run the leakage / missing-type check
first** (`application-services.md#domain-logic-leakage-checks`): a for-loop over
domain objects, arithmetic on quantities, a conditional on domain state — each
of those belongs on a **domain type or method**:

- Behavior on one object's data → a **method on that object**.
- Behavior over a collection (sum, filter, group) → a **collection type** with
  that method, or a method on the aggregate that owns them.
- The same operation duplicated across callers → it belongs on the **producer's
  return type**, not scattered.

Exhaust those first. A named `SomethingService` in the domain layer is a
magnet: once it exists, agents move the fat service's logic one layer down into
it and call the result "domain-driven." That is the failure this stub exists to
prevent — especially in Python, where a loose module of functions is frictionless
to create.

## Is this what I'm building?

**Test:** *Is this a genuine domain operation that belongs to **no single
type** — it meaningfully involves two or more domain objects and forcing it onto
either one would distort that object?* Only then → domain service (Evans,
*Domain-Driven Design*, ch. 5).

The classic example is a transfer between two accounts: the operation is real
domain logic, but it isn't naturally "owned" by the source account or the
destination account. That is the rare shape a domain service fits.

**It is still NOT a domain service if:**
- One of the objects could reasonably own the behavior (put it there).
- It's coordination/orchestration (that's an **application service** — no domain
  logic).
- It's persistence (that's a **repository**).
- It's a calculation over one object's data (that's a **method**).

## Rules (provisional — stub)

1. **Stateless.** A domain service holds no state of its own; it operates on the
   domain objects passed to it and returns a domain result. If it's
   accumulating state, it's the wrong tool.
2. **Domain logic only, expressed in domain terms.** It takes and returns
   domain objects/value objects — never DTOs, never storage types. If it speaks
   request/response shapes, it's an application service.
3. **Named for the operation, in the ubiquitous language** — the concept the
   domain expert would name, not `XxxManager`/`XxxHelper`/`XxxService`-by-reflex.
4. **The last resort, not the first.** Reach for it only after the missing-type
   check above comes up empty.

## Now build it

Mechanics are **deliberately deferred** — there is no validated reference
implementation yet, and shipping a shallow `go.md#domain-services` /
`python.md#domain-services` skeleton would invite exactly the dumping-ground use
this stub warns against. When real usage (the pilot loop) shows agents genuinely
hitting the no-single-owner case, deepen this file with mechanics and worked
examples and add the language sections then. Until then: prove the type doesn't
exist first; if it truly doesn't, write a stateless function in the domain layer
that takes and returns domain objects, and flag it for review.
