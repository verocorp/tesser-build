package lending

import "testing"

func TestNewMemberID_Valid(t *testing.T) {
	if _, err := NewMemberID("member-1"); err != nil {
		t.Errorf("NewMemberID(%q) returned unexpected error: %v", "member-1", err)
	}
}

func TestNewMemberID_EmptyRejected(t *testing.T) {
	for _, v := range []string{"", "   "} {
		if _, err := NewMemberID(v); err == nil {
			t.Errorf("NewMemberID(%q) = nil error, want error", v)
		}
	}
}

func TestMemberID_Equality(t *testing.T) {
	a := MustNewMemberID("member-1")
	b := MustNewMemberID("member-1")
	c := MustNewMemberID("member-2")
	if a != b {
		t.Error("member ids built from the same value must be equal")
	}
	if a == c {
		t.Error("member ids built from different values must not be equal")
	}
}

func TestMustNewMemberID_PanicsOnInvalid(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Error("MustNewMemberID did not panic on invalid input")
		}
	}()
	MustNewMemberID("")
}

func TestMemberID_String(t *testing.T) {
	id := MustNewMemberID("member-1")
	if got, want := id.String(), "member-1"; got != want {
		t.Errorf("String() = %q, want %q", got, want)
	}
}
