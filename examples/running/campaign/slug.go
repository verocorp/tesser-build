package campaign

import (
	"fmt"
	"regexp"
)

var slugPattern = regexp.MustCompile(`^[a-z0-9-]{4,20}$`)

type Slug struct {
	value string
}

func NewSlug(value string) (Slug, error) {
	if !slugPattern.MatchString(value) {
		return Slug{}, fmt.Errorf("invalid slug %q: must be 4-20 characters of lowercase letters, digits, and hyphens", value)
	}
	return Slug{value: value}, nil
}

func MustNewSlug(value string) Slug {
	s, err := NewSlug(value)
	if err != nil {
		panic(err)
	}
	return s
}

func (s Slug) String() string {
	return s.value
}
