// Package voscan holds the value-object identification shared by the
// go/analysis-based DDD checkers. A value object is a type X with a free
// constructor NewX(...) (X, error) whose suffix matches the return type name.
// This mirrors the heuristic the standalone cmd/check* tools use, so the
// analyzers agree with them on what counts as a value object.
package voscan

import (
	"go/ast"
	"strings"
)

// ParseExcludes turns a comma-separated flag value (aggregate/entity type
// names that aren't value objects) into a lookup set.
func ParseExcludes(s string) map[string]bool {
	out := map[string]bool{}
	for _, name := range strings.Split(s, ",") {
		if name = strings.TrimSpace(name); name != "" {
			out[name] = true
		}
	}
	return out
}

// VOTypeNames returns the set of value-object type names declared across the
// given files, identified by their NewX(...) (X, error) constructors and minus
// any excluded names.
func VOTypeNames(files []*ast.File, excluded map[string]bool) map[string]bool {
	out := map[string]bool{}
	for _, f := range files {
		for _, d := range f.Decls {
			fn, ok := d.(*ast.FuncDecl)
			if !ok {
				continue
			}
			if name, ok := MatchVOConstructor(fn, excluded); ok {
				out[name] = true
			}
		}
	}
	return out
}

// MatchVOConstructor reports whether fn is a value-object constructor
// NewX(...) (X, error) and returns the type name X. A function matches when its
// name is "New" + an uppercase-led suffix, it returns exactly (T, error), and
// the suffix equals the named return type T (so factories like
// NewCollect -> Operation don't match). Excluded names never match.
func MatchVOConstructor(fn *ast.FuncDecl, excluded map[string]bool) (string, bool) {
	if fn.Recv != nil {
		return "", false
	}
	name := fn.Name.Name
	if !strings.HasPrefix(name, "New") || len(name) < 4 {
		return "", false
	}
	suffix := name[3:]
	if suffix[0] < 'A' || suffix[0] > 'Z' {
		return "", false
	}
	results := fn.Type.Results
	if results == nil || len(results.List) != 2 {
		return "", false
	}
	if !isErrorType(results.List[1].Type) {
		return "", false
	}
	if identName(results.List[0].Type) != suffix {
		return "", false
	}
	if excluded[suffix] {
		return "", false
	}
	return suffix, true
}

func isErrorType(expr ast.Expr) bool {
	id, ok := expr.(*ast.Ident)
	return ok && id.Name == "error"
}

// identName returns the name of a type expression, handling plain identifiers
// (Foo), single-param generics (Foo[T]), and multi-param generics (Foo[T, U]).
func identName(expr ast.Expr) string {
	switch e := expr.(type) {
	case *ast.Ident:
		return e.Name
	case *ast.IndexExpr:
		return identName(e.X)
	case *ast.IndexListExpr:
		return identName(e.X)
	}
	return ""
}
