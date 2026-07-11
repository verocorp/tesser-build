# Repository

A repository is the **persistence boundary** for an aggregate: it maps the
aggregate to and from storage and hides how that storage works (Evans,
*Domain-Driven Design*, ch. 6; Vernon, *IDDD*, ch. 12). It has exactly two jobs
— **save** an aggregate (decompose it into rows/documents) and **retrieve** one
(reconstruct it through its constructor). It holds **no business logic**: the
domain already enforced every invariant before the aggregate reached the repo.
The interface is defined in terms the domain speaks — whole aggregates and value
objects, never raw rows.

## Is this what I'm building?

**Test:** *Am I moving an aggregate between the domain and storage, without
deciding any domain rule?* Yes → repository.

**Near-misses that are NOT repositories:**
- A **domain service** or a method on an aggregate — anything that *computes* a
  domain result. A repo maps and reconstructs; it never calculates.
- A **query/read model** — a read that returns something other than a whole
  aggregate (a list of child projections, a summary row) for display. That is a
  legitimate *read concern*, and this file names it below, but it is not the
  aggregate write path and must not grow domain logic.
- An **application service** — it *calls* the repository; it is not one.

## Rules

1. **Save takes the whole aggregate; the repo decomposes it.** The caller passes
   the root (`repo.Save(ctx, order)`), never extracted children
   (`repo.SaveLineItems(ctx, order.Items())`). Flattening the aggregate into
   rows is a persistence concern and lives inside the repo, not in the service.
2. **Retrieve reconstructs through the constructor.** Reading rebuilds the
   aggregate by calling its constructor with a spec, so every invariant is
   re-established on the way out. Storage never hands back a half-built object
   with fields poked in directly.
3. **No business logic.** No invariant checks, no domain calculations, no
   domain decisions. If the repo is computing a total or deciding validity, that
   logic belongs on a domain type. The repo may **filter, order, and reconstruct
   as persistence mechanics** — but it must not *compute domain results*. That
   line is the whole rule: mapping and selection, yes; domain math, no.
4. **Speak domain types at the boundary.** Method signatures take and return
   aggregates and value objects; queries are typed structs of value objects, not
   loose strings. Raw storage types (rows, `sql.NullString`, ORM models) never
   cross the interface.
5. **The interface lives with its caller.** Define the repository interface in
   the package that uses it (the application service's package); concrete
   implementations satisfy it. The domain depends on the abstraction, never on a
   database.

## The read side — draw the line explicitly

certus's own repository does two things the write path doesn't, and conflating
them is how agents put query logic in repos:

- **Load an aggregate by identity** → returns the whole aggregate (or not
  found). This is the mirror of Save and the common case.
- **Query for a read result** → may return **child objects or a projection**
  (`[]Transfer`, a summary), and may **filter/order/select**. This is a read
  concern, named as such. It is allowed, but it is *persistence selection*, not
  domain computation — no summing, no rule evaluation, no branching on domain
  state inside the repo.

A **query object uses domain value objects** (`CustomerID`, `Period`) as its
fields — but it is **not a Spec**. Specs carry construction data with primitive
leaves (`value-objects.md` / the Spec pattern); query objects carry selection
criteria with domain-typed leaves. Keep them distinct: a spec builds a domain
object, a query selects stored ones. Don't put primitives in a query object and
don't put domain objects in a spec.

## Shape

```
OrderRepository                     (interface, defined in the service package)
  Save(ctx, Order) → error                          // whole aggregate in
  Load(ctx, OrderID) → (Order, error)               // reconstructed via constructor
  Find(ctx, OrderQuery) → ([]OrderSummary, error)   // read concern: projection out

OrderQuery                          (selection criteria — domain-typed, NOT a spec)
  - Customer CustomerID
  - Period   Period
```

Construction mechanics: `go.md#repositories` / `python.md#repositories`.

## Decisions you must make

1. **Aggregate load or read query?** If the caller will *change* the thing, load
   the whole aggregate so its transitions and invariants are available. If the
   caller only *displays* it, a read query returning a projection is fine — and
   cheaper — but it is read-only by contract.
2. **Where does decomposition live?** Always in the repo. If a service is
   flattening an aggregate before calling the repo, move that into the repo's
   Save. The service should not know the aggregate's internal shape.
3. **In-memory vs backed implementation.** Start with an in-memory
   implementation (a map keyed by identity) for tests and early use; a
   database-backed one satisfies the same interface later. Neither adds domain
   logic.

## How the machine sees it

**No analyzer backs this in v2.** A repository has no structural signal `ddd-vet`
keys on. The tell that logic has leaked into a repo — arithmetic on domain
quantities, a conditional on domain state, an invariant check — is the same
signal set as the application-service leakage checks
(`application-services.md#domain-logic-leakage-checks`), and it carries the same
caveat: a repo *legitimately* loops to decompose an aggregate or map rows, so a
bare "for-loop over domain objects" is not a violation here. Layer and intent
decide. Review, not the compiler.

## Tests you must write

- **Round-trip:** save an aggregate, load it back, assert it equals the original
  (by identity/value per the aggregate's rules) — reconstruction went through
  the constructor.
- **Whole-aggregate save:** the Save signature takes the root; a test that tries
  to save extracted children shouldn't type-check (or is absent by design).
- **No business logic:** there is no repo test that asserts a domain rule —
  because the repo enforces none. If you're writing one, the rule is in the
  wrong layer.
- **Query is read-only and typed:** a Find returns the projection type for a
  query of value objects; it never mutates and never computes a domain result.

## Common mistakes

- **Service extracts children before saving.** `order.Items()` then
  `repo.SaveItems(...)`. The service now depends on the aggregate's internals.
  Pass the whole aggregate; the repo decomposes.
- **Business logic in the repo.** Summing amounts, checking a balance, deciding
  validity during save/load. That's domain work — it belongs on a domain type
  (`application-services.md#domain-logic-leakage-checks`).
- **Raw strings in queries.** `Find(ctx, customerID string)`. Query fields are
  value objects (`CustomerID`), so the boundary stays type-safe and the repo
  can't be handed an unvalidated identifier.
- **Reconstructing by field-poking.** Building the aggregate by assigning
  fields instead of calling its constructor — the invariants are skipped and a
  stored-but-invalid aggregate comes back to life. Reconstruct via the
  constructor.
- **A query object that's really a spec (or vice versa).** Primitive leaves in a
  query, or domain objects in a spec. Keep selection criteria (domain-typed) and
  construction data (primitive-leaved) apart.

## Now build it

- Go: `go.md#repositories`
- Python: `python.md#repositories`
