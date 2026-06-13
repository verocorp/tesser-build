package excl

// Skip looks like a value object but is on the exclude list (an entity or
// aggregate), so the analyzer must not require a Test*_Equality for it.
type Skip struct{ v string }

func NewSkip(v string) (Skip, error) { return Skip{v: v}, nil }
