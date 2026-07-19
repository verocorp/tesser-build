package catalog

import "testing"

func TestMoney_EqualityAcrossRepresentations(t *testing.T) {

	a := MustNewMoney(MoneySpec{Amount: "1.5", Currency: "USD"})
	b := MustNewMoney(MoneySpec{Amount: "1.50", Currency: "USD"})
	if !a.Equal(b) {
		t.Errorf("1.5 and 1.50 USD should be equal by value")
	}
	if a.Equal(MustNewMoney(MoneySpec{Amount: "1.5", Currency: "EUR"})) {
		t.Errorf("same amount, different currency should not be equal")
	}
	if a.Equal(MustNewMoney(MoneySpec{Amount: "2.0", Currency: "USD"})) {
		t.Errorf("different amounts should not be equal")
	}
}

func TestMoney_RejectsInvalid(t *testing.T) {
	cases := map[string]MoneySpec{
		"empty currency": {Amount: "1.00", Currency: ""},
		"non-numeric":    {Amount: "abc", Currency: "USD"},
		"negative":       {Amount: "-1.00", Currency: "USD"},
	}
	for name, spec := range cases {
		t.Run(name, func(t *testing.T) {
			if _, err := NewMoney(spec); err == nil {
				t.Errorf("expected %s to be rejected", name)
			}
		})
	}
}

func TestMoney_Add(t *testing.T) {
	a := MustNewMoney(MoneySpec{Amount: "1.50", Currency: "USD"})
	b := MustNewMoney(MoneySpec{Amount: "2.25", Currency: "USD"})
	sum, err := a.Add(b)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !sum.Equal(MustNewMoney(MoneySpec{Amount: "3.75", Currency: "USD"})) {
		t.Errorf("1.50 + 2.25 should be 3.75, got %s", sum)
	}
}

func TestMoney_AddRejectsCurrencyMismatch(t *testing.T) {
	usd := MustNewMoney(MoneySpec{Amount: "1.00", Currency: "USD"})
	eur := MustNewMoney(MoneySpec{Amount: "1.00", Currency: "EUR"})
	if _, err := usd.Add(eur); err == nil {
		t.Errorf("adding USD and EUR should be rejected")
	}
}

func TestMoney_String(t *testing.T) {

	m := MustNewMoney(MoneySpec{Amount: "1.5", Currency: "USD"})
	if got := m.String(); got != "1.50 USD" {
		t.Errorf("String() = %q, want %q", got, "1.50 USD")
	}
}
