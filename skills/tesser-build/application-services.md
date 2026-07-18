# Application service

<!-- tb-status: full -->

An application service is the **coordination layer** between a request and the
domain. It orchestrates a single use case — convert the request, drive the
domain, persist the result, shape the response — and holds **no business logic
of its own** (Vernon, *IDDD*, ch. 14). Every rule, every invariant, every
calculation lives in the domain objects it calls; the service only sequences
them. It is the thin waist a handler calls into and the only place a repository
is invoked.

## Is this what I'm building?

**Test:** *Am I coordinating one use case — taking a request, driving domain
objects, persisting, returning a result — without deciding any domain rule
myself?* Yes → application service.

**Near-misses that are NOT application services:**
- A **domain service** (`domain-services.md`) — domain logic that belongs to no
  single object. That *is* business logic; it lives in the domain layer and an
  application service *calls* it. If you're about to put a calculation in the
  service, stop — see the leakage checks below.
- A **transport handler** (HTTP/gRPC/CLI entry point) — parses the request,
  authenticates, calls the application service, writes the response. It holds no
  domain logic and no persistence either. One-line rule: **a handler
  parses/authenticates and calls the application service — through the
  component's public `Client` interface where one exists (`public-interface.md`),
  never a concrete it built itself; it never does domain math or touches a
  repository.** (Full guidance: `handlers.md` — the handler is where the leak
  starts.)
- A **DTO / request struct** — data crossing the boundary. It has no behavior.

## Rules

1. **No business logic in the service.** No domain calculation, no invariant
   decision, no branching on domain state. If it's a rule, it belongs on a
   domain object (a type, an aggregate transition, or a domain service). The
   leakage checks below are how you catch yourself breaking this.
2. **The four-step shape.** Every method reads as a short sequence of named
   steps, each one call:
   1. **Convert** — request DTO → domain input (a spec or value objects). Pure
      mapping, no rules.
   2. **Delegate** — the domain work. Exactly one of: *construct* a new
      aggregate from the spec; or *load* an existing aggregate and call its
      guarded method/transition; or call a *domain service*. Validation and
      invariants happen here, inside the domain, never in the service.
   3. **Persist** — hand the **whole aggregate** to the repository
      (`repositories.md`); the repo decomposes it. The service never extracts
      children.
   4. **Respond** — map the resulting domain object → a **response DTO**. A
      domain object never leaves the service; returning one is a boundary leak
      (the service-layer twin of a value object leaking its representation).
   Not every method uses all four (a pure command may skip Respond beyond an
   ack), but the order never changes and no step hides domain logic.
3. **Dependencies come in through the constructor.** The repository (and any
   domain service) is injected, never constructed inside. The service owns
   coordination, not wiring.
4. **One transaction boundary per use case.** The service decides *where* the
   unit of work begins and ends; it does not decide *what* is valid inside it.
   (In Python this is the session/unit-of-work lifetime — a consumer-specific
   decision; see `python.md#application-services`.)

## Shape

```
CreditService                       (holds an injected repository)
  - repo  JournalRepository          (dependency — an interface)

  RecordPayment(ctx, RecordPaymentRequest) → (RecordPaymentResponse, error)
    1. spec    := toPaymentSpec(req)              // Convert
    2. payment := domain.NewPayment(spec)         // Delegate (construct) …
       //  or:  acct := repo.Load(id); acct.Apply(x)   … or (load + transition)
    3. repo.Save(ctx, payment)                     // Persist (whole aggregate)
    4. return toResponse(payment), nil             // Respond (domain → DTO)
```

Construction mechanics: `go.md#application-services` /
`python.md#application-services`.

## Decisions you must make

1. **Construct or load?** A create use case *constructs* a new aggregate from
   the spec. A change use case *loads* the existing aggregate and calls its
   guarded transition (`order.AddLineItem(...)`), then saves. Both are the
   Delegate step — the difference is which one, never whether the service
   reaches inside the aggregate to mutate it. Poking an aggregate's fields from
   the service is the modify-time version of skipping the constructor.
2. **What does the response carry?** Map to a DTO that exposes only what the
   caller needs. Never return the domain object (leak) and never return a raw
   collection the caller must post-process (that's a missing domain type — see
   the leakage checks).
3. **Where's the transaction boundary?** One use case, one unit of work. If a
   method spans several aggregates, the boundary wraps them, but the
   consistency *rules* still live in each aggregate — the service does not
   reconcile them by hand.

## Where the response mapping lives — and the alternatives {#where-the-response-mapping-lives}

Respond is the *service's* job for a reason. The tempting shortcut is to put it on
the domain object — `func (m Maneuver) ToResponse() ManeuverResponse` — so any caller
can get the DTO straight off the aggregate. **Don't.** A domain object that emits its
own outward representation drags the wire shape into the domain: every read-side
dependent that reaches `m.ToResponse().SomeField` is bound to the wire format, so an
outward-format change (a renamed or retyped response field) fans out to *N* of them
instead of the one Respond site. (Measured: `rationale/changeability/nooutward` — the
domain-emitting arm pays N; the service-Respond arm pays 1.)

There is more than one *correct* way to get a value to a caller; pick by where the
caller starts:

- **Already holding the aggregate** (domain-side code, another domain method): read
  its **value objects** — `m.Burn()`, never a DTO. Right when you have the object and
  want domain behavior; routing through the service would be needless ceremony.
- **Starting from an id / a read endpoint** (wants a scalar or a projection, not the
  whole aggregate): a **query method on the application service** — or a thin
  projection over its `Client` — that returns just what the read needs. Lower ceremony
  than making the caller load the aggregate and walk its value-object graph; this is
  the CQRS read side (`repositories.md`), and it keeps mapping inside the service.

What does **not** work is the domain emitting the DTO to save one of the above: it
reads as a convenience and buys the N-way coupling. Both good patterns are the same
sanctioned mapper (Respond) reached from the two directions a caller actually arrives
from — the domain object's representation still never lives on the domain object.

## How the machine sees it

**No analyzer backs this in v2.** Unlike value objects, entities, and
aggregates, an application service has no structural signal `tessercheck` keys on;
its correctness is enforced by review, not the compiler. The leakage checks
below are a *future*-analyzer seed, not a live check — and even then only two of
the four grep cleanly. A `for`-loop over domain objects is not by itself a
violation: a repository legitimately loops to decompose an aggregate, and a
DTO→spec mapper legitimately loops over input. A real analyzer must know the
file's layer and the loop's intent before it flags. Treat the checks as a review
discipline a human applies, not a definition.

## Tests you must write

- **The service holds no logic:** a use-case test drives the happy path and
  asserts the domain object it produced is correct — but the *rules* are tested
  on the domain objects, not here. If you find yourself asserting a domain
  calculation against the service, the calculation is in the wrong place.
- **Rejection propagates:** an invalid request makes the domain constructor/
  transition error, and the service returns that error wrapped with context —
  it does not swallow or re-derive it.
- **Response is a DTO, not a domain object:** assert the returned type is the
  response DTO; a domain object escaping the service is a failure.
- **Change use cases load-then-transition:** the modify path loads, calls the
  aggregate's guarded transition, and saves — the service never sets a field.

## Common mistakes

### Domain-logic leakage checks {#domain-logic-leakage-checks}

**This is the canonical list of the leakage signals; other files reference this
anchor rather than restating it.** After writing a service method, scan for
these — each means domain logic has leaked into the coordination layer and
belongs on a domain type instead (route it via `domain-services.md` or a method
on the owning type — see "Recognizing a missing domain type"):

1. **A `for`-loop over domain objects** that computes a result (sum, filter,
   group). The iteration is domain behavior; it belongs on a domain collection
   type's method, not the service. (A loop mapping DTOs→specs is pure
   conversion — fine.)
2. **String manipulation on a domain identifier** (concatenating, parsing,
   slicing an ID). The identity type should own its formatting.
3. **Arithmetic on domain quantities** outside a conversion function
   (`total += line.Amount`). Money/measure math lives on the value object.
4. **A conditional on domain state** (`if order.status == ...`). The decision
   belongs behind a guarded method on the aggregate.

Signals 1–2 are grep-visible; 3–4 need to know what's a domain quantity/state,
so they are review-only. None is a bare grep — layer and intent matter (see
"How the machine sees it").

### Other named mistakes

- **The fat service.** Business logic accretes in the service until the domain
  is anemic. The leakage checks exist to catch this before it sets.
- **Extracting children before persisting.** `txn.Transfers()` then
  `repo.SaveTransfers(...)` — the service now knows the aggregate's internals.
  Pass the whole aggregate; the repo decomposes (`repositories.md`).
- **Returning the domain object.** Skipping the Respond step leaks the domain
  past its boundary; the caller can now depend on internals. Map to a DTO.
- **Reaching into the aggregate to modify it.** `order.status = closed` from the
  service instead of `order.Close()`. Load and call the guarded transition.

## Now build it

- Go: `go.md#application-services`, then `go.md#the-spec-pattern`
- Python: `python.md#application-services`, then `python.md#the-spec-pattern`
