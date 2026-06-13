package dom

// Money is a pure value object: no identity, immutable, no children. It must
// NOT be excluded.
type Money struct{ cents int64 }

func NewMoney(c int64) (Money, error) { return Money{cents: c}, nil }
func (m Money) String() string        { return "money" }

// Item is a child element and also a pure value object. NOT excluded.
type Item struct{ sku string }

func NewItem(s string) (Item, error) { return Item{sku: s}, nil }
func (i Item) String() string        { return i.sku }

// Ledger is an entity: it has an ID() method (strongest signal).
type Ledger struct{ balance Money }

func NewLedger() (Ledger, error) { return Ledger{}, nil }
func (l Ledger) ID() string      { return "L1" }

// Account is an entity: it has an id field.
type Account struct {
	id      string
	balance Money
}

func NewAccount() (Account, error) { return Account{}, nil }

// Transfer is an aggregate: a pointer-receiver method mutates a field.
type Transfer struct{ applied bool }

func NewTransfer() (Transfer, error) { return Transfer{}, nil }
func (t *Transfer) Apply()           { t.applied = true }

// Basket is an aggregate: it holds a child collection of Items (no identity, no
// mutator).
type Basket struct{ items []Item }

func NewBasket() (Basket, error) { return Basket{}, nil }
