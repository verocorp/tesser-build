// Package reachthrough is a realistic coupled contender for the
// public-interface rule (skills/tesser-build/public-interface.md): consumers
// should depend on the public orders.Client boundary, not backend-specific
// adapter helpers.
//
// Authored by the Codex adversary against the frozen SCORING.md; see
// ../../adversary_provenance.md. It fails to build after `-tags swap` because its
// own source names backend.FetchRawA / backend.OrderRowA — a forced edit.
package reachthrough

import (
	"context"

	"github.com/verocorp/tesser-build/rationale/changeability/anchor/backend"
	"github.com/verocorp/tesser-build/rationale/changeability/anchor/orders"
)

// Snapshot places an order through the public client, then reaches through to
// backend A to fetch the storage row for ad-hoc reconciliation.
func Snapshot(ctx context.Context, client orders.Client, customerID string, skus []string) (backend.OrderRowA, error) {
	placed, err := client.PlaceOrder(ctx, orders.PlaceOrderRequest{
		CustomerID: customerID,
		SKUs:       skus,
	})
	if err != nil {
		return backend.OrderRowA{}, err
	}

	return backend.FetchRawA(placed.OrderID), nil
}
