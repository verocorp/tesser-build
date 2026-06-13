package a

// Good is a value object with a String() method — not flagged.
type Good struct{ v string }

func NewGood(v string) (Good, error) { return Good{v: v}, nil }
func (g Good) String() string        { return g.v }

// Missing is a value object with no String() method — flagged.
type Missing struct{ v string } // want `value object Missing has no String\(\) string method`

func NewMissing(v string) (Missing, error) { return Missing{v: v}, nil }

// WrongResult has a String method that does not return string, so it does not
// satisfy the rule — flagged.
type WrongResult struct{ v string } // want `value object WrongResult has no String\(\) string method`

func NewWrongResult(v string) (WrongResult, error) { return WrongResult{v: v}, nil }
func (w WrongResult) String() int                  { return len(w.v) }

// PtrOnly has String() on a pointer receiver, so the value type does not
// implement it — flagged (value objects are used by value).
type PtrOnly struct{ v string } // want `value object PtrOnly has no String\(\) string method`

func NewPtrOnly(v string) (PtrOnly, error) { return PtrOnly{v: v}, nil }
func (p *PtrOnly) String() string          { return p.v }

// NotAVO has no constructor, so it is not identified as a value object and is
// never considered here.
type NotAVO struct{ v string }

func (n NotAVO) display() string { return n.v }
