package lending

import (
	"reflect"
	"testing"
)

func TestNewMoney_Valid(t *testing.T) {
	for _, cents := range []int64{0, 1, 25, 1000} {
		if _, err := NewMoney(cents); err != nil {
			t.Errorf("NewMoney(%d) returned unexpected error: %v", cents, err)
		}
	}
}

func TestNewMoney_NegativeRejected(t *testing.T) {
	if _, err := NewMoney(-1); err == nil {
		t.Error("NewMoney(-1) = nil error, want error")
	}
}

func TestMustNewMoney_PanicsOnInvalid(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Error("MustNewMoney did not panic on invalid input")
		}
	}()
	MustNewMoney(-1)
}

func TestMoney_Equality(t *testing.T) {
	if !reflect.TypeFor[Money]().Comparable() {
		t.Fatal("Money wraps a single int64 and must remain natively comparable")
	}
	a := MustNewMoney(125)
	b := MustNewMoney(125)
	c := MustNewMoney(150)
	if a != b {
		t.Error("money built from the same cents must be equal")
	}
	if a == c {
		t.Error("money built from different cents must not be equal")
	}
}

func TestMoney_Add(t *testing.T) {
	a := MustNewMoney(125)
	b := MustNewMoney(50)
	if got, want := a.Add(b).Cents(), int64(175); got != want {
		t.Errorf("Add: Cents() = %d, want %d", got, want)
	}
}

func TestMoney_String(t *testing.T) {
	tests := []struct {
		cents int64
		want  string
	}{
		{0, "$0.00"},
		{5, "$0.05"},
		{100, "$1.00"},
		{125, "$1.25"},
	}
	for _, tt := range tests {
		if got := MustNewMoney(tt.cents).String(); got != tt.want {
			t.Errorf("Money{%d}.String() = %q, want %q", tt.cents, got, tt.want)
		}
	}
}
