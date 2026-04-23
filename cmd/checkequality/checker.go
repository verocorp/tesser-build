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

// Violation represents a VO constructor missing its Test*_Equality test.
type Violation struct {
	File     string
	Line     int
	FuncName string // e.g. "NewCustomerID"
	TypeName string // e.g. "CustomerID"
}

func (v Violation) String() string {
	return fmt.Sprintf("MISSING: Test%s_Equality — expected in %s/ (%s at %s:%d)",
		v.TypeName, filepath.Dir(v.File), v.FuncName, v.File, v.Line)
}

// CheckPackageDir scans a single package directory for VO constructors
// missing Test*_Equality counterparts in test files.
func CheckPackageDir(dir string, excluded map[string]bool) ([]Violation, error) {
	fset := token.NewFileSet()

	// Parse source files (non-test).
	srcPkgs, err := parser.ParseDir(fset, dir, func(fi os.FileInfo) bool {
		return !strings.HasSuffix(fi.Name(), "_test.go")
	}, 0)
	if err != nil {
		return nil, fmt.Errorf("parsing source in %s: %w", dir, err)
	}

	// Parse test files.
	testPkgs, err := parser.ParseDir(fset, dir, func(fi os.FileInfo) bool {
		return strings.HasSuffix(fi.Name(), "_test.go")
	}, 0)
	if err != nil {
		return nil, fmt.Errorf("parsing tests in %s: %w", dir, err)
	}

	// Collect all Test*_Equality function names from test files.
	equalityTests := make(map[string]bool)
	for _, pkg := range testPkgs {
		for _, file := range pkg.Files {
			for _, decl := range file.Decls {
				fn, ok := decl.(*ast.FuncDecl)
				if !ok || fn.Recv != nil {
					continue
				}
				name := fn.Name.Name
				if strings.HasPrefix(name, "Test") && strings.HasSuffix(name, "_Equality") {
					// Extract type name: "TestFoo_Equality" → "Foo"
					typeName := name[4 : len(name)-9]
					equalityTests[typeName] = true
				}
			}
		}
	}

	var violations []Violation

	for _, pkg := range srcPkgs {
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

				if !equalityTests[typeName] {
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

// matchVOConstructor checks whether fn is a VO constructor.
// Returns the type name and true if it matches.
//
// A function matches when:
//   - Name starts with "New" followed by an uppercase letter
//   - Returns exactly (T, error) where T is a named type
//   - The suffix after "New" equals the return type name
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

	returnTypeName := identName(results.List[0].Type)
	if returnTypeName == "" || returnTypeName != suffix {
		return "", false
	}

	if excluded[suffix] {
		return "", false
	}

	return suffix, true
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
