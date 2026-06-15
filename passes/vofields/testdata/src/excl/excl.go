package excl

// Ledger is an aggregate identified as value-object-shaped by its NewLedger
// constructor. It is on the exclude list, so its exported field must NOT be
// flagged — aggregates legitimately expose fields.
type Ledger struct {
	Entries []string
}

func NewLedger(entries []string) (Ledger, error) { return Ledger{Entries: entries}, nil }

// RealVO is not excluded, so its exported field is flagged — proving exclusion
// is selective, not a blanket off-switch.
type RealVO struct {
	Name string // want `value object RealVO exposes exported field Name`
	tag  string
}

func NewRealVO(name, tag string) (RealVO, error) { return RealVO{Name: name, tag: tag}, nil }
