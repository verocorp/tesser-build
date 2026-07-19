package consumer

type Ledger struct {
	entries []Posted
	balance int64
}

func (l *Ledger) Post(p Posted) {
	l.entries = append(l.entries, p)
	l.balance += p.Multiplier()
}

func (l *Ledger) Balance() int64 { return l.balance }
