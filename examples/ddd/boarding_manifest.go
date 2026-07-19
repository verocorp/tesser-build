package ddd

import "fmt"

type BoardingManifest struct {
	flight     FlightNumber
	passengers []Passenger
	_          [0]func()
}

type BoardingManifestSpec struct {
	Flight     string
	Passengers []PassengerSpec
}

func NewBoardingManifest(spec BoardingManifestSpec) (BoardingManifest, error) {
	flight, err := NewFlightNumber(spec.Flight)
	if err != nil {
		return BoardingManifest{}, fmt.Errorf("invalid flight number: %w", err)
	}

	manifest := BoardingManifest{flight: flight}
	for i, pSpec := range spec.Passengers {
		passenger, err := NewPassenger(pSpec)
		if err != nil {
			return BoardingManifest{}, fmt.Errorf("invalid passenger at index %d: %w", i, err)
		}
		if err := manifest.addPassenger(passenger); err != nil {
			return BoardingManifest{}, err
		}
	}
	return manifest, nil
}

func (m BoardingManifest) Flight() FlightNumber { return m.flight }

func (m BoardingManifest) Passengers() []Passenger {
	out := make([]Passenger, len(m.passengers))
	copy(out, m.passengers)
	return out
}

func (m *BoardingManifest) AddPassenger(p Passenger) error {
	return m.addPassenger(p)
}

func (m *BoardingManifest) addPassenger(p Passenger) error {
	for _, existing := range m.passengers {
		if existing.Seat() == p.Seat() {
			return fmt.Errorf("seat %s is already occupied", p.Seat())
		}
	}
	m.passengers = append(m.passengers, p)
	return nil
}
