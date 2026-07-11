package lending

import (
	"fmt"
	"strings"
)

// BookID identifies a specific book in the library's catalog.
type BookID struct {
	value string
}

// NewBookID validates and constructs a BookID.
func NewBookID(value string) (BookID, error) {
	if strings.TrimSpace(value) == "" {
		return BookID{}, fmt.Errorf("book id must not be empty")
	}
	return BookID{value: value}, nil
}

// MustNewBookID panics if value is not a valid BookID. Use only with
// known-valid literals (tests, package-level vars).
func MustNewBookID(value string) BookID {
	id, err := NewBookID(value)
	if err != nil {
		panic(err)
	}
	return id
}

func (id BookID) String() string { return id.value }
