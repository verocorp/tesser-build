package ddd

import (
	"reflect"
	"testing"
)

func validManifestSpec() BoardingManifestSpec {
	return BoardingManifestSpec{
		Flight: "DL2703",
		Passengers: []PassengerSpec{
			{ID: "PNR-1", Name: "Ada Lovelace", Seat: "12A"},
			{ID: "PNR-2", Name: "Grace Hopper", Seat: "12B"},
		},
	}
}

func TestNewBoardingManifest_Valid(t *testing.T) {
	spec := validManifestSpec()
	m, err := NewBoardingManifest(spec)
	if err != nil {
		t.Fatalf("NewBoardingManifest(%+v) returned unexpected error: %v", spec, err)
	}
	if got, want := len(m.Passengers()), len(spec.Passengers); got != want {
		t.Errorf("len(Passengers()) = %d, want %d", got, want)
	}
	if got, want := m.Flight().String(), spec.Flight; got != want {
		t.Errorf("Flight() = %q, want %q", got, want)
	}
}

func TestNewBoardingManifest_InvalidFlightNumberRejected(t *testing.T) {
	spec := validManifestSpec()
	spec.Flight = "not-a-flight"
	if _, err := NewBoardingManifest(spec); err == nil {
		t.Error("NewBoardingManifest with invalid flight number = nil error, want error")
	}
}

func TestNewBoardingManifest_InvalidPassengerRejected(t *testing.T) {
	spec := validManifestSpec()
	spec.Passengers[1].Name = ""
	if _, err := NewBoardingManifest(spec); err == nil {
		t.Error("NewBoardingManifest with invalid passenger = nil error, want error")
	}
}

func TestNewBoardingManifest_DuplicateSeatRejected(t *testing.T) {
	spec := BoardingManifestSpec{
		Flight: "DL2703",
		Passengers: []PassengerSpec{
			{ID: "PNR-1", Name: "Ada Lovelace", Seat: "12A"},
			{ID: "PNR-2", Name: "Grace Hopper", Seat: "12A"},
		},
	}
	if _, err := NewBoardingManifest(spec); err == nil {
		t.Error("NewBoardingManifest with a duplicate seat = nil error, want error")
	}
}

func TestBoardingManifest_Passengers_DefensiveCopy(t *testing.T) {
	m, err := NewBoardingManifest(validManifestSpec())
	if err != nil {
		t.Fatalf("NewBoardingManifest returned unexpected error: %v", err)
	}

	got := m.Passengers()
	got[0] = Passenger{}

	again := m.Passengers()
	if again[0].ID().String() != "PNR-1" {
		t.Error("mutating the slice returned by Passengers() must not affect the manifest")
	}
}

func TestBoardingManifest_Equality_Blocked(t *testing.T) {
	if reflect.TypeFor[BoardingManifest]().Comparable() {
		t.Fatal("BoardingManifest must be non-comparable")
	}
}

func TestBoardingManifest_AddPassenger_Succeeds(t *testing.T) {
	m, err := NewBoardingManifest(validManifestSpec())
	if err != nil {
		t.Fatalf("NewBoardingManifest returned unexpected error: %v", err)
	}

	newPassenger, err := NewPassenger(PassengerSpec{ID: "PNR-3", Name: "Katherine Johnson", Seat: "14C"})
	if err != nil {
		t.Fatalf("NewPassenger returned unexpected error: %v", err)
	}
	if err := m.AddPassenger(newPassenger); err != nil {
		t.Fatalf("AddPassenger returned unexpected error: %v", err)
	}

	passengers := m.Passengers()
	if got, want := len(passengers), 3; got != want {
		t.Fatalf("len(Passengers()) = %d, want %d", got, want)
	}
	if !passengers[2].Equal(newPassenger) {
		t.Error("AddPassenger did not seat the new passenger")
	}
}

func TestBoardingManifest_AddPassenger_RejectsDuplicateSeat(t *testing.T) {
	m, err := NewBoardingManifest(validManifestSpec())
	if err != nil {
		t.Fatalf("NewBoardingManifest returned unexpected error: %v", err)
	}
	before := len(m.Passengers())

	conflicting, err := NewPassenger(PassengerSpec{ID: "PNR-3", Name: "Katherine Johnson", Seat: "12A"})
	if err != nil {
		t.Fatalf("NewPassenger returned unexpected error: %v", err)
	}
	if err := m.AddPassenger(conflicting); err == nil {
		t.Error("AddPassenger with an occupied seat = nil error, want error")
	}

	if got := len(m.Passengers()); got != before {
		t.Errorf("len(Passengers()) after rejected AddPassenger = %d, want %d (no partial mutation)", got, before)
	}
}
