package consumer

import (
	"errors"
	"fmt"
)

// Money is a conforming value object: private fields, a single validating
// constructor, a paired Must helper, value equality, and a display String. It
// is the control — it must trip none of the analyzers.
type Money struct {
	amount   int64
	currency string
}

// NewMoney is the validating constructor and the only construction path.
func NewMoney(amount int64, currency string) (Money, error) {
	if currency == "" {
		return Money{}, errors.New("currency required")
	}
	return Money{amount: amount, currency: currency}, nil
}

// MustNewMoney panics on error; tests use it for inline construction.
func MustNewMoney(amount int64, currency string) Money {
	m, err := NewMoney(amount, currency)
	if err != nil {
		panic(err)
	}
	return m
}

// Equal compares Money by value.
func (m Money) Equal(other Money) bool {
	return m.amount == other.amount && m.currency == other.currency
}

// String is the display form.
func (m Money) String() string {
	return fmt.Sprintf("%s %d", m.currency, m.amount)
}
