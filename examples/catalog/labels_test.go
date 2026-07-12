package catalog

import "testing"

func TestLabels_NilNormalizesToEmpty(t *testing.T) {
	l := NewLabels(nil)
	if l.Len() != 0 {
		t.Errorf("nil map should normalize to empty, got len %d", l.Len())
	}
}

func TestLabels_CopiesInputDefensively(t *testing.T) {
	src := map[string]string{"color": "black"}
	l := NewLabels(src)
	src["color"] = "white" // mutating the source must not affect the value object
	if got, _ := l.Get("color"); got != "black" {
		t.Errorf("Labels captured a reference to the input map: got %q", got)
	}
}

func TestLabels_CopiesOutputDefensively(t *testing.T) {
	l := NewLabels(map[string]string{"color": "black"})
	out := l.Values()
	out["color"] = "white" // mutating the returned map must not affect the value object
	if got, _ := l.Get("color"); got != "black" {
		t.Errorf("Values() leaked the backing map: got %q", got)
	}
}

func TestLabels_Equality(t *testing.T) {
	a := NewLabels(map[string]string{"color": "black", "size": "M"})
	b := NewLabels(map[string]string{"size": "M", "color": "black"})
	if !a.Equal(b) {
		t.Errorf("label sets with the same content should be equal regardless of order")
	}
	if a.Equal(NewLabels(map[string]string{"color": "black"})) {
		t.Errorf("different label sets should not be equal")
	}
}

func TestRequireLabels_RejectsEmpty(t *testing.T) {
	if _, err := RequireLabels(nil); err == nil {
		t.Errorf("RequireLabels(nil) should be rejected")
	}
	if _, err := RequireLabels(map[string]string{"color": "black"}); err != nil {
		t.Errorf("RequireLabels with a label should succeed, got %v", err)
	}
}
