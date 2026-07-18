//go:build swap

// Backend B — the POST-migration state (build with -tags swap). It has a
// different row shape (OrderRowB) and NO OrderRowA / FetchRawA, so any dependent
// that reached through to backend A's specifics fails to compile here. The
// domain port (New) is unchanged, so Client-only dependents are untouched — that
// contrast is the whole point. See ../SCORING.md.
package backend

import (
	"context"

	"github.com/verocorp/tesser-build/rationale/changeability/anchor/ordersapp"
)

// OrderRowB is backend B's row shape. Deliberately different from OrderRowA, and
// OrderRowA is gone: the migration removed backend A's surface.
type OrderRowB struct {
	ID     string
	Amount int64
}

type repoB struct{ rows map[string]OrderRowB }

func New() ordersapp.Repository { return &repoB{rows: map[string]OrderRowB{}} }

func (r *repoB) Save(_ context.Context, o ordersapp.Order) error {
	r.rows[o.ID()] = OrderRowB{ID: o.ID(), Amount: o.Total()}
	return nil
}

func (r *repoB) Get(_ context.Context, id string) (ordersapp.Order, error) {
	row := r.rows[id]
	return ordersapp.NewOrder(ordersapp.OrderSpec{ID: row.ID, Total: row.Amount})
}
