// Package stringer enforces value-object requirement #6: a value object has a
// String() string method for display. Value objects are identified by their
// NewX(...) (X, error) constructor; the check is whether the value type's method
// set includes String() string (equivalently, the value type implements
// fmt.Stringer). The value method set is used deliberately — a value object is
// used by value, so String() must have a value receiver to be reachable.
package stringer

import (
	"go/types"

	"golang.org/x/tools/go/analysis"

	"github.com/chrisconley/go-ddd/internal/voscan"
)

var exclude string

// Analyzer reports value objects whose value method set lacks String() string.
var Analyzer = &analysis.Analyzer{
	Name: "stringer",
	Doc:  "value objects must have a String() string method (display)",
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
		if !hasStringMethod(obj.Type()) {
			pass.Reportf(obj.Pos(), "value object %s has no String() string method; add one (a value object needs a display form)", name)
		}
	}
	return nil, nil
}

// hasStringMethod reports whether t's value method set contains a method
// String() string returning the predeclared string type.
func hasStringMethod(t types.Type) bool {
	ms := types.NewMethodSet(t)
	for i := 0; i < ms.Len(); i++ {
		fn, ok := ms.At(i).Obj().(*types.Func)
		if !ok || fn.Name() != "String" {
			continue
		}
		sig, ok := fn.Type().(*types.Signature)
		if !ok {
			continue
		}
		if sig.Params().Len() == 0 && sig.Results().Len() == 1 &&
			types.Identical(sig.Results().At(0).Type(), types.Typ[types.String]) {
			return true
		}
	}
	return false
}
