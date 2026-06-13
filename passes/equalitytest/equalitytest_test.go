package equalitytest_test

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"testing"

	"golang.org/x/tools/go/analysis"

	"github.com/chrisconley/go-ddd/passes/equalitytest"
)

// runDir mirrors what `go vet` feeds an analyzer: the test-augmented variant of
// a package — every .go file in the directory, production and in-package
// _test.go together, in one pass. analysistest cannot be used here: it checks
// every package variant as a root, including the plain non-test variant that
// cannot see the test files, so it would flag a covered value object that
// `go vet` (which only vets the test-augmented variant) never flags. See the
// analyzer's package doc.
func runDir(t *testing.T, dir string) []string {
	t.Helper()
	fset := token.NewFileSet()
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatal(err)
	}
	var files []*ast.File
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".go") {
			continue
		}
		f, err := parser.ParseFile(fset, filepath.Join(dir, e.Name()), nil, parser.ParseComments)
		if err != nil {
			t.Fatal(err)
		}
		files = append(files, f)
	}
	var got []string
	pass := &analysis.Pass{
		Analyzer: equalitytest.Analyzer,
		Fset:     fset,
		Files:    files,
		Report: func(d analysis.Diagnostic) {
			pos := fset.Position(d.Pos)
			got = append(got, fmt.Sprintf("%s:%d: %s", filepath.Base(pos.Filename), pos.Line, d.Message))
		},
		ResultOf: map[*analysis.Analyzer]any{},
	}
	if _, err := equalitytest.Analyzer.Run(pass); err != nil {
		t.Fatalf("analyzer run: %v", err)
	}
	sort.Strings(got)
	return got
}

func assertDiagnostics(t *testing.T, got, want []string) {
	t.Helper()
	sort.Strings(want)
	if len(got) != len(want) {
		t.Fatalf("diagnostics mismatch\n got: %v\nwant: %v", got, want)
	}
	for i := range got {
		if got[i] != want[i] {
			t.Fatalf("diagnostics mismatch\n got: %v\nwant: %v", got, want)
		}
	}
}

func TestEqualityTest(t *testing.T) {
	got := runDir(t, "testdata/src/a")
	want := []string{
		"a.go:11: value object Uncovered: constructor NewUncovered has no TestUncovered_Equality locking its equality semantics",
		"a.go:19: value object Box: constructor NewBox has no TestBox_Equality locking its equality semantics",
	}
	assertDiagnostics(t, got, want)
}

func TestEqualityTest_Exclude(t *testing.T) {
	if err := equalitytest.Analyzer.Flags.Set("exclude", "Skip"); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = equalitytest.Analyzer.Flags.Set("exclude", "") }()
	got := runDir(t, "testdata/src/excl")
	assertDiagnostics(t, got, nil)
}
