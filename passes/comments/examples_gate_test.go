package comments_test

// The zero-comment gate for the Go example trees CI cannot yet run the full
// analyzer set on: catalog/lending/running carry pre-existing stereotype
// misclassifications from the other analyzers (see the ddd-vet
// seam-misclassification learning), so the tessercheck CI step gates only
// examples/ddd. Without this test, a comment regression in the other three
// templates would be invisible to CI (Codex review finding, 2026-07-19).

import (
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"golang.org/x/tools/go/analysis"

	"github.com/verocorp/tesser-build/passes/comments"
)

func TestComments_UngatedGoExampleTreesStayClean(t *testing.T) {
	root := repoRoot(t)
	for _, tree := range []string{"examples/catalog", "examples/lending", "examples/running"} {
		dir := filepath.Join(root, tree)
		err := filepath.WalkDir(dir, func(path string, d os.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if d.IsDir() || !strings.HasSuffix(path, ".go") {
				return nil
			}
			fset := token.NewFileSet()
			f, perr := parser.ParseFile(fset, path, nil, parser.ParseComments)
			if perr != nil {
				t.Errorf("%s: %v", path, perr)
				return nil
			}
			pass := &analysis.Pass{
				Analyzer: comments.Analyzer,
				Fset:     fset,
				Files:    []*ast.File{f},
				Report: func(diag analysis.Diagnostic) {
					t.Errorf("%s: %s", fset.Position(diag.Pos), diag.Message)
				},
			}
			if _, rerr := comments.Analyzer.Run(pass); rerr != nil {
				t.Errorf("%s: %v", path, rerr)
			}
			return nil
		})
		if err != nil {
			t.Fatalf("%s: %v", tree, err)
		}
	}
}

func repoRoot(t *testing.T) string {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	for {
		if _, statErr := os.Stat(filepath.Join(dir, "go.mod")); statErr == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatal("go.mod not found above working directory")
		}
		dir = parent
	}
}
