package campaign

import (
	"fmt"
	"strings"
)

type TargetURL struct {
	value string
}

func NewTargetURL(value string) (TargetURL, error) {
	if !strings.HasPrefix(value, "http://") && !strings.HasPrefix(value, "https://") {
		return TargetURL{}, fmt.Errorf("invalid target URL %q: must start with http:// or https://", value)
	}
	return TargetURL{value: value}, nil
}

func MustNewTargetURL(value string) TargetURL {
	u, err := NewTargetURL(value)
	if err != nil {
		panic(err)
	}
	return u
}

func (u TargetURL) String() string {
	return u.value
}
