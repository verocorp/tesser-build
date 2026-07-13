// Package portless is the Codex red-team arm for skills/ddd/composition-root.md
// (the public-interface rule). It is the adversary's best attempt to match the
// decoupled arm's 0 forced-edits under the backend A->B migration with LESS
// ceremony than orders.Client: a package-level facade over anchor.Wire(),
// importing only anchor + the orders DTOs, never backend.
//
// Authored by the Codex adversary against the frozen SCORING.md; see
// ../../adversary_provenance.md. Codex's own verdict: it lowers consumer setup
// only by giving up dependency injection / substitutability, a cost the anchor's
// single (migration) change does not exercise — so orders.Client earns its place
// here. That gap is the T3 finding.
package portless

import (
	"context"

	"github.com/verocorp/go-ddd/rationale/changeability/anchor"
	"github.com/verocorp/go-ddd/rationale/changeability/anchor/orders"
)

// PlaceOrder is a package-level facade over the app composition root.
func PlaceOrder(ctx context.Context, customerID string, skus []string) (orders.PlaceOrderResponse, error) {
	return anchor.Wire().PlaceOrder(ctx, orders.PlaceOrderRequest{
		CustomerID: customerID,
		SKUs:       skus,
	})
}

// GetOrder is the matching read facade over the app composition root.
func GetOrder(ctx context.Context, orderID string) (orders.GetOrderResponse, error) {
	return anchor.Wire().GetOrder(ctx, orders.GetOrderRequest{OrderID: orderID})
}
