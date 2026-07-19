package catalog

import (
	"fmt"
	"regexp"
)

var skuPattern = regexp.MustCompile(`^[A-Z0-9-]{3,20}$`)

type SKU struct {
	value string
}

func NewSKU(value string) (SKU, error) {
	if !skuPattern.MatchString(value) {
		return SKU{}, fmt.Errorf("invalid SKU %q: must be 3-20 characters of uppercase letters, digits, and hyphens", value)
	}
	return SKU{value: value}, nil
}

func MustNewSKU(value string) SKU {
	s, err := NewSKU(value)
	if err != nil {
		panic(err)
	}
	return s
}

func (s SKU) String() string {
	return s.value
}
