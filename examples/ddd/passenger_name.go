package ddd

import (
	"fmt"
	"strings"
)

type PassengerName struct {
	value string
}

func NewPassengerName(value string) (PassengerName, error) {
	if strings.TrimSpace(value) == "" {
		return PassengerName{}, fmt.Errorf("passenger name must not be empty")
	}
	return PassengerName{value: value}, nil
}

func MustNewPassengerName(value string) PassengerName {
	n, err := NewPassengerName(value)
	if err != nil {
		panic(err)
	}
	return n
}

func (n PassengerName) String() string {
	return n.value
}
