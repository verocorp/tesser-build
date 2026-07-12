package campaign

import (
	"fmt"
	"strings"
)

// TargetURL is the URL a ShortLink redirects to. Simple, single-value value
// object: flat constructor, native equality (one representation per value).
type TargetURL struct {
	value string
}

// NewTargetURL validates and constructs a TargetURL: it must start with
// "http://" or "https://".
func NewTargetURL(value string) (TargetURL, error) {
	if !strings.HasPrefix(value, "http://") && !strings.HasPrefix(value, "https://") {
		return TargetURL{}, fmt.Errorf("invalid target URL %q: must start with http:// or https://", value)
	}
	return TargetURL{value: value}, nil
}

// MustNewTargetURL panics on invalid input; use only with known-valid
// literals (tests, package-level vars), never with runtime data.
func MustNewTargetURL(value string) TargetURL {
	u, err := NewTargetURL(value)
	if err != nil {
		panic(err)
	}
	return u
}

// String is the display form and the sole string accessor.
func (u TargetURL) String() string {
	return u.value
}
