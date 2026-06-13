package analyzers_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chrisconley/go-ddd/internal/analyzers"
)

// repoRoot walks up from the test's working directory to the module root.
func repoRoot(t *testing.T) string {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatal("go.mod not found above working directory")
		}
		dir = parent
	}
}

// TestEveryAnalyzerIsTested is the meta-test: an analyzer cannot land without
// test coverage. For each registered analyzer it requires passes/<name>/ to
// exist with both a _test.go and a testdata/ directory.
func TestEveryAnalyzerIsTested(t *testing.T) {
	root := repoRoot(t)
	for _, a := range analyzers.All {
		dir := filepath.Join(root, "passes", a.Name)
		if _, err := os.Stat(dir); err != nil {
			t.Errorf("analyzer %q: package dir passes/%s not found", a.Name, a.Name)
			continue
		}
		if !hasTestFile(t, dir) {
			t.Errorf("analyzer %q: no _test.go in passes/%s — an analyzer must ship with tests", a.Name, a.Name)
		}
		if _, err := os.Stat(filepath.Join(dir, "testdata")); err != nil {
			t.Errorf("analyzer %q: no testdata/ in passes/%s", a.Name, a.Name)
		}
	}
}

// TestNoUnregisteredAnalyzer is the reverse guard: any package under passes/
// that defines an Analyzer must be registered in All, so a built-but-forgotten
// checker can't silently sit out of ddd-vet.
func TestNoUnregisteredAnalyzer(t *testing.T) {
	root := repoRoot(t)
	registered := map[string]bool{}
	for _, a := range analyzers.All {
		registered[a.Name] = true
	}

	entries, err := os.ReadDir(filepath.Join(root, "passes"))
	if err != nil {
		t.Fatal(err)
	}
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		dir := filepath.Join(root, "passes", e.Name())
		if !definesAnalyzer(t, dir) {
			continue
		}
		if !registered[e.Name()] {
			t.Errorf("passes/%s defines an Analyzer but is not in analyzers.All — register it (or its dir name must match its Analyzer.Name)", e.Name())
		}
	}
}

func hasTestFile(t *testing.T, dir string) bool {
	t.Helper()
	entries, err := os.ReadDir(dir)
	if err != nil {
		return false
	}
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), "_test.go") {
			return true
		}
	}
	return false
}

// definesAnalyzer reports whether any non-test .go file in dir declares
// `var Analyzer = &analysis.Analyzer{`.
func definesAnalyzer(t *testing.T, dir string) bool {
	t.Helper()
	entries, err := os.ReadDir(dir)
	if err != nil {
		return false
	}
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".go") || strings.HasSuffix(e.Name(), "_test.go") {
			continue
		}
		b, err := os.ReadFile(filepath.Join(dir, e.Name()))
		if err != nil {
			continue
		}
		if strings.Contains(string(b), "var Analyzer = &analysis.Analyzer{") {
			return true
		}
	}
	return false
}
