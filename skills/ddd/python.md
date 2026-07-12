# Building domain code in Python

Construction mechanics only — the concepts and the rules' whys live in the
concept files (`value-objects.md`, `entities.md`, `aggregates.md`,
`application-services.md`, `repositories.md`, `domain-services.md`). This file
covers the domain building blocks *and* the seams that serve them (application
services, repositories) — not domain objects themselves, but their construction
mechanics live here alongside the objects they orchestrate and persist. Section
headings here are stable anchors; the resolver and the coverage matrix link to
them.

> **Verification status — verified.** Every pattern below is backed by a
> runnable, type-checked worked example under `examples/python/`:
> the **running arc** (`campaign` value objects and aggregate, `campaignapp`
> service + repository, and the `linkcampaign`/`linkcampaignimpl`/`main`
> composition root, wired into a live HTTP service) and the **`catalog`**
> package (the compound value object `Money` backed by `decimal.Decimal`, and
> the collection value object `Labels`). The whole tree passes `mypy --strict`
> and `pytest` in CI — the same bar the Go mechanics meet. Where a Go/Python
> difference is load-bearing — frozen-dataclass equality vs Go's `Equal`,
> `Protocol` structural typing vs Go's struct embedding, the absence of
> `context.Context` — it is called out inline.

## Value objects

**Simple (wraps a single value) — frozen dataclass, validation in
`__post_init__`:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class EmailAddress:
    value: str

    def __post_init__(self) -> None:
        if "@" not in self.value:
            raise ValueError(f"invalid email address: {self.value!r}")

    def __str__(self) -> str:
        return self.value
```

`frozen=True` gives immutability (assignment raises) and a field-wise
`__eq__`/`__hash__`. `__post_init__` is the **single validation site**: it
runs on every construction path, so an invalid instance is unrepresentable —
there is no bypassable factory.

**Compound (two or more fields) — spec in, parsed and validated:**

```python
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

@dataclass(frozen=True)
class MoneySpec:          # spec: primitive leaves only
    amount: str
    currency: str

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    @classmethod
    def from_spec(cls, spec: MoneySpec) -> "Money":
        try:
            amount = Decimal(spec.amount)   # conversion only — no rules here
        except InvalidOperation as e:
            raise ValueError(f"invalid amount: {spec.amount!r}") from e
        return cls(amount=amount, currency=spec.currency)

    def __post_init__(self) -> None:        # the rules live here, always run
        if not self.currency:
            raise ValueError("currency is required")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)
```

Factories (`from_spec`) convert primitives to typed values; **rules live only
in `__post_init__`** so direct construction can't skip them.

**Collection (wraps a dict/list):**

```python
@dataclass(frozen=True)
class Labels:
    _values: tuple[tuple[str, str], ...] = ()   # immutable, hashable storage

    def __post_init__(self) -> None:            # canonicalize on EVERY path
        object.__setattr__(self, "_values", tuple(sorted(self._values)))

    @classmethod
    def new(cls, values: Mapping[str, str] | None = None) -> "Labels":
        return cls(tuple((values or {}).items()))

    @classmethod
    def require(cls, values: Mapping[str, str] | None = None) -> "Labels":
        if not values:                          # variant for a mandatory set
            raise ValueError("labels must not be empty")
        return cls.new(values)

    def as_dict(self) -> dict[str, str]:        # copy out, never a reference
        return dict(self._values)
```

Go wraps a `map` and must add `Equal` (a map-backed struct is non-comparable);
Python stores an immutable, **sorted** tuple instead, so the frozen dataclass's
default equality is content-based *and* the value is hashable. Sorting in
`__post_init__` (not just in `new`) means every construction path is
canonicalized. When callers need different nil-handling, add a variant
(`require`) rather than pushing checks to parents.

**Rules of the section:**

- `frozen=True` always; no setters, no mutation — behavior methods return new
  instances.
- No `Must*` twin is needed: construction already raises on invalid input.
  The Go `New/MustNew` split exists because Go returns errors; Python's
  exception IS the panic path — in tests, construct directly with known-valid
  literals.
- `__str__` is for display only. Never compare domain objects via
  `str(a) == str(b)`.

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
  the collection VO above does — it sorts its entries in `__post_init__`). Reach
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
    def __init__(self, id: TransferID, from_account: AccountRef,
                 to_account: AccountRef, amount: Money) -> None:
        self._id = id
        self._from = from_account
        self._to = to_account
        self._amount = amount

    @classmethod
    def from_spec(cls, spec: TransferSpec) -> "Transfer":
        try:
            id = TransferID(spec.id)
        except ValueError as e:
            raise ValueError(f"invalid transfer ID: {e}") from e
        # ... each child via its own constructor, error context added ...
        return cls(id, from_account, to_account, amount)

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
        payment = Payment.from_spec(spec)           # 2. Delegate (construct; raises on invalid)
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
(`repositories.md`).

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
        return Order.from_spec(rec.to_spec())         # reconstruct THROUGH the constructor
```

- **`save` takes the root**; `decompose` (private) flattens it. The service
  never extracts children to save them.
- **`load` reconstructs via `from_spec`**, so invariants re-run — never build
  the aggregate by assigning attributes.
- **No domain math.** `find` may filter/order (persistence selection); summing
  or rule-checking is a leak
  (`application-services.md#domain-logic-leakage-checks`).
- **Query fields are value objects.** (Persistence backends — SQLAlchemy,
  async drivers — are consumer-specific; the `Protocol` is the stable contract,
  the backing store is not this skill's decision. The worked example uses an
  in-memory repository; a database-backed one satisfies the same `Protocol`.)

## The composition root

The public interface + the wiring site (`composition-root.md`). The `Client`
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

**The composition root — one hand-wired entry point that chooses and wires:**

```python
# main.py — the only module that imports the concrete impl package.
from http.server import ThreadingHTTPServer

from ordersapp import OrderService
from ordersimpl import PostgresOrderRepository, new_client
from transport import make_handler


def wire(addr: tuple[str, int]) -> ThreadingHTTPServer:
    repo = PostgresOrderRepository(...)   # the impl choice lives here …
    svc = OrderService(repo)              # … inject the repo into the service
    client = new_client(svc)              # compose behind the public Client
    handler = make_handler(client)        # construct the handler, INJECT the Client
    return ThreadingHTTPServer(addr, handler)
```

- **`new_client` returns `Client`** (the Protocol), never the concrete service
  or a domain type — the caller sees only the contract.
- **The handler depends on the `Client` Protocol**, injected; it constructs
  nothing. (Here the Client is captured by a handler-factory closure, since a
  stdlib `BaseHTTPRequestHandler` is instantiated by the server, not by you.)
- **Only the composition root imports `ordersimpl`.** Nothing else selects the
  concrete implementation. That boundary is a *convention* here; a
  package-private layout or an `__all__`/naming discipline is the Python analog
  of Go's compiler-enforced `internal/` (`composition-root.md`).
- **No `context.Context`.** A plain synchronous Python service has no such
  idiom; thread a unit-of-work/session where your codebase already does (see the
  application-services note above).

## The Spec pattern

Specs are frozen dataclasses with **primitive leaves** that carry construction
data across the layer boundary; `from_spec` factories convert, `__post_init__`
validates.

- A spec field is never a domain value object — the caller shouldn't have to
  step inside the domain to build one, and validation must run in one place.
- **Nesting mirrors composition:** `TransferSpec` holds `AccountRefSpec`,
  never flattened prefixed fields. Ubiquitous child types are embedded in many
  parents; nesting means a change to the child's construction touches the
  child's spec only.
- 1 field → skip the spec, construct directly; 2+ fields → spec.
- Enums cross the boundary as enums (`NormalBalance.CREDIT`), not strings.

**Return types:** domain functions return domain types. If callers must
sum/filter/group a returned list before it's useful, introduce the type that
represents the finished result.

## Testing patterns

```python
def test_money_equality():
    a = Money.from_spec(MoneySpec("1.5", "USD"))
    b = Money.from_spec(MoneySpec("1.50", "USD"))
    assert a == b            # equal logical values, across representations
    assert hash(a) == hash(b)

def test_money_rejects_missing_currency():
    with pytest.raises(ValueError, match="currency is required"):
        Money.from_spec(MoneySpec("1.00", ""))

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
- Never `str(a) == str(b)` as an equality assertion; display gets its own
  `test_*_str`.
