package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"strings"
)

// Violation represents a .String() call found outside a Test*_String function.
type Violation struct {
	File     string
	Line     int
	FuncName string // enclosing function, or "" if at package level
}

func (v Violation) String() string {
	if v.FuncName == "" {
		return fmt.Sprintf("VIOLATION: %s:%d: .String() at package level", v.File, v.Line)
	}
	return fmt.Sprintf("VIOLATION: %s:%d: .String() in %s (only allowed in Test*_String)", v.File, v.Line, v.FuncName)
}

// CheckPackageDir scans test files in dir for .String() calls outside
// Test*_String accessor contract tests.
func CheckPackageDir(dir string) ([]Violation, error) {
	fset := token.NewFileSet()

	// Parse test files only.
	pkgs, err := parser.ParseDir(fset, dir, func(fi os.FileInfo) bool {
		return strings.HasSuffix(fi.Name(), "_test.go")
	}, 0)
	if err != nil {
		return nil, fmt.Errorf("parsing tests in %s: %w", dir, err)
	}

	var violations []Violation

	for _, pkg := range pkgs {
		for filename, file := range pkg.Files {
			violations = append(violations, checkFile(fset, filename, file)...)
		}
	}

	return violations, nil
}

// checkFile scans a single AST file for .String() calls outside allowed functions.
func checkFile(fset *token.FileSet, filename string, file *ast.File) []Violation {
	var violations []Violation

	for _, decl := range file.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if !ok {
			continue
		}

		funcName := fn.Name.Name

		// Test*_String functions are allowed to call .String().
		if isStringAccessorTest(funcName) {
			continue
		}

		// Walk the function body looking for .String() calls.
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
				pos := fset.Position(sel.Sel.Pos())
				violations = append(violations, Violation{
					File:     filename,
					Line:     pos.Line,
					FuncName: funcName,
				})
			}

			return true
		})
	}

	return violations
}

// isStringAccessorTest reports whether funcName matches the Test*_String pattern.
func isStringAccessorTest(name string) bool {
	return strings.HasPrefix(name, "Test") && strings.HasSuffix(name, "_String")
}
