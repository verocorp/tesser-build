package lending

import "fmt"

type Money struct {
	cents int64
}

func NewMoney(cents int64) (Money, error) {
	if cents < 0 {
		return Money{}, fmt.Errorf("money: cents must not be negative, got %d", cents)
	}
	return Money{cents: cents}, nil
}

func MustNewMoney(cents int64) Money {
	m, err := NewMoney(cents)
	if err != nil {
		panic(err)
	}
	return m
}

func (m Money) Cents() int64 { return m.cents }

func (m Money) Add(other Money) Money {
	return Money{cents: m.cents + other.cents}
}

func (m Money) String() string {
	return fmt.Sprintf("$%d.%02d", m.cents/100, m.cents%100)
}
