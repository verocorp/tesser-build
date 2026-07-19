package ddd

import "testing"

func TestNewFlightNumber_Valid(t *testing.T) {
	valid := []string{"AA100", "DL2703", "UAL204", "WN2400"}
	for _, v := range valid {
		if _, err := NewFlightNumber(v); err != nil {
			t.Errorf("NewFlightNumber(%q) returned unexpected error: %v", v, err)
		}
	}
}

func TestNewFlightNumber_InvalidRejected(t *testing.T) {
	invalid := []string{
		"",
		"100",
		"AA",
		"aa100",
		"ABCD100",
		"AA12345",
		"AA 100",
	}
	for _, v := range invalid {
		if _, err := NewFlightNumber(v); err == nil {
			t.Errorf("NewFlightNumber(%q) = nil error, want error", v)
		}
	}
}

func TestFlightNumber_Equality(t *testing.T) {
	a := MustNewFlightNumber("DL2703")
	b := MustNewFlightNumber("DL2703")
	c := MustNewFlightNumber("DL2704")

	if a != b {
		t.Error("flight numbers built from the same value must be equal")
	}
	if a == c {
		t.Error("flight numbers built from different values must not be equal")
	}
}

func TestMustNewFlightNumber_PanicsOnInvalid(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Error("MustNewFlightNumber did not panic on invalid input")
		}
	}()
	MustNewFlightNumber("not-a-flight")
}

func TestFlightNumber_String(t *testing.T) {
	f := MustNewFlightNumber("DL2703")
	if got, want := f.String(), "DL2703"; got != want {
		t.Errorf("String() = %q, want %q", got, want)
	}
}
