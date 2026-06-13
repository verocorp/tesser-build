package a

// Comparable has only comparable fields, so == works. Whether it should still
// expose Equal is equalitytest's concern, not this analyzer's. Not flagged.
type Comparable struct{ v string }

func NewComparable(v string) (Comparable, error) { return Comparable{v: v}, nil }

// SliceVO has a slice field (not Go-comparable) but provides Equal. Not flagged.
type SliceVO struct{ vs []string }

func NewSliceVO(vs []string) (SliceVO, error) { return SliceVO{vs: vs}, nil }
func (s SliceVO) Equal(other SliceVO) bool {
	if len(s.vs) != len(other.vs) {
		return false
	}
	for i := range s.vs {
		if s.vs[i] != other.vs[i] {
			return false
		}
	}
	return true
}

// MapVO has a map field (not Go-comparable) and no Equal method. Flagged.
type MapVO struct{ m map[string]int } // want `value object MapVO is not Go-comparable .* add an Equal\(MapVO\) bool method`

func NewMapVO() (MapVO, error) { return MapVO{m: map[string]int{}}, nil }

// Blocked uses a [0]func() blocker to force non-comparability and has no Equal.
// Flagged.
type Blocked struct { // want `value object Blocked is not Go-comparable`
	v string
	_ [0]func()
}

func NewBlocked(v string) (Blocked, error) { return Blocked{v: v}, nil }

// PtrEqual has its Equal on a pointer receiver, so the value type does not have
// it; a value object is used by value, so this is flagged.
type PtrEqual struct{ vs []string } // want `value object PtrEqual is not Go-comparable`

func NewPtrEqual(vs []string) (PtrEqual, error) { return PtrEqual{vs: vs}, nil }
func (p *PtrEqual) Equal(other PtrEqual) bool   { return len(p.vs) == len(other.vs) }
