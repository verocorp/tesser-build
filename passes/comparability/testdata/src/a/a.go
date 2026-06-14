package a

// Comparable has only comparable scalar fields, so == is a correct value
// comparison. Requiring Equal here is a taste call, not a structural hazard, so
// it is not flagged.
type Comparable struct{ v string }

func NewComparable(v string) (Comparable, error) { return Comparable{v: v}, nil }

// PointerField is statically comparable (pointers compare), but == compares the
// pointer's identity, not the pointee value. With no Equal it is flagged.
type PointerField struct{ meta *int } // want `value object PointerField has a pointer field, so == compares identity, not value`

func NewPointerField() (PointerField, error) { return PointerField{}, nil }

// InterfaceField is statically comparable, but == on the interface compares the
// dynamic value and can panic at runtime. With no Equal it is flagged.
type InterfaceField struct{ v any } // want `value object InterfaceField has an interface field`

func NewInterfaceField() (InterfaceField, error) { return InterfaceField{}, nil }

// PointerWithEqual has a pointer field but defines Equal, so it is not flagged.
type PointerWithEqual struct{ meta *int }

func NewPointerWithEqual() (PointerWithEqual, error) { return PointerWithEqual{}, nil }
func (p PointerWithEqual) Equal(other PointerWithEqual) bool {
	if p.meta == nil || other.meta == nil {
		return p.meta == other.meta
	}
	return *p.meta == *other.meta
}

// Nested holds a value-struct field that itself contains a pointer, so the
// recursive walk finds the hazard. Flagged.
type inner struct{ p *int }
type Nested struct{ in inner } // want `value object Nested has a pointer field`

func NewNested() (Nested, error) { return Nested{}, nil }

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
