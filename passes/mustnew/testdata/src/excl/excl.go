package excl

// Ledger is an aggregate identified as value-object-shaped by its NewLedger
// constructor, but it is on the exclude list, so the missing MustNewLedger must
// NOT be flagged — aggregates carry real construction risk and get no Must*.
type Ledger struct{ entries []string }

func NewLedger(entries []string) (Ledger, error) { return Ledger{entries: entries}, nil }

// RealVO is not excluded, so its missing MustNew helper is flagged — proving
// exclusion is selective, not a blanket off-switch.
type RealVO struct{ v string }

func NewRealVO(v string) (RealVO, error) { return RealVO{v: v}, nil } // want `value object RealVO: constructor NewRealVO has no paired MustNewRealVO`
