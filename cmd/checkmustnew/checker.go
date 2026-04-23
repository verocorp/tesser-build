package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"strings"
)

// Violation represents a New* constructor missing its MustNew* counterpart.
type Violation struct {
	File     string
	Line     int
	FuncName string // e.g. "NewCustomerID"
	TypeName string // e.g. "CustomerID"
}

func (v Violation) String() string {
	return fmt.Sprintf("MISSING: Must%s — expected in %s/ (%s at %s:%d)",
		v.FuncName, filepath.Dir(v.File), v.FuncName, v.File, v.Line)
}

// CheckPackageDir scans a single package directory for VO constructors
// missing MustNew* counterparts.
func CheckPackageDir(dir string, excluded map[string]bool) ([]Violation, error) {
	fset := token.NewFileSet()
	pkgs, err := parser.ParseDir(fset, dir, func(fi os.FileInfo) bool {
		return !strings.HasSuffix(fi.Name(), "_test.go")
	}, 0)
	if err != nil {
		return nil, fmt.Errorf("parsing %s: %w", dir, err)
	}

	var violations []Violation

	for _, pkg := range pkgs {
		// Collect all MustNew* function names in the package.
		mustNews := collectMustNews(pkg)

		// Find New* constructors that need a MustNew* counterpart.
		for filename, file := range pkg.Files {
			for _, decl := range file.Decls {
				fn, ok := decl.(*ast.FuncDecl)
				if !ok || fn.Recv != nil {
					continue
				}

				typeName, ok := matchVOConstructor(fn, excluded)
				if !ok {
					continue
				}

				mustName := "MustNew" + typeName
				if !mustNews[mustName] {
					pos := fset.Position(fn.Pos())
					violations = append(violations, Violation{
						File:     filename,
						Line:     pos.Line,
						FuncName: fn.Name.Name,
						TypeName: typeName,
					})
				}
			}
		}
	}

	return violations, nil
}

// matchVOConstructor checks whether fn is a VO constructor that needs a
// MustNew* counterpart. Returns the type name suffix and true if it matches.
//
// A function matches when:
//   - Name starts with "New" followed by an uppercase letter
//   - Returns exactly (T, error) where T is a named type
//   - The suffix after "New" equals the return type name (excludes factories
//     like NewCollect→Operation)
//   - The type name is not in the exclusion set
func matchVOConstructor(fn *ast.FuncDecl, excluded map[string]bool) (string, bool) {
	if fn.Recv != nil {
		return "", false
	}

	name := fn.Name.Name

	if !strings.HasPrefix(name, "New") || len(name) < 4 {
		return "", false
	}

	suffix := name[3:]
	// Must start with uppercase (e.g., NewCustomerID, not "Newfoo")
	if suffix[0] < 'A' || suffix[0] > 'Z' {
		return "", false
	}

	results := fn.Type.Results
	if results == nil || len(results.List) != 2 {
		return "", false
	}

	// Second return must be "error".
	if !isErrorType(results.List[1].Type) {
		return "", false
	}

	// First return must be a named type whose name matches the suffix.
	returnTypeName := identName(results.List[0].Type)
	if returnTypeName == "" || returnTypeName != suffix {
		return "", false
	}

	if excluded[suffix] {
		return "", false
	}

	return suffix, true
}

// collectMustNews returns the set of MustNew* function names in a package.
func collectMustNews(pkg *ast.Package) map[string]bool {
	names := make(map[string]bool)
	for _, file := range pkg.Files {
		for _, decl := range file.Decls {
			fn, ok := decl.(*ast.FuncDecl)
			if !ok || fn.Recv != nil {
				continue
			}
			if strings.HasPrefix(fn.Name.Name, "MustNew") {
				names[fn.Name.Name] = true
			}
		}
	}
	return names
}

// isErrorType reports whether expr is the identifier "error".
func isErrorType(expr ast.Expr) bool {
	ident, ok := expr.(*ast.Ident)
	return ok && ident.Name == "error"
}

// identName returns the name of a type expression. It handles plain
// identifiers (Foo), single-param generics (Foo[T]), and multi-param
// generics (Foo[T, U]).
func identName(expr ast.Expr) string {
	switch e := expr.(type) {
	case *ast.Ident:
		return e.Name
	case *ast.IndexExpr:
		// Single type param: Foo[T] → extract "Foo"
		return identName(e.X)
	case *ast.IndexListExpr:
		// Multi type params: Foo[T, U] → extract "Foo"
		return identName(e.X)
	}
	return ""
}
