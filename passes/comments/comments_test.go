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

func runSrc(t *testing.T, src string) []analysis.Diagnostic {
	t.Helper()
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, "x.go", src, parser.ParseComments)
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

func TestComments_CgoPreambleIsExempt(t *testing.T) {
	// The comments attached to an `import "C"` declaration are consumed by the
	// Go toolchain — they are code. Both the doc-group-on-GenDecl and the
	// spec-level shapes must be exempt; an ordinary comment elsewhere in the
	// same file must still be flagged.
	src := "package a\n\n" +
		"// #include <stdlib.h>\n" +
		"// #cgo LDFLAGS: -lm\n" +
		"import \"C\"\n\n" +
		"// ordinary prose that must still be flagged\n" +
		"func F() {}\n"
	got := runSrc(t, src)
	if len(got) != 1 {
		t.Fatalf("cgo file: want exactly 1 diagnostic (the prose comment), got %d: %v", len(got), got)
	}
}

func TestComments_ParenthesizedCgoImportPreambleIsExempt(t *testing.T) {
	// The spec-level Doc branch: a preamble inside a parenthesized import
	// group attaches to the ImportSpec, not the GenDecl.
	src := "package a\n\n" +
		"import (\n" +
		"\t// #include <stdlib.h>\n" +
		"\t\"C\"\n" +
		")\n\n" +
		"func F() {}\n"
	if got := runSrc(t, src); len(got) != 0 {
		t.Fatalf("parenthesized cgo preamble: want exempt, got %v", got)
	}
}

func TestComments_BlockCgoPreambleAndLineDirectiveExempt(t *testing.T) {
	src := "package a\n\n" +
		"/*\n#include <stdlib.h>\n*/\n" +
		"import \"C\"\n\n" +
		"/*line x.go:10*/\n" +
		"func F() {}\n"
	if got := runSrc(t, src); len(got) != 0 {
		t.Fatalf("block cgo preamble + block line directive: want exempt, got %v", got)
	}
}

func TestComments_GoDirectiveWithSpaceIsProse(t *testing.T) {
	src := "package a\n\n//go: this is prose riding the directive namespace\nfunc F() {}\n"
	if got := runSrc(t, src); len(got) != 1 {
		t.Fatalf("`//go: prose`: want 1 diagnostic, got %d: %v", len(got), got)
	}
}

func TestComments_EveryDirectiveLedgerEntryIsExempt(t *testing.T) {
	// good.go proves only //go: and //nolint. The rest of the ledger — the
	// remaining directivePrefixes and the tb-status/tb-allow-missing markers —
	// has no matching input in the fixtures, so a regression dropping one would
	// go unflagged. Each must be exempt on its own.
	// The tb-* markers are assembled at runtime; a contiguous marker token in
	// this source would be picked up by roadmap/generate.py's marker scan.
	exempt := []string{
		"//line x.go:1",
		"//export Foo",
		"//extern foo",
		"//sysnb bar",
		"//tb-" + "status: green",
		"//tb-" + "allow-missing: reason",
	}
	for _, d := range exempt {
		src := "// +build linux\n\npackage a\n\n" + d + "\nfunc F() {}\n"
		if got := runSrc(t, src); len(got) != 0 {
			t.Errorf("directive %q (with old-style build tag): want exempt, got %v", d, got)
		}
	}
}
