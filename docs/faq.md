# DDD FAQ

Questions people actually ask, answered as decisions. Each answer ends with
the rule you can apply in the next five minutes. Expandable — when a question
comes up twice, it belongs here (see "Adding an entry" at the bottom).

## 1. What's the difference between a value object and an entity — and when do I use which?

Identity. A value object is *what* it is (defined entirely by attributes: any
"USD 100" is interchangeable with any other); an entity is *which* one it is
(the system tracks this specific one even if another has identical
attributes — two transfers of the same amount are still two transfers).

**Decide:** ask "could I swap this for another instance with the same
attributes and nothing would change?" Yes → value object. No — the system
genuinely needs to say *that one* → entity. Default to value object; identity
must be earned, not assumed. (Evans ch. 5; Vernon ch. 5–6.)

## 2. What's the difference between an entity and an aggregate — and when do you use one over the other?

An aggregate is not a bigger entity — it's a **consistency boundary**. Every
aggregate has a root that *is* an entity, but the aggregate exists because
some rule spans several objects ("these transfers must balance", "line items
must sum to the total") and someone has to guarantee it. The root owns the
objects the rule spans and is the only way in.

**Decide:** list the rules. A rule about one tracked thing → entity. A rule
across several objects one thing owns → that thing is an aggregate root, the
rule lives in its constructor (or transitions), and outsiders only ever touch
the root. No spanning rule → plain entity, even if it holds a list.

## 3. Why must value objects be immutable when entities don't have to be?

Because a value object has no identity, there is no "it" to change — altering
the attributes just makes a different value. Sharing also depends on it: two
holders of the same `Money` must never see it mutate under them. Entities are
different: identity is exactly what persists *through* change, so mutability
is a domain question — a posted transfer is a fact (immutable); a contract has
a lifecycle (mutable, through guarded transitions).

**Decide:** value object → immutable, no exceptions. Entity/aggregate → ask
"fact that happened, or thing with a lifecycle?" Facts stay immutable; state
changes return new instances. Lifecycles mutate through transition methods
that enforce the rules.

## 4. When should I wrap a primitive in a value object — and when shouldn't I?

Wrap when the value is **domain-meaningful**: it has validation rules
(an email must parse), behavior (money adds same-currency only), or a meaning
the type should carry so the compiler can catch a swapped argument
(`CustomerID` vs `OrderID`, both strings). Don't wrap plumbing: log lines,
technical counters, persistence-only columns. Wrapping everything is
*value-object theater* — ceremony without meaning, and a real cost in noise.

**Decide:** would a validation rule, a behavior method, or a
prevented-mix-up justify this type's existence in one sentence? If you can't
write that sentence, keep the primitive.

## 5. Why does validation live in the constructor and not the service layer (or the parent)?

One door. If the constructor is the only way to make the type, then holding
an instance *proves* it's valid — every function that receives it drops its
defensive checks. Scatter validation across services and parents, and every
new call site is a chance to forget one rule; the check count grows with the
codebase instead of staying at one. Parents never re-validate children for
the same reason: the child's constructor already proved it.

**Rule:** invalid states are unrepresentable after construction. If you find
an `if !valid(x)` outside a constructor, either the type is missing or its
door has a hole.

## 6. What is a Spec, and why are its leaves primitives instead of domain objects?

A Spec is the construction boundary: a plain data struct the outside world
(handlers, DTO mappers, tests) fills with primitives, which the constructor
turns into a validated domain object. If a spec field were already a domain
value object, the caller would have to construct *that* first — meaning the
caller has stepped inside the domain, and validation now happens in two
places in ambiguous order. Primitive leaves keep the boundary a boundary and
the constructor the single validation site.

**Rule:** spec in (primitives), validated domain object out. One-argument
types skip the spec entirely — they are their value.

## 7. Why are specs nested instead of flattened into one big struct?

Composition frequency. A ubiquitous child (`TimeWindow`, `LedgerAccount`)
gets embedded in *many* parent specs. Flatten it and every parent hard-codes
the child's field list — add one field to the child and you're editing every
parent and every call site. Nest it and the change lands in the child's spec
alone. The nesting also keeps the spec legible as domain shape: you can *see*
that a transfer has two accounts, each with a ledger.

**Rule:** the spec's nesting mirrors the domain object's composition;
flatten only at single-value leaves.

## 8. Why can't I compare two domain objects by their string output?

Because `String()`/`__str__` is a *display* representation, and display can
be lossy or ambiguous exactly when it matters: `1.5` and `1.50` may render
identically (masking a real difference) or differently (masking a real
equality). String comparison silently turns "equal values" into "equal
renderings". The `stringequality` analyzer rejects it in tests.

**Rule:** compare by value — native equality where one representation per
value exists, an explicit `Equal` where it doesn't. Stringification gets its
own test and is never an equality proxy.

## 9. Do entities and aggregates get `MustNew` constructors like value objects?

No. `MustNew*` (panic on error) exists for value objects because tests
construct known-valid literals constantly and the error path is pure noise.
Entities and aggregates carry real construction risk — a multi-field spec, a
cross-object invariant — and their construction failures are exactly what
tests need to exercise, not skip past.

**Rule:** `MustNew*` is a value-object convenience for known-valid literals,
never a production path, never on entities/aggregates.

## 10. How big should an aggregate be? When does my entity become one?

As small as its true invariant allows. The moment a rule spans objects one
thing owns, that thing is an aggregate root (see #2) — but resist the other
direction: pulling more objects inside "to be safe" creates a god-aggregate
that serializes every change through one lock and one constructor. If a rule
seems to span two aggregates, that's a boundary-design question (eventual
consistency, domain events) — don't solve it by merging them.

**Rule:** every object inside the boundary must be touched by an invariant
the root enforces. Anything the invariant doesn't touch belongs outside.

## 11. Isn't this over-engineering for a small codebase?

It's a fair question, and the honest answer is: the conventions cost
something (more types, spec ceremony, copy taxes — `rationale/`'s benchmarks
put numbers on it), and they pay for themselves on the **change** axis, not
the first-write axis. The repo's measured claim (see
`docs/design-three-contender-changeability.md` and `docs/case-study.md`) is
that a field change on a conforming type is caught at every affected site by
the compiler, while the primitive version fails silently at N call sites. If
your code will never change or nobody but you will ever touch it, skip all of
this. If agents are writing code in your repo daily, consistency is the whole
ballgame — a convention applied 90% of the time buys ~0% of the benefit.

## 12. Where do application services, repositories, and bounded contexts fit?

Application services and repositories are now covered (see #13–#16 and the
skill's `application-services.md` / `repositories.md`). **Bounded contexts are
still coming** — the toolkit doesn't yet help you draw context boundaries or map
between them; model the pieces inside one context with the skill and flag the
cross-context question for a human.

## 13. Where does business logic go — the service, or the domain?

The domain, always. An **application service coordinates a use case** and holds
no business logic of its own: it runs four steps — **convert** the request to a
domain input, **delegate** to the domain (construct a new aggregate, or load an
existing one and call its guarded transition, or call a domain service),
**persist** the whole aggregate through a repository, and **respond** by mapping
the result to a DTO. Every rule, sum, and decision lives on a domain object the
service calls.

**Decide:** if a service method has a `for`-loop over domain objects, arithmetic
on domain quantities, or an `if` on domain state, the logic is misplaced — move
it onto the owning domain type (see #14). And never return a domain object from
a service; return a DTO, or the domain leaks past its boundary.

## 14. My service has a loop that sums/filters domain objects. Is that wrong?

Usually yes — it's a **missing domain type**. A loop that computes a result over
domain objects (sum, filter, group) is domain behavior wearing a service
disguise; it belongs on a domain collection type's method, or on the aggregate
that owns them. These are the **domain-logic leakage checks**: (1) a `for`-loop
over domain objects, (2) string-munging a domain identifier, (3) arithmetic on
domain quantities outside a conversion, (4) a conditional on domain state.

**Rule:** a loop that maps DTOs→specs is pure conversion and is fine; a loop that
*computes a domain result* is a missing method. Find the type that should own it.

## 15. Can a handler/endpoint just do the work if it's simple?

No — that's where the bleeding starts. A **handler parses and authenticates the
request, then calls an application service.** It does no domain math and touches
no repository. "It's just a small calculation" is how domain logic ends up
duplicated across every endpoint, drifting out of sync.

**Rule:** handler → application service → domain. If a handler is looping over
domain objects or opening a DB call, push that down a layer.

## 16. Why can't my repository just compute the total / filter the results?

A repository is the **persistence boundary**: whole aggregate in (it decomposes
it), reconstructed aggregate out (through the constructor). It may **filter,
order, and reconstruct** as persistence mechanics, but it must not **compute
domain results** — no summing, no invariant checks, no decisions on domain
state. A read that returns child objects or a projection is a legitimate *read
concern*, but it's read-only and still holds no domain logic.

**Rule:** the service passes the whole aggregate (never extracted children); the
repo speaks value objects and aggregates, not raw rows; a query object carries
domain-typed selection criteria and is **not** a Spec (specs have primitive
leaves and build objects; query objects select stored ones).

---

## Adding an entry

An entry earns its place when the question has come up twice (in review, in a
session, in an adoption conversation). Format: the question as someone
actually asks it; the distinction in plain language; a **Decide/Rule** line
that fits in five minutes. If the entry states a convention the skill also
teaches, add the FAQ column for that rule's row in `rationale/coverage.md` so
drift between the two renderings is visible.
