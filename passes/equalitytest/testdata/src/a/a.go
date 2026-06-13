package a

// Covered is a value object with the required Test*_Equality coverage.
type Covered struct{ v string }

func NewCovered(v string) (Covered, error) { return Covered{v: v}, nil }

// Uncovered is a value object missing its Test*_Equality.
type Uncovered struct{ v string }

func NewUncovered(v string) (Uncovered, error) { return Uncovered{v: v}, nil } // flagged: no TestUncovered_Equality

// NewCollect is a factory (suffix != return type), so it must NOT be flagged.
func NewCollect(v string) (Covered, error) { return NewCovered(v) }

// Box is a generic value object missing its Test*_Equality.
type Box[T any] struct{ v T }

func NewBox[T any](v T) (Box[T], error) { return Box[T]{v: v}, nil } // flagged: no TestBox_Equality
