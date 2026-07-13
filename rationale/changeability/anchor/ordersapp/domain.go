// Package ordersapp is the impl behind orders.Client: the domain Order, the
// repository port, and the service that satisfies the public contract. It is
// deliberately minimal — a changeability fixture, not the DDD worked example
// (examples/ holds that).
package ordersapp

// Order is the domain object. It never crosses the public boundary; the service
// maps it to a DTO. Backend rows map to and from Order via the Repository.
type Order struct {
	id     string
	status string
	total  int64
}

// NewOrder is the single construction path for a placed order.
func NewOrder(id string, total int64) Order {
	return Order{id: id, status: "placed", total: total}
}

func (o Order) ID() string     { return o.id }
func (o Order) Status() string { return o.status }
func (o Order) Total() int64   { return o.total }
