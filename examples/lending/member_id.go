package lending

import (
	"fmt"
	"strings"
)

// MemberID identifies a specific library member, independent of anything
// else about them. It is the identity a Member aggregate carries for its
// whole lifecycle.
type MemberID struct {
	value string
}

// NewMemberID validates and constructs a MemberID.
func NewMemberID(value string) (MemberID, error) {
	if strings.TrimSpace(value) == "" {
		return MemberID{}, fmt.Errorf("member id must not be empty")
	}
	return MemberID{value: value}, nil
}

// MustNewMemberID panics if value is not a valid MemberID. Use only with
// known-valid literals (tests, package-level vars).
func MustNewMemberID(value string) MemberID {
	id, err := NewMemberID(value)
	if err != nil {
		panic(err)
	}
	return id
}

func (id MemberID) String() string { return id.value }
