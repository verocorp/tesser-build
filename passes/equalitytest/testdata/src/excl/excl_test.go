package excl

import "testing"

// TestDummy exists so the package has a test file (the analyzer only acts on
// the test variant); it proves Skip is exempted by exclusion, not by the
// absence of tests.
func TestDummy(t *testing.T) {}
