# Public interface

<!-- tb-status: full -->

A `Client` interface plus its DTOs, published at the component's top level — the
API you deliberately offer, **and nothing else**. Its purpose is to be a
**decoupling boundary**: it separates the contract callers depend on from how you
build the internals, so you can refactor the internals freely and the contract
holds. Concept authority: the public-interface-as-boundary and
dependency-direction discipline is the ported vero practice, genericized here; in
strategic-design terms the `Client` + DTOs are the contract a bounded context
exposes to its peers (`strategic-design.md#bounded-contexts`).

Where this seam sits in a context's anatomy — the top level of the context, above
`domain` / `application` / `adapters` / `wiring` — is `map.md`'s subject.

**Why an interface and not just a facade?** A package of exported functions over a
wired composition root — `func PlaceOrder(ctx, req) { return wire().PlaceOrder(ctx, req) }` —
is a real, lower-ceremony alternative, and it decouples callers from the backend
too: a backend swap does not touch them. What a facade gives up is
**substitutability**. Bound to a global, it cannot take a fake in a test or a
second implementation without editing the facade (or every caller). The `Client`
earns its place exactly there — callers *receive* it, so a test passes a fake and
a second implementation drops in at **zero** caller-side cost. Reach for the
interface when you need substitution (isolated tests, multiple implementations);
decoupling from a backend alone does not demand it.

> **The name.** Here `Client` means the public **face of this component** — the
> operations it offers a caller — not an outbound adapter to a remote service.
> The skill uses `Client` because the vero prior art does; read it as "the
> client-facing contract," and define the term this way wherever you introduce it.

**The callers.** The callers on the far side of this contract are other **bounded
contexts** — a component's public interface is the seam *between* contexts
(`strategic-design.md#bounded-contexts`). A peer reaches this contract through a
cross-context gateway of its own (`gateway-cross-context.md`); it never imports
what sits behind the seam.

## Is this what I'm building?

**Test:** *Am I defining the deliberately-exposed contract of a component — the
operations a caller may invoke and the DTOs they exchange — separate from how
those operations are implemented?* Yes → public interface.

**Near-misses that are NOT a public interface:**
- The **application service** (`application-services.md`) — that is the
  *implementation behind* the interface. The `Client` is the *contract*,
  satisfied by the service, but defined independently so you can reshape it
  without touching the service.
- A **DTO** on its own — data with no operations. The DTOs live *with* the
  `Client` (same package) but they are not it.
- A **repository interface** (`repositories.md`) — that is an *outbound port* the
  implementation needs (persistence), defined beside its consumer. The `Client`
  is the contract the component offers callers, facing the other way.

## Rules

1. **Declares signatures + DTOs, no implementation.** An interface is a behavior
   contract. "No implementation" — not "no behavior"; the behavior lives behind
   it, in the service the interface is satisfied by.
2. **It is a decoupling boundary — that is the whole point.** You may
   rename / subset / group / nest its methods, and compose several internal
   components behind it, independently of how those internals are built. The
   internals refactor freely; as long as the signatures and DTOs hold, nothing
   outside breaks.
3. **Satisfied by a struct that embeds the application service(s).** Embedding
   promotes the service's methods, so the common **single-service case needs
   zero forwarding code** — the struct satisfies the `Client` by promotion.
   Write explicit methods **only when you reshape** (rename, subset, nest, or
   union several components). This is the boundary earning its place, not a
   redundant wrapper.
4. **Speak DTOs at the boundary, never domain objects.** A `Client` method takes
   and returns DTOs — the same no-leak rule as an application service's *Respond*
   step (`application-services.md`), now made structural: a domain object in a
   `Client` signature is a boundary leak.
5. **Name it `Client`** (term defined above), and put it — with its DTOs — at the
   component's top level, its public package.

**Single-service now; multi-component later (footnote).** This file teaches the
`Client` satisfied by embedding **one** service. In a richer component the
`Client` composes several application pieces — a service plus a background
process, or several services — and the embedding struct unions them
(`struct { *OrderService; *OrderProcesses }`). Deferred; the single-service
shape is the whole of this cut.

## Shape

```
orders/                          ← public package: interface + DTOs only

type Client interface {
    PlaceOrder(ctx, PlaceOrderRequest) (PlaceOrderResponse, error)
    GetOrder(ctx, GetOrderRequest)     (GetOrderResponse, error)
}

type PlaceOrderRequest  struct { CustomerID string; Items []ItemInput }   // DTO: primitive-leaved
type PlaceOrderResponse struct { OrderID string; Total string }           // DTO: never a domain object
```

Construction mechanics — the embedding struct that satisfies it:
`go.md#the-composition-root`.

## Decisions you must make

1. **One component behind the `Client`, or several?** Single service (the common
   case): embed it — zero forwarding code. Reshaping the contract
   (rename / subset) or composing several pieces: write the explicit methods on
   the embedding struct. Never add a method that only forwards to the embedded
   service — embedding already promoted it.

## How the machine sees it

**No analyzer backs this.** A `Client` that leaks a domain object has no
structural signal `tessercheck` keys on today — it is caught by **review, not the
compiler** (a `tessercheck` no-leak analyzer on `Client` signatures is a candidate
future increment; the import-boundary side lives with the composition root,
`bootstrap.md#how-the-machine-sees-it`). The tells a reviewer looks for:
- a **domain type in a `Client` method signature** — a boundary leak;
- a **forwarding method that reshapes nothing** — embedding already promoted it;
- a **caller importing the impl package** instead of the public one — the seam
  is being reached around.

## Tests you must write

- **The `Client` speaks DTOs only:** a `Client` method returns a DTO, never a
  domain object. The compiler enforces that the impl matches the interface (it
  can't return an aggregate where the interface declares a DTO) — but that the
  *declared* return type is a DTO and not a domain object is the review call (see
  "How the machine sees it"); assert it with a test that reads the response's DTO
  fields.
- **The handler depends on the interface:** the handler is constructed with a
  `Client` and compiles against the public package, never the impl package
  (`handlers.md`).

## Common mistakes

- **The `Client` leaks a domain object.** A method returns `*Order` (an
  aggregate) instead of an `OrderResponse` DTO — the boundary is broken and
  callers couple to internals. Map to a DTO (the *Respond* step, made structural).
- **A forwarding wrapper.** Hand-writing
  `func (c *client) PlaceOrder(...) { return c.svc.PlaceOrder(...) }` when
  embedding would promote the method for free. Embed the service; write explicit
  methods only to *reshape* the contract.
- **A handler holding a concrete.** `handler{ svc *OrderService }` instead of
  `handler{ client orders.Client }`. Depend on the interface; the composition
  root injects it (`handlers.md`, `bootstrap.md`).

## Now build it

- Go: `go.md#the-composition-root` (the public package + the embedding struct)
- Python: `python.md#the-composition-root` — a `typing.Protocol` for the
  `Client` (satisfied structurally, no adapter code), backed by the
  `examples/python/` and `examples/python-app/` worked examples.
