package ddd

import "fmt"

type Passenger struct {
	id   PassengerID
	name PassengerName
	seat SeatNumber
}

type PassengerSpec struct {
	ID   string
	Name string
	Seat string
}

func NewPassenger(spec PassengerSpec) (Passenger, error) {
	id, err := NewPassengerID(spec.ID)
	if err != nil {
		return Passenger{}, fmt.Errorf("invalid passenger ID: %w", err)
	}
	name, err := NewPassengerName(spec.Name)
	if err != nil {
		return Passenger{}, fmt.Errorf("invalid passenger name: %w", err)
	}
	seat, err := NewSeatNumber(spec.Seat)
	if err != nil {
		return Passenger{}, fmt.Errorf("invalid seat number: %w", err)
	}
	return Passenger{id: id, name: name, seat: seat}, nil
}

func (p Passenger) ID() PassengerID { return p.id }

func (p Passenger) Name() PassengerName { return p.name }

func (p Passenger) Seat() SeatNumber { return p.seat }

func (p Passenger) Equal(other Passenger) bool {
	return p.id == other.id
}
