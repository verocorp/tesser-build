// Package vofields enforces value-object requirement #1: a value object
// encapsulates its representation, so it must not expose exported fields. (The
// "public accessors" half of the rubric is intentionally not enforced — not
// every private field warrants an accessor.) Value objects are identified via
// their NewX(...) (X, error) constructor.
//
// This analyzer uses type information (go/types) to inspect the struct's fields.
package vofields

import (
	"go/types"

	"golang.org/x/tools/go/analysis"

	"github.com/chrisconley/go-ddd/internal/voscan"
)

var exclude string

// Analyzer reports value objects that expose exported fields.
var Analyzer = &analysis.Analyzer{
	Name: "vofields",
	Doc:  "value objects must not have exported fields (encapsulate the representation)",
	Run:  run,
}

func init() {
	Analyzer.Flags.StringVar(&exclude, "exclude", "", "comma-separated type names exempt (aggregates/entities)")
}

func run(pass *analysis.Pass) (any, error) {
	excluded, err := voscan.CombinedExcludes(pass, exclude)
	if err != nil {
		return nil, err
	}
	for name := range voscan.VOTypeNames(pass.Files, excluded) {
		obj := pass.Pkg.Scope().Lookup(name)
		if obj == nil {
			continue
		}
		st, ok := obj.Type().Underlying().(*types.Struct)
		if !ok {
			continue // a non-struct VO (e.g. a named primitive) has no fields to leak
		}
		for i := 0; i < st.NumFields(); i++ {
			if f := st.Field(i); f.Exported() {
				pass.Reportf(f.Pos(), "value object %s exposes exported field %s; encapsulate the representation (unexported field + accessor)", name, f.Name())
			}
		}
	}
	return nil, nil
}
