package lending

import (
	"fmt"
	"strings"
)

type BookID struct {
	value string
}

func NewBookID(value string) (BookID, error) {
	if strings.TrimSpace(value) == "" {
		return BookID{}, fmt.Errorf("book id must not be empty")
	}
	return BookID{value: value}, nil
}

func MustNewBookID(value string) BookID {
	id, err := NewBookID(value)
	if err != nil {
		panic(err)
	}
	return id
}

func (id BookID) String() string { return id.value }
