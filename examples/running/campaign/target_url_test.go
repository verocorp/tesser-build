package campaign

import "testing"

func TestNewTargetURL_Rejection(t *testing.T) {
	cases := []string{"", "example.com", "ftp://example.com", "www.example.com"}
	for _, value := range cases {
		if _, err := NewTargetURL(value); err == nil {
			t.Fatalf("NewTargetURL(%q): expected error, got nil", value)
		}
	}
}

func TestNewTargetURL_Accepts(t *testing.T) {
	cases := []string{"http://example.com", "https://example.com/spring"}
	for _, value := range cases {
		if _, err := NewTargetURL(value); err != nil {
			t.Fatalf("NewTargetURL(%q): unexpected error: %v", value, err)
		}
	}
}

func TestMustNewTargetURL_PanicsOnInvalid(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Fatal("MustNewTargetURL: expected panic on invalid input")
		}
	}()
	MustNewTargetURL("not-a-url")
}

func TestTargetURL_Equality(t *testing.T) {
	a := MustNewTargetURL("https://example.com")
	b := MustNewTargetURL("https://example.com")
	c := MustNewTargetURL("https://example.org")

	if a != b {
		t.Error("target URLs with the same value must be equal")
	}
	if a == c {
		t.Error("target URLs with different values must not be equal")
	}
}

func TestTargetURL_String(t *testing.T) {
	u := MustNewTargetURL("https://example.com")
	if u.String() != "https://example.com" {
		t.Errorf("String() = %q, want %q", u.String(), "https://example.com")
	}
}
