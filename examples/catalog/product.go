package catalog

import "fmt"

// Product is the entity that gives the value objects a domain-meaningful home:
// the system tracks a specific product by its SKU identity, and two products
// with identical prices and labels but different SKUs are different products.
// It is a fact entity — it records a product's price and labels, with no
// lifecycle transition — so its equality is identity (by SKU) and it exposes
// no setters.
type Product struct {
	sku    SKU
	price  Money
	labels Labels
}

// ProductSpec carries construction data across the layer boundary: primitive
// leaves and nested specs (Price is a MoneySpec; Labels is a raw map the
// Labels constructor will copy), never assembled value objects.
type ProductSpec struct {
	SKU    string
	Price  MoneySpec
	Labels map[string]string
}

// NewProduct validates spec and constructs a Product, building each child
// value object through its own constructor and adding error context.
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

// SKU returns the product's identity.
func (p Product) SKU() SKU { return p.sku }

// Price returns the product's price.
func (p Product) Price() Money { return p.price }

// Labels returns the product's labels (itself a value object that copies its
// backing map out).
func (p Product) Labels() Labels { return p.labels }

// Equal compares Products by identity (SKU) — never by price or labels.
func (p Product) Equal(other Product) bool {
	return p.sku == other.sku
}
