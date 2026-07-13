//go:build !swap

// Package backend is the persistence adapter for the ordering context. This
// file is backend A — the DEFAULT (pre-migration) state. Building with
// -tags swap replaces it with backend B (backend_b.go), modelling a backend
// migration (e.g. DynamoDB -> RDS) inside one committed tree. See ../SCORING.md.
package backend

import (
	"context"

	"github.com/verocorp/go-ddd/rationale/changeability/anchor/ordersapp"
)

// OrderRowA is backend A's persistence row — a BACKEND-SPECIFIC type. A
// dependent that reaches through to this type (the coupled arm) is bound to
// backend A and will not compile after the migration to backend B, which has no
// OrderRowA. A dependent that stays on orders.Client never sees it.
type OrderRowA struct {
	PK    string // backend-A specific: partition key
	Cents int64
}

type repoA struct{ rows map[string]OrderRowA }

// New returns the adapter typed as the domain port. Present in BOTH backends,
// so the composition root and Client-only dependents are stable across the swap.
func New() ordersapp.Repository { return &repoA{rows: map[string]OrderRowA{}} }

func (r *repoA) Save(_ context.Context, o ordersapp.Order) error {
	r.rows[o.ID()] = OrderRowA{PK: o.ID(), Cents: o.Total()}
	return nil
}

func (r *repoA) Get(_ context.Context, id string) (ordersapp.Order, error) {
	row := r.rows[id]
	return ordersapp.NewOrder(row.PK, row.Cents), nil
}

// FetchRawA exposes the backend-A row directly. It is the leak the coupled arm
// reaches for; it exists only in backend A, so a caller of it breaks on migration.
func FetchRawA(id string) OrderRowA { return OrderRowA{PK: id} }
