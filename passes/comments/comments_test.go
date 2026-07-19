package comments_test

// This pass cannot use analysistest: the `// want "..."` expectation grammar
// is itself a comment, so annotating a bad fixture would either trip the
// analyzer or force a permanent `// want` exemption into the production
// ledger. Instead a minimal driver parses the fixtures (comments included —
// the analyzer needs no type info) and runs the pass directly.

import (
	"go/ast"
	"go/parser"
	"go/token"
	"path/filepath"
	"strings"
	"testing"

	"golang.org/x/tools/go/analysis"
	"golang.org/x/tools/go/analysis/analysistest"

	"github.com/verocorp/tesser-build/passes/comments"
)

func runOn(t *testing.T, path string) []analysis.Diagnostic {
	t.Helper()
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, path, nil, parser.ParseComments)
	if err != nil {
		t.Fatal(err)
	}
	var got []analysis.Diagnostic
	pass := &analysis.Pass{
		Analyzer: comments.Analyzer,
		Fset:     fset,
		Files:    []*ast.File{f},
		Report:   func(d analysis.Diagnostic) { got = append(got, d) },
	}
	if _, err := comments.Analyzer.Run(pass); err != nil {
		t.Fatal(err)
	}
	return got
}

func TestComments_BadFixtureIsFlagged(t *testing.T) {
	bad := filepath.Join(analysistest.TestData(), "src", "a", "bad.go")
	got := runOn(t, bad)
	if len(got) != 4 {
		t.Fatalf("bad.go: want 4 diagnostics (doc comment, inline, block, trailing), got %d: %v", len(got), got)
	}
	for _, d := range got {
		if !strings.Contains(d.Message, "zero-comment norm") {
			t.Errorf("diagnostic message %q does not name the norm", d.Message)
		}
	}
}

func TestComments_GoodFixtureIsClean(t *testing.T) {
	good := filepath.Join(analysistest.TestData(), "src", "a", "good.go")
	if got := runOn(t, good); len(got) != 0 {
		t.Fatalf("good.go: directives must be exempt, got %v", got)
	}
}

func TestComments_GeneratedFileIsSkipped(t *testing.T) {
	gen := filepath.Join(analysistest.TestData(), "src", "a", "generated.go")
	if got := runOn(t, gen); len(got) != 0 {
		t.Fatalf("generated.go: generated files must be skipped, got %v", got)
	}
}
