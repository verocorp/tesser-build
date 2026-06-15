// Package stringequality enforces that .String() is for display, not equality:
// it flags a test that compares two value objects by their string form
// (a.String() == b.String(), or assert.Equal(t, a.String(), b.String())) instead
// of comparing them by value (== or Equal). That comparison silently mis-equates
// value objects with more than one valid representation (0°C vs 273.15K), which is
// the exact bug a value object exists to prevent.
//
// The analyzer fires only on a .String() result used as one side of a value
// comparison whose other side is also a .String() call. A lone .String() — a
// display call, a discarded race-exercise (_ = x.String()), or an assertion
// against a string literal (assert.Equal(t, "NaN", x.String())) — is legitimate
// and is NOT flagged. This is a pure usage scan: it does not identify value
// objects (so it needs no exclude list) and, by design, does not distinguish a
// value object's .String() from a stdlib one — but the both-sides-are-.String()
// requirement keeps that from producing false positives on display code.
//
// Scope is _test.go files only; .String() comparisons in production code are out
// of scope here (display use dominates there). Under `go vet`, in-package test
// files arrive in the test-augmented variant and external (package foo_test) test
// files arrive in their own unit, so both are covered.
package stringequality

import (
	"go/ast"
	"go/token"
	"strings"

	"golang.org/x/tools/go/analysis"
)

const message = "compares value objects by their .String() form; compare by value (Equal or ==), not by string representation"

// Analyzer reports value comparisons whose operands are both .String() calls.
var Analyzer = &analysis.Analyzer{
	Name: "stringequality",
	Doc:  ".String() is for display, not equality: don't compare two value objects by their string form (use == or Equal)",
	Run:  run,
}

func run(pass *analysis.Pass) (any, error) {
	for _, f := range pass.Files {
		tf := pass.Fset.File(f.Pos())
		if tf == nil || !strings.HasSuffix(tf.Name(), "_test.go") {
			continue // .String() comparisons in production code are not the concern here
		}
		ast.Inspect(f, func(n ast.Node) bool {
			switch e := n.(type) {
			case *ast.BinaryExpr:
				// a.String() == b.String()  /  a.String() != b.String()
				if (e.Op == token.EQL || e.Op == token.NEQ) && isStringCall(e.X) && isStringCall(e.Y) {
					pass.Reportf(e.OpPos, message)
				}
			case *ast.CallExpr:
				// assert.Equal(t, a.String(), b.String()) and the require/NotEqual/f variants
				if expected, actual, ok := equalityAssertionOperands(e); ok && isStringCall(expected) && isStringCall(actual) {
					pass.Reportf(e.Lparen, message)
				}
			}
			return true
		})
	}
	return nil, nil
}

// isStringCall reports whether expr is a no-argument call to a method named
// String — i.e. an x.String() call.
func isStringCall(expr ast.Expr) bool {
	call, ok := expr.(*ast.CallExpr)
	if !ok || len(call.Args) != 0 {
		return false
	}
	sel, ok := call.Fun.(*ast.SelectorExpr)
	return ok && sel.Sel.Name == "String"
}

// equalityAssertionOperands recognizes a testify-style equality assertion
// (assert/require . Equal/Equalf/NotEqual/NotEqualf) and returns its two compared
// operands (expected, actual), which sit at args[1] and args[2] after the
// TestingT argument.
func equalityAssertionOperands(call *ast.CallExpr) (expected, actual ast.Expr, ok bool) {
	sel, isSel := call.Fun.(*ast.SelectorExpr)
	if !isSel {
		return nil, nil, false
	}
	pkg, isIdent := sel.X.(*ast.Ident)
	if !isIdent || (pkg.Name != "assert" && pkg.Name != "require") {
		return nil, nil, false
	}
	switch sel.Sel.Name {
	case "Equal", "Equalf", "NotEqual", "NotEqualf":
	default:
		return nil, nil, false
	}
	if len(call.Args) < 3 {
		return nil, nil, false
	}
	return call.Args[1], call.Args[2], true
}
