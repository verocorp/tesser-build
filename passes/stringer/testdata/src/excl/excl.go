package excl

// Entity is identified as a value object by its constructor, but it is on the
// exclude list, so the missing String() is not flagged.
type Entity struct{ v string }

func NewEntity(v string) (Entity, error) { return Entity{v: v}, nil }

// RealVO is not excluded, so its missing String() is flagged.
type RealVO struct{ v string } // want `value object RealVO has no String\(\) string method`

func NewRealVO(v string) (RealVO, error) { return RealVO{v: v}, nil }
