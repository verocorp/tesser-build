# Building domain code in Go

Construction mechanics only — the concepts and the rules' whys live in the
concept files (`value-objects.md`, `entities.md`, `aggregates.md`,
`application-services.md`, `repositories.md`, `domain-services.md`). This file
covers the domain building blocks *and* the seams that serve them (application
services, repositories) — application services and repositories are not domain
objects, but their construction mechanics live here alongside the objects they
orchestrate and persist. Section headings here are stable anchors; the resolver
and the coverage matrix link to them.

## Value objects

**Simple (wraps a single primitive) — flat constructor, no spec:**

```go
type EmailAddress struct {
	value string
}

func NewEmailAddress(value string) (EmailAddress, error) {
	if !strings.Contains(value, "@") {
		return EmailAddress{}, fmt.Errorf("invalid email address: %q", value)
	}
	return EmailAddress{value: value}, nil
}

func MustNewEmailAddress(value string) EmailAddress {
	v, err := NewEmailAddress(value)
	if err != nil {
		panic(err)
	}
	return v
}

func (e EmailAddress) String() string {
	return e.value
}
```

**Compound (two or more fields) — constructed via a spec:**

```go
type MoneySpec struct {
	Amount   string // primitive leaf — parsed and validated by the constructor
	Currency string
}

type Money struct {
	amount   decimal.Decimal
	currency string
	_        [0]func() // non-comparable: decimals have multiple representations
}

func NewMoney(spec MoneySpec) (Money, error) {
	if spec.Currency == "" {
		return Money{}, fmt.Errorf("currency is required")
	}
	amount, err := decimal.NewFromString(spec.Amount)
	if err != nil {
		return Money{}, fmt.Errorf("invalid amount: %w", err)
	}
	return Money{amount: amount, currency: spec.Currency}, nil
}
```

**Collection (wraps a map or slice):**

```go
type Labels struct {
	values map[string]string
}

func NewLabels(m map[string]string) Labels { // normalizes nil to empty
	return Labels{values: copyMap(m)}
}
```

Copy on the way in, copy on the way out — the backing collection never
escapes. When callers need different nil-handling (optional vs required), add
a constructor variant (`RequireLabels`) rather than pushing checks to parents.

**Rules of the section:**

- Private fields; value semantics (no pointers to value objects).
- No setters, no mutation methods. Domain behavior (`Add`, `Cmp`, ...) returns
  new values and enforces its own consistency (same-currency arithmetic).
- Every `NewX(...) (X, error)` gets a `MustNewX(...) X` in the same file,
  immediately below it. It panics with the error from `NewX` — no wrapping.
  Known-valid literals only (tests, package-level vars); never production
  paths with runtime data.
- Every VO implements `fmt.Stringer`. `String()` is the display method AND the
  sole string accessor — no separate `ToString()`. Formats: single-value VOs
  return the wrapped value; amount VOs compose `"100.00 USD"`; compound VOs
  use the simplest identifying form (`"Money:USD"`); intervals use half-open
  `"[start, end)"`.

**Equality — pick the correct path:**

- **One representation per logical value** (string wrappers, comparable
  structs): `==` is correct. Nothing extra to build.
- **Multiple representations per logical value** (anything wrapping a decimal
  or measure — `1.5` vs `1.50`): `==` LIES. Block it with a `_ [0]func()`
  field and provide `Equal`:

```go
func (m Money) Equal(other Money) bool {
	return m.currency == other.currency && m.amount.Equal(other.amount)
}
```

## Entities

```go
type Transfer struct {
	id     TransferID // identity — a value object, assigned once
	from   AccountRef
	to     AccountRef
	amount Money
}

type TransferSpec struct {
	ID     string
	From   AccountRefSpec // nested spec
	To     AccountRefSpec
	Amount MoneySpec
}

func NewTransfer(spec TransferSpec) (Transfer, error) {
	id, err := NewTransferID(spec.ID)
	if err != nil {
		return Transfer{}, fmt.Errorf("invalid transfer ID: %w", err)
	}
	from, err := NewAccountRef(spec.From)
	if err != nil {
		return Transfer{}, fmt.Errorf("invalid from account: %w", err)
	}
	// ... each child via its own constructor, error wrapped with field context
	return Transfer{id: id, from: from /* ... */}, nil
}

func (t Transfer) ID() TransferID { return t.id }
```

- Fields are value objects, never raw primitives. The entity builds each via
  the child's constructor and wraps errors with context; it re-validates
  nothing.
- No `MustNew*` for entities or aggregates — they carry real construction
  risk; the panic shortcut is a value-object convenience only.
- **Fact entities (immutable):** value receivers; a state change returns a new
  instance.
- **Lifecycle entities (mutable):** pointer receivers; transitions guard state
  and mutate in place:

```go
func (c *Contract) Activate() error {
	if c.status != StatusDraft {
		return fmt.Errorf("can only activate a draft contract")
	}
	c.status = StatusActive
	return nil
}
```

Two states → a guard clause like this. More → a transition table or state
pattern instead of stacked conditionals.

## Aggregates

```go
type Operation struct {
	id        OperationID
	transfers []Transfer
	_         [0]func() // non-comparable — aggregates are never compared by value
}

func NewOperation(spec OperationSpec) (Operation, error) {
	// ... construct children via their constructors ...
	if err := balanced(transfers); err != nil { // the cross-object invariant
		return Operation{}, fmt.Errorf("operation does not balance: %w", err)
	}
	return Operation{id: id, transfers: transfers}, nil
}

func (o Operation) Transfers() []Transfer { // defensive copy, always
	out := make([]Transfer, len(o.transfers))
	copy(out, o.transfers)
	return out
}
```

- The invariant check is IN the constructor — an unbalanced Operation is
  unrepresentable.
- `_ [0]func()` makes the type non-comparable at compile time: `a == b` on an
  aggregate won't build.
- Accessors return copies of collections, never the backing slice/map.
- **Fact aggregates:** state changes return new instances:

```go
func (l Ledger) Backfill(ops []Operation) (Ledger, error) {
	// ... compute new state ...
	return Ledger{identity: l.identity, operations: newOps /* ... */}, nil
}
```

- **Lifecycle aggregates:** root-guarded transitions that re-establish the
  invariant before returning:

```go
func (o *Order) AddLineItem(item LineItem) error {
	if o.status != StatusDraft {
		return fmt.Errorf("cannot add items to a non-draft order")
	}
	o.lineItems = append(o.lineItems, item)
	return nil
}
```

## Application services

Coordination only — no business logic. The method reads as the four named steps
(`application-services.md`): convert → delegate → persist → respond.

```go
type CreditService struct {
	repo JournalRepository // injected — an interface, never constructed here
}

func NewCreditService(repo JournalRepository) *CreditService {
	return &CreditService{repo: repo}
}

// Create use case: Delegate constructs a new aggregate.
func (s *CreditService) RecordPayment(ctx context.Context, req RecordPaymentRequest) (RecordPaymentResponse, error) {
	spec := toPaymentSpec(req)                    // 1. Convert (DTO → spec)

	payment, err := accounting.NewPayment(spec)   // 2. Delegate (construct)
	if err != nil {
		return RecordPaymentResponse{}, fmt.Errorf("invalid payment: %w", err)
	}

	if err := s.repo.SavePayment(ctx, payment); err != nil { // 3. Persist (whole aggregate)
		return RecordPaymentResponse{}, fmt.Errorf("persist payment %s: %w", req.ID, err)
	}

	return toPaymentResponse(payment), nil        // 4. Respond (domain → DTO)
}

// Change use case: Delegate LOADS an aggregate and calls its guarded transition.
func (s *CreditService) ApplyRefund(ctx context.Context, req ApplyRefundRequest) (ApplyRefundResponse, error) {
	id, err := accounting.NewPaymentID(req.PaymentID) // 1. Convert
	if err != nil {
		return ApplyRefundResponse{}, fmt.Errorf("invalid payment id: %w", err)
	}

	payment, err := s.repo.LoadPayment(ctx, id)   // 2a. load …
	if err != nil {
		return ApplyRefundResponse{}, fmt.Errorf("load payment %s: %w", req.PaymentID, err)
	}
	if err := payment.Refund(toRefundSpec(req)); err != nil { // 2b. … call the guarded transition
		return ApplyRefundResponse{}, fmt.Errorf("refund rejected: %w", err)
	}

	if err := s.repo.SavePayment(ctx, payment); err != nil {  // 3. Persist
		return ApplyRefundResponse{}, fmt.Errorf("persist refund: %w", err)
	}
	return toRefundResponse(payment), nil          // 4. Respond
}
```

- **Each step is one call.** If a step needs more than a line or two, extract a
  private `toXxxSpec`/`toXxxResponse` helper. The method body is a readable
  sequence, not inline assembly.
- **No `for` loops over domain objects, no arithmetic on domain quantities, no
  `if` on domain state** in the method — those are the leakage checks
  (`application-services.md#domain-logic-leakage-checks`). A `for` that maps
  `req.Items → []Spec` is pure conversion and belongs in the `toXxxSpec` helper.
- **The response is a DTO.** `toPaymentResponse` reads fields off the domain
  object and returns a plain struct; the domain object itself never escapes.
- **The repo takes the whole aggregate** (`s.repo.SavePayment(ctx, payment)`),
  never extracted children — see `go.md#repositories`.

## Repositories

Interface in the caller's package; whole aggregate in, reconstructed aggregate
out, no business logic (`repositories.md`). Go's structural typing means the
implementation satisfies the interface implicitly.

```go
// Defined in the service package — the domain depends on this, not on a DB.
type OrderRepository interface {
	Save(ctx context.Context, order Order) error          // whole aggregate in
	Load(ctx context.Context, id OrderID) (Order, error)  // reconstructed out
	Find(ctx context.Context, q OrderQuery) ([]OrderSummary, error) // read projection
}

type OrderQuery struct { // selection criteria — value objects, NOT a spec
	Customer CustomerID
	Period   Period
}

// In-memory implementation (tests + early use); a DB-backed one satisfies the
// same interface later.
type InMemoryOrderRepo struct {
	mu     sync.Mutex
	orders map[string]OrderRecord // storage rows, not aggregates
}

func (r *InMemoryOrderRepo) Save(ctx context.Context, order Order) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.orders[order.ID().String()] = decompose(order) // repo decomposes — caller never does
	return nil
}

func (r *InMemoryOrderRepo) Load(ctx context.Context, id OrderID) (Order, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	rec, ok := r.orders[id.String()]
	if !ok {
		return Order{}, fmt.Errorf("order %s not found", id)
	}
	return NewOrder(rec.ToSpec()) // reconstruct THROUGH the constructor — invariants re-run
}
```

- **`Save` takes the root**, and `decompose` (private to the repo) flattens it
  into storage. The service never calls `order.Items()` to save children.
- **`Load` reconstructs via `NewOrder`**, never by assigning fields — so a
  stored-but-invalid aggregate cannot come back to life.
- **No domain math in here.** Filtering/ordering in `Find` is persistence
  selection; summing amounts or checking a balance would be a leak
  (`go.md#application-services` leakage checks).
- **Query fields are value objects** (`CustomerID`, `Period`), so the boundary
  can't be handed a raw unvalidated string.

## The Spec pattern

A spec is a **primitive-leaved struct that carries construction data across
the layer boundary**. The constructor is the single validation site: spec in,
validated domain object out.

```go
type OperationSpec struct {
	ID        string
	Transfers []TransferSpec // nesting mirrors the domain composition
}
```

- **Leaves are primitives** (`string`, `int`, `time.Time`, enums). A spec
  field is never a domain value object — otherwise the caller has already
  stepped inside the domain, and validation happens twice in ambiguous order.
- **Nesting mirrors composition.** A compound child gets its own nested spec
  (`TransferSpec` holds `AccountRefSpec` holds ...) — never flattened into
  prefixed fields. Why: ubiquitous child types are embedded in many parent
  specs; nested specs mean a change to how the child is built touches the
  child's spec only, not every parent. Flat args couple every parent to the
  child's constructor signature.
- **1 arg → no spec** (flat constructor); **2+ args → spec**. Single-value
  types are their value and won't grow; compound concepts accrete fields.
- **Enums cross the boundary as themselves** (`NormalBalance`), not as
  strings to re-parse.

**Return types (the pattern in reverse):** domain functions return domain
types. If the caller must sum/filter/group a returned `[]T` before it's
useful, the function returned an intermediate — introduce the type that
represents the finished result (often a value object like `Total`, not a
slice wrapper). Raw `[]T` is correct when the caller only stores, passes, or
ranges.

## Testing patterns

```go
func TestMoney_Equality(t *testing.T) {
	// blocked native comparison, for multi-representation VOs:
	if reflect.TypeOf(Money{}).Comparable() {
		t.Fatal("Money must be non-comparable; use Equal")
	}
	a := MustNewMoney(MoneySpec{Amount: "1.5", Currency: "USD"})
	b := MustNewMoney(MoneySpec{Amount: "1.50", Currency: "USD"})
	if !a.Equal(b) {
		t.Error("equal logical values must be Equal across representations")
	}
}
```

- `Test*_Equality` for every VO — the one test whose name doesn't match a
  method, because it locks semantics, not a signature.
- Constructor rejection tests: one per validation rule, asserting error (not
  panic).
- `MustNew*` contract: panics on invalid input (use `recover` in the test).
- Invariant-violation test per aggregate: the breaking spec errors.
- Defensive-copy test: mutate the accessor's result, assert the aggregate
  unchanged.
- Never `a.String() == b.String()` as an equality assertion — the
  `stringequality` analyzer rejects it. Stringification gets its own
  `Test*_String`.
- Use `MustNew*` for inline test fixtures; `New*` + error assertions for the
  paths under test.
