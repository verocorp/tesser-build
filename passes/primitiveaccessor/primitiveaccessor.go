// Package primitiveaccessor enforces value-object requirements #6a/#6b: a value
// object must not leak its representation through a primitive accessor. Two
// shapes are flagged on a value object's value method set:
//
//	#6a  a method named ToString — use String() instead.
//	#6b  a To* accessor whose result is a Go builtin primitive (ToInt() int,
//	     ToCents() int64, ...) — it hands out the raw representation.
//
// A To* method that returns another named type (another value object, e.g.
// Feet.ToMeters() Meters) is a legitimate conversion and is NOT flagged: the
// distinction is *types.Basic (a raw primitive) versus *types.Named (a wrapper).
// Value objects are identified by their NewX(...) (X, error) constructor.
package primitiveaccessor

import (
	"go/types"

	"golang.org/x/tools/go/analysis"

	"github.com/chrisconley/go-ddd/internal/voscan"
)

var exclude string

// Analyzer reports value objects with ToString or primitive-returning To*
// accessors.
var Analyzer = &analysis.Analyzer{
	Name: "primitiveaccessor",
	Doc:  "value objects must not expose ToString or a To* accessor returning a Go primitive",
	Run:  run,
}

func init() {
	Analyzer.Flags.StringVar(&exclude, "exclude", "", "comma-separated type names exempt (aggregates/entities)")
}

func run(pass *analysis.Pass) (any, error) {
	excluded := voscan.CombinedExcludes(pass, exclude)
	for name := range voscan.VOTypeNames(pass.Files, excluded) {
		obj := pass.Pkg.Scope().Lookup(name)
		if obj == nil {
			continue
		}
		ms := types.NewMethodSet(obj.Type())
		for i := 0; i < ms.Len(); i++ {
			fn, ok := ms.At(i).Obj().(*types.Func)
			if !ok {
				continue
			}
			mName := fn.Name()
			if mName == "ToString" {
				pass.Reportf(fn.Pos(), "value object %s exposes ToString; use String() instead (do not leak the representation)", name)
				continue
			}
			if isToAccessor(mName) && returnsPrimitive(fn) {
				pass.Reportf(fn.Pos(), "value object %s exposes %s returning a Go primitive; it leaks the representation (return a value object, or keep the accessor unexported)", name, mName)
			}
		}
	}
	return nil, nil
}

// isToAccessor reports whether name is a To-prefixed accessor: "To" followed by
// an uppercase letter (ToInt, ToMeters), so ordinary words like "Total" or
// "Token" do not match.
func isToAccessor(name string) bool {
	return len(name) > 2 && name[:2] == "To" && name[2] >= 'A' && name[2] <= 'Z'
}

// returnsPrimitive reports whether fn's first result is a Go builtin primitive
// (a *types.Basic, e.g. int/string/bool), as opposed to a named wrapper type.
func returnsPrimitive(fn *types.Func) bool {
	sig, ok := fn.Type().(*types.Signature)
	if !ok || sig.Results().Len() == 0 {
		return false
	}
	basic, ok := sig.Results().At(0).Type().(*types.Basic)
	if !ok {
		return false
	}
	return basic.Kind() != types.Invalid && basic.Kind() != types.UnsafePointer
}
