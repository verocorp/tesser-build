package catalog

import (
	"fmt"
	"sort"
	"strings"
)

type Labels struct {
	values map[string]string
}

func NewLabels(m map[string]string) Labels {
	return Labels{values: copyMap(m)}
}

func (l Labels) Get(key string) (string, bool) {
	v, ok := l.values[key]
	return v, ok
}

func (l Labels) Len() int { return len(l.values) }

func (l Labels) Values() map[string]string {
	return copyMap(l.values)
}

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

func (l Labels) String() string {
	keys := make([]string, 0, len(l.values))
	for k := range l.values {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	pairs := make([]string, len(keys))
	for i, k := range keys {
		pairs[i] = fmt.Sprintf("%s=%s", k, l.values[k])
	}
	return strings.Join(pairs, ",")
}

func copyMap(m map[string]string) map[string]string {
	out := make(map[string]string, len(m))
	for k, v := range m {
		out[k] = v
	}
	return out
}
