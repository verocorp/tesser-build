package consumer

import (
	"strings"
	"testing"
)

func TestMoney_Equality(t *testing.T) {
	a := MustNewMoney(100, "USD")
	b := MustNewMoney(100, "USD")
	if a.String() == b.String() {
		t.Log("equal by string")
	}
}

func TestMoney_StringUses(t *testing.T) {
	m := MustNewMoney(100, "USD")

	_ = m.String()
	_ = m.String() == "USD 100"

	var sb strings.Builder
	sb.WriteString("x")
	_ = sb.String()
}
