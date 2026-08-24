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
tesser norm modules the placement may from-import. The
`# tesser:debt TB062` markers earlier revisions of these excerpts
carried are gone — the app-level `errors`/`serialization` root modules they
excused moved into the tesser runtime.)

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

from tesser.errors import invalid
from tesser.serialization import canonical_str


class CampaignID(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _CAMPAIGN_ID_RE.fullmatch(value):
            raise invalid("invalid_campaign_id", f"campaign id {value!r} must be 16 lowercase hex chars")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)   # canonical exit: one-line delegation to the policy

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

    def __init__(self, amount: str, currency: str) -> None:   # the one constructor: primitives in, child VOs built
        object.__setattr__(self, "_amount", MoneyAmount(amount))
        object.__setattr__(self, "_currency", MoneyCurrency(currency))

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

**Construction (ruled 2026-08-23, superseding both the 2026-07-20
(b)-uniform ruling and the shells revision's value-object allowance):**
construction data is **primitives and specs, never value objects**. A
**value object's** single constructor takes **primitives and child specs**
— `Money("9.99", "USD")` — and builds its child value objects inside; a
value object is never a constructor parameter (a spec field or constructor
parameter typed as a VO is TB080). A **structured domain object** — entity
or aggregate — constructs from **exactly one `ts.Spec`** (the same shape as
Go's `NewCampaign(spec)`), converts the spec's data to value objects in its
`__init__`, and from then on its methods hold, take, and return only value
objects. That `__init__` is the only place a spec is read: everywhere else
code builds a spec and hands it on whole — it never reads a spec's fields
and never stores one (TB083). The one holder besides a spec carrying its
child spec is a mapper assembling a parent spec. There is **no `from_spec`** and no factory of any spelling: on a
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
        self._budget = money.Money(spec.budget.amount, spec.budget.currency)
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

## Application services

Coordination only — no business logic. Four named steps
(`application-services.md`): convert → delegate → persist → respond. Every
dependency is a `ts.Port` `Protocol` (the analyzer requires it), every public
method takes exactly one `ts.Request` and returns a `ts.Response`, and the
method inlines its logic — no delegation chains, at most ten source lines,
one level of branching, a condition satisfied by one domain call.

```python
# campaign/application/service.py (verified impl: examples/errorspy/)
class CampaignService(ts.ApplicationService):

    def __init__(self, repo: campaign_repository.CampaignRepository) -> None:
        self._repo = repo

    def create_campaign(self, req: client.CreateCampaignRequest) -> client.CampaignView:
        c = campaign.Campaign(views.create_spec(req))
        self._repo.save(views.save_request(c))
        return views.campaign_view(c)

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=req.campaign_id))
        c = views.required_campaign(found, req.campaign_id)
        return views.campaign_view(c)
```

- **No `for` over domain objects, no arithmetic on domain quantities, no `if`
  on domain state** in the method — the leakage checks
  (`application-services.md#domain-logic-leakage-checks`).
- **Return a DTO** (a `client.py` view), never the domain object.
- **Every dependency is a port, injected, never built here** (TB081), and the
  port is declared in the context's `application/ports/` package — never in
  the service module (**Application ports**, below).
- **Ports speak port DTOs and primitives, never domain objects** (TB081) — the
  application's mapping module turns the aggregate into a `SaveCampaignRequest`
  on the way to persistence and rebuilds it from the response's
  `CampaignRecord` on the way back. The service never hands a domain object
  across a port, and the port module never learns a domain type exists.
- **Transaction / session boundary is consumer-specific.** Where the unit of
  work opens and commits — a SQLAlchemy `Session`, an async transaction, a
  FastAPI dependency — is a decision for the consuming codebase, not this
  skill. Wrap the use case in one unit of work; do **not** invent an ORM
  lifecycle here.

## Application ports {#ports}

Every outbound dependency a context owns — a repository, a peer-context
gateway, a vendor client — is a `ts.Port` `Protocol` in the context's
**`application/ports/` package**. Never a `ports.py` module (TB041); the
package's `__init__.py` is empty (TB042). **One module, one port**, plus the
`ts.Request`/`ts.Response` DTOs that port speaks and nothing else (TB052).

```python
# campaign/application/ports/campaign_repository.py (verified impl: examples/errorspy/)
from __future__ import annotations

import enum
from typing import Protocol

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


class CampaignRepository(ts.Port, Protocol):

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
  response hierarchy is a union mypy cannot check for exhaustiveness.
- **A multi-outcome answer is an enum outcome plus payload; a collection is a
  tuple.** Where cardinality *is* the answer (list-all), the tuple alone says
  it — no outcome enum. The enum is a plain `enum.Enum`, never `StrEnum`/
  `IntEnum` or a hand-mixed base (`class Outcome(str, enum.Enum)`) (TB052):
  a str- or int-backed member compares equal to a raw literal and reopens
  the typo the enum closes.
- **Mapping stays in the application role, never in ports.** A sibling
  `mapping.py` / `views.py` owns domain ↔ port-DTO translation — it may import
  the domain and the ports package; ports import neither.

The reader matches, exhaustively:

```python
# campaign/application/views.py (verified impl: examples/errorspy/)
def required_campaign(
    found: campaign_repository.FindCampaignResponse, campaign_id: str
) -> campaign.Campaign:
    match found.outcome:
        case campaign_repository.CampaignLookup.FOUND:
            return rebuilt_campaign(found.campaigns[0])
        case campaign_repository.CampaignLookup.MISSING:
            raise not_found("campaign_missing", f"no campaign {campaign_id!r}")
        case _ as unreachable:
            typing.assert_never(unreachable)
```

`typing.assert_never` is the whole point of the enum: add a third outcome and
every reader that does not handle it fails `mypy --strict` at the missed
branch. Six encodings of the same two-outcome answer were measured against the
repo's silent-site metric in `docs/design-application-ports.md` — the enum is the only
union-free one that scores **zero** silent sites; a `found: bool` flag and a
0-or-1 tuple each leave the reader silently wrong.

## Repositories

The port is declared in `application/ports/` (**Application ports**, above), as a `ts.Port`
`Protocol` speaking port DTOs; the adapter subclasses `ts.Repository` and
satisfies it structurally (like Go's implicit satisfaction). Whole aggregate
in — as a request DTO — reconstructed aggregate out, no business logic
(`repositories.md`). How the aggregate decomposes is the serialization norm
(`serialization.md` rules 6-8).

```python
# campaign/adapters/gateways/repo_storage.py (verified impl: examples/errorspy/)
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
  (`Campaign(_campaign_spec(record))`), so invariants re-run — never build a
  domain object by assigning attributes.
- **No domain math.** A finder may filter/order (persistence selection);
  summing or rule-checking is a leak.
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
constants are `Final`; a context module is imported **as an aliased module,
never its members** (TB053).

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

    def json_body(self) -> JSONObject:            # the record carries its readers
        return _json_object(self.body)

    def path_param(self, name: str) -> str: ...


class HttpResponse(ts.Response):

    status_code: int
    body: bytes                                   # raw; the handler serialized it
    headers: Mapping[str, str]

    @classmethod
    def json(cls, status_code: int, body: JSONObject, headers: Mapping[str, str] | None = None) -> HttpResponse: ...

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
- **Value objects take primitives and child specs at their own constructor —
  never value objects** (`Slug(value)`, `Money(amount, currency)`).
  **Entities and aggregates take exactly one spec** (`ShortLink(spec)`,
  `Campaign(spec)`).

**Return types:** domain functions return domain types. If callers must
sum/filter/group a returned list before it's useful, introduce the type that
represents the finished result.

## Testing patterns

```python
def test_money_equality() -> None:
    a = money.Money("1.50", "USD")
    b = money.Money("1.50", "USD")
    assert a == b
    assert hash(a) == hash(b)

def test_money_rejects_a_malformed_currency() -> None:
    with pytest.raises(DomainError):
        money.Money("1.00", "usd")

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
