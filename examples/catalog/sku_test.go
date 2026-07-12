package catalog

import "testing"

func TestSKU_Equality(t *testing.T) {
	black := MustNewSKU("TSHIRT-BLK-M")
	sameBlack := MustNewSKU("TSHIRT-BLK-M")
	white := MustNewSKU("TSHIRT-WHT-M")
	if black != sameBlack {
		t.Errorf("SKUs with the same value should be equal")
	}
	if black == white {
		t.Errorf("SKUs with different values should not be equal")
	}
}

func TestSKU_RejectsInvalid(t *testing.T) {
	for _, bad := range []string{"", "ab", "tshirt", "TS_HIRT", "TOO-LONG-A-SKU-VALUE-X"} {
		if _, err := NewSKU(bad); err == nil {
			t.Errorf("expected %q to be rejected", bad)
		}
	}
}

func TestSKU_String(t *testing.T) {
	if got := MustNewSKU("TSHIRT-BLK-M").String(); got != "TSHIRT-BLK-M" {
		t.Errorf("String() = %q", got)
	}
}
