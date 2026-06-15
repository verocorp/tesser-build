package a

import (
	"testing"

	"assert"
	"require"
)

// A lone .String() is legitimate display use — not flagged anywhere.
func TestFoo_Display(t *testing.T) {
	f := Foo{v: "x"}
	_ = f.String() // discarded race-exercise / display: allowed
	t.Log(f.String())
}

// .String() asserted against a string literal is a representation check, not a
// value-object comparison — not flagged.
func TestFoo_StringLiteral(t *testing.T) {
	f := Foo{v: "x"}
	assert.Equal(t, "x", f.String())
}

// Comparing two value objects by their string form via == / != is the hazard.
func TestFoo_BinaryEquality(t *testing.T) {
	a := Foo{v: "a"}
	b := Foo{v: "b"}
	_ = a.String() == b.String() // want `compare by value`
	_ = a.String() != b.String() // want `compare by value`
}

// The same hazard through a testify equality assertion (and its variants).
func TestFoo_AssertEquality(t *testing.T) {
	a := Foo{v: "a"}
	b := Foo{v: "b"}
	assert.Equal(t, a.String(), b.String())         // want `compare by value`
	require.Equal(t, a.String(), b.String())        // want `compare by value`
	assert.NotEqual(t, a.String(), b.String())      // want `compare by value`
	assert.Equalf(t, a.String(), b.String(), "msg") // want `compare by value`
}

// ToString is not String, so it is ignored even in a comparison.
func TestFoo_Other(t *testing.T) {
	a := Foo{v: "a"}
	b := Foo{v: "b"}
	_ = a.ToString() == b.ToString()
}
