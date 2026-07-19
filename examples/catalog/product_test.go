package catalog

import "testing"

func validProductSpec() ProductSpec {
	return ProductSpec{
		SKU:    "TSHIRT-BLK-M",
		Price:  MoneySpec{Amount: "19.99", Currency: "USD"},
		Labels: map[string]string{"color": "black", "size": "M"},
	}
}

func TestProduct_Construction(t *testing.T) {
	p, err := NewProduct(validProductSpec())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if p.SKU() != MustNewSKU("TSHIRT-BLK-M") {
		t.Errorf("unexpected sku %s", p.SKU())
	}
	if !p.Price().Equal(MustNewMoney(MoneySpec{Amount: "19.99", Currency: "USD"})) {
		t.Errorf("unexpected price %s", p.Price())
	}
	if got, _ := p.Labels().Get("color"); got != "black" {
		t.Errorf("unexpected color label %q", got)
	}
}

func TestProduct_RejectsInvalidChild(t *testing.T) {
	spec := validProductSpec()
	spec.Price = MoneySpec{Amount: "-1.00", Currency: "USD"}
	if _, err := NewProduct(spec); err == nil {
		t.Errorf("a negative price should make the product invalid")
	}
}

func TestProduct_EqualityIsIdentity(t *testing.T) {
	a, _ := NewProduct(validProductSpec())

	other := validProductSpec()
	other.Price = MoneySpec{Amount: "29.99", Currency: "USD"}
	other.Labels = map[string]string{"color": "white"}
	b, _ := NewProduct(other)
	if !a.Equal(b) {
		t.Errorf("products with the same SKU should be equal by identity")
	}

	diff := validProductSpec()
	diff.SKU = "TSHIRT-WHT-L"
	c, _ := NewProduct(diff)
	if a.Equal(c) {
		t.Errorf("products with different SKUs should not be equal")
	}
}
