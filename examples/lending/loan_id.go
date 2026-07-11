package lending

import (
	"fmt"
	"strings"
)

// LoanID identifies one specific checkout of one book. It is the identity
// a Loan entity carries for its whole lifecycle — from checkout through
// return.
type LoanID struct {
	value string
}

// NewLoanID validates and constructs a LoanID.
func NewLoanID(value string) (LoanID, error) {
	if strings.TrimSpace(value) == "" {
		return LoanID{}, fmt.Errorf("loan id must not be empty")
	}
	return LoanID{value: value}, nil
}

// MustNewLoanID panics if value is not a valid LoanID. Use only with
// known-valid literals (tests, package-level vars).
func MustNewLoanID(value string) LoanID {
	id, err := NewLoanID(value)
	if err != nil {
		panic(err)
	}
	return id
}

func (id LoanID) String() string { return id.value }
