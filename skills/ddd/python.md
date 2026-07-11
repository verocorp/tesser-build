# Building domain code in Python

Construction mechanics only — the concepts and the rules' whys live in the
concept files (`value-objects.md`, `entities.md`, `aggregates.md`,
`application-services.md`, `repositories.md`, `domain-services.md`). This file
covers the domain building blocks *and* the seams that serve them (application
services, repositories) — not domain objects themselves, but their construction
mechanics live here alongside the objects they orchestrate and persist. Section
headings here are stable anchors; the resolver and the coverage matrix link to
them.

> **Maturity note:** this guidance is v1 best-effort — the Go doctrine has a
> battle-tested reference implementation; the Python rendering does not yet.
> When it fights your codebase's reality, record the friction (it feeds the
> next revision) rather than silently diverging.

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
    _values: tuple[tuple[str, str], ...]    # immutable storage

    @classmethod
    def new(cls, values: dict[str, str] | None) -> "Labels":
        return cls(tuple(sorted((values or {}).items())))

    def as_dict(self) -> dict[str, str]:    # copy out, never a reference
        return dict(self._values)
```

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
- **Custom semantics needed** (a field compares by normalized form): set
  `eq=False` and implement `__eq__`/`__hash__` together, explicitly. Never
  define one without the other.

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
  here. Record what your codebase actually does and feed the friction back
  (this is v1 best-effort Python — see the maturity note at the top).

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
  the backing store is not this skill's decision. v1 best-effort — see the
  maturity note at the top.)

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
