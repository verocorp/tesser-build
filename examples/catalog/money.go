package catalog

import (
	"fmt"
	"math/big"
)

// MoneySpec carries construction data across the layer boundary: primitive
// leaves only. Amount is a decimal string (e.g. "19.99"), parsed and
// validated by the constructor.
type MoneySpec struct {
	Amount   string
	Currency string
}

// Money is a compound value object: an amount plus a currency. The amount is
// held as a *big.Rat so decimal values are exact (no float drift), but that
// makes Money a value whose field has *multiple representations* — 1.5 and
// 1.50 are the same amount — and whose backing is a pointer. Either alone
// means native == is wrong: it would compare the pointers, not the values. So
// the struct is made non-comparable (the [0]func() field) and Equal is the
// only correct comparison.
type Money struct {
	amount   *big.Rat
	currency string
	_        [0]func() // block ==: *big.Rat compares by pointer, and 1.5 == 1.50 only by value
}

// NewMoney validates spec and constructs a Money. The amount must parse as a
// decimal and must not be negative (there is no negative price in this
// domain).
func NewMoney(spec MoneySpec) (Money, error) {
	if spec.Currency == "" {
		return Money{}, fmt.Errorf("currency is required")
	}
	amount, ok := new(big.Rat).SetString(spec.Amount)
	if !ok {
		return Money{}, fmt.Errorf("invalid amount: %q", spec.Amount)
	}
	if amount.Sign() < 0 {
		return Money{}, fmt.Errorf("amount must not be negative: %q", spec.Amount)
	}
	return Money{amount: amount, currency: spec.Currency}, nil
}

// MustNewMoney panics on invalid input; use only with known-valid literals
// (tests, package-level vars), never with runtime data.
func MustNewMoney(spec MoneySpec) Money {
	m, err := NewMoney(spec)
	if err != nil {
		panic(err)
	}
	return m
}

// Currency returns the ISO currency code.
func (m Money) Currency() string { return m.currency }

// Add returns the sum of two Money values in the same currency. Two
// non-negative amounts always sum to a non-negative amount, so it builds the
// result directly rather than round-tripping through NewMoney — the same
// "domain behavior enforces its own consistency" pattern go.md describes.
func (m Money) Add(other Money) (Money, error) {
	if m.currency != other.currency {
		return Money{}, fmt.Errorf("cannot add %s and %s", m.currency, other.currency)
	}
	return Money{amount: new(big.Rat).Add(m.amount, other.amount), currency: m.currency}, nil
}

// Equal compares by value across representations — never ==, which would
// compare the *big.Rat pointers.
func (m Money) Equal(other Money) bool {
	return m.currency == other.currency && m.amount.Cmp(other.amount) == 0
}

// String formats the amount to two decimal places with its currency, e.g.
// "19.99 USD". Never compare two Money values by their String() form.
func (m Money) String() string {
	return fmt.Sprintf("%s %s", m.amount.FloatString(2), m.currency)
}
