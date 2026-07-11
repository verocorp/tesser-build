# Building domain objects in Go

Construction mechanics only — the concepts and the rules' whys live in
`value-objects.md`, `entities.md`, `aggregates.md`. Section headings here are
stable anchors; the resolver and the coverage matrix link to them.

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
