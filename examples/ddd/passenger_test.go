package ddd

import "testing"

func validPassengerSpec() PassengerSpec {
	return PassengerSpec{ID: "PNR-ABC123", Name: "Ada Lovelace", Seat: "12A"}
}

func TestNewPassenger_Valid(t *testing.T) {
	spec := validPassengerSpec()
	p, err := NewPassenger(spec)
	if err != nil {
		t.Fatalf("NewPassenger(%+v) returned unexpected error: %v", spec, err)
	}
	if got, want := p.ID().String(), spec.ID; got != want {
		t.Errorf("ID() = %q, want %q", got, want)
	}
	if got, want := p.Name().String(), spec.Name; got != want {
		t.Errorf("Name() = %q, want %q", got, want)
	}
	if got, want := p.Seat().String(), spec.Seat; got != want {
		t.Errorf("Seat() = %q, want %q", got, want)
	}
}

func TestNewPassenger_InvalidIDRejected(t *testing.T) {
	spec := validPassengerSpec()
	spec.ID = ""
	if _, err := NewPassenger(spec); err == nil {
		t.Error("NewPassenger with empty ID = nil error, want error")
	}
}

func TestNewPassenger_InvalidNameRejected(t *testing.T) {
	spec := validPassengerSpec()
	spec.Name = ""
	if _, err := NewPassenger(spec); err == nil {
		t.Error("NewPassenger with empty name = nil error, want error")
	}
}

func TestNewPassenger_InvalidSeatRejected(t *testing.T) {
	spec := validPassengerSpec()
	spec.Seat = "not-a-seat"
	if _, err := NewPassenger(spec); err == nil {
		t.Error("NewPassenger with invalid seat = nil error, want error")
	}
}

func TestPassenger_Equality(t *testing.T) {
	same, err := NewPassenger(PassengerSpec{ID: "PNR-ABC123", Name: "Ada Lovelace", Seat: "12A"})
	if err != nil {
		t.Fatalf("NewPassenger returned unexpected error: %v", err)
	}
	renamedReseated, err := NewPassenger(PassengerSpec{ID: "PNR-ABC123", Name: "A. Lovelace", Seat: "14C"})
	if err != nil {
		t.Fatalf("NewPassenger returned unexpected error: %v", err)
	}
	if !same.Equal(renamedReseated) {
		t.Error("passengers with the same ID must be Equal regardless of name or seat")
	}

	other, err := NewPassenger(PassengerSpec{ID: "PNR-XYZ999", Name: "Ada Lovelace", Seat: "12A"})
	if err != nil {
		t.Fatalf("NewPassenger returned unexpected error: %v", err)
	}
	if same.Equal(other) {
		t.Error("passengers with different IDs must not be Equal even with identical attributes")
	}
}
