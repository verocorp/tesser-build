package ddd

import (
	"fmt"
	"regexp"
)

var flightNumberPattern = regexp.MustCompile(`^[A-Z]{2,3}[0-9]{1,4}$`)

type FlightNumber struct {
	value string
}

func NewFlightNumber(value string) (FlightNumber, error) {
	if !flightNumberPattern.MatchString(value) {
		return FlightNumber{}, fmt.Errorf("invalid flight number: %q", value)
	}
	return FlightNumber{value: value}, nil
}

func MustNewFlightNumber(value string) FlightNumber {
	f, err := NewFlightNumber(value)
	if err != nil {
		panic(err)
	}
	return f
}

func (f FlightNumber) String() string {
	return f.value
}
