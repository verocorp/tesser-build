# Entity

<!-- tb-status: full -->

An entity is a domain concept the system must track by **identity over time**:
*this specific one*, distinguishable from another instance with identical
attributes. Its attributes may change (or not); its identity persists through
its whole lifecycle (Evans, *Domain-Driven Design*, ch. 5; Vernon, *IDDD*,
ch. 5). A bank transfer is an entity: two transfers of the same amount between
the same accounts on the same day are still two different transfers.

## Is this what I'm building?

**Test:** *Does the system need to distinguish this instance from another with
identical attributes but a different ID?* Yes → entity. No → it's a value
object; **identity must be earned, not assumed**.

**Near-misses that are NOT entities:**
- A **value object that wraps an ID** (`CustomerID`, `OrderID`) — it *is* the
  identity of something else; it has no identity of its own.
- A **DTO/row with an `id` column** — storage rows have primary keys for the
  database's sake; that alone doesn't make the concept an entity in the
  domain. Ask the test question about the *concept*, not the table.
- An **aggregate root** — every root is an entity, but if it also owns a
  cluster and enforces rules across it, read `aggregates.md` instead; the
  stricter rules apply.
- A **value with a uniqueness constraint** — a field the domain requires to be
  unique within a scope (a receipt number unique within a report, a coupon code
  unique within a campaign). **Uniqueness is not identity.** It is a business
  rule the owning **aggregate** enforces (`aggregates.md` — a cross-object
  invariant: "no two members share this value"), implemented in the domain; it
  does not, on its own, mean the system tracks *this specific one* through a
  lifecycle. Run the identity test on the concept itself: no lifecycle and
  interchangeable with an attribute-identical instance ⇒ **value object** whose
  uniqueness the aggregate guards, even though it "has a unique field." (A unique
  field *may* serve as an entity's natural-key ID — but only once the identity
  test is independently met, never because it is unique.)

## Rules

1. **Identity is explicit and immutable.** An ID field, assigned at creation,
   never reassigned. The ID itself is a value object, not a raw string.
2. **Fields are value objects, never raw primitives.** The entity composes
   validated values; it does not re-validate them (that's the values' job).
3. **Private fields, public accessors.** Same representation discipline as
   value objects.
4. **One validating constructor**, taking a spec, is the only construction
   path. It builds each child value object and wraps its error with context.
5. **Mutability is a domain decision, not a default** — see the decision
   below. Either way, every state change preserves the entity's invariants.
6. **Equality is identity.** Two entities are "the same" iff same ID — never
   by attribute comparison, and never by string form.

## Shape

```
Transfer
  - id       TransferID     (identity — value object)
  - from     AccountRef     (value object)
  - to       AccountRef     (value object)
  - amount   Money          (value object)

  NewTransfer(TransferSpec) → (Transfer, error)
```

Construction mechanics: `go.md#entities` / `python.md#entities`.

## Decisions you must make

1. **Fact or lifecycle?** Ask: *does this represent a fact that happened, or a
   thing with a lifecycle?*
   - **Fact that happened** (a posted transfer, a recorded measurement) →
     immutable entity: value semantics, state changes return new instances.
     Append-only domains (accounting, event logs) live here.
   - **Thing with a lifecycle** (a contract: draft → active → cancelled) →
     mutable entity: the type exposes transition methods that guard state and
     enforce invariants after each change. Don't force immutability where the
     domain doesn't call for it — and don't add setters where it does.
2. **Guard style for transitions** (mutable case): two states → a guard clause
   in the transition method is fine; more states → prefer a transition table
   or state pattern over stacked conditionals.

## How the machine sees it

Strongest signal first: **identity** — an `ID()` method or a field named
`id`/`ID`/`<Type>ID`; then **mutability** — a pointer-receiver/instance method
assigning to a field; then owned domain collections (which point at
*aggregate* — see that file). These heuristics flag the type for the
human-ratified exclude list so value-object analyzers skip it. They are
indicators, not the definition — ratify, don't assume.

## Tests you must write

- **Constructor rejection:** each invalid spec leaf produces a wrapped,
  contextful error.
- **Identity semantics:** same ID ⇒ same entity (regardless of other
  attributes); different ID ⇒ different entity.
- **Transition guards** (mutable case): each illegal transition errors and
  leaves state unchanged; each legal transition lands with invariants intact.
- **Immutability** (fact case): a state-changing method returns a new
  instance; the original is untouched.

## Common mistakes

- **Assuming identity:** reaching for an entity because the concept feels
  important. Importance isn't identity; run the test.
- **Primitive fields:** `customer string` instead of `customer CustomerID`.
  The entity becomes the validation dumping ground for every field.
- **Attribute equality:** comparing entities field-by-field in domain logic.
  Same ID is same entity; attribute comparison belongs to value objects.
- **Setters by reflex:** public setters on a fact-type entity, or "just one
  setter" that bypasses the transition guards on a lifecycle entity.

## Now build it

- Go: `go.md#entities`, then `go.md#the-spec-pattern`
- Python: `python.md#entities`, then `python.md#the-spec-pattern`
