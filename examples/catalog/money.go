package catalog

import (
	"fmt"
	"math/big"
)

type MoneySpec struct {
	Amount   string
	Currency string
}

type Money struct {
	amount   *big.Rat
	currency string
	_        [0]func()
}

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

func MustNewMoney(spec MoneySpec) Money {
	m, err := NewMoney(spec)
	if err != nil {
		panic(err)
	}
	return m
}

func (m Money) Currency() string { return m.currency }

func (m Money) Add(other Money) (Money, error) {
	if m.currency != other.currency {
		return Money{}, fmt.Errorf("cannot add %s and %s", m.currency, other.currency)
	}
	return Money{amount: new(big.Rat).Add(m.amount, other.amount), currency: m.currency}, nil
}

func (m Money) Equal(other Money) bool {
	return m.currency == other.currency && m.amount.Cmp(other.amount) == 0
}

func (m Money) String() string {
	return fmt.Sprintf("%s %s", m.amount.FloatString(2), m.currency)
}
