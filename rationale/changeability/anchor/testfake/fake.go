// Package testfake provides a fake orders.Client — the substitute a dependent
// swaps in to be unit-tested in isolation. It exists to show the SUBSTITUTION
// axis of the public-interface decision (change C2 in ../SCORING.md): a dependent
// that receives orders.Client accepts this fake with zero source edits, so it is
// testable at O(1); a facade dependent bound to a global has no seam to accept it.
package testfake

import (
	"context"

	"github.com/verocorp/tesser-build/rationale/changeability/anchor/orders"
)

type fake struct{}

// New returns a fake orders.Client. It satisfies the public contract with no
// backend, no wiring — the point of the interface.
func New() orders.Client { return fake{} }

func (fake) PlaceOrder(_ context.Context, req orders.PlaceOrderRequest) (orders.PlaceOrderResponse, error) {
	return orders.PlaceOrderResponse{OrderID: "fake-" + req.CustomerID, Total: 0}, nil
}

func (fake) GetOrder(_ context.Context, req orders.GetOrderRequest) (orders.GetOrderResponse, error) {
	return orders.GetOrderResponse{OrderID: req.OrderID, Status: "fake", Total: 0}, nil
}
