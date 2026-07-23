# Building domain code in Python

Construction mechanics only — the concepts and the rules' whys live in the
concept files (`value-objects.md`, `entities.md`, `aggregates.md`,
`application-services.md`, `repositories.md`, `domain-services.md`). This file
covers the domain building blocks *and* the boundaries that serve them (application
services, repositories) — not domain objects themselves, but their construction
mechanics live here alongside the objects they orchestrate and persist. Section
headings here are stable anchors; the resolver and the coverage matrix link to
them.

> **Verification status — verified.** The patterns these examples exercise —
> value objects (simple, compound, collection), the entity and aggregate
> lifecycle, the application-service boundary, the repository, and the composition
> root — are backed by runnable, type-checked worked examples under
> `examples/python/`: the **running arc** (`campaign` value objects and
> aggregate, `campaignapp` service + repository, and the
> `linkcampaign`/`linkcampaignimpl`/`main` composition root, wired into a live
> HTTP service) and the **`catalog`** package (the compound value object `Money`
> backed by `decimal.Decimal`, and the collection value object `Labels`). The
> whole tree passes `mypy --strict` and `pytest` in CI, the same bar the Go
> mechanics meet. The app-level anatomy — `bootstrap` + per-context `wiring` +
> `srv` hosts + inbound handlers — is backed the same way by
> `examples/python-app/` (multi-context, self-enforcing tests). A few variants are stated below for completeness but shown for
> shape only — the examples here are all *lifecycle* and *1:1*, so they do not
> exercise a **fact** aggregate/entity that returns a new instance on change, an
> explicit **reshaping** `Client`, or a hand-written `__eq__`/`__hash__`; each is
> marked where it appears. Where a Go/Python difference is load-bearing —
> frozen-dataclass equality vs Go's `Equal`, `Protocol` structural typing vs
> Go's struct embedding, the absence of `context.Context` — it is called out
> inline.

## Value objects

**Simple (wraps a single value) — frozen dataclass, validation in
`__post_init__`:**

```python
from dataclasses import dataclass

from serialization import canonical_str

@dataclass(frozen=True)
class EmailAddress:
    _value: str           # hidden — the primitive never leaks (TB010)

    def __post_init__(self) -> None:
        if "@" not in self._value:
            raise ValueError(f"invalid email address: {self._value!r}")

    def __str__(self) -> str:
        return canonical_str(self._value)   # canonical exit: one-line delegation to the policy helper
```

`frozen=True` gives immutability (assignment raises) and a field-wise
`__eq__`/`__hash__`. `__post_init__` is the **single validation site**: it
runs on every construction path, so an invalid instance is unrepresentable —
there is no bypassable factory. The field is **hidden and stays hidden**: a
leaf value object gets **no accessor at all** — no public field, no `value`
property handing the raw string back (a passthrough accessor is the same
leak as the public field, and TB010 flags both). The leaf's **canonical
exit** is the one conversion dunder matching its backing primitive —
str-backed → `__str__` (as here), int-backed → `__int__`, float-backed →
`__float__`, bytes-backed → `__bytes__`; `Decimal`/`datetime` exit as
canonical text via `__str__` under the explicit per-type policy in
`serialization.md` rule 3. One dunder per leaf, matching its
representation — a second or mismatched one is a disguise. The canonical
form is what the serialization layer carries (`serialization.md`); display
formatting is a presentation concern and never the value object's job. The
round-trip law locks the exit: `EmailAddress(str(email)) == email`, asserted
in a test per leaf.

**Compound (two or more fields): the components are child value objects.**
Not hidden raw primitives — child VOs (maintainer rulings 2026-07-19/20:
`rect.x` returning `"1"` is primitive obsession wearing an accessor; `x` and
`y` are value objects, held and exposed as such). Single-concept behavior
migrates into the child (`MoneyAmount.add` owns the arithmetic — the
reference discipline's `quanta.Decimal` pattern); what remains the
compound's own is exactly the **cross-field invariants** (currency match on
`Money.add`). This is what gives each component's rules one home, makes
same-primitive transposition a type error, and gives serialization a
conformant path (`serialization.md` rule 5).

*The construction REVISIT is closed (2026-07-20, revised same day to
(b)-uniform):* **every structured type has ONE door, and that door is its
own `__init__` taking the spec** — `@dataclass(frozen=True, init=False)`
with `__init__(self, spec)` assigning child VOs via `object.__setattr__`
(TB003 sanctions exactly this site). This is the same single door an entity
has (TB013), and the same shape as Go's `NewMoney(spec)` — one construction
story across types and languages. There is **no `from_spec`** (a factory
classmethod is a second public idiom for the same job) and no reliance on
the dataclass auto-init. On a value object this is machine-enforced and
name-agnostic: **any** classmethod or staticmethod returning its own type is
a second door (TB017) — `from_spec`, `parse`, `new`, `require`, `of` alike.
A leaf whose construction involves conversion
(str → Decimal) takes the **canonical form** at its one door and converts
inside — no `parse` classmethod, no union-typed door (ruled 2026-07-20: a
union adds special cases for what is only a performance benefit). The
cost, priced in deliberately: behavior methods — leaf and compound alike —
that produce new instances re-enter **through the door** via canonical
forms (`MoneyAmount(canonical_decimal(total))`), lossless by the round-trip law, so
every instance that exists passed the one validating door. Revisit only on
a measured performance problem (`TODOS.md`: behavior-rebuild ergonomics).

**Warning — hiding a field breaks keyword construction.** Renaming `amount` to
`_amount` renames the auto-generated `__init__` parameter, so
`Money(amount=..., currency=...)` raises `TypeError` at every call site the
moment you comply with TB010. Don't reach for `Money(_amount=...)` (leaks the
private name) or positional args (unreadable past two fields) — **route
construction through the spec** (`Money(MoneySpec(...))` — the one door), which is
the construction path tests should exercise
anyway. Field data (consumer pilot, 2026-07-19): the field rename itself is
minutes; the construction-site fallout is the real cost, and spec-routing is the
shape that survives it.

```python
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from serialization import canonical_decimal, canonical_str

@dataclass(frozen=True)
class MoneySpec:          # spec: primitive leaves only — the inbound door
    amount: str
    currency: str

@dataclass(frozen=True, init=False)
class MoneyAmount:        # child VO: owns the single-concept rules + behavior
    _value: Decimal

    def __init__(self, value: str) -> None:   # ONE door: the canonical form in
        try:
            parsed = Decimal(value)
        except InvalidOperation as e:
            raise ValueError(f"invalid amount: {value!r}") from e
        if parsed < 0:
            raise ValueError(f"amount must not be negative: {parsed}")
        object.__setattr__(self, "_value", parsed)

    def add(self, other: "MoneyAmount") -> "MoneyAmount":
        return MoneyAmount(canonical_decimal(self._value + other._value))   # re-enter the door

    def __str__(self) -> str:               # canonical exit: the Decimal text policy, one site
        return canonical_decimal(self._value)

@dataclass(frozen=True)
class MoneyCurrency:                        # no conversion needed → the auto-init IS the one door
    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("currency is required")

    def __str__(self) -> str:
        return canonical_str(self._value)

@dataclass(frozen=True, init=False)
class Money:
    _amount: MoneyAmount   # child VOs — invalid Money is unrepresentable by types
    _currency: MoneyCurrency

    def __init__(self, spec: MoneySpec) -> None:   # the one door: spec in, child VOs built
        object.__setattr__(self, "_amount", MoneyAmount(spec.amount))
        object.__setattr__(self, "_currency", MoneyCurrency(spec.currency))

    @property
    def amount(self) -> MoneyAmount:        # components exposed as VOs, never primitives
        return self._amount

    @property
    def currency(self) -> MoneyCurrency:
        return self._currency

    def add(self, other: "Money") -> "Money":
        if self._currency != other._currency:   # cross-field invariant: the compound's own job
            raise ValueError(f"cannot add {self._currency} and {other._currency}")
        total = self._amount.add(other._amount)
        return Money(MoneySpec(amount=str(total), currency=str(self._currency)))  # re-enter the door
```

Note what `Money` does **not** define: any conversion dunder. A compound has
zero — no `__str__`, no "debug display" (`serialization.md` rule 5); the
default `repr` is the debug surface, and logging is its own norm
(`logging.md`).

**Each rule lives on the type that owns it** — the child's `__post_init__`
guards the child; the compound's methods guard only cross-field relations —
so no construction path can skip a rule, and no rule has two homes.
Verified impl: `examples/python/catalog/money.py`.

**Collection (wraps a dict/list):**

```python
@dataclass(frozen=True, init=False)
class Labels:
    _values: tuple[tuple[str, str], ...]        # immutable, hashable storage

    def __init__(self, values: Mapping[str, str]) -> None:
        # ONE door: the collection VO takes the collection, and canonicalizes
        # (sort) on the only path in.
        object.__setattr__(self, "_values", tuple(sorted(values.items())))

    def as_dict(self) -> dict[str, str]:        # copy out, never a reference
        return dict(self._values)
```

Go wraps a `map` and must add `Equal` (a map-backed struct is non-comparable);
Python stores an immutable, **sorted** tuple instead, so the frozen dataclass's
default equality is content-based *and* the value is hashable. `init=False`
plus a hand-written `__init__` is what makes the canonicalization unskippable:
there is exactly ONE way in, so no caller can hold a non-canonical value.
Verified impl: `examples/python/catalog/labels.py`.

**No `new`/`require` factory pair** (TB017). A second door is a second set of
invariants: if `new` is permissive and `require` demands non-empty, what the
type guarantees depends on which door the caller picked — so it guarantees
nothing. When you genuinely need a stricter set, that is a *different type*
with its own invariant, not a second factory on this one.

**Rules of the section:**

- `frozen=True` always; no setters, no mutation — behavior methods return new
  instances. This is total, not domain-scoped: **every dataclass in the tree
  is frozen** — specs, DTOs, and adapter wire shapes included (TB001). Frozen
  costs an inert carrier nothing, and a non-frozen dataclass is invisible to
  the VO classifier, so any scope carve-out would let a would-be domain value
  hide. A boundary shape that genuinely must mutate declares itself with an
  inline `# tessercheck:ignore`.
- **The primitive never escapes** (TB010): no public primitive field, and no
  passthrough accessor returning one — a leaf VO exposes nothing but its
  canonical exit; a compound VO's components are child value objects, held
  and exposed as such. Defensive copy-outs of a collection VO's entries
  (`as_dict`) remain the sanctioned collection read.
- No `Must*` twin is needed: construction already raises on invalid input.
  The Go `New/MustNew` split exists because Go returns errors; Python's
  exception IS the panic path — in tests, construct directly with known-valid
  literals.
- A leaf's conversion dunder is its **canonical form**, not display —
  locked by the round-trip law. The dunder body is a one-line delegation to
  the app-level per-type `canonical_*` policy helper (`canonical_str`,
  `canonical_decimal`, `canonical_datetime`, …); edges consume it via the
  conversion protocol (`str(vo)`, `int(vo)`); display formatting
  belongs to the presentation edge (`serialization.md`). A compound,
  entity, or aggregate defines **no conversion dunder at all** — `repr` is
  the debug surface. Never compare domain objects via `str(a) == str(b)`.

**Equality — pick the correct path:**

- **Frozen dataclass default** (`__eq__` field-wise) is correct when each
  logical value has one representation. Note `Decimal("1.5") ==
  Decimal("1.50")` is numerically `True`, but the two hash the same only
  because Python normalizes numeric hashing — verify equality AND hashing in
  the equality test whenever a field type has multiple representations.
- **Custom equality needed:** implement `__eq__` and `__hash__` **together**,
  never one without the other. This is the entity case — comparison by identity,
  not attributes (see the Entities section, where every entity does exactly
  this). For a *value object* whose field would otherwise compare wrong (a
  case-insensitive code, say), prefer **normalizing on input** in
  `__post_init__` so the default field-wise equality stays correct (this is what
  the collection VO above does — it sorts its entries at its one door). Reach
  for a hand-written `__eq__`/`__hash__` (with `eq=False`) only in the rare case
  where the original representation must be preserved *and* compared by a
  normalized form.

## Entities

```python
@dataclass(frozen=True)
class TransferSpec:       # primitive leaves, nested specs
    id: str
    from_account: AccountRefSpec
    to_account: AccountRefSpec
    amount: MoneySpec

class Transfer:
    def __init__(self, spec: TransferSpec) -> None:
        # The single construction path: the constructor takes the spec, builds
        # each child value object via its own constructor (error context added),
        # and enforces any cross-field invariant. There is no second constructor.
        try:
            self._id = TransferID(spec.id)
        except ValueError as e:
            raise ValueError(f"invalid transfer ID: {e}") from e
        # ... each remaining child via its own constructor, error context added ...

    @property
    def id(self) -> TransferID:
        return self._id

    def __eq__(self, other: object) -> bool:      # identity, not attributes
        return isinstance(other, Transfer) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)
```

- Fields are value objects, never raw primitives; underscore-private with
  read-only `@property` accessors, no setters.
- Equality is **identity**: `__eq__`/`__hash__` by ID, defined together.
- **Fact entities:** no mutation methods; a state change returns a new
  instance.
- **Lifecycle entities:** transition methods that guard state:

```python
def activate(self) -> None:
    if self._status is not Status.DRAFT:
        raise InvalidTransition("can only activate a draft contract")
    self._status = Status.ACTIVE
```

Two states → a guard like this; more → a transition table, not stacked
conditionals.

## Aggregates

```python
class Operation:
    def __init__(self, id: OperationID, transfers: list[Transfer]) -> None:
        if not balanced(transfers):                 # the cross-object invariant
            raise ValueError("operation does not balance")
        self._id = id
        self._transfers = list(transfers)           # own your copy

    @property
    def transfers(self) -> tuple[Transfer, ...]:    # defensive copy out
        return tuple(self._transfers)

    __eq__ = None  # type: ignore[assignment]  # comparing aggregates is a bug
    __hash__ = None  # type: ignore[assignment]
```

- The invariant is checked in `__init__` — an unbalanced Operation is
  unrepresentable.
- Setting `__eq__ = None` makes comparison raise `TypeError` at runtime — the
  closest Python gets to Go's compile-time non-comparability. (If the
  aggregate must live in sets/dicts, use identity equality by ID instead,
  like an entity — never field-wise.)
- Children are copied in and copied out (`tuple(...)`); the backing list never
  escapes.
- **Fact aggregates:** state changes return new instances. **Lifecycle
  aggregates:** root-guarded transitions that re-establish the invariant
  before returning.

## Application services

Coordination only — no business logic. Four named steps
(`application-services.md`): convert → delegate → persist → respond. The
repository is injected as a `Protocol` (see `python.md#repositories`).

```python
class CreditService:
    def __init__(self, repo: JournalRepository) -> None:  # injected, never built here
        self._repo = repo

    # Create use case: Delegate constructs a new aggregate.
    def record_payment(self, req: RecordPaymentRequest) -> RecordPaymentResponse:
        spec = to_payment_spec(req)                 # 1. Convert (DTO → spec)
        payment = Payment(spec)                     # 2. Delegate (construct; raises on invalid)
        self._repo.save_payment(payment)            # 3. Persist (whole aggregate)
        return to_payment_response(payment)         # 4. Respond (domain → DTO)

    # Change use case: Delegate LOADS an aggregate and calls its guarded transition.
    def apply_refund(self, req: ApplyRefundRequest) -> ApplyRefundResponse:
        payment = self._repo.load_payment(PaymentID(req.payment_id))  # 1+2a. convert + load
        payment.refund(to_refund_spec(req))         # 2b. guarded transition (raises on illegal)
        self._repo.save_payment(payment)            # 3. Persist
        return to_refund_response(payment)          # 4. Respond
```

- **No `for` over domain objects, no arithmetic on domain quantities, no `if` on
  domain state** in the method — the leakage checks
  (`application-services.md#domain-logic-leakage-checks`). A comprehension
  mapping `req.items → [Spec]` is pure conversion; put it in `to_payment_spec`.
- **Return a DTO**, never the domain object.
- **Transaction / session boundary is consumer-specific.** Where the unit of
  work opens and commits — a SQLAlchemy `Session`, an async transaction, a
  FastAPI dependency — is a decision for the consuming codebase, not this skill.
  Wrap the use case in one unit of work; do **not** invent an ORM lifecycle
  here. Record what your codebase actually does and feed the friction back —
  the transaction boundary is genuinely a consuming-codebase decision, not a gap
  in this skill.

## Repositories

Interface as a `Protocol` (structural typing, like Go's implicit satisfaction);
whole aggregate in, reconstructed aggregate out, no business logic
(`repositories.md`). How the aggregate decomposes on the way out — the
per-context parts module, and when a repo-private record suffices — is the
serialization norm (`serialization.md` rules 6-8).

```python
from typing import Protocol

class OrderRepository(Protocol):          # defined with the service, not the DB
    def save(self, order: Order) -> None: ...            # whole aggregate in
    def load(self, id: OrderID) -> Order: ...            # reconstructed out
    def find(self, q: OrderQuery) -> list[OrderSummary]: ...  # read projection

@dataclass(frozen=True)
class OrderQuery:                          # selection criteria — VOs, NOT a spec
    customer: CustomerID
    period: Period

class InMemoryOrderRepo:                   # satisfies the Protocol structurally
    def __init__(self) -> None:
        self._rows: dict[str, OrderRecord] = {}

    def save(self, order: Order) -> None:
        self._rows[str(order.id)] = decompose(order)  # repo decomposes, not the caller

    def load(self, id: OrderID) -> Order:
        rec = self._rows.get(str(id))
        if rec is None:
            raise LookupError(f"order {id} not found")
        return Order(rec.to_spec())                   # reconstruct THROUGH the constructor
```

- **`save` takes the root**; `decompose` (private) flattens it. The service
  never extracts children to save them.
- **`load` reconstructs through the constructor** (spec in), so invariants
  re-run — never build the aggregate by assigning attributes.
- **No domain math.** `find` may filter/order (persistence selection); summing
  or rule-checking is a leak
  (`application-services.md#domain-logic-leakage-checks`).
- **Query fields are value objects.** (Persistence backends — SQLAlchemy,
  async drivers — are consumer-specific; the `Protocol` is the stable contract,
  the backing store is not this skill's decision. The worked example uses an
  in-memory repository; a database-backed one satisfies the same `Protocol`.)

## The composition root

The public interface + the wiring site (`public-interface.md`, `bootstrap.md`). The `Client`
`Protocol` and its DTOs live in a public package; the application service
**satisfies the Protocol structurally** (no inheritance, no adapter code); a
hand-wired entry point chooses the concrete implementations and injects the
`Client` into the handler.

**The public package — a `Protocol` + DTOs, no implementation:**

```python
# orders/client.py — the public surface of the component
# (get_order's DTOs elided).
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ItemInput:
    sku: str
    quantity: int


@dataclass(frozen=True)
class PlaceOrderRequest:
    customer_id: str
    items: tuple[ItemInput, ...]


@dataclass(frozen=True)
class PlaceOrderResponse:          # DTO — never a domain object
    order_id: str
    total: str


class Client(Protocol):
    def place_order(self, req: PlaceOrderRequest) -> PlaceOrderResponse: ...
    def get_order(self, req: GetOrderRequest) -> GetOrderResponse: ...
```

**Satisfy it structurally — no forwarding code, no inheritance.** Because
`Client` is a `Protocol`, any object whose methods match its names and
signatures satisfies it. The application service already has exactly those
methods, taking and returning the **public package's DTO types**
(`python.md#application-services`), so it *is* a `Client` — Python's analog of
Go's embed-to-satisfy:

```python
# ordersimpl/client.py
from orders import Client
from ordersapp import OrderService


def new_client(svc: OrderService) -> Client:
    return svc      # the service satisfies the Protocol structurally
```

The `-> Client` return annotation is the compile-time proof (mypy's analog of
Go's `var _ orders.Client = (*client)(nil)`): if a service method's signature
drifts from the Protocol, type checking stops here.

**Reshape only when the surface must differ.** When you must rename a method,
expose a subset, or compose several internal services into one contract (the
decoupling boundary's real purpose), write an explicit class that holds the
component(s) and delegates — the analog of Go's explicit reshape method:

```python
class _OrdersClient:                # explicit only to reshape
    def __init__(self, svc: OrderService) -> None:
        self._svc = svc

    def place_order(self, req: PlaceOrderRequest) -> PlaceOrderResponse:
        return self._svc.create_order(req)   # expose create_order as place_order
    # ... the rest of the Client's methods ...


def new_client(svc: OrderService) -> Client:
    return _OrdersClient(svc)
```

**The composition root — the settled app anatomy** (`bootstrap.md`,
`wiring.md`; verified impl `examples/python-app/`). Each context owns a
`wiring/` package (its spec-shaped `Config` + a `build` contract); the app-level
`bootstrap` nests the configs and calls each context's `build` in dependency
order, onto a cleanup stack:

```python
# <context>/wiring/config.py — the context's OWN construction config
@dataclass(frozen=True)
class Config:
    storage: str          # the resource coordinate; "memory" for in-process


# <context>/wiring/wire.py — coordinate-driven, fail-fast, uniform build contract
def repo_for(cfg: Config) -> tuple[CampaignRepository, Closeable]:
    if cfg.storage == "memory":
        repo = InMemoryCampaignRepository()
        return repo, repo
    if not cfg.storage:
        raise invalid("missing_coordinate", "campaign storage coordinate is required")
    raise invalid("unknown_backend", f"campaign storage {cfg.storage!r} not supported")


def build(cfg: Config, checker: TargetChecker) -> tuple[Client, Closeable]:
    repo, closeable = repo_for(cfg)
    return CampaignService(repo, checker), closeable


# bootstrap/config.py — the app Config nests the per-context ones
@dataclass(frozen=True)
class Config:
    campaign: CampaignConfig
    linkpolicy: LinkPolicyConfig


# bootstrap/bootstrap.py — new(cfg): build ONCE, in dependency order
def new(cfg: Config) -> App:
    stack = CleanupStack()
    try:
        policy_client, policy_closeable = linkpolicy_wire.build(cfg.linkpolicy)
        stack.push(policy_closeable)
        checker = LinkPolicyTargetChecker(policy_client)   # cross-context adapter:
        campaign_client, c_closeable = campaign_wire.build(cfg.campaign, checker)
        stack.push(c_closeable)                            # built HERE, injected
        return App(campaign_client, policy_client, stack)  # App owns close()
    except Exception:
        stack.close_all()      # partial construction unwinds — no leaked pools
        raise
```

- **`build` returns `(Client, Closeable)`** — the Protocol and a resource
  handle, never the concrete service or a domain type. A context with no
  resources returns a named no-op closeable; the build contract stays uniform.
- **Each context gets only its slice** (`cfg.campaign`), and cross-context
  adapters are constructed in `new` and injected — only the root knows two
  contexts at once.
- **`App.close()` is idempotent** and pops the stack in reverse; a close that
  raises must not orphan the rest (`CleanupStack.close_all` collects errors).
- **Only bootstrap/wiring import the concretes.** That boundary is a
  *convention* in Python; an `__all__`/naming discipline is the analog of
  Go's compiler-enforced `internal/` (`bootstrap.md`).
- **No `context.Context`.** A plain synchronous Python service has no such
  idiom; thread a unit-of-work/session where your codebase already does (see
  the application-services note above).
- **The degenerate case:** a single-context app can collapse this to one
  hand-wired `main` that chooses the repo, builds the service, and composes
  the `Client` (the `examples/python/` running arc does exactly that) — the
  rules are unchanged: one place chooses, the contract crosses, nothing else
  imports the concretes. Grow the full `bootstrap`/`wiring` shape when a
  second context (or a second host) arrives.

## Inbound handlers and hosts

The two-layer transport split (`handlers.md`, `srv.md`; verified impl
`examples/python-app/campaign/adapters/handlers/http.py` and
`examples/python-app/srv/`). The per-context **handler** translates
wire ↔ `Client` DTOs through one respond path; the app-level **host** is the
env edge — it calls the one `from_env` loader, builds the graph once, and runs
under a runner that installs SIGTERM and closes the app.

```python
# httpwire.py — the mechanism's wire vocabulary, shared by every HTTP handler
class BadRequest(Exception):                        # transport failure -> 400
    pass


@dataclass(frozen=True)
class Response:
    status: int
    body: JSONObject


def problem(code: str, detail: str) -> JSONObject:
    return {"type": f"/problems/{code}", "detail": detail}


def respond(run: Callable[[], Response]) -> Response:
    try:
        return run()
    except BadRequest as e:
        return Response(400, problem("malformed_request", str(e)))
    except DomainError as e:
        return Response(status_for(e.kind), problem(e.code, e.message))
    except InfraError:
        return Response(503, problem("unavailable", "a dependency is unavailable; please retry"))
    except Exception:
        return Response(500, problem("internal", "unexpected error"))


# <context>/adapters/handlers/http.py
class Handler:
    def __init__(self, client: Client) -> None:
        self._client = client                       # injected; never constructed

    def add_link(self, raw: str) -> Response:
        def run() -> Response:
            body = _parse(raw)                      # wire guard, field by field
            view = self._client.add_link(
                AddLinkRequest(campaign_id=_str(body.get("campaign_id")),
                               slug=_str(body.get("slug")),
                               target_url=_str(body.get("target_url")))
            )
            return Response(200, _campaign_body(view))  # DTO -> wire, the edge's own shape

        return respond(run)
```

- **One `Client` call per endpoint method**; the method translates in, calls,
  translates out. `_parse`/`_str` raise `BadRequest` — the handler's own
  transport guard, distinct from domain validation.
- **`respond` is the whole error table for the mechanism**: transport → 400,
  domain kind → status through the one pure mapper (`status_for` over the
  closed `Kind` set), infra → 503, unexpected → 500 with a generic body.
- **`problem`** renders the RFC 9457-shaped problem object (`type` from the
  open `Code`, `detail`) — decided once at this path.
- **The wire vocabulary is app-level, not context-owned.** `Response`,
  `problem`, and `respond` describe the *mechanism*, so they live in one
  shared module every HTTP handler imports (`examples/python-app/httpwire.py`)
  — never in whichever context happened to grow a handler first, which would
  make its peers import a sibling's adapter internals to answer a request.

```python
# srv/http/main.py — the host: env edge, build once, hand to the runner
def main() -> None:
    cfg = from_env(os.getenv)            # the ONE config loader (bootstrap/config)
    app = new(cfg)                       # ONCE per process; validates fail-fast
    host = HttpHost((cfg.http.host, cfg.http.port), app)  # implements Host: serve + drain
    run_until_signal(host, app)          # installs SIGTERM, guarantees app.close()
```

- **One loader, one env read.** The host passes its own `os.getenv` to
  `from_env` (`bootstrap/config.py`) — the single place the app reads the
  environment. `from_env` loads app config **and** the host's launch config
  (`cfg.http`) into one `Config`; nothing below the host reads env. It stays a
  pure function (`getenv` injected), so it's testable with a dict and the
  env-edge check still holds.
- **`HttpHost` implements the `Host` contract** (`run(stop)`): it serves in a
  thread and drains on stop. `make_server` constructs each exposed context's
  handler once from the single `App` — `CampaignHandler(app.campaign)` and
  `ReportsHandler(app.reports)` — then routes to them; no per-request
  construction, and it owns routing + middleware for its mechanism. **A context
  the host exposes owns a handler**: the host maps a path to a handler method
  and serializes what comes back, and never touches a `Client` itself
  (`handlers.md`). Its own routing failures are the exception — an unmatched
  path is the host's to answer, through the same `problem` shape.
- **`run_until_signal` owns the process lifecycle**: it installs SIGINT/SIGTERM
  and calls `app.close()` in a `finally`. This is the lifecycle **minimum, and
  it is load-bearing** — a bare `finally: app.close()` does **not** survive
  Python's default SIGTERM (the process dies without unwinding), so the host
  installs the handler. Drain ordering, readiness, and health stay the host's
  fill-in (`examples/python-app/srv/run.py`, `srv/http/host.py`).
- **A CLI host** is the same env edge minus the `Host`/runner (it is not
  long-running): `new(from_env(os.getenv))`, dispatch the command to one
  `Client` call, render, and `close()` in `finally`
  (`examples/python-app/srv/cli/main.py`); with one command the handler role is
  played inline in the dispatch (`handlers.md#decisions-you-must-make`).

## The Spec pattern

Specs are frozen dataclasses with **primitive leaves** that carry construction
data across the layer boundary. A structured domain object's **constructor takes
its spec** — that is the single construction path (no separate factory); it
converts each primitive to a value object and `__post_init__`/the constructor
validates.

- A spec field is never a domain value object — the caller shouldn't have to
  step inside the domain to build one, and validation must run in one place.
- **Nesting mirrors composition:** `TransferSpec` holds `AccountRefSpec`,
  never flattened prefixed fields. Ubiquitous child types are embedded in many
  parents; nesting means a change to the child's construction touches the
  child's spec only.
- **1 primitive field → no spec; the constructor takes the raw primitive**
  (`Slug(value)`). **2+ fields (or embedded domain objects) → the constructor
  takes the spec** (`Transfer(spec)`).
- Enums cross the boundary as enums (`NormalBalance.CREDIT`), not strings.

**Return types:** domain functions return domain types. If callers must
sum/filter/group a returned list before it's useful, introduce the type that
represents the finished result.

## Testing patterns

```python
def test_money_equality():
    a = Money(MoneySpec("1.5", "USD"))
    b = Money(MoneySpec("1.50", "USD"))
    assert a == b            # equal logical values, across representations
    assert hash(a) == hash(b)

def test_money_rejects_missing_currency():
    with pytest.raises(ValueError, match="currency is required"):
        Money(MoneySpec("1.00", ""))

def test_operation_rejects_unbalanced():
    with pytest.raises(ValueError, match="does not balance"):
        Operation(op_id, [debit_only])

def test_operation_transfers_are_defensive():
    op = Operation(op_id, transfers)
    assert isinstance(op.transfers, tuple)   # callers can't mutate the root
```

- One equality test per VO (`test_*_equality`) locking `__eq__` AND
  `__hash__` semantics.
- One rejection test per validation rule (`pytest.raises`, matching the
  message).
- One invariant-violation test per aggregate — its reason to exist.
- Defensive-copy assertions on every collection accessor.
- Never `str(a) == str(b)` as an equality assertion; each leaf's canonical
  exit gets its own round-trip test (`serialization.md#tests-you-must-write`).
