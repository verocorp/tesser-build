package a

import "testing"

// TestCovered_Equality locks Covered's equality semantics — this is the
// coverage the analyzer requires.
func TestCovered_Equality(t *testing.T) {
	x, _ := NewCovered("v")
	y, _ := NewCovered("v")
	if x != y {
		t.Fatal("expected equal")
	}
}
