package catalog

import (
	"fmt"
	"regexp"
)

// skuPattern enforces the format rule: 3-20 characters of uppercase letters,
// digits, and hyphens (e.g. "TSHIRT-BLK-M").
var skuPattern = regexp.MustCompile(`^[A-Z0-9-]{3,20}$`)

// SKU is a product's stock-keeping unit and its identity. Simple,
// single-value value object: one field, flat constructor, native equality.
type SKU struct {
	value string
}

// NewSKU validates and constructs a SKU.
func NewSKU(value string) (SKU, error) {
	if !skuPattern.MatchString(value) {
		return SKU{}, fmt.Errorf("invalid SKU %q: must be 3-20 characters of uppercase letters, digits, and hyphens", value)
	}
	return SKU{value: value}, nil
}

// MustNewSKU panics on invalid input; use only with known-valid literals
// (tests, package-level vars), never with runtime data.
func MustNewSKU(value string) SKU {
	s, err := NewSKU(value)
	if err != nil {
		panic(err)
	}
	return s
}

// String is the display form and the sole string accessor.
func (s SKU) String() string {
	return s.value
}
