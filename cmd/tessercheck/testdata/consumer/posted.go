package consumer

import "fmt"

type Posted struct {
	multiplier int64
	currency   string
}

func FromMultiplier(multiplier int64, currency string) Posted {
	return Posted{multiplier: multiplier, currency: currency}
}

func (p Posted) Multiplier() int64 { return p.multiplier }

func (p Posted) Equal(other Posted) bool {
	return p.multiplier == other.multiplier && p.currency == other.currency
}

func (p Posted) String() string {
	return fmt.Sprintf("posted[%s %d]", p.currency, p.multiplier)
}
