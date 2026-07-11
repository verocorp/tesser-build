package lending

import "fmt"

// Money is an amount of money, held as a whole number of US cents.
// Representing money as an integer count of cents — never a float or a
// decimal string — means every logical value has exactly one
// representation, so arithmetic never drifts and native `==` is a correct,
// sufficient equality check; there is no multi-representation case to
// guard against the way there is for a decimal-backed Money.
type Money struct {
	cents int64
}

// NewMoney validates and constructs a Money value. Money can never be
// negative in this domain — there is no such thing as a negative late fee.
func NewMoney(cents int64) (Money, error) {
	if cents < 0 {
		return Money{}, fmt.Errorf("money: cents must not be negative, got %d", cents)
	}
	return Money{cents: cents}, nil
}

// MustNewMoney panics if cents is negative. Use only with known-valid
// literals (tests, package-level vars).
func MustNewMoney(cents int64) Money {
	m, err := NewMoney(cents)
	if err != nil {
		panic(err)
	}
	return m
}

// Cents returns the amount as a whole number of US cents.
func (m Money) Cents() int64 { return m.cents }

// Add returns the sum of two Money values. It is domain behavior on the
// type: two non-negative amounts always sum to a non-negative amount, so
// Add builds the result directly rather than round-tripping through
// NewMoney (the same "domain behavior enforces its own consistency"
// pattern go.md describes for value-object arithmetic).
func (m Money) Add(other Money) Money {
	return Money{cents: m.cents + other.cents}
}

// String formats the amount for display, e.g. "$1.25". Never compare two
// Money values by their String() form — compare by value (native `==`) or
// by Cents().
func (m Money) String() string {
	return fmt.Sprintf("$%d.%02d", m.cents/100, m.cents%100)
}
