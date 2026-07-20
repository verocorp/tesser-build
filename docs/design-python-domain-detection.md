# Design — Python domain-type detection (the identity-taxonomy classifier)

**Status:** design, not built. This supersedes ddd-vet-py v1's "operate on
dataclasses generically" approach (`design-python-analyzer.md`) with a
**whole-tree, type-aware classifier** that identifies each domain class as
exactly one stereotype and checks conformance for that stereotype. v1's four
checks (DDD001–004) are **subsumed** into this model, not discarded.

Derived in a long working session (2026-07-15); the mypy-plugin spike that
informed the "how much needs types" question is archived (out of mainline) at
the `spike/mypy-plugin-archive` tag — `git show spike/mypy-plugin-archive`.

---

## 1. The problem v1 didn't solve

v1 keys VO-identification off the `@dataclass(frozen=True)` decorator and checks
dataclasses generically. That conflates *mechanism* with *identity* and has a
blind spot: a domain object that dodges the decorator dodges detection. The goal
now is to **determine conforming value objects, entities, aggregates — and flag
everything that conforms to none — in any `*/domain/**/*.py`.** That requires
classifying by what a thing *is*, not how it's built.

---

## 2. The taxonomy — the identity 2×2

Every **data-bearing** domain type classifies on two axes:

- **Axis 1 — kind of identity.** A value object's identity *is its values* (two
  with equal attributes are the same, interchangeable). An entity's identity is
  a *distinct identifier, independent of its values* (it persists as attributes
  change). Behavior constructs (services, factories) have *no* identity.
- **Axis 2 — does it embed another entity** (an identity-bearing object) by
  composition?

|                       | embeds ≥1 entity   | embeds no entity              |
|-----------------------|--------------------|-------------------------------|
| **value-identity**    | *impossible*       | **Value object**              |
| **reference-identity**| **Aggregate root** | **Entity**                    |
| **no identity**       | → **"other"**      | → **"other"** (behavior)      |

Three data-bearing types, one impossible cell, and a residual "other" bucket for
non-data constructs.

**Why the impossible cell is void:** a value object cannot embed an entity. An
embedded entity is a *member* and needs a *root*, and a root must itself be an
entity (identity is what lets it be the entry point) — a VO has none. Equally, a
VO's equality is by value over all its attributes, but an embedded entity
compares by identity; the two equality models can't coexist. The moment a value
owns something compared by identity, it has become an identity object.

### Two things that are NOT separate types

- **Entity vs aggregate root is a non-distinction *as a type*.** An aggregate
  root *is* an entity — one in the *state* of guarding a cross-member invariant.
  `aggregates.md`: "the moment a rule spans the items… the parent has become an
  aggregate root." So we classify to the **entity family** and treat "aggregate"
  as the sub-state detectable by *embeds-an-entity + owns-and-guards-a-collection*.
- **Member vs standalone is an orthogonal *position* axis** (the composition
  graph), not a type. A member entity is still "Entity"; its position changes its
  *obligations* (defensive-copy, reference-by-ID), not its stereotype.

### The value family has one internal fork

Events and collection-VOs are just value objects. **Specs** are also
value-identity objects, split from domain VOs by **validation + exposure**:

- **Domain VO** — validates (always-valid), hides its field.
- **Spec** — public primitive fields, no validation; a boundary carrier that
  *exposes* primitives on purpose.

---

## 3. Detection signals (Python, grounded)

### Axis 1 — identity kind (primary, reliable, pure-AST)

| Signal | Verdict |
|---|---|
| frozen dataclass + value-equality (default or custom `__eq__` over fields) | **value family** |
| plain class + identity field + identity-`__eq__` (`hash(self._id)`) or `__eq__ = None` | **entity family** |
| neither — behavior, no identity, no value-state | **"other"** (ejected) |

Grounded: entities/aggregates are plain classes with identity equality
(`Product.__eq__` by SKU; `Campaign.__eq__ = None`); VOs are frozen dataclasses
with value equality (`Money`, `Slug`). This is the *reliable* line — value-eq vs
identity-eq — because the skill mandates it: entities forbid value equality
(`entities.md` rule 6), aggregates block it (`aggregates.md` rule 4).

### Axis 2 — embeds an entity (composition graph, pass 2)

| Signal | Verdict |
|---|---|
| entity embeds only VOs | **Entity** |
| embeds ≥1 entity by composition (a field/collection whose type is an entity) | **Aggregate root** |
| holds another *root* by object instead of by ID | **boundary violation** |

Needs the pass-1 registry to know whether a field's type is an entity. A member
is any entity **transitively composed below a root**, accessed only through it.

### Within the value family

| Signal | Verdict |
|---|---|
| no public *primitive* field; accessors return only VOs / defensive copies (never a primitive); validates; is a `Stringer` | **domain VO** |
| public primitive fields + no validation + no behavior | **spec** |

Exposure and validation both point the same way, so spec-vs-VO is decidable. A
VO *may* expose accessors returning another VO or a defensive copy — **never a
primitive**. A multi-rep primitive (a `Decimal` amount) is wrapped in its own VO
(`DecimalAmount`) and exposed as that VO; a leaf VO's own primitive has no
accessor at all, only `__str__`.

> **Amended 2026-07-19 (maintainer ruling, first consumer feedback).** The
> original text here allowed a "safe single-representation value" accessor
> (`Money.Currency()` → a currency-code string). That allowance is **closed**:
> an accessor returning a bare primitive — single-rep or multi-rep, compound
> component or leaf `value` — is the public field with extra steps, and consumer
> field data showed the check-vs-norm gap immediately (a `@property` returning
> `self._x` passed TB010 while the message claimed the representation was
> hidden). Components are exposed as value objects; TB010 now flags the
> passthrough accessor shape too.

> **Amended 2026-07-20 (maintainer rulings, serialization norm).** Two
> refinements, doctrine in `skills/tesser-build/serialization.md`:
> (1) "only `__str__`" generalizes to the **canonical conversion exit** — a
> leaf VO exposes exactly ONE conversion dunder, the one matching its
> backing primitive (`__str__`/`__int__`/`__float__`/`__bytes__`);
> `Decimal`/`datetime` exit as canonical text via `__str__` under an
> explicit per-type policy; the round-trip law locks it; display formatting
> is a presentation concern, never the VO's. A second or mismatched
> conversion dunder is a disguise (checker queued this wave).
> (2) A compound VO's components are **child value objects internally**,
> not hidden raw primitives — `Money{MoneyAmount, MoneyCurrency}`
> (`examples/python/catalog/money.py`); single-concept behavior lives on
> the child, cross-field invariants on the compound; the compound
> construction REVISIT is closed to the factory shape (`from_spec` parses
> leaves into child VOs; the auto-init accepts only child VOs and needs no
> guard). Compounds, entities, and aggregates have no primitive exit at
> all — they decompose via the per-context parts module (application
> layer); the spec stays inbound-only.

---

## 4. Decided rules (this session)

1. **Identify by the taxonomy, not by `@dataclass`.**
2. **Entity/aggregate collapse** to one family; keep member-vs-root (graph
   position). Aggregate = entity that embeds + guards a collection.
3. **VOs must not expose their primitive.** VO field is hidden (`_value`, no
   public field, no primitive getter — **no passthrough accessor either**,
   per the 2026-07-19 amendment above); the only value surface is `__str__`
   (display, never equality) + accessors returning value objects + domain
   behavior + defensive-copy collection accessors. Specs keep public fields.
   *This reinstates the `primitiveaccessor` check that v1 dropped — it is
   load-bearing here because it is the spec/VO discriminator, not just
   leak-prevention.*
4. **Construction discipline.** A structured domain object is built from outside
   the boundary through its **spec + `from_spec`**; leaf primitive-wrapper VOs
   construct directly and validate in `__post_init__`. Collection VOs may take a
   raw collection. The spec is the **inbound** construction surface only. A
   domain object exposes **no public `decompose()`/`.Spec()` method** — a
   public decompose-to-primitives surface was **red-teamed out in certus**
   (it enables string/decomposed-form equality that bypasses value equality, and
   is a "public decompiler" representation leak). The primitive leaves the domain
   **only at the service/repository boundary**, unwrapped *inline there*
   (accessor chains that return VOs, `.String()` at the very edge — that is where
   cross-domain translation legitimately lives). **Domain functions return domain
   types, never raw primitives/collections.**
5. **Value family = VO / event / collection-VO / spec**, forked by
   validates-or-not.
6. **Semantic invariants are the user's to test, never the analyzer's.**

### Grounded against Go (the reference discipline)

- VO fields **unexported** (`Money{amount, currency}`); spec fields **exported**
  (`MoneySpec{Amount, Currency}`) — the compiler-level spec/VO line.
- **Every VO implements `fmt.Stringer`**; `String()` is the display method AND
  the *sole* string accessor — no `ToString()` (`go.md:97`).
- **No typed accessor that returns a primitive** — no
  `Int()`/`Value()`/`Amount()` handing back the wrapped `int`/`*big.Rat`/`Decimal`.
  An accessor *may* return **another value object** (certus: `Quantity() →
  quanta.Decimal`, itself a VO) or a **defensive copy** of a collection
  (`Labels.Values()`). *(Amended 2026-07-19: the "safe single-representation
  value" carve-out — `Money.Currency()` → a currency code — is closed; a
  currency code is a `Currency` value object. The ban covers every bare
  primitive, not just multi-rep ones.)*
- Equality is by value (`Equal`/`==`), never by `String()` or a decomposed form.

---

## 5. The check set

### Detectable — the analyzer's job

- **Classify** each domain class (axis 1, pass 1; axis 2, pass 2).
- **VO:** frozen; validates; no mutable-collection field *(subsumes DDD002)*;
  hides field / no primitive getter beyond `__str__` *(reinstated
  primitiveaccessor)*; implements `__str__`; no `str==str` *(subsumes DDD004)*;
  immutable / no setattr bypass *(subsumes DDD003)*.
- **Spec:** public fields + no validation → classified as spec, **exempt** from
  VO validation/exposure rules.
- **Entity:** plain class; identity field; identity-eq or `__eq__ = None`, never
  value-eq; private field + `@property`; no setters.
- **Aggregate role:** owns a collection of entities → accessors return defensive
  copies, never the backing collection; no raw mutable-collection field.
- **Boundary:** holds another root by object instead of by ID → violation.
- **Construction:** structured type has a `from_spec`; leaf VO constructs directly.

**v1 subsumption:** DDD001 frozen → VO signature; DDD002 hash-hazard → VO rule;
DDD003 setattr-bypass → immutability rule; DDD004 str-eq → VO rule.

### Semantic — the user's job (tests, never the analyzer)

- Whether a cross-member **invariant** is present, correct, or complete.
- Whether an entity **should** have been an aggregate (a *missing* invariant is
  structurally undetectable).

The skill already puts these in each concept's "Tests you must write" — the
aggregate's invariant-violation test is the one written first.

---

## 6. Architecture — whole-tree, two-pass

v1 is per-file. This model needs whole-tree context:

- **Pass 1** — classify every class by axis 1 (local, pure AST) → a registry of
  `{qualified name → stereotype}`.
- **Pass 2** — resolve embedding/boundary by matching each field's annotation
  against the pass-1 registry.

**Consequence: most of the type-awareness needs no mypy** — pass 2 resolves names
against our own registry, not full inference. The mypy plugin only buys the
*disguised* cases (alias / `NewType` / cross-module import) — ~4 of 16 rows in
the spike (archived at the `spike/mypy-plugin-archive` tag; `README.md` there).
So mypy stays **optional hardening**, not a prerequisite.

---

## 7. Out of scope / not domain

These do **not** live under `*/domain/**` and are not classified here:
application services, repository *interfaces* (they live in application) and
implementations, public-interface clients + DTOs, handlers, composition root.
Domain services / events / specs are value-family or behavior and are handled by
the "other"/value-family rules above.

---

## 8. Open items (do not block the rewrite)

1. **Scope rule** — *which* classes under `*/domain/**` must be classified
   (exclude enums, `Protocol`s, exceptions, nested helpers). **Only the
   "unclassified domain object → flag" exhaustiveness check needs this**; every
   positive per-type check fires on signature matches and ships without it.
2. **Int/Decimal-backed VO exposure — pattern decided; worked example pending.**
   The pattern: a `DecimalAmount` VO wraps the exact `Decimal` (value equality so
   `1.5 == 1.50`; domain methods `is_positive`/`add`/`exceeds`; `__str__` as the
   sole serialization surface); the owning type holds it hidden and exposes it as
   a VO accessor; the boundary unwraps via that accessor + `str()`, never a raw
   `Decimal` and never a domain-object `decompose`. This is Option 2 (the
   certus/`quanta.Decimal` pattern), chosen over a `String()` round-trip because
   that round-trip is the smell the certus notes flagged. The worked example
   previously lived in `examples/python-expenses`, which was **removed** because
   its `ExpenseReport` "aggregate root" owned a collection of *value objects*,
   contradicting the settled root definition (§2: a root embeds ≥1 **entity**).
   *Resolved 2026-07-20: the worked example is `MoneyAmount` in
   `examples/python/catalog/money.py` (Decimal-backed child VO — `parse`,
   non-negative guard, `add`, canonical text via `__str__`, round-trip law
   locked in tests), held by `Money` and exposed as a VO accessor, exactly
   this pattern.*
3. **Do specs live in `*/domain/**`** — they sit beside domain types; detection
   classifies them by signature regardless, so this is a labeling call, not a
   blocker.

---

## 9. Impact: `examples/python` must be reworked

The exposure rule (§4.3) **breaks the current examples** — `examples/python` VOs
expose public fields (`slug.value`, `money.amount`). Since the acceptance gate
requires the analyzer to pass clean on `examples/python`, the rewrite **requires
bringing the Python examples into conformance**: hidden VO fields, spec/VO split,
`__str__` + decompose out. This is where most of the rewrite's effort lives — the
analyzer logic is smaller than the example-tree rework it forces.

---

## 10. Build sequence

1. **This spec** (done).
2. **Rework `examples/python`** to the new idiom (hidden VO fields, spec/VO
   split, decompose paths) — the conformance target.
3. **Build the two-pass classifier + checks** against those examples, check by
   check, subsuming DDD001–004.
4. **Defer** the "unclassified → flag" exhaustiveness check until the scope rule
   is settled.
5. **Optional later:** the narrow mypy plugin for disguised-type hardening
   (spike already scoped it).
