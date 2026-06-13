package excl

// Entity is identified as a value object by its constructor but is excluded, so
// its ToString is not flagged.
type Entity struct{ v string }

func NewEntity(v string) (Entity, error) { return Entity{v: v}, nil }
func (e Entity) ToString() string        { return e.v }

// RealVO is not excluded, so its primitive accessor is flagged.
type RealVO struct{ v string }

func NewRealVO(v string) (RealVO, error) { return RealVO{v: v}, nil }
func (r RealVO) ToString() string        { return r.v } // want `value object RealVO exposes ToString`
