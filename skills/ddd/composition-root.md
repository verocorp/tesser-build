# Wiring the application — the public interface + the composition root

Two concepts that complete the arc **domain (v1) → application services +
repositories (v2) → wire it together (v3)**. The **public interface** is the
contract a component exposes; the **composition root** is the single place that
constructs the concrete pieces, composes them behind that contract, and hands it
to a handler. Concept authority: the composition root is Mark Seemann's term
(*Dependency Injection*, ch. 4) for the one place an application wires its object
graph; the public-interface-as-boundary and dependency-direction discipline is
the ported vero practice, genericized here.

This file teaches **wiring**, not the full run/lifecycle. Config loading,
connection-pool lifecycle, graceful shutdown, health checks, and background
workers are a later increment — named here, not taught.

---

## The public interface

A `Client` interface plus its DTOs, published in a package that exposes the API
you deliberately offer — **and nothing else**. Its purpose is to be a
**decoupling boundary**: it separates the contract callers depend on from how you
build the internals, so you can refactor the internals freely and the contract
holds.

> **The name.** Here `Client` means the public **face of this component** — the
> operations it offers a caller — not an outbound adapter to a remote service.
> The skill uses `Client` because the vero prior art does; read it as "the
> client-facing contract," and define the term this way wherever you introduce it.

**The callers, in a fuller treatment (footnote).** The *callers* on the far side
of this contract are, in a fuller treatment, other **bounded contexts** — a
component's public interface is the seam between contexts. Named here, not
introduced; bounded contexts are a later increment.

### Is this a public interface?

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
- A **repository interface** (`repositories.md`) — that is an *inbound*
  dependency the implementation needs (persistence), defined in the impl's
  package. The `Client` is the *outbound* contract the component offers callers.

### Rules

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
5. **Name it `Client`** (term defined above), and put it — with its DTOs — in the
   component's public package.

**Single-service now; multi-component later (footnote).** v3 teaches the `Client`
satisfied by embedding **one** service. In a richer component the `Client`
composes several application pieces — a service plus a background process, or
several services — and the embedding struct unions them
(`struct { *OrderService; *OrderProcesses }`). Deferred; the single-service
shape is the whole of this cut.

### Shape

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

---

## The composition root

The single place that wires the app. It **constructs** the concrete services and
repositories, **composes** them to satisfy the public `Client`, **constructs the
handler, and injects the `Client` into it**. Seemann's canonical name; it is what
the vero prior art calls `init` / `registry`.

### Is this a composition root?

**Test:** *Am I in the one place that chooses concrete implementations and wires
them together — the entry point, not a service and not a handler?* Yes →
composition root.

**Near-misses that are NOT a composition root:**
- An **application service** — coordinates a use case; it *receives* its
  repository injected, it does not choose which one.
- A **handler** — *receives* the `Client` injected; it constructs nothing.
- A **repository / adapter constructor** (`New*`) — builds *one* concrete. The
  composition root *calls* these; it owns the **choice** of which to wire in, not
  every construction in the program.

### Rules

1. **Returns / injects public interfaces, never raw domain objects.** This is a
   *boundary* rule: what crosses **out** of the composition root is the `Client`
   (and its DTOs), never an aggregate or value object. Inside the
   implementation, richer domain types are correct — the rule is about what
   leaves.
2. **The only place that CHOOSES the concrete implementation.** Not "no `New*`
   anywhere else" — repositories, fakes, and adapters have their own
   constructors. The composition root owns *which* one the app wires in;
   swapping a database repo for an in-memory one is a **one-site** change, here.
3. **Constructs the handler and injects the `Client`.** The handler *receives*
   its dependency through its constructor; it does **not** reach into the root to
   "obtain" it (that is service-locator). The handler depends on `Client`, never
   on a concrete type.
4. **Keep the reasoning — the *why* is the product.** One wiring site, no domain
   leak past the boundary, contract decoupled from build. Those three are what
   the layer buys; a composition root that abandons them is just a `main` with
   the imports in one file.

### Shape

```
main.go                          ← the composition root

func main() {
    db     := openDB()                          // the impl choice lives here …
    repo   := ordersimpl.NewPostgresRepo(db)    // … and ONLY here
    svc    := ordersimpl.NewOrderService(repo)
    client := ordersimpl.NewClient(svc)         // embedding struct → satisfies orders.Client
    handler := api.NewHandler(client)           // construct handler, INJECT the Client
    http.ListenAndServe(":8080", handler)       // a minimal runnable main
}
```

The impl-selection line (`NewPostgresRepo` vs an in-memory repo) is the only
place that changes when you swap infrastructure. Construction mechanics:
`go.md#the-composition-root`.

---

## Decisions you must make

1. **One component behind the `Client`, or several?** Single service (the v3
   case): embed it — zero forwarding code. Reshaping the contract
   (rename / subset) or composing several pieces: write the explicit methods on
   the embedding struct. Never add a method that only forwards to the embedded
   service — embedding already promoted it.
2. **Which implementation does the root choose?** The composition root is where
   an in-memory repository (tests, early use) or a database-backed one gets
   selected — both satisfy the **same v2 repository interface**, so the choice is
   local and cheap. (In-memory is **not doctrine** — it is just an example
   implementation of the v2 interface; the root chooses it, and a test can
   substitute its own *because* the repository is an interface, not because of
   any new v3 rule.)
3. **Convention, or compiler-enforced?** "Only the composition root imports the
   concretes" is a **convention** in this cut. Go's `internal/` directory makes
   it compiler-enforced — a package under `internal/` cannot be imported from
   outside its parent. That is a later addition (footnoted, not required here);
   without it the boundary is a discipline review upholds, not a guarantee.

## How the machine sees it

**No analyzer backs this.** Neither the public interface nor the composition root
has a structural signal `ddd-vet` keys on today — a `Client` that returns a
domain object, or a second site that constructs a concrete to choose an impl, is
caught by **review, not the compiler**. Two enforcement upgrades are named, not
built: `internal/` would make the import boundary compiler-enforced, and a
`ddd-vet` no-leak analyzer on `Client` signatures is a candidate future
increment. The tells a reviewer looks for:
- a **domain type in a `Client` method signature** — a boundary leak;
- a **`New<concrete>` call outside the composition root** that selects an impl —
  scattered wiring;
- a **handler holding a concrete field** instead of `Client` — coupling to
  internals.

As with the v2 seams, layer and intent decide; a `New*` inside the root is
correct, the same call in a handler is the leak.

## Tests you must write

- **The `Client` speaks DTOs only:** a `Client` method returns a DTO, never a
  domain object. The compiler enforces that the impl matches the interface (it
  can't return an aggregate where the interface declares a DTO) — but that the
  *declared* return type is a DTO and not a domain object is the review call (see
  "How the machine sees it"); assert it with a test that reads the response's DTO
  fields.
- **The composition root wires end-to-end:** build the `Client` through the root,
  call a method, assert the result — the object graph is connected and a real use
  case runs through it.
- **A test substitutes its own repository:** the root (or the test) wires a fake
  repository that satisfies the v2 interface, and the use case runs against it.
  This demonstrates the wiring point — framed as "a test provides its own repo
  impl" (v2's repository-is-an-interface), **not** as an in-memory-vs-real
  doctrine.
- **The handler depends on the interface:** the handler is constructed with a
  `Client` and compiles against the public package, never the impl package.

## Common mistakes

- **The handler holds a concrete.** `handler{ svc *OrderService }` instead of
  `handler{ client orders.Client }`. Depend on the interface; the root injects it.
- **The `Client` leaks a domain object.** A method returns `*Order` (an
  aggregate) instead of an `OrderResponse` DTO — the boundary is broken and
  callers couple to internals. Map to a DTO (the *Respond* step, made structural).
- **Wiring scattered across the app.** A service or handler calls
  `NewPostgresRepo(...)` to build its own dependency. The **choice** of impl
  belongs in the composition root; everything else receives it injected.
- **A service-locator handler.** The handler reaches into the root to "obtain"
  the `Client`. Inject it through the handler's constructor instead — the
  dependency is *pushed in*, not *pulled out*.
- **A forwarding wrapper.** Hand-writing
  `func (c *client) PlaceOrder(...) { return c.svc.PlaceOrder(...) }` when
  embedding would promote the method for free. Embed the service; write explicit
  methods only to *reshape* the contract.

## Now build it

- Go: `go.md#the-composition-root`
- Python: `python.md#the-composition-root` — a `typing.Protocol` for the
  `Client` (satisfied structurally, no adapter code), hand-wired construction in
  a `main`/entry module, backed by the `examples/python/` worked example.
