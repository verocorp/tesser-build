package consumer

import (
	"strings"
	"testing"
)

// TestMoney_Equality contains the real stringequality hazard: comparing two
// value objects by their string form. This is the one stringequality finding
// the e2e expects.
func TestMoney_Equality(t *testing.T) {
	a := MustNewMoney(100, "USD")
	b := MustNewMoney(100, "USD")
	if a.String() == b.String() {
		t.Log("equal by string")
	}
}

// TestMoney_StringUses collects the .String() uses that the tightened analyzer
// must NOT flag — these are the exact shapes that were false positives on quanta
// before the comparison-context tightening.
func TestMoney_StringUses(t *testing.T) {
	m := MustNewMoney(100, "USD")

	_ = m.String()              // discarded display / race-exercise
	_ = m.String() == "USD 100" // compared to a string literal, not another VO

	var sb strings.Builder // stdlib .String(), not a value object at all
	sb.WriteString("x")
	_ = sb.String()
}
