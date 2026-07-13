// Package locator is a realistic coupled arm for skills/ddd/composition-root.md
// (the public-interface rule): service locators can hide wiring while still
// returning backend-specific types.
//
// Authored by the Codex adversary against the frozen SCORING.md; see
// ../../adversary_provenance.md. It fails to build after `-tags swap` because its
// own source names backend.OrderRowA / backend.FetchRawA — a forced edit.
package locator

import (
	"github.com/verocorp/go-ddd/rationale/changeability/anchor/backend"
)

// RawOrderLocator is a consumer-level global accessor used by legacy jobs that
// want raw persisted records without threading dependencies through call stacks.
type RawOrderLocator struct {
	prefix string
}

// DefaultRawOrders is the package global used by batch and diagnostic code.
var DefaultRawOrders = RawOrderLocator{prefix: "ord-"}

// Find returns backend A's raw row from the globally available locator.
func (l RawOrderLocator) Find(customerID string) backend.OrderRowA {
	return backend.FetchRawA(l.prefix + customerID)
}

// Default finds an order through the package global.
func Default(customerID string) backend.OrderRowA {
	return DefaultRawOrders.Find(customerID)
}
