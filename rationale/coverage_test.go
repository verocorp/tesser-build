package changeability_test

import (
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"

	"github.com/chrisconley/go-ddd/internal/analyzers"
)

// TestCoverageMatrix_NoSilentGaps keeps coverage.md honest: every analyzer
// ddd-vet ships (internal/analyzers.All) must appear in the matrix, and every
// Test* the matrix names must exist in this package. It tolerates the ❌/⚠️ rows
// by design (the rationale is broader than the enforcement, and some analyzers
// enforce a rubric rule whose demo is still pending); it forbids a SILENT gap —
// a shipping analyzer missing from the matrix, or a dangling test reference that
// rotted.
func TestCoverageMatrix_NoSilentGaps(t *testing.T) {
	matrix, err := os.ReadFile("coverage.md")
	if err != nil {
		t.Fatalf("read coverage.md: %v", err)
	}
	content := string(matrix)

	// 1. Every analyzer ddd-vet ships is named in the matrix. Keyed off the
	// analyzers.All registry — not the cmd/check* dirs — so the guard stays live
	// after the standalone walkers are removed.
	for _, a := range analyzers.All {
		if !strings.Contains(content, a.Name) {
			t.Errorf("analyzer %q has no row in coverage.md (silent gap)", a.Name)
		}
	}

	// 2. Every concrete Test* the matrix references actually exists here.
	// (Patterns like "Test*_Equality" carry an asterisk and are not matched.)
	var src strings.Builder
	testFiles, _ := filepath.Glob("*_test.go")
	for _, f := range testFiles {
		b, _ := os.ReadFile(f)
		src.Write(b)
	}
	srcStr := src.String()

	for _, name := range regexp.MustCompile(`Test[A-Za-z0-9_]+`).FindAllString(content, -1) {
		if !strings.Contains(srcStr, "func "+name+"(") {
			t.Errorf("coverage.md references %q but no such test exists (dangling reference)", name)
		}
	}
}
