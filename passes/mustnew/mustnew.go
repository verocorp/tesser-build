// Package mustnew is the go/analysis port of cmd/checkmustnew: every
// value-object constructor NewX(...) (X, error) must have a paired MustNewX
// that panics on error. As an analyzer it composes with go vet
// (go vet -vettool=<binary>) and runs in editors via gopls, which the
// standalone directory-walker could not.
package mustnew

import (
	"go/ast"
	"strings"

	"golang.org/x/tools/go/analysis"

	"github.com/chrisconley/go-ddd/internal/voscan"
)

var exclude string

// Analyzer reports value-object constructors with no paired MustNew helper.
var Analyzer = &analysis.Analyzer{
	Name: "mustnew",
	Doc:  "value-object constructors NewX(...) (X, error) must have a paired MustNewX",
	Run:  run,
}

func init() {
	Analyzer.Flags.StringVar(&exclude, "exclude", "", "comma-separated type names exempt (aggregates/entities)")
}

func run(pass *analysis.Pass) (any, error) {
	excluded := voscan.CombinedExcludes(pass, exclude)

	// Collect every MustNew* free function in the package.
	mustNews := map[string]bool{}
	for _, f := range pass.Files {
		for _, d := range f.Decls {
			fn, ok := d.(*ast.FuncDecl)
			if !ok || fn.Recv != nil {
				continue
			}
			if strings.HasPrefix(fn.Name.Name, "MustNew") {
				mustNews[fn.Name.Name] = true
			}
		}
	}

	// Flag any VO constructor whose MustNew counterpart is missing.
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
			if !mustNews["MustNew"+typeName] {
				pass.Reportf(fn.Pos(), "value object %s: constructor %s has no paired MustNew%s", typeName, fn.Name.Name, typeName)
			}
		}
	}
	return nil, nil
}
