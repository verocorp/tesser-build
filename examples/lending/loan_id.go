package lending

import (
	"fmt"
	"strings"
)

type LoanID struct {
	value string
}

func NewLoanID(value string) (LoanID, error) {
	if strings.TrimSpace(value) == "" {
		return LoanID{}, fmt.Errorf("loan id must not be empty")
	}
	return LoanID{value: value}, nil
}

func MustNewLoanID(value string) LoanID {
	id, err := NewLoanID(value)
	if err != nil {
		panic(err)
	}
	return id
}

func (id LoanID) String() string { return id.value }
