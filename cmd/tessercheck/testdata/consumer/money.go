package consumer

import (
	"errors"
	"fmt"
)

type Money struct {
	amount   int64
	currency string
}

func NewMoney(amount int64, currency string) (Money, error) {
	if currency == "" {
		return Money{}, errors.New("currency required")
	}
	return Money{amount: amount, currency: currency}, nil
}

func MustNewMoney(amount int64, currency string) Money {
	m, err := NewMoney(amount, currency)
	if err != nil {
		panic(err)
	}
	return m
}

func (m Money) Equal(other Money) bool {
	return m.amount == other.amount && m.currency == other.currency
}

func (m Money) String() string {
	return fmt.Sprintf("%s %d", m.currency, m.amount)
}
