package campaign

import (
	"fmt"
	"regexp"
)

// slugPattern enforces the business rule: 4-20 characters, lowercase
// letters, digits, and hyphens only.
var slugPattern = regexp.MustCompile(`^[a-z0-9-]{4,20}$`)

// Slug is the short code of a ShortLink (e.g. "spring-sale"). It is a
// simple, single-value value object: one field, flat constructor, native
// equality (a slug has exactly one representation).
type Slug struct {
	value string
}

// NewSlug validates and constructs a Slug.
func NewSlug(value string) (Slug, error) {
	if !slugPattern.MatchString(value) {
		return Slug{}, fmt.Errorf("invalid slug %q: must be 4-20 characters of lowercase letters, digits, and hyphens", value)
	}
	return Slug{value: value}, nil
}

// MustNewSlug panics on invalid input; use only with known-valid literals
// (tests, package-level vars), never with runtime data.
func MustNewSlug(value string) Slug {
	s, err := NewSlug(value)
	if err != nil {
		panic(err)
	}
	return s
}

// String is the display form and the sole string accessor.
func (s Slug) String() string {
	return s.value
}
