package consumer

// Ledger matches the voconstructor heuristic (exported struct, all-unexported
// fields, no NewLedger constructor) but is an entity/aggregate, not a value
// object — it owns a child collection and is mutated in place. The fixture's
// .tesser-build.yaml excludes it; with the exclude it is skipped, without it
// voconstructor flags it. The e2e runs both ways to prove the config path works.
type Ledger struct {
	entries []Posted
	balance int64
}

// Post mutates the ledger in place (entity behavior).
func (l *Ledger) Post(p Posted) {
	l.entries = append(l.entries, p)
	l.balance += p.Multiplier()
}

// Balance reports the running balance.
func (l *Ledger) Balance() int64 { return l.balance }
