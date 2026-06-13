// Package equalitytest is the go/analysis port of cmd/checkequality: every
// value object X must have a Test*_Equality function that locks its equality
// semantics, so a later field or comparability change is caught. Value objects
// are identified the same way as cmd/checkmustnew, via their NewX(...) (X, error)
// constructor.
//
// Package-variant note: the constructors live in production files and the
// Test*_Equality functions live in test files, so the two must be visible in a
// single pass to correlate. Under `go vet`, cmd/go vets the test-augmented
// variant of a package (production files + its in-package _test.go files) in one
// pass, so an in-package equality test is seen alongside the constructor.
//
// This requires the equality test to live IN-PACKAGE (package foo, foo_test.go).
// An external test package (package foo_test) is vetted as its own unit that
// does not include the constructors, so an externally-tested value object is
// reported as missing coverage — a false positive. In-package is the idiom for
// tests that lock value semantics over unexported representation, but this is a
// real behavior change from the cmd/checkequality directory-walker (which read
// the whole directory at once). See the design doc's external-test-package open
// question.
package equalitytest

import (
	"go/ast"
	"strings"

	"golang.org/x/tools/go/analysis"

	"github.com/chrisconley/go-ddd/internal/voscan"
)

var exclude string

// Analyzer reports value objects with no paired Test*_Equality coverage.
var Analyzer = &analysis.Analyzer{
	Name: "equalitytest",
	Doc:  "value objects must have a Test*_Equality function locking their equality semantics",
	Run:  run,
}

func init() {
	Analyzer.Flags.StringVar(&exclude, "exclude", "", "comma-separated type names exempt (aggregates/entities)")
}

func run(pass *analysis.Pass) (any, error) {
	excluded := voscan.CombinedExcludes(pass, exclude)

	// Collect every Test*_Equality function: "TestFoo_Equality" -> "Foo".
	equalityTests := map[string]bool{}
	for _, f := range pass.Files {
		for _, d := range f.Decls {
			fn, ok := d.(*ast.FuncDecl)
			if !ok || fn.Recv != nil {
				continue
			}
			name := fn.Name.Name
			if strings.HasPrefix(name, "Test") && strings.HasSuffix(name, "_Equality") {
				equalityTests[name[len("Test"):len(name)-len("_Equality")]] = true
			}
		}
	}

	// Flag any VO constructor (in the production files) whose Test*_Equality is
	// missing.
	for _, f := range pass.Files {
		for _, d := range f.Decls {
			fn, ok := d.(*ast.FuncDecl)
			if !ok || fn.Recv != nil {
				continue
			}
			typeName, ok := voscan.MatchVOConstructor(fn, excluded)
			if !ok {
				continue
			}
			if !equalityTests[typeName] {
				pass.Reportf(fn.Pos(), "value object %s: constructor %s has no Test%s_Equality locking its equality semantics", typeName, fn.Name.Name, typeName)
			}
		}
	}
	return nil, nil
}
