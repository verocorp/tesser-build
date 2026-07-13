// Package orders is the PUBLIC boundary of the ordering context: the Client
// contract and the DTOs it speaks. It imports nothing internal. A dependent
// that depends only on this package survives a backend migration untouched —
// the O(1) (decoupled) arm of the public-interface changeability decision.
//
// See ../SCORING.md for how the arms are scored.
package orders

import "context"

// Client is the public contract. It speaks DTOs, never domain objects, so the
// internals behind it (services, repositories, the backend) can be reshaped or
// re-backed without touching callers.
type Client interface {
	PlaceOrder(ctx context.Context, req PlaceOrderRequest) (PlaceOrderResponse, error)
	GetOrder(ctx context.Context, req GetOrderRequest) (GetOrderResponse, error)
}

// PlaceOrderRequest / PlaceOrderResponse and the Get* pair are the DTOs that
// cross the boundary. They are deliberately backend-agnostic.
type PlaceOrderRequest struct {
	CustomerID string
	SKUs       []string
}

type PlaceOrderResponse struct {
	OrderID string
	Total   int64 // minor units
}

type GetOrderRequest struct{ OrderID string }

type GetOrderResponse struct {
	OrderID string
	Status  string
	Total   int64
}
