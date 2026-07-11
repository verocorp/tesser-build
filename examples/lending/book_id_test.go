package lending

import "testing"

func TestNewBookID_Valid(t *testing.T) {
	if _, err := NewBookID("book-1"); err != nil {
		t.Errorf("NewBookID(%q) returned unexpected error: %v", "book-1", err)
	}
}

func TestNewBookID_EmptyRejected(t *testing.T) {
	for _, v := range []string{"", "   "} {
		if _, err := NewBookID(v); err == nil {
			t.Errorf("NewBookID(%q) = nil error, want error", v)
		}
	}
}

func TestBookID_Equality(t *testing.T) {
	a := MustNewBookID("book-1")
	b := MustNewBookID("book-1")
	c := MustNewBookID("book-2")
	if a != b {
		t.Error("book ids built from the same value must be equal")
	}
	if a == c {
		t.Error("book ids built from different values must not be equal")
	}
}

func TestMustNewBookID_PanicsOnInvalid(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Error("MustNewBookID did not panic on invalid input")
		}
	}()
	MustNewBookID("")
}

func TestBookID_String(t *testing.T) {
	id := MustNewBookID("book-1")
	if got, want := id.String(), "book-1"; got != want {
		t.Errorf("String() = %q, want %q", got, want)
	}
}
