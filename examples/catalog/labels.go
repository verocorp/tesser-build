package catalog

import "fmt"

// Labels is a collection value object: a set of key/value tags on a product
// (e.g. {"color": "black", "size": "M"}). It wraps a map, so it is
// non-comparable and Equal is mandatory; the backing map is copied on the way
// in and on the way out, so it never escapes and a Labels value is
// effectively immutable.
type Labels struct {
	values map[string]string
}

// NewLabels constructs a Labels, normalizing a nil map to an empty set. It
// has no error path — an absent or empty set of labels is valid — so it needs
// no MustNewLabels twin.
func NewLabels(m map[string]string) Labels {
	return Labels{values: copyMap(m)}
}

// RequireLabels is the constructor variant for a context where at least one
// label is mandatory. Adding a variant here keeps the nil-handling decision
// out of parent constructors.
func RequireLabels(m map[string]string) (Labels, error) {
	if len(m) == 0 {
		return Labels{}, fmt.Errorf("labels must not be empty")
	}
	return Labels{values: copyMap(m)}, nil
}

// Get returns the value for key and whether it was present.
func (l Labels) Get(key string) (string, bool) {
	v, ok := l.values[key]
	return v, ok
}

// Len returns how many labels are set.
func (l Labels) Len() int { return len(l.values) }

// Values returns a defensive copy — the backing map never escapes.
func (l Labels) Values() map[string]string {
	return copyMap(l.values)
}

// Equal compares two label sets by content — never ==, which won't compile
// for a map-backed struct.
func (l Labels) Equal(other Labels) bool {
	if len(l.values) != len(other.values) {
		return false
	}
	for k, v := range l.values {
		if ov, ok := other.values[k]; !ok || ov != v {
			return false
		}
	}
	return true
}

// copyMap returns a shallow copy of m, treating nil as empty.
func copyMap(m map[string]string) map[string]string {
	out := make(map[string]string, len(m))
	for k, v := range m {
		out[k] = v
	}
	return out
}
