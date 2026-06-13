package a

// Good is value-object shaped and has its validating constructor.
type Good struct{ v string }

func NewGood(v string) (Good, error) { return Good{v: v}, nil }

// Missing is value-object shaped (exported, one unexported field) with no
// constructor at all.
type Missing struct{ v string } // want `value object Missing has no validating constructor NewMissing\(\.\.\.\) \(Missing, error\)`

// WrongShape has a NewWrongShape, but it does not return an error, so the
// required error-returning constructor is still absent.
type WrongShape struct{ v string } // want `value object WrongShape has no validating constructor`

func NewWrongShape(v string) WrongShape { return WrongShape{v: v} }

// Leaky has an exported field: it is directly constructable, so the missing
// constructor is not this analyzer's concern (it is vofields' encapsulation
// concern). Not flagged here.
type Leaky struct {
	Name string
	tag  string
}

// Empty is a marker struct with no fields: not the shape this rule covers.
type Empty struct{}

// hidden is unexported, so it is out of scope.
type hidden struct{ v string }

var _ = hidden{}
