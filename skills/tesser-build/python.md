# Building domain code in Python

Two shape rules hold for every class in every module kind (TB051). A module
holds classes, never functions. And **a method is for outsiders** — no method
references a sibling method through its receiver, so what a method does is
visible at its call site; direct recursion is exempt, and so is calling a
directly recursive sibling (it has no inline expansion). A class that wants
shared logic composes a collaborating class instead of reaching into itself.

Construction mechanics only — the concepts and the rules' whys live in the
concept files (`value-objects.md`, `entities.md`, `aggregates.md`,
`application-services.md`, `repositories.md`, `domain-services.md`). This file
covers the domain building blocks *and* the boundaries that serve them (application
services, application ports, repositories) — not domain objects themselves, but their construction
mechanics live here alongside the objects they orchestrate and persist. Section
headings here are stable anchors; the resolver and the coverage matrix link to
them.

> **Verification status — verified.** Every pattern here is backed by runnable,
> type-checked worked examples in the **shell idiom**: `tesser-py`'s classes
> (`ts.ValueObject`, `ts.Entity`, `ts.AggregateRoot`, `ts.Spec`,
> `ts.ApplicationService`, `ts.Port`, `ts.Repository`, `ts.Gateway`,
> `ts.Handler`, `ts.Client`, `ts.Request`, `ts.Response`) carry no behavior —
> subclassing one is a *declaration* of what a class is — and **tessercheck**
> (`tessercheck-py/`) verifies everything against its declaration, at zero
> findings in CI. The domain mechanics live in
> `examples/python-app/campaign/domain/` (leaf value objects in `values.py`,
> the compound `Money` backed by `decimal.Decimal` in `money.py`, the
> collection value object `Labels` in `labels.py`, the entity `ShortLink`, the
> aggregate `Campaign`). The service, repository, public-interface, and
> composition-root mechanics — and the app-level anatomy of `bootstrap` +
> per-context `client.py`/`wiring` + `srv` hosts + inbound handlers — are
> `examples/python-app/` end to end (multi-context, self-enforcing tests).
> `examples/ports/` is the second exemplar (one context, two application
> ports, the enum outcome read with `match` + `assert_never`, the collection
> answer carried as a tuple). All trees pass `mypy --strict`, `pytest`, and the
> analyzer in CI, the same bar the Go mechanics meet. The examples here are
> all *lifecycle* and *1:1*, so they do not exercise a **fact**
> aggregate/entity that returns a new instance on change or an explicit
> **reshaping** `Client`; each is marked where it appears. Where a Go/Python
> difference is load-bearing — base-owned equality vs Go's `Equal`, `Protocol`
> structural typing vs Go's struct embedding, the absence of
> `context.Context` — it is called out inline.

(`tesser.errors` and `tesser.serialization` need no debt markers: they are
tesser norm modules every placement may import — as modules, like everything
else: `import tesser.errors as errors`, then `errors.invalid(...)`. The
`# tesser:debt TB062` markers earlier revisions of these excerpts
carried are gone — the app-level `errors`/`serialization` root modules they
excused moved into the tesser runtime.)

**Every import is a module import** (TB053, maintainer ruling 2026-08-24):
`import x` or `import x as name`, never `from x import name` — the stdlib,
the tesser norm modules, kernels, and the tree's own modules alike. The one
form with no module spelling, `from __future__ import annotations`, is the
one exemption; a kernel or tesser `__init__` that re-exports (`from kernel.slug
import Slug as Slug`) is TB042's business, not an import — a role `__init__`
holds module imports or nothing, as it always has. A context module further
carries an alias (`import campaign.domain.money as money`), because the
analyzer resolves names as attribute-over-alias.

**What the shell buys, once.** `ts.ValueObject` owns immutability and value
equality at runtime: assignment and deletion raise, `__eq__`/`__hash__`
compare by type and content, and a subclass that tries to override
`__eq__`/`__hash__`/`__setattr__`/`__delattr__` (or declare `__slots__`)
raises `TypeError` **at class-definition time** — the identity contract
cannot drift. `ts.Entity` owns identity equality the same way: the subclass
declares an `identity` property, the base compares and hashes by it, and an
attempted override raises at import. What the runtime cannot see — placement,
imports, representation leaks, construction paths, serialization exits — the
analyzer enforces (`tessercheck-py/RULES.md`, one row per rule with its
family code).

## Value objects

**Simple (wraps a single value) — a leaf: declare the base, hide the field,
validate in the one constructor:**

```python
# campaign/domain/values.py (verified impl)
import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization


class CampaignID(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _CAMPAIGN_ID_RE.fullmatch(value):
            raise errors.invalid("invalid_campaign_id", f"campaign id {value!r} must be 16 lowercase hex chars")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)   # canonical exit: one-line delegation to the policy

    _value: str
```

The base gives immutability (assignment raises) and content equality;
`object.__setattr__` inside `__init__` is the **only** sanctioned assignment
site, so `__init__` is the **single validation site**: it runs on every
construction path, and an invalid instance is unrepresentable — there is no
bypassable factory. Declare the field at class level (`_value: str`) — the
analyzer reads representation from those annotations, and `mypy --strict`
needs them. The field is **hidden and stays hidden**: a leaf value object
gets **no accessor at all** — no public field, no `value` property handing
the raw string back (a passthrough accessor is the same leak as the public
field, and TB010 flags both). The leaf's **canonical exit** is the one
conversion dunder matching its backing primitive — str-backed → `__str__`
(as here), int-backed → `__int__`, float-backed → `__float__`, bytes-backed
→ `__bytes__`; `Decimal`/`datetime` exit as canonical text via `__str__`
under the explicit per-type policy in `serialization.md` rule 3. One dunder
per leaf, matching its representation — a second or mismatched one is a
disguise (TB015), and the dunder body is a **one-line delegation** to the
runtime's `tesser.serialization.canonical_*` policy helper (TB018), so each
canonical form has exactly one implementation site. The canonical form is what the
serialization layer carries (`serialization.md`); display formatting is a
presentation concern and never the value object's job. The round-trip law
locks the exit: `CampaignID(str(id)) == id`, asserted in a test per leaf.

**Compound (two or more fields): the components are child value objects.**
Not hidden raw primitives — child VOs (maintainer rulings 2026-07-19/20:
`rect.x` returning `"1"` is primitive obsession wearing an accessor; `x` and
`y` are value objects, held and exposed as such — TB016 flags a bare
wrappable primitive field on a compound, TB019 flags any public method
handing back a non-domain type). Single-concept behavior migrates into the
child; what remains the compound's own is exactly the **cross-field
invariants**.

```python
# campaign/domain/money.py (verified impl)
class MoneySpec(ts.Spec):

    def __init__(self, amount: str, currency: str) -> None:
        self.amount = amount
        self.currency = currency


class MoneyAmount(ts.ValueObject):

    def __init__(self, value: str) -> None:       # ONE constructor: the canonical form in
        try:
            parsed = Decimal(value)
        except InvalidOperation as e:
            raise invalid("invalid_budget_amount", f"budget amount {value!r} is not a number") from e
        if parsed < 0:
            raise invalid("invalid_budget_amount", f"budget amount must not be negative: {parsed}")
        object.__setattr__(self, "_value", parsed)

    def __str__(self) -> str:                     # canonical exit: the Decimal text policy, one site
        return canonical_decimal(self._value)

    _value: Decimal


class MoneyCurrency(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _CURRENCY_RE.fullmatch(value):
            raise invalid("invalid_budget_currency", f"budget currency {value!r} must be 3 uppercase letters")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class Money(ts.ValueObject):

    def __init__(self, spec: MoneySpec) -> None:              # the one constructor: its spec in, child VOs built
        object.__setattr__(self, "_amount", MoneyAmount(spec.amount))
        object.__setattr__(self, "_currency", MoneyCurrency(spec.currency))

    @property
    def amount(self) -> MoneyAmount:              # components exposed as VOs, never primitives
        return self._amount

    @property
    def currency(self) -> MoneyCurrency:
        return self._currency

    _amount: MoneyAmount
    _currency: MoneyCurrency
```

Note what `Money` does **not** define: any conversion dunder. A compound has
zero — no `__str__`, no "debug display" (`serialization.md` rule 5, enforced
as TB015); the base's `repr` is the debug surface, and logging is its own
norm (`logging.md`).

**Each rule lives on the type that owns it** — the child's `__init__` guards
the child; the compound's methods guard only cross-field relations — so no
construction path can skip a rule, and no rule has two homes. Verified impl:
`examples/python-app/campaign/domain/money.py`.

**Construction (ruled 2026-08-24, superseding the 2026-08-23
primitives-and-specs ruling, the 2026-07-20 (b)-uniform ruling, and the
shells revision's value-object allowance):** construction data is
**primitives and specs, never value objects**, and a constructor takes
**exactly one parameter**. A **leaf** value object wrapping one value takes
that primitive — `Slug(value)`, `MoneyAmount("9.99")`. Anything with
**two or more construction values** — a compound value object, an entity,
an aggregate — takes **exactly one `ts.Spec`** (`Money(MoneySpec("9.99",
"USD"))`, `Campaign(spec)`, the same shape as Go's `NewCampaign(spec)`;
TB080), converts the spec's data to value objects in its `__init__`, and
from then on its methods hold, take, and return only value objects; a value
object is never a constructor parameter or a spec field. That `__init__` is
the only place **its own** spec is read: a parent reads its own spec's
fields and hands a child spec on **whole** — `money.Money(spec.budget)`,
`ShortLink(link_spec)` — never reaching through it (`spec.budget.amount`
is TB083, because `MoneySpec` belongs to `Money.__init__`). Everywhere
else code builds a spec and passes it on; it never reads a spec's fields
and never stores one (TB083; a test module is exempt, because a
completeness test reads the spec it fed the constructor — `testing.md`
rule 2). A spec `__init__` holding its child spec is the one holder;
a mapper is not one — it hands a child spec whole into `super().__init__`
and keeps nothing (TB080). There is **no `from_spec`** and no
factory of any spelling: on a
value object, **any** classmethod or staticmethod returning its own type
(`Self`, quoted, or inferred from a body that constructs `cls`) is a second
construction path (TB017) — `from_spec`, `parse`, `new`, `require`, `of`
alike. A leaf whose construction involves conversion (str → Decimal) takes
the **canonical form** at its constructor and converts inside — no `parse`
classmethod, no union-typed parameter (ruled 2026-07-20: a union adds
special cases for what is only a performance benefit; the one union the
analyzer admits in construction data is `X | None`, optionality). Behavior
methods that produce new instances re-enter **through the constructor** via
canonical forms, lossless by the round-trip law, so every instance that
exists passed the one validating constructor.

**Collection (wraps a mapping/sequence):**

```python
# campaign/domain/labels.py (verified impl)
class Labels(ts.ValueObject):

    def __init__(self, values: tuple[tuple[str, str], ...]) -> None:
        seen: set[str] = set()
        for key, value in values:
            if not key:
                raise invalid("invalid_label", "label key must not be empty")
            if not value:
                raise invalid("invalid_label", f"label {key!r} carries an empty value")
            if key in seen:
                raise invalid("invalid_label", f"label {key!r} appears twice")
            seen.add(key)
        object.__setattr__(self, "_values", tuple(sorted(values)))   # canonicalize in the constructor

    def get(self, key: str) -> LabelValue | None:   # entries come back as VOs
        raw = dict(self._values).get(key)
        return LabelValue(raw) if raw is not None else None

    def __len__(self) -> int:                        # language-fixed dunder: licensed
        return len(self._values)

    _values: tuple[tuple[str, str], ...]
```

Go wraps a `map` and must add `Equal` (a map-backed struct is
non-comparable); the shell stores an immutable, **sorted** tuple instead, so
the base's content equality is canonical *and* the value is hashable
(TB002: a `list`/`dict`/`set` field would make `__hash__` raise — back a
collection with a tuple). The constructor takes the plain tuple-of-pairs, not a
`Mapping` — construction data is primitives and specs, and the sort
in the constructor is what makes the canonical form unskippable: there is exactly
ONE way in, so no caller can hold a non-canonical value. Reads come back as
value objects (`LabelValue`), never raw entries. Verified impl:
`examples/python-app/campaign/domain/labels.py`.

**No `new`/`require` factory pair** (TB017). A second constructor is a second set of
invariants: if `new` is permissive and `require` demands non-empty, what the
type guarantees depends on which construction path the caller picked — so it guarantees
nothing. When you genuinely need a stricter set, that is a *different type*
with its own invariant, not a second factory on this one.

**Rules of the section:**

- Subclass `ts.ValueObject`; the base owns immutability and equality and
  refuses overrides at class-definition time. No setters, no mutation —
  behavior methods return new instances through the one constructor.
- Declare every field at class level (`_value: str`); assign only via
  `object.__setattr__` inside `__init__`.
- **The primitive never escapes** (TB010): no public primitive field, and no
  passthrough accessor returning one — a leaf VO exposes nothing but its
  canonical exit; a compound VO's components are child value objects, held
  and exposed as such; a value object's public behavior hands back domain
  objects (TB019 — the licensed exits are the language-fixed dunders, the
  canonical exit, and a `-> None` transition; quoting an annotation is not
  an escape hatch).
- **A domain object's public method takes one thing** (TB019's parameter
  mirror): besides `self`, at most one parameter, and it is a primitive (an
  enum counts), a spec, or a domain object — never a port or client DTO,
  never a container, never two, never `*args`/`**kwargs`, and never
  unannotated. Unlike the return rule it reads a `-> None` transition too,
  and a public `__call__` is a public method like any other
  (`domain-return.md` rule 7).
- **`bool` and `complex` are not value-object material** (TB016), at any
  field count — a bool is atomic (model the raw value where it lives, or
  reach for a richer type when it is really more than binary; a validated
  multi-valued leaf is the shell idiom's enum), and neither has a canonical
  conversion exit.
- No `Must*` twin is needed: construction already raises on invalid input.
  The Go `New/MustNew` split exists because Go returns errors; Python's
  exception IS the panic path — in tests, construct directly with known-valid
  literals.
- A leaf's conversion dunder is its **canonical form**, not display — locked
  by the round-trip law, delegated to the one `canonical_*` policy site
  (TB018; module-qualified delegation counts). Never compare domain objects
  via `str(a) == str(b)` (TB004).

**Equality — the base decides:**

- `ts.ValueObject` compares by type and content; each logical value should
  have one representation, and the way to guarantee that is **normalizing in
  the one constructor** (the collection VO above sorts on the way in; a
  case-insensitive code lowercases in `__init__`). There is no hand-written
  `__eq__` on a shell value object — the base raises if you try; if the
  default is wrong, fix the representation, not the comparison.
- Note `Decimal("1.5") == Decimal("1.50")` is numerically `True` and hashes
  consistently only because Python normalizes numeric hashing — verify
  equality AND hashing in the equality test whenever a field type has
  multiple representations.

## Entities

```python
# campaign/domain/short_link.py (verified impl)
class ShortLinkSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str, active: bool) -> None:
        self.slug = slug
        self.target_url = target_url
        self.active = active


class ShortLink(ts.Entity):

    def __init__(self, spec: ShortLinkSpec) -> None:       # the single construction path
        self._slug = values.Slug(spec.slug)
        self._target_url = values.TargetURL(spec.target_url)
        self._status = values.LinkStatus(
            values.LinkState.ACTIVE if spec.active else values.LinkState.INACTIVE
        )

    @property
    def slug(self) -> values.Slug:
        return self._slug

    @property
    def status(self) -> values.LinkStatus:
        return self._status

    def deactivate(self) -> None:                          # lifecycle transition
        self._status = values.LinkStatus(values.LinkState.INACTIVE)

    @property
    def identity(self) -> values.Slug:                     # the base compares and hashes by this
        return self._slug

    def _clone(self) -> "ShortLink": ...                   # the aggregate's defensive copy-out
```

- Fields are value objects, never raw primitives; underscore-private with
  read-only `@property` accessors returning value objects, no setters. An
  accessor must never hand back a backing mutable collection — return a
  defensive copy (TB011).
- A closed set of states is a **domain enum** — a plain `enum.Enum` in
  `values.py` (`LinkState`), no `ts.*` base. An enum is a primitive with a
  name: legal as a spec field and as a value-object constructor parameter,
  exactly like `str`. The `LinkStatus` value object wraps it (storing the
  member's string value, so the canonical `__str__` exit stands) and never
  hands the enum back out — TB010 flags an accessor returning one. The enum
  lives beside the value objects it feeds, because a role module imports its
  tesser package exactly once (TB050) and ruff bans an unused import, so an
  enum-only module has no legal form.
- Equality is **identity**, and the base owns it: declare the `identity`
  property (the ID value object) and `ts.Entity` compares and hashes by it —
  a hand-written `__eq__`/`__hash__` raises at class definition.
- The constructor takes **exactly one spec** and builds each child value
  object via its own constructor; there is no second constructor.
- **Fact entities:** no mutation methods; a state change returns a new
  instance. **Lifecycle entities:** transition methods that guard state
  (`deactivate` above; two states → a guard, more → a transition table, not
  stacked conditionals).

## Aggregates

```python
# campaign/domain/campaign.py (verified impl)
class Campaign(ts.AggregateRoot):

    def __init__(self, spec: CampaignSpec) -> None:
        self._id = values.CampaignID(spec.id)
        self._budget = money.Money(spec.budget)
        admitted: list[short_link.ShortLink] = []
        for i, link_spec in enumerate(spec.links):
            try:
                link = short_link.ShortLink(link_spec)
            except DomainError as e:
                raise invalid("invalid_short_link", f"invalid short link at index {i}: {e}") from e
            admitted = _admit(admitted, link)              # the cross-object invariant, one site
        self._links = admitted

    @property
    def links(self) -> tuple[short_link.ShortLink, ...]:   # defensive copy out
        return tuple(link._clone() for link in self._links)

    def add_short_link(self, spec: short_link.ShortLinkSpec) -> None:
        self._links = _admit(self._links, short_link.ShortLink(spec))

    def deactivate_short_link(self, slug: values.Slug) -> None:
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise not_found("link_missing", f"no short link with slug {slug} in campaign {self._id}")

    __eq__ = None  # type: ignore[assignment]              # comparing aggregates is a bug
    __hash__ = None  # type: ignore[assignment]
```

- The invariant is checked at construction and re-established by every
  transition (`_admit` — slug uniqueness) — an invalid Campaign is
  unrepresentable.
- Setting `__eq__ = None` makes comparison raise `TypeError` at runtime — the
  closest Python gets to Go's compile-time non-comparability, and the one
  override the base permits (it blocks replacements, not removal). If the
  aggregate must live in sets/dicts, declare `identity` like an entity —
  never field-wise.
- Children are copied in and cloned out; the backing list never escapes
  (TB011), and another aggregate root is referenced by its ID value object,
  never held (TB012).
- **Fact aggregates:** state changes return new instances. **Lifecycle
  aggregates:** root-guarded transitions that re-establish the invariant
  before returning.

## Outcomes {#outcomes}

A transition the caller must act on returns a `ts.Outcome` — a closed set of
names that is a value object (`domain-return.md` rule 6). It is the answer to
a call, never a field: nothing stores it, and it has no canonical exit because
it never leaves the process.

```python
# alpha/domain/widget.py (verified impl: examples/minimal/)
class Taken(ts.Outcome):
    TAKEN = enum.auto()
    HELD = enum.auto()


class Widget(ts.AggregateRoot):

    def take(self, spec: PartSpec) -> Taken:
        part = Part(spec)
        if part == self._part:
            return Taken.HELD
        self._part = part
        return Taken.TAKEN
```

```python
# alpha/application/alpha_service.py (verified impl: examples/minimal/)
    def add(self, request: client.AddRequest) -> client.AddResponse:
        added = widget.Widget(MapToWidgetSpec(request))
        taken = added.take(MapToPartSpec(request))
        match taken:
            case widget.Taken.TAKEN:
                self._widgets.save(MapToSaveRequest(added))
            case widget.Taken.HELD:
                self._checks.check(MapToCheckRequest(added))
            case _ as never:
                typing.assert_never(never)
        return MapToAddResponse(added)
```

- **`ts.Outcome` directly and alone, undecorated, members only, every member
  `enum.auto()`** (TB084) — no mixin, no intermediate base. The runtime base
  raises at class definition for a method or a descriptor of any name (a
  `functools.cached_property`, dunders included), class data, an annotation, a
  valued member, a member repeating another member's value (an alias makes a
  `case` arm unreachable), a mixed-in or intermediate base, or a custom
  metaclass, and `.value`/`.name` raise on every member; `_ignore_` and
  `_order_` are the exception, because enum strips what they name before the
  base sees the class, and TB084 reports them instead. The analyzer reports
  the same shapes and flags `_value_`/`_name_`. An outcome is matched, never
  read, never serialized.
- **Returned by a transition, read by a `match`.** A member is named in
  exactly two places: the `return` that produces it and the `case` that
  consumes it. `is Taken.HELD` / `== Taken.HELD` anywhere else is TB084, and
  so is naming the class outside an annotation (`Taken["HELD"]`,
  `getattr(Taken, ...)`, `list(Taken)`); a `status()` accessor returning one
  is the status-in-a-coat mistake (`domain-return.md`).
- **Every `match` on an outcome closes on `case _ as never:
  typing.assert_never(never)`** (TB084) — unguarded, one statement, the name
  still `typing`'s — because the `-> None` handler that just does side effects
  per arm otherwise fails open when a member is added (verified: mypy reports
  nothing without the closer). Import `typing` as a module, per the import
  norm.
- **Never held, never carried, never passed on.** A field annotated with an
  outcome, `self._last = self.advance()` off the object's own
  outcome-returning method, or a parameter typed as an outcome, is TB084; a
  spec, DTO, or port signature carrying one is already TB080/TB081. What
  must be kept is state, on the spec, with an exit.
- **Each arm is coordination**: one port call and/or one transition, `break`
  or `return`. A rule inside an arm is leakage check 4.
- **The loop** is the two-member case, `while True:` around the `match`, the
  subject a local rebound by the arm that continues:

```python
# the analyzer's own fixture (tessercheck-py, test_an_outcome_member_is_read_only_by_an_exhaustive_match)
        outcome = driven.advance()
        while True:
            match outcome:
                case run.Advance.CONTINUE:
                    self._runs.save(MapToSaveRequest(driven))
                    outcome = driven.advance()
                case run.Advance.DONE:
                    break
                case _ as never:
                    typing.assert_never(never)
```

  TB082 accepts a `match` subject that is a call on a domain object, or a
  local bound to one — here `outcome`, bound and rebound by `driven.advance()`.
  A third member (`BLOCKED`) is a type error at every reader, not a redesign.

## Application services

Coordination only — no business logic. Four named steps
(`application-services.md`): convert → delegate → persist → respond. Every
dependency is a `ts.Port` `Protocol` (the analyzer requires it), every public
method takes exactly one `ts.Request` and returns a `ts.Response` — and a
public `__call__` is a public method, not a private one — and the
method inlines its logic — no delegation chains, no `if`, no conditional
`while`, no comparison (spelled, or called as `a.__eq__(b)` or
`operator.eq(a, b)`), no `not`, no conditional expression, no `and`/`or`, no
comprehension filter: the one branch a service has is **one** `match` on the
`ts.Outcome` a transition returned (**Outcomes**, above), whose
subject is a call on a domain object *whose method is annotated to return that
outcome*, and the one loop
is `while True:` ended by a match arm's `break`. A second decision in the same
method is a second `match`, and a second `match` is a finding — call the port
every time, fold the question into the first request, or make it a workflow
(**Orchestrators, actions, jobs**, below). What an arm does after deciding is
not itself a decision: it may drive a `-> None` transition that records the
answer as state, and the method then persists unconditionally. Every
translation the method needs is a **mapper** — a class that *is* the spec or
DTO it maps to (`MapTo…`, **Application ports** below) — so the service names
the use case and never spells a field out.

```python
# campaign/application/service.py (verified impl: examples/python-app/)
class CampaignService(ts.ApplicationService):

    def __init__(
        self,
        repo: campaign_repository.CampaignRepository,
        identity_gateway: campaign_identity.CampaignIdentity,
        queries: campaign_queries.CampaignQueries,
    ) -> None:
        self._repo = repo
        self._identity_gateway = identity_gateway
        self._queries = queries

    def create_campaign(self, req: client.CreateCampaignRequest) -> client.CampaignView:
        issued_campaign_identity = self._identity_gateway.issue(
            campaign_identity.IssueCampaignIdentityRequest()
        )
        c = campaign.Campaign(MapToCampaignSpec(
            create_campaign_request=req,
            issued_campaign_identity=issued_campaign_identity,
            links=short_links.ShortLinksSpec(links=()),
        ))
        save_request = MapToSaveCampaignRequest(campaign_aggregate=c)
        self._repo.save(save_request)
        find_campaign_view_request = campaign_queries.FindCampaignViewRequest(
            campaign_id=save_request.id,
        )
        found_campaign_view = self._queries.find_view(find_campaign_view_request)
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            found_campaign_view=found_campaign_view,
        )

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        find_campaign_view_request = campaign_queries.FindCampaignViewRequest(
            campaign_id=campaign_id_text,
        )
        found_campaign_view = self._queries.find_view(find_campaign_view_request)
        return MapToCampaignView(
            find_campaign_view_request=find_campaign_view_request,
            found_campaign_view=found_campaign_view,
        )
```

- **No `for` over domain objects, no arithmetic on domain quantities, no
  conditional that computes domain state** in the method — the leakage checks
  (`application-services.md#domain-logic-leakage-checks`). The service
  branches one way: `match` on an outcome, closed by `assert_never`.
- **Return a DTO** (a `client.py` view), never the domain object.
- **Every dependency is a port, injected, never built here** (TB081), and the
  port is declared in the context's `application/ports/` package — never in
  the service module (**Application ports**, below).
- **Ports speak port DTOs and primitives, never domain objects** (TB081) — the
  application's mapping module turns the aggregate into a `SaveCampaignRequest`
  on the way to persistence and rebuilds it from the response's
  `CampaignRecord` on the way back. The service never hands a domain object
  across a port, and the port module never learns a domain type exists.
- **The transaction boundary is a `ts.Store`** (**Application ports**, below).
  The service opens exactly one per method — `async with
  self._widget_store.transaction() as widgets_repo:` — and writes nothing of
  the mechanics; the driver's connection and commit live in the adapter behind
  the store. One unit of work per use case; do **not** invent an ORM lifecycle
  here.

## Application ports {#ports}

Every outbound dependency a context owns — a repository, a peer-context
gateway, a vendor client — is a `ts.Port` `Protocol` in the context's
**`application/ports/` package**. Never a `ports.py` module (TB041); the
package's `__init__.py` is empty (TB042). **One module, one port**, plus the
`ts.Request`/`ts.Response` DTOs that port speaks and nothing else (TB052).

**A transaction boundary is a `ts.Store`.** When a use case must read, decide,
and write inside one transaction, the port splits in two and both live in the
one module: a long-lived `ts.Store` and the short-lived, connection-bound
`ts.Port` it yields. The store declares exactly one method, `transaction()`,
taking nothing and returning `typing.AsyncContextManager` of the port declared
beside it (TB081); a ports module holds at most one store, and a store without
its port is a finding (TB052). A service may depend on a store as well as on a
port (TB081). The store is the only place a ports module may name
`typing.AsyncContextManager` — `contextlib` stays out of a ports module
(TB067), so the implementations, not the declaration, carry
`@contextlib.asynccontextmanager`.

```python
# alpha/application/ports/widget_repository.py (verified impl: examples/asyncpg/)
class WidgetRepository(ts.Port, typing.Protocol):

    async def save_widget(self, request: SaveWidgetRequest) -> SaveWidgetResponse: ...

    async def load_widget(self, request: LoadWidgetRequest) -> LoadWidgetResponse: ...


class WidgetStore(ts.Store, typing.Protocol):

    def transaction(self) -> typing.AsyncContextManager[WidgetRepository]: ...
```

The service writes the boundary and never the mechanics:

```python
async with self._widget_store.transaction() as widgets_repo:
    loaded = await widgets_repo.load_widget(MapToLoadWidgetRequest(sought))
```

One transaction per service method, and nothing crosses a context while one is
open — a gateway call inside an open transaction deadlocks against its own
pool. Not checked; a rule you keep.

```python
# campaign/application/ports/campaign_repository.py (verified impl: examples/errorspy/)
from __future__ import annotations

import enum
import typing

import tesser.application as ts


class CampaignLookup(enum.Enum):
    FOUND = "found"
    MISSING = "missing"


class LinkRecord(ts.Response):

    def __init__(self, slug: str, target_url: str) -> None:
        self.slug = slug
        self.target_url = target_url


class CampaignRecord(ts.Response):

    def __init__(self, id: str, window: WindowRecord, links: tuple[LinkRecord, ...]) -> None:
        self.id = id
        self.window = window
        self.links = links


...                                   # WindowRecord, SaveCampaign{Request,Response} — elided


class FindCampaignRequest(ts.Request):

    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id


class FindCampaignResponse(ts.Response):

    def __init__(self, outcome: CampaignLookup, campaigns: tuple[CampaignRecord, ...]) -> None:
        self.outcome = outcome
        self.campaigns = campaigns


class CampaignRepository(ts.Port, typing.Protocol):

    def save(self, request: SaveCampaignRequest) -> SaveCampaignResponse: ...

    def find(self, request: FindCampaignRequest) -> FindCampaignResponse: ...
```

- **The module is a leaf** (TB067): it imports `tesser.application` exactly
  once as `ts` (TB050) plus the pure stdlib the shape needs (`typing`, `enum`,
  `__future__`) — **nothing from its own tree, its ports siblings included**.
  That leaf rule is what makes DTO sharing unrepresentable rather than merely
  forbidden: `ports/b.py` cannot see a request declared in `ports/a.py`, and a
  module declares exactly one port, so two ports can never share a DTO.
- **Imports and classes only** (TB051). No module-level functions, no
  constants — a ports module holds no logic to import, which is also why the
  outcome cannot degrade into a bare string constant.
- **One `ts.Request` in, one `ts.Response` out, and the body is `...`**
  (TB081, TB051). No extra parameters, no `*args`/`**kwargs`, no second return
  channel — an exception carrying the "missing" case is exactly what one
  request in / one response out exists to prevent.
- **A port DTO field is never a union (optional included) and never a bare
  `bool`** (TB080), and **a port DTO is never subclassed** (TB052) — a
  response hierarchy is a union mypy cannot check for exhaustiveness. The
  bare-bool clause covers a `Client` request/response DTO too, where the fix
  is the canonical string rather than an enum (`domain-return.md` rule 8).
- **A DTO compares by value.** `tesser.application` and `tesser.context`
  `Request`/`Response` (a port DTO and a client DTO alike) are equal when
  they are the same concrete type with equal fields, and hash the same way,
  so a nested record or a tuple of records compares through; a subclass may
  not redefine `__eq__`/`__hash__`. A test that wants "the reloaded save
  request equals the original" writes `loaded == original`; it never
  projects both to a tuple first (maintainer ruling 2026-08-30). The
  protocol tier's `tesser.srv` request/response is a `Record` — equal by
  value too, but unhashable.
- **A multi-outcome answer is an enum outcome plus payload; a collection is a
  tuple.** Where cardinality *is* the answer (list-all), the tuple alone says
  it — no outcome enum. The enum is a plain `enum.Enum`, never `StrEnum`/
  `IntEnum` or a hand-mixed base (`class Outcome(str, enum.Enum)`) (TB052):
  a str- or int-backed member compares equal to a raw literal and reopens
  the typo the enum closes.
- **Mapping stays in the application role, never in ports.** A sibling
  `mapping.py` / `views.py` owns domain ↔ port-DTO translation — it may import
  the domain and the ports package; ports import neither.

The reader is a **mapper** (TB080): a class that subclasses `ts.Mapper` and
then the one spec or DTO it maps to, so constructing the mapper constructs
the target. Its `__init__` takes whole objects (never a field pulled off
one), matches exhaustively where the port answer has outcomes, and calls
`super().__init__(...)` exactly once; it stores nothing of its own and has
no other method, and it is named `MapTo` plus its target. A nested target
is a nested mapper when it needs its own translation
(`budget=MapToMoneySpec(request)`) or a plain spec constructor when it does
not (`window=values.DateWindowSpec(start=…, end=…)`); a collection is
`tuple(MapToLinkRecord(link) for link in c.links)`. The service then reads
`campaign.Campaign(MapToCampaignSpec(request, found))` and
`self._repo.save(MapToSaveCampaignRequest(c))`: the mapping is hidden in one
place, and the service reads as the use case (maintainer ruling 2026-08-25,
superseding the 2026-08-17 accessor mapper, whose every field the service
had to re-name at the construction site). A spec built by a mapper is still
a spec — bind it, pass it whole, never read its fields in the service
(TB083 types the local as the target).

An adapter maps too, and it has its own base: `tesser.adapters.Mapper`,
same contract, declared beside the gateway or repository that uses it so a
`gateways/` or `repositories/` module still imports only `tesser.adapters`
(maintainer ruling 2026-08-30). A gateway or repository ends in
`return MapToX(answer)` and reads as call-then-map, never as logic. One
carve-out applies on that side only: **an adapters mapper may take a
primitive**, because a repository wrapping a client that hands back a `bool`
or a row value is the normal case (`MapToHasKeyResponse(result: bool)`).
The application side is unchanged — a mapper there takes whole objects,
never a field already pulled off one (TB080).

```python
# campaign/application/views.py (verified impl: examples/errorspy/)
class MapToCampaignSpec(ts.Mapper, campaign.CampaignSpec):

    def __init__(
        self,
        find_campaign_request: campaign_repository.FindCampaignRequest,
        found_campaign: campaign_repository.FindCampaignResponse,
    ) -> None:
        match found_campaign.outcome:
            case campaign_repository.CampaignLookup.FOUND:
                record = found_campaign.campaigns[0]
            case campaign_repository.CampaignLookup.MISSING:
                raise errors.not_found(
                    "campaign_missing", f"no campaign {find_campaign_request.campaign_id!r}"
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            id=record.id,
            window=values.DateWindowSpec(start=record.window.start, end=record.window.end),
            links=tuple(MapToShortLinkSpec(link_record=link) for link in record.links),
        )
```

`typing.assert_never` is the whole point of the enum: add a third outcome and
every reader that does not handle it fails `mypy --strict` at the missed
branch. Six encodings of the same two-outcome answer were measured against the
repo's silent-site metric in `docs/design-application-ports.md` — the enum is the only
union-free one that scores **zero** silent sites; a `found: bool` flag and a
0-or-1 tuple each leave the reader silently wrong.

## Orchestrators, actions, and jobs {#orchestrators-actions-jobs}

A workflow on a durable-execution engine (Restate, Temporal) adds two
application kinds that are **not** application services, and one adapter kind
the engine calls back into. The rules and the why are
`docs/design-app-service-types.md`; the verified impl is
`examples/durable-execution/`. All three keep the service body rules above
(one `ts.Request` in, one `ts.Response` out, `match` only, mappers for every
translation) — what differs is scope, reach, and what each may depend on.

- **An orchestrator** (`ts.Orchestrator`, in `application/orchestrators/`,
  one per module) is built **per invocation by a job**, with that
  invocation's **job context** — `ts.JobContext`, the engine-neutral
  protocol for what a step may do inside an invocation (`call(step,
  request)` today; `sleep`, `wait_for`, `send` when an orchestrator needs
  them). It depends on exactly one job context plus **action ports** — a port
  some application client speaks (below) — never a repository, never the
  workflow-start port; it stores nothing but those, because everything it
  does between journaled calls re-runs on replay. It threads the job context
  as the **leading argument of every action-port call**, the way Go threads
  `ctx`. It takes the workflow port's own request and returns a response it
  declares itself (the one `ts.Response` allowed outside a ports module).
- **A class of actions** (`ts.Actions`, beside the services) takes **exactly
  one port** in `__init__` and each public method calls it **exactly once**:
  an action is the engine's retry unit, and one side effect per unit is what
  keeps a retry safe. It speaks the port DTOs of the port an orchestrator
  calls it through, and it is **not on the public `Client`**.
- **An application client** (`tesser.application.Client`, in
  `application/client/`, one protocol per module named for the actions it
  fronts) is how a job reaches a class of actions — the inbound twin of a
  port. Same word as the context client, different package, exactly as
  `Request`/`Response` already are. It imports exactly one ports module and
  speaks its DTOs; only a job may import it.
- **A job** (`ts.Job`, in `adapters/jobs/`) is where the engine hands work
  back to us. A handler calls the context client; **a job calls an
  application client or constructs an orchestrator** — wrapping the
  invocation's engine context as its own `ts.JobContext` implementation
  (`RestateJobContext(ctx)`, also in `adapters/jobs/`) first. Every gateway
  and every repository is built once by the component and **never stores an
  invocation's context** (TB081); an action-port method takes the job context
  as its leading parameter and the gateway does
  `job.call(self._quote, request)`. Jobs carry placement and import rules
  only for now.

```python
# ordering/application/client/order_actions.py (verified impl: examples/durable-execution/)
class Client(ts.Client, typing.Protocol):

    def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse: ...


# ordering/application/order_actions.py (verified impl: examples/durable-execution/)
class OrderActions(ts.Actions):

    def __init__(self, catalog: catalog_repository.CatalogRepository) -> None:
        self._catalog = catalog

    def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        quoted_sku = order.Sku(request.sku)
        priced = self._catalog.price(MapToPriceRequest(quoted_sku))
        return MapToQuoteResponse(priced)


# ordering/application/ports/quoting.py (verified impl: examples/durable-execution/)
class Quoting(ts.Port, typing.Protocol):

    async def quote(self, job: ts.JobContext, request: QuoteRequest) -> QuoteResponse: ...


# ordering/application/orchestrators/order_orchestrator.py (verified impl: examples/durable-execution/)
class RunResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents


class OrderOrchestrator(ts.Orchestrator):

    def __init__(self, job: ts.JobContext, quotes: quoting.Quoting) -> None:
        self._job = job
        self._quotes = quotes

    async def run(self, request: order_workflow.StartRequest) -> RunResponse:
        running = order.Order(MapToOrderSpec(request))
        quoted = await self._quotes.quote(self._job, MapToQuoteRequest(running))
        total = running.total(MapToPriceSpec(quoted))
        return MapToRunResponse(running, total)


# ordering/adapters/gateways/restate_quoting.py (verified impl: examples/durable-execution/)
class RestateQuoting(ts.Gateway):                       # built once; holds the handler function only

    def __init__(self, quote: abc.Callable[[typing.Any, quoting.QuoteRequest], abc.Awaitable[quoting.QuoteResponse]]) -> None:
        self._quote = quote

    async def quote(self, job: ts.JobContext, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        return await job.call(self._quote, request)


# ordering/adapters/jobs/restate_context.py (verified impl: examples/durable-execution/)
class RestateJobContext(ts.JobContext):                 # the one per-invocation object

    def __init__(self, ctx: restate.Context) -> None:
        self._ctx = ctx

    async def call[I, O](self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I) -> O:
        return await self._ctx.service_call(step, request)


# ordering/adapters/jobs/restate.py (verified impl: examples/durable-execution/)
class RestateActionJobs(ts.Job):

    def __init__(self, actions: order_actions_client.Client) -> None:
        self.service = restate.Service("OrderingActions")

        @self.service.handler(...)
        async def quote(ctx: restate.Context, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
            return actions.quote(request)

        self.quote = quote


class RestateWorkflowJobs(ts.Job):

    def __init__(self, quotes: quoting.Quoting) -> None:
        self.workflow = restate.Workflow("Ordering")

        @self.workflow.main(...)
        async def run(ctx: restate.WorkflowContext, request: order_workflow.StartRequest) -> order_orchestrator.RunResponse:
            orchestrator = order_orchestrator.OrderOrchestrator(
                restate_context.RestateJobContext(ctx), quotes
            )
            return await orchestrator.run(request)

        self.run = run


# ordering/component/component.py (verified impl: examples/durable-execution/)
class Ordering(ts.Component):

    def __init__(self, cfg: config.Config) -> None:
        self._catalog = memory.MemoryCatalogRepository()
        self._actions = order_actions.OrderActions(self._catalog)
        action_jobs = restate_jobs.RestateActionJobs(self._actions)
        workflow_jobs = restate_jobs.RestateWorkflowJobs(restate_quoting.RestateQuoting(action_jobs.quote))
        self.jobs: tuple[restate_jobs.RestateActionJobs, restate_jobs.RestateWorkflowJobs] = (action_jobs, workflow_jobs)
        self.client: client.Client = order_service.OrderService(
            restate_workflow.RestateOrderWorkflow(cfg.ingress, workflow_jobs.run)
        )
```

- **Messages are declared once, on the port.** The engine is a relay, so the
  send side and the receive side of one message are not independent: the
  gateway sends the port's `ts.Request`, the job receives it, and the
  application client speaks the same shape. No wire types.
- **Where the SDK cannot serialize a `ts.Request` itself, the job's package
  brings a serde** (`ts.Serde`, in `adapters/jobs/`, maintainer ruling
  2026-08-30). It declares exactly `serialize` and `deserialize` over **one
  type parameter**, may hold at most the target type it was built with, and
  branches on nothing but the empty payload — a serde with decision logic is
  a finding (TB081, TB082), because a decision made on the wire is one no
  domain object owns. It is the **one adapter class allowed a base from
  outside the tree** (TB052): the engine is the caller and the SDK's ABC is
  the shape it calls, so the class reads
  `class RecordSerde[T](ts.Serde, restate.serde.Serde[T])`.
- **A component publishes exactly `client` and `jobs`**, each typed; every
  other attribute is private (TB081). `jobs` is one job or a tuple of them;
  where it is a tuple the host mounts the definitions of each — `[d for job in
  app.<context>.jobs for d in job.definitions()]` — and knows nothing else
  about the engine.
- **Reach is carried by the adapter kind package** (TB060): `handlers/` →
  the context client; `jobs/` → `application.client`,
  `application.orchestrators`, `application.ports`;
  `gateways/` and `repositories/` → `application.ports`; a kind imports only
  its own kind. Every adapters module lives in one of the four kind
  packages and holds the kind its package names (TB041/TB052).
- **Not yet ruled:** payload versioning on a durable leg (a field added to a
  port DTO changes the bytes an in-flight journal holds — port DTOs on a
  durable leg are append-only until it is); the Temporal mirror binds its
  serde at the client/worker rather than at a decorator, and the kinds are
  expected to survive it unchanged.

## Repositories

The port is declared in `application/ports/` (**Application ports**, above), as a `ts.Port`
`Protocol` speaking port DTOs; the adapter subclasses `ts.Repository` and
satisfies it structurally (like Go's implicit satisfaction). Whole aggregate
in — as a request DTO — reconstructed aggregate out, no business logic
(`repositories.md`). How the aggregate decomposes is the serialization norm
(`serialization.md` rules 6-8).

```python
# campaign/adapters/repositories/repo_storage.py (verified impl: examples/errorspy/)
import tesser.adapters as ts

import campaign.application.ports.campaign_repository as campaign_repository


class StorageCampaignRepository(ts.Repository):

    def __init__(self, storage: FakeStorage) -> None:
        self._storage = storage

    def save(
        self, request: campaign_repository.SaveCampaignRequest
    ) -> campaign_repository.SaveCampaignResponse:
        self._storage.put(request.id, _to_record(request))
        return campaign_repository.SaveCampaignResponse()

    def find(
        self, request: campaign_repository.FindCampaignRequest
    ) -> campaign_repository.FindCampaignResponse:
        try:
            row = self._storage.load(request.campaign_id)
        except StorageMiss:
            return campaign_repository.FindCampaignResponse(
                outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
            )
        return campaign_repository.FindCampaignResponse(
            outcome=campaign_repository.CampaignLookup.FOUND,
            campaigns=(_from_record(request.campaign_id, row),),
        )
```

- **The import block is the rule made visible** (TB060): the only module this
  adapter imports from its own context is its ports module. It cannot reach
  the service, the mapping module, or the domain — so the gateway is decoupled
  from the implementation it serves by the import matrix, not by discipline.
- **The adapter speaks records** (TB081): port DTOs and primitives cross the
  port; the *application layer* reconstructs the aggregate through its spec
  (`campaign.Campaign(MapToCampaignSpec(request, found))`), so invariants re-run — never build a
  domain object by assigning attributes.
- **No domain math.** A finder may filter/order (persistence selection);
  summing or rule-checking is a leak.
- **Assemble the answer with a mapper, not by hand** (`ts.Mapper` from
  `tesser.adapters`, declared beside the adapter): the method ends in
  `return MapToFindCampaignResponse(row)` so the adapter reads as
  call-then-map. On the adapter side that mapper may take the primitive the
  client handed back — see **Application ports** above.
- Persistence backends — SQLAlchemy, async drivers — are consumer-specific;
  the `Protocol` is the stable contract, the backing store is not this
  skill's decision. The worked examples use an in-memory map and a fake
  key-value store; a database-backed one satisfies the same port.

## The composition root

The public interface + the wiring site (`public-interface.md`,
`app.md`). The context's `client.py` holds the `ts.Client` `Protocol`
and its `ts.Request`/`ts.Response` DTOs; the application service **satisfies
the Protocol structurally** (no inheritance, no adapter code); the app-level
`bootstrap` chooses the concretes and injects the `Client` into the handlers.

**The public surface — a `Protocol` + DTOs, no implementation:**

```python
# campaign/client/client.py (verified impl)
class CreateCampaignRequest(ts.Request):

    def __init__(self, budget_amount: str, budget_currency: str) -> None:
        self.budget_amount = budget_amount
        self.budget_currency = budget_currency


class CampaignView(ts.Response):
    ...                                     # DTO — primitive fields, never a domain object


class Client(ts.Client, Protocol):
    def create_campaign(self, req: CreateCampaignRequest) -> CampaignView: ...
    def resolve(self, req: ResolveRequest) -> ResolveResponse: ...
    ...                                     # add_link, deactivate_link, get_campaign, list_links
```

Because `Client` is a `Protocol`, any object whose methods match satisfies
it — the service *is* a `Client`, Python's analog of Go's embed-to-satisfy.
The wiring function's `-> client.Client` return annotation is the
compile-time proof (mypy's analog of Go's `var _ orders.Client =
(*client)(nil)`): if a service method's signature drifts from the Protocol,
type checking stops there. **Reshape only when the surface must differ**
(rename, subset, composition) — then an explicit class that holds the
service and delegates.

**The composition root — the settled app anatomy** (`app.md`,
`component.md`; verified impl `examples/python-app/`). Each context owns a
`wiring/` package (its spec-shaped `Config` + a `build` contract); the
app-level `bootstrap` nests the configs and constructs each component in
dependency order. A component selects its impl inline where it constructs
(coordinate `if`s in `__init__` — the verified impl has no helper method); module
constants are `Final`; every import is a module import, and a context module
is imported **as an aliased module** (TB053) — the analyzer resolves a name
as attribute over alias.

```python
# campaign/component/component.py (verified impl) — coordinate-driven, fail-fast, uniform
class Campaign(ts.Component):
    def __init__(self, cfg: config.Config, policy: target_policy.TargetPolicy) -> None:
        if not cfg.storage:
            raise invalid("missing_coordinate", "campaign storage coordinate is required")
        if cfg.storage != "memory":
            raise invalid("unknown_backend", f"campaign storage {cfg.storage!r} not supported")
        self._repo = repo_memory.InMemoryCampaignRepository()  # the concrete it chose, held by its own type
        self.client: client.Client = service.CampaignService(self._repo, policy)

    def close(self) -> None:
        self._repo.close()                          # releases only what it constructed


# bootstrap/app.py (verified impl) — build ONCE, in dependency order
class App(ts.App):
    def __init__(self, cfg: config.Config) -> None:
        linkpolicy = linkpolicy_wire.LinkPolicy(cfg.linkpolicy)
        try:
            policy = target_policy.LinkPolicyTargetPolicy(linkpolicy.client)  # cross-context
            campaign = campaign_wire.Campaign(cfg.campaign, policy)           # adapter built HERE
        except Exception:
            linkpolicy.close()                      # partial construction unwinds
            raise
        ...
```

- **A component exposes a `Client` and a `close()`** — the Protocol and its own
  teardown, never the concrete service or a domain type. A component with no
  infrastructure has an empty `close()`, which is honest rather than ceremonial.
 — the Protocol and a resource
- **The port types wiring annotates come from `application/ports/`**
  (**Application ports**) — `campaign_repository` and `target_policy` above are ports
  modules, not the service module. Wiring is the one role that may hold both
  the port and the concrete: it reaches application, adapters, and client
  (TB060), which is exactly what choosing an implementation requires.
- **Each context gets only its slice** (`cfg.campaign`), and cross-context
  adapters are constructed in `new` and injected — only the root knows two
  contexts at once. The import matrix is machine-enforced: bootstrap builds
  from wiring, clients, and adapters, never domain or application (TB063);
  a context reaches another context only through its client, and only from
  gateways and wiring (TB061).
- **`App.close()` closes each component it built**, one named call apiece. No
  ordering doctrine: with strict ownership no component's close depends on
  another still being open.
- **No `context.Context`.** A plain synchronous Python service has no such
  idiom; thread a unit-of-work/session where your codebase already does.
- **The degenerate case:** a single-context app can collapse this to one
  hand-wired `main` that chooses the repo, builds the service, and composes
  the `Client` — the rules are unchanged: one place chooses, the contract
  crosses, nothing else imports the concretes. Grow the full
  `bootstrap`/`wiring` shape when a second context (or a second host)
  arrives.

## Inbound handlers and hosts

The two-layer transport split (`handlers.md`, `srv.md`; verified impl
`examples/python-app/campaign/adapters/handlers/http.py` and
`examples/python-app/srv/`). **The host routes; the handler transforms.** The
host owns the transport — the socket, the route table, raw body **bytes**,
framing, headers on the wire — and is the env edge that calls the one `from_env`
loader, builds the graph once, and runs under a runner that installs SIGTERM. The
per-context handler owns the content — raw bytes ↔ `Client` DTOs, and the
response's `Content-Type` — through one respond path.

**The protocol package is the app-owned vocabulary**: handlers define it,
hosts conform to it. Its records are `ts.Request`/`ts.Response` subclasses
(frozen wire records — one-shot construction, kwargs checked against the
class's annotations, value equality, no subclass overrides), its refusals
are `ts.Rejection`s, and the endpoint contract is a `ts.Port`:

```python
# protocol/http.py (verified impl)
class BadRequest(ts.Rejection): ...
class PayloadTooLarge(ts.Rejection): ...
class StreamingUnsupported(ts.Rejection): ...


class HttpRequest(ts.Request):

    method: str
    path: str
    path_params: Mapping[str, str]
    query_params: Mapping[str, str]
    headers: Mapping[str, str]
    body: bytes                                   # raw; the handler interprets it

    def json_body(self) -> dict[str, object]:     # the record carries its readers
        return _json_object(self.body)

    def path_param(self, name: str) -> str: ...


class HttpResponse(ts.Response):

    status_code: int
    body: bytes                                   # raw; the handler serialized it
    headers: Mapping[str, str]

    @classmethod
    def json(cls, status_code: int, body: dict[str, object], headers: Mapping[str, str] | None = None) -> HttpResponse: ...

    @classmethod
    def problem(cls, status_code: int, code: str, detail: str) -> HttpResponse:
        return cls.json(status_code, {"type": f"/problems/{code}", "detail": detail})

    @classmethod
    def redirect(cls, url: str, status_code: int = 302) -> HttpResponse: ...


class Endpoint(ts.Port, Protocol):
    def __call__(self, request: HttpRequest, /) -> HttpResponse: ...
```

```python
# campaign/adapters/handlers/http.py (verified impl)
class Handler(ts.Handler):
    def __init__(self, client: client.Client) -> None:
        self._client = client                     # injected; never constructed

    def add_link(self, req: HttpRequest) -> HttpResponse:
        body = req.json_body()                    # raw bytes -> JSON; the handler's call
        view = self._client.add_link(
            client.AddLinkRequest(
                campaign_id=string_field(body.get("campaign_id")),
                slug=string_field(body.get("slug")),
                target_url=string_field(body.get("target_url")),
            )
        )
        return HttpResponse.json(200, _campaign_body(view))

    def resolve(self, req: HttpRequest) -> HttpResponse:
        resp = self._client.resolve(client.ResolveRequest(slug=req.path_param("slug")))
        return HttpResponse.redirect(resp.target_url)   # 302 + Location, empty body
```

- **Wire records carry their behavior** (the srv-vocabulary ruling,
  2026-08-08): `json_body`/`path_param` live on `HttpRequest`,
  `json`/`problem`/`redirect` on `HttpResponse` — not as loose module
  functions. The DTO-purity objection dissolves on the package-scoped kind
  grammar: `ts.srv.Request`/`Response` are distinct kinds from the context
  DTOs, which keep carrying data and nothing else.
- **The body is `bytes` on both sides**, so the edge is content-type-agnostic:
  the handler reads `req.json_body()` (or the bytes as an image), and
  `HttpResponse.json`/`redirect` serialize and set the `Content-Type` on the
  way out. The host neither parses nor serializes.
- **Every endpoint has the one signature** (`Endpoint`), so the host can hold
  them all in a table and route by it instead of growing a branch per
  endpoint.
- **The handler never sees transport.** Everything it needs rides in the one
  `HttpRequest`, so a test builds one by hand (bytes body included) and
  asserts on the returned `HttpResponse`. Only a handler imports its own
  context's client (TB060).
- **`respond` is the whole error table for the mechanism** (it lives with the
  host, `srv/http/host.py`): shape guard → 400, domain kind → status through
  the one pure mapper (`status_for` over the closed `Kind` set), infra → 503,
  unexpected → 500 — plus the host's own framing rejections (413, 411)
  through the same table. `HttpResponse.problem` renders the RFC 9457-shaped
  object — decided once, at this path.

```python
# srv/http/host.py (verified impl) — the route table: the whole URL surface, one place
def routes_for(app: App) -> tuple[Route, ...]:
    campaign = http.Handler(app.campaign)         # one handler per exposed context,
    reports = reports_http.Handler(app.reports)   # built once from the single App
    return (
        Route("POST", "/campaigns", campaign.create_campaign),
        Route("POST", "/links", campaign.add_link),
        Route("POST", "/links/deactivate", campaign.deactivate_link),
        Route("GET", "/campaigns/{campaign_id}", campaign.get_campaign),
        Route("GET", "/r/{slug}", campaign.resolve),
        Route("GET", "/reports/links-by-verdict", reports.links_by_verdict),
    )


        def _dispatch(self, method: str) -> HttpResponse:   # the host's entire request path
            def run() -> HttpResponse:
                found = match(routes, method, self.path)     # router: URL knowledge lives there
                if found is None:
                    return HttpResponse.problem(404, "not_found", "unknown route")
                declared = self.headers.items()
                headers = {name.lower(): value for name, value in declared}
                body = self.rfile.read(buffered_length(declared))
                return found.endpoint(HttpRequest(
                    method=method, path=self.path,
                    path_params=found.path_params, query_params=found.query_params,
                    headers=headers, body=body,              # raw bytes; the host never decodes
                ))

            return respond(run)


# srv/http/main.py (verified impl) — the host: env edge, build once, hand to the runner
class HttpEdge(ts.Host):

    def __init__(self) -> None:
        self._app = load()                   # ONCE per process; validates fail-fast
        self._host = HttpHost((self._app.http.host, self._app.http.port), self._app)
        self._stop = threading.Event()

    def stop(self, signum: int, frame: Optional[FrameType]) -> None:
        self._stop.set()

    def run(self, argv: list[str]) -> int:
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        try:
            self._host.run(self._stop)             # serves until stopped
        finally:
            self._app.close()                      # guaranteed, signal or not
        return 0


if __name__ == "__main__":
    ts.main(HttpEdge().run)                  # the ONE statement a srv module holds outside a class
```

- **Route, read bytes, call, write bytes — nothing between the steps.** No
  `json.loads`, no hardcoded `Content-Type`, no field name, no `Client` call.
  `buffered_length` (a reader on the request's headers) decides the framing
  (finite and under-cap → read it; chunked → 411; over cap → 413); `_send`
  writes the `status_code`, the raw `body` bytes, and copies the handler's
  `headers`. That is the host's entire share of the wire.
- **Buffered, with the streaming boundary named.** A declared, bounded body is
  read; `Transfer-Encoding: chunked` is refused with 411 — the honest in-code
  marker that a live/large stream needs a different shape, which is
  **documented, not built**. Reach for a framework when you need streaming,
  multipart, or content negotiation.
- **The route table is app-level.** URLs are the app's decision, not a
  context's: one table names every exposed endpoint. Pattern matching lives
  in `srv/http/router.py` — the only component that knows
  `/campaigns/{campaign_id}` has a parameter in it. A host reaches a context
  only through its handlers (TB063), and a srv module imports `tesser.srv`
  exactly once, as `ts` (TB050).
- **The host's own failures use the same vocabulary** — an unmatched route
  (404), an oversized body (413), a streaming body (411) all render through
  the same `respond`/`problem` path a handler uses, so a client sees one
  error format from the whole process.
- **One loader, one env read.** `from_env` (`bootstrap/config.py`) is the
  single place the app reads the environment, loading app config **and** the
  host's launch config into one `Config`; it stays a pure function (`getenv`
  injected), so it's testable with a dict.
- **The host's `run(argv) -> int` owns the process lifecycle**: it installs
  SIGINT/SIGTERM and calls `app.close()` in a `finally` — a bare
  `finally: app.close()` does **not** survive Python's default SIGTERM.
- **`ts.main(run)` is the process edge, and the only loose statement a srv
  module may hold.** `if __name__ == "__main__": ts.main(Host().run)` — one
  guard, one call, nothing else (TB051). `ts.main` reads `sys.argv` and raises
  `SystemExit` with what `run` returns, so no host touches `argv` or the exit
  code itself; the same line starts a CLI host and an HTTP host.
- **A CLI host** is the same split for a different mechanism. The shared
  vocabulary is `protocol/cli.py`: `CliRequest` carries its arg readers
  (`arg`, `no_extra_args` — `UsageError`, a `ts.Rejection`, on violation),
  `CliResponse` its `ok` builder, and `Command` is the endpoint port.
  `srv/cli/main.py` routes a command name through a table, prints
  `stdout`/`stderr`, exits the `exit_code`; the handler
  (`campaign/adapters/handlers/cli.py`) never touches `argv`, `print`, or
  the process, and the host's error table maps the closed domain `Kind` to
  an exit code via `tesser.errors.exit_code_for` — the CLI's `status_for`. Piped
  **stdin** would be the CLI's "body" and reopens the same
  buffered-vs-stream question as HTTP; none of these commands read it, so it
  stays a named boundary.

## The Spec pattern

Specs are `ts.Spec` subclasses with **primitive leaves** (and nested child
specs) that carry construction data across the layer boundary — plain
attribute assignment in `__init__`, no behavior (a spec only carries
construction data; a method on one is a finding). A structured domain
object's **constructor takes its spec** — that is the single construction
path; it converts each primitive to a value object and validates.

- A spec field is a primitive or a child spec — **never a value object** or
  any domain object the caller must construct — and the one admissible union
  is `X | None` (optionality).
- **Nesting mirrors composition:** `CampaignSpec` holds `MoneySpec` and
  `ShortLinkSpec`s, never flattened prefixed fields; a change to the child's
  construction touches the child's spec only.
- **A leaf value object takes its one primitive** (`Slug(value)`); **any
  domain object with two or more construction values takes exactly one
  spec** (`Money(spec)`, `ShortLink(spec)`, `Campaign(spec)`) — never value
  objects. A parent hands a child spec on whole; only the child's own
  `__init__` reads it.

**Return types:** domain functions return domain types. If callers must
sum/filter/group a returned list before it's useful, introduce the type that
represents the finished result.

## Testing patterns

```python
def test_money_equality() -> None:
    a = money.Money(money.MoneySpec("1.50", "USD"))
    b = money.Money(money.MoneySpec("1.50", "USD"))
    assert a == b
    assert hash(a) == hash(b)

def test_money_rejects_a_malformed_currency() -> None:
    with pytest.raises(DomainError):
        money.Money(money.MoneySpec("1.00", "usd"))

def test_campaign_rejects_a_duplicate_slug() -> None:
    with pytest.raises(DomainError):
        campaign.Campaign(campaign.CampaignSpec(id=CID, budget=BUDGET, links=(LINK, LINK)))

def test_campaign_links_are_defensive() -> None:
    c = campaign.Campaign(campaign.CampaignSpec(id=CID, budget=BUDGET, links=(LINK,)))
    assert isinstance(c.links, tuple)     # callers can't mutate the root
```

- One equality test per VO locking `__eq__` AND `__hash__` semantics (the
  base owns them; the test locks the *representation* — normalization in the
  constructor).
- One rejection test per validation rule (`pytest.raises`).
- One invariant-violation test per aggregate — its reason to exist.
- Defensive-copy assertions on every collection accessor.
- One round-trip test per leaf: `Leaf(str(leaf)) == leaf` locks the canonical
  exit.
- Never `str(a) == str(b)` as an equality assertion (TB004).
- **Placement carries the tier** (`testing.md`): a sibling test lives inside
  the role it exercises (`campaign/domain/test_labels.py`), imports what its
  subject may import plus the subject itself; a test double is a hand-written
  `@ts.fake` implementing the port or client it doubles (TB072), never a
  mocking library (TB030); a builder is a `@ts.helper` that takes defaulted
  primitives and returns a spec.
