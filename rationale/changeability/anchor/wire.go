// Package anchor is the composition root for the changeability anchor (the
// public-interface decision): the one place that chooses the concrete backend
// and wires it behind the public orders.Client. Migrating backends changes ONLY
// this wiring (modelled by -tags swap on package backend); dependents on
// orders.Client do not move.
package anchor

//go:generate go run ./internal/gen

import (
	"github.com/verocorp/tesser-build/rationale/changeability/anchor/backend"
	"github.com/verocorp/tesser-build/rationale/changeability/anchor/orders"
	"github.com/verocorp/tesser-build/rationale/changeability/anchor/ordersapp"
)

// Wire constructs the ordering Client over whichever backend is compiled in.
func Wire() orders.Client { return ordersapp.New(backend.New()) }
