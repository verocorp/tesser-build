package catalog

import "fmt"

type Product struct {
	sku    SKU
	price  Money
	labels Labels
}

type ProductSpec struct {
	SKU    string
	Price  MoneySpec
	Labels map[string]string
}

func NewProduct(spec ProductSpec) (Product, error) {
	sku, err := NewSKU(spec.SKU)
	if err != nil {
		return Product{}, fmt.Errorf("invalid sku: %w", err)
	}
	price, err := NewMoney(spec.Price)
	if err != nil {
		return Product{}, fmt.Errorf("invalid price: %w", err)
	}
	return Product{sku: sku, price: price, labels: NewLabels(spec.Labels)}, nil
}

func (p Product) SKU() SKU { return p.sku }

func (p Product) Price() Money { return p.price }

func (p Product) Labels() Labels { return p.labels }

func (p Product) Equal(other Product) bool {
	return p.sku == other.sku
}
