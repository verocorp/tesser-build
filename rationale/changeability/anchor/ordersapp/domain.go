// Package ordersapp is the impl behind orders.Client: the domain Order, the
// repository port, and the service that satisfies the public contract. It is a
// focused changeability fixture, not the full DDD worked example (examples/ holds
// that), but it follows the toolkit's own conventions so tessercheck is clean here.
package ordersapp

import "fmt"

// OrderSpec carries construction data across the layer boundary: primitive leaves
// only. The service builds it and hands it to NewOrder.
type OrderSpec struct {
	ID    string
	Total int64
}

// Order is the domain entity: identity is by ID (see Order.Equal). It never
// crosses the public boundary; the service maps it to a DTO. Backend rows map to
// and from Order via the Repository.
type Order struct {
	id     string
	status string
	total  int64
}

// NewOrder validates spec and constructs a placed order — the single construction
// path.
func NewOrder(spec OrderSpec) (Order, error) {
	if spec.ID == "" {
		return Order{}, fmt.Errorf("order id must not be empty")
	}
	if spec.Total < 0 {
		return Order{}, fmt.Errorf("order total must not be negative: %d", spec.Total)
	}
	return Order{id: spec.ID, status: "placed", total: spec.Total}, nil
}

func (o Order) ID() string     { return o.id }
func (o Order) Status() string { return o.status }
func (o Order) Total() int64   { return o.total }

// Equal is identity equality: two orders are the same when their ids match.
func (o Order) Equal(other Order) bool { return o.id == other.id }
