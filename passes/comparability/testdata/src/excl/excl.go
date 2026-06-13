package excl

// Aggregate is a non-comparable constructor-bearing type on the exclude list,
// so the missing Equal is not flagged.
type Aggregate struct{ items []string }

func NewAggregate() (Aggregate, error) { return Aggregate{}, nil }

// RealVO is not excluded, so its missing Equal is flagged.
type RealVO struct{ vs []string } // want `value object RealVO is not Go-comparable`

func NewRealVO(vs []string) (RealVO, error) { return RealVO{vs: vs}, nil }
