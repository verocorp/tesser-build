# Aggregate

An aggregate is a **consistency boundary**: a cluster of objects that must
change together under rules that span them, with one root entity as the only
entry point. Outside code holds a reference to the root and nothing inside;
every modification goes through the root so it can enforce the cluster's
invariants (Evans, *Domain-Driven Design*, ch. 6; Vernon, *IDDD*, ch. 10). An
accounting operation is an aggregate: its transfers must balance — debits
equal credits — and only the operation can guarantee that.

**The boundary is the definition — not the collection.** Many aggregates own
child collections, but an aggregate with no collection is still an aggregate
if it guards a multi-object invariant; and an entity owning a convenience list
is not an aggregate root if no rule spans the items.

## Is this what I'm building?

**Test:** *Does this type enforce invariants across a group of related objects,
as their single entry point?* Yes → aggregate.

**When adding a collection field to an entity, re-run this test.** The moment
a rule spans the items ("the lines must sum to the total", "no two windows may
overlap", "no two line items share a SKU"), the parent has become an aggregate
root and takes on the rules below. A **uniqueness constraint** ("no two members
share this value") is one such cross-object invariant — it lives on the root,
and it does *not* make the constrained child an entity (`entities.md`). If no rule spans them, it's an entity holding a list — don't pay the
aggregate tax.

**Near-misses that are NOT aggregates:**
- An **entity with a convenience collection** and no cross-item rule.
- A **collection value object** (a validated set of labels) — it has
  collection behavior but no identity and no child entities.
- A **service-layer bundle** (a struct grouping things for one request) —
  that's transport, not a consistency boundary.

## Rules

1. **The root is the only door.** Nothing outside the aggregate holds or
   mutates its children directly; external references are to the root only.
2. **Cross-object invariants are enforced in the root's constructor** — and,
   for mutable aggregates, re-established after every transition. Callers
   never carry the invariant.
3. **Own your children.** The aggregate's collections are its internals:
   accessors return **defensive copies**, never the backing collection.
4. **Block accidental equality.** An aggregate is not a value; comparing two
   aggregates with native equality is a bug. Make the type non-comparable
   where the language allows and give it identity-based equality only.
5. **Mutability is a domain decision** (same fact-vs-lifecycle test as
   entities). Fact aggregates return new instances from state changes;
   lifecycle aggregates expose root-guarded transitions.
6. **Keep it small.** An aggregate is as small as its true invariant allows —
   objects with no shared rule belong outside it. Rules that span *other*
   aggregates are coordinated above (eventually via domain events), not by
   inflating the boundary.

## Shape

```
Operation                          (root — an entity)
  - id         OperationID          (identity — value object)
  - transfers  [Transfer, ...]      (owned children — entities)
  - (non-comparable marker)

  NewOperation(OperationSpec) → (Operation, error)   // enforces: debits == credits
```

Construction mechanics: `go.md#aggregates` / `python.md#aggregates`.

## Decisions you must make

1. **Where's the boundary?** List the rules the feature introduces. Each rule
   that spans several objects must live inside exactly one root that owns all
   of them. If a rule spans objects that can't share one root, do NOT force a
   god-aggregate — flag the boundary question for a human (v1 of this skill
   doesn't settle cross-aggregate design).
2. **Fact or lifecycle?** Same decision as entities, applied to the whole
   cluster. A posted operation is a fact (immutable, state changes return new
   instances); an open order is a lifecycle (root-guarded transitions like
   `AddLineItem` that re-check invariants).

## How the machine sees it

The aggregate-shaped signals: an **owned domain collection** (slice/map/list
of a named domain type), plus the entity signals (identity; mutation methods).
These flag the type for the human-ratified exclude list so value-object
analyzers skip it. Heuristics, not definitions — a collection-free aggregate
won't match the collection signal and still belongs on the list; ratify with
judgment.

## Tests you must write

- **Invariant holds:** a valid spec constructs; the invariant is visibly true.
- **Invariant violation:** a spec that breaks the cross-object rule is
  rejected by the constructor with a contextful error — this is the
  aggregate's reason to exist; test it first.
- **Defensive copies:** mutate the collection returned by an accessor; assert
  the aggregate is unchanged.
- **Equality blocked:** native comparison of two aggregates is impossible
  (compile-time) or rejected/identity-only (runtime), per language.
- **Transitions:** fact case — state change returns a new instance, original
  untouched; lifecycle case — every transition re-establishes the invariant,
  and illegal transitions error without partial mutation.

## Common mistakes

- **Everything-is-an-aggregate:** promoting any entity with a slice. No
  cross-item rule → no aggregate.
- **God-aggregate:** widening the boundary until every rule fits inside.
  Boundaries are as small as the true invariant allows.
- **Leaked children:** returning the backing slice/list, letting callers
  mutate past the root. Defensive copies, always.
- **Caller-enforced invariants:** "everyone who builds one should check that
  it balances." Nobody will. The constructor does.
- **Cross-aggregate reach:** one aggregate directly mutating another's
  children. Coordination happens above the aggregates, never through a side
  door.

## Now build it

- Go: `go.md#aggregates`, then `go.md#the-spec-pattern`
- Python: `python.md#aggregates`, then `python.md#the-spec-pattern`
