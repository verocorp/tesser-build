package lending

import "testing"

func TestNewLoanID_Valid(t *testing.T) {
	if _, err := NewLoanID("loan-1"); err != nil {
		t.Errorf("NewLoanID(%q) returned unexpected error: %v", "loan-1", err)
	}
}

func TestNewLoanID_EmptyRejected(t *testing.T) {
	for _, v := range []string{"", "   "} {
		if _, err := NewLoanID(v); err == nil {
			t.Errorf("NewLoanID(%q) = nil error, want error", v)
		}
	}
}

func TestLoanID_Equality(t *testing.T) {
	a := MustNewLoanID("loan-1")
	b := MustNewLoanID("loan-1")
	c := MustNewLoanID("loan-2")
	if a != b {
		t.Error("loan ids built from the same value must be equal")
	}
	if a == c {
		t.Error("loan ids built from different values must not be equal")
	}
}

func TestMustNewLoanID_PanicsOnInvalid(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Error("MustNewLoanID did not panic on invalid input")
		}
	}()
	MustNewLoanID("")
}

func TestLoanID_String(t *testing.T) {
	id := MustNewLoanID("loan-1")
	if got, want := id.String(), "loan-1"; got != want {
		t.Errorf("String() = %q, want %q", got, want)
	}
}
