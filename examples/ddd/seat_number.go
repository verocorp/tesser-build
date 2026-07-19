package ddd

import (
	"fmt"
	"regexp"
)

var seatNumberPattern = regexp.MustCompile(`^[1-9][0-9]?[A-Z]$`)

type SeatNumber struct {
	value string
}

func NewSeatNumber(value string) (SeatNumber, error) {
	if !seatNumberPattern.MatchString(value) {
		return SeatNumber{}, fmt.Errorf("invalid seat number: %q", value)
	}
	return SeatNumber{value: value}, nil
}

func MustNewSeatNumber(value string) SeatNumber {
	s, err := NewSeatNumber(value)
	if err != nil {
		panic(err)
	}
	return s
}

func (s SeatNumber) String() string {
	return s.value
}
