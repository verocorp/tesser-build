// Package stringequality enforces that .String() is for display, not equality:
// a value object's .String() may only be called inside its Test*_String accessor
// test. A .String() call anywhere else
// in a test file is flagged — it usually means a test is comparing value
// objects by their string form (a.String() == b.String()) instead of by value.
//
// The analyzer scans only _test.go files; .String() in production code is not
// the concern. Under `go vet`, in-package test files arrive in the
// test-augmented variant and external (package foo_test) test files arrive in
// their own unit, so both are covered. This is a pure usage scan — it does not
// identify value objects, so it needs no exclude list.
package stringequality

import (
	"go/ast"
	"strings"

	"golang.org/x/tools/go/analysis"
)

// Analyzer reports .String() calls in test code outside Test*_String tests.
var Analyzer = &analysis.Analyzer{
	Name: "stringequality",
	Doc:  ".String() may only be called inside a Test*_String accessor test (it is for display, not equality)",
	Run:  run,
}

func run(pass *analysis.Pass) (any, error) {
	for _, f := range pass.Files {
		tf := pass.Fset.File(f.Pos())
		if tf == nil || !strings.HasSuffix(tf.Name(), "_test.go") {
			continue // .String() in production code is not the concern
		}
		for _, decl := range f.Decls {
			fn, ok := decl.(*ast.FuncDecl)
			if !ok || fn.Body == nil {
				continue
			}
			if isStringAccessorTest(fn.Name.Name) {
				continue // the one place .String() is allowed
			}
			where := fn.Name.Name
			ast.Inspect(fn.Body, func(n ast.Node) bool {
				call, ok := n.(*ast.CallExpr)
				if !ok {
					return true
				}
				sel, ok := call.Fun.(*ast.SelectorExpr)
				if !ok {
					return true
				}
				if sel.Sel.Name == "String" {
					pass.Reportf(sel.Sel.Pos(), "%s calls .String() outside a Test*_String accessor test; compare value objects by value, not by their string form", where)
				}
				return true
			})
		}
	}
	return nil, nil
}

// isStringAccessorTest reports whether name matches the Test*_String pattern,
// the only function permitted to exercise .String().
func isStringAccessorTest(name string) bool {
	return strings.HasPrefix(name, "Test") && strings.HasSuffix(name, "_String")
}
