package excl

// Ledger is an aggregate that shares the value-object shape (exported, only
// unexported fields, no constructor). It is on the exclude list, so it must not
// be flagged.
type Ledger struct{ entries []string }

// RealVO is not excluded, so the missing constructor is flagged — proving
// exclusion is selective, not a blanket off-switch.
type RealVO struct{ v string } // want `value object RealVO has no validating constructor`
