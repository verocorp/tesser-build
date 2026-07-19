package ddd

import (
	"fmt"
	"strings"
)

type PassengerID struct {
	value string
}

func NewPassengerID(value string) (PassengerID, error) {
	if strings.TrimSpace(value) == "" {
		return PassengerID{}, fmt.Errorf("passenger ID must not be empty")
	}
	return PassengerID{value: value}, nil
}

func MustNewPassengerID(value string) PassengerID {
	id, err := NewPassengerID(value)
	if err != nil {
		panic(err)
	}
	return id
}

func (p PassengerID) String() string {
	return p.value
}
