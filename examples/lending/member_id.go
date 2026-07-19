package lending

import (
	"fmt"
	"strings"
)

type MemberID struct {
	value string
}

func NewMemberID(value string) (MemberID, error) {
	if strings.TrimSpace(value) == "" {
		return MemberID{}, fmt.Errorf("member id must not be empty")
	}
	return MemberID{value: value}, nil
}

func MustNewMemberID(value string) MemberID {
	id, err := NewMemberID(value)
	if err != nil {
		panic(err)
	}
	return id
}

func (id MemberID) String() string { return id.value }
