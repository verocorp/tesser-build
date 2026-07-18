package consumer

import "fmt"

// Posted mirrors quanta's Quantized: a genuine value object (private fields,
// value equality, display String) whose only construction paths are a
// multiplier helper and an upstream operation — it has no canonical
// NewPosted(...) (Posted, error). voconstructor flags exactly this, and nothing
// else does. It is the true-positive the e2e asserts.
type Posted struct {
	multiplier int64
	currency   string
}

// FromMultiplier builds a Posted from storage. Note: not the canonical
// NewPosted(...) (Posted, error) construction path.
func FromMultiplier(multiplier int64, currency string) Posted {
	return Posted{multiplier: multiplier, currency: currency}
}

// Multiplier returns the integer multiplier. Named accessor, not a To<builtin>
// primitive accessor, so primitiveaccessor leaves it alone.
func (p Posted) Multiplier() int64 { return p.multiplier }

// Equal compares Posted by value.
func (p Posted) Equal(other Posted) bool {
	return p.multiplier == other.multiplier && p.currency == other.currency
}

// String is the display form.
func (p Posted) String() string {
	return fmt.Sprintf("posted[%s %d]", p.currency, p.multiplier)
}
