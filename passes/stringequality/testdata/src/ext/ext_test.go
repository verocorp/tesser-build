package ext_test

import (
	"testing"

	"ext"
)

// An external test package (package ext_test) is still scanned: comparing two
// value objects by their .String() form is flagged here too. A lone display
// .String() is not.
func TestFoo(t *testing.T) {
	a := ext.Foo{}
	b := ext.Foo{}
	_ = a.String()               // display: allowed
	_ = a.String() == b.String() // want `compare by value`
}
