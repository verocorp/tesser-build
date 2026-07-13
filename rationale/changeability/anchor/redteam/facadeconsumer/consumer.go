// Package facadeconsumer is a dependent of the red-team facade (redteam/portless).
// It calls the package-level facade functions, which are bound to the global
// anchor.Wire(). This is what a real caller of the lower-ceremony facade looks
// like.
//
// It builds fine by default and survives the backend migration (portless never
// imports backend). Its cost shows up on the SUBSTITUTION axis (change C2): see
// subst_bug.go — there is no seam to inject a fake, so making this dependent
// unit-testable forces an edit here (or to portless). Contrast the decoupled
// consumers, which already accept orders.Client and need no change.
package facadeconsumer

import (
	"context"

	"github.com/verocorp/go-ddd/rationale/changeability/anchor/redteam/portless"
)

// Reserve places an order through the facade. It cannot be handed a substitute
// implementation — the facade offers no parameter for one.
func Reserve(ctx context.Context, customerID string) (string, error) {
	resp, err := portless.PlaceOrder(ctx, customerID, []string{"x"})
	if err != nil {
		return "", err
	}
	return resp.OrderID, nil
}
