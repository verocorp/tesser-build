package campaign

import "testing"

func TestNewSlug_Rejection(t *testing.T) {
	cases := map[string]string{
		"too short":          "abc",
		"too long":           "this-slug-is-way-too-long-to-be-valid",
		"uppercase letters":  "Spring-Sale",
		"invalid characters": "spring_sale!",
		"empty":              "",
	}
	for name, value := range cases {
		t.Run(name, func(t *testing.T) {
			if _, err := NewSlug(value); err == nil {
				t.Fatalf("NewSlug(%q): expected error, got nil", value)
			}
		})
	}
}

func TestNewSlug_Accepts(t *testing.T) {
	cases := []string{"spring-sale", "abc1", "a1b2c3d4e5f6g7h8i9j0"}
	for _, value := range cases {
		if _, err := NewSlug(value); err != nil {
			t.Fatalf("NewSlug(%q): unexpected error: %v", value, err)
		}
	}
}

func TestMustNewSlug_PanicsOnInvalid(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Fatal("MustNewSlug: expected panic on invalid input")
		}
	}()
	MustNewSlug("NOPE")
}

func TestSlug_Equality(t *testing.T) {
	a := MustNewSlug("spring-sale")
	b := MustNewSlug("spring-sale")
	c := MustNewSlug("winter-sale")

	if a != b {
		t.Error("slugs with the same value must be equal")
	}
	if a == c {
		t.Error("slugs with different values must not be equal")
	}
}

func TestSlug_String(t *testing.T) {
	s := MustNewSlug("spring-sale")
	if s.String() != "spring-sale" {
		t.Errorf("String() = %q, want %q", s.String(), "spring-sale")
	}
}
