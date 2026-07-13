// Package exportrow is a realistic coupled arm for skills/ddd/composition-root.md
// (the public-interface rule): consumers should not expose backend persistence
// rows in their own public APIs.
//
// Authored by the Codex adversary against the frozen SCORING.md; see
// ../../adversary_provenance.md. It fails to build after `-tags swap` because its
// own exported API names backend.OrderRowA — a forced edit.
package exportrow

import (
	"github.com/verocorp/go-ddd/rationale/changeability/anchor/backend"
)

// OrderExport is a consumer-owned API type that accidentally bakes backend A's
// row shape into another package's contract.
type OrderExport struct {
	Source string
	Row    backend.OrderRowA
}

// NewOrderExport prepares a backend-row export record for downstream reporting.
func NewOrderExport(source string, row backend.OrderRowA) OrderExport {
	return OrderExport{Source: source, Row: row}
}

// Cents returns the backend-A amount field used by the reporting job.
func (e OrderExport) Cents() int64 {
	return e.Row.Cents
}
