// Package comparability enforces the high-confidence half of value-object
// requirement #7: equality must be well-defined. If a value object is not
// Go-comparable — it has a slice, map, or func field, or a [0]func() blocker —
// then == is a compile error, so the type must provide an Equal(X) bool method
// for callers (and the equality test) to use. This analyzer flags a
// non-comparable value object that lacks Equal.
//
// The other half — a value object that IS comparable but should still expose
// Equal as the equality contract — is a semantic judgment and stays with the
// equalitytest analyzer (which checks the Test*_Equality exists). Here we only
// flag the case the compiler makes unambiguous: not comparable, no Equal.
//
// Value objects are identified by their NewX(...) (X, error) constructor.
package comparability

import (
	"go/types"

	"golang.org/x/tools/go/analysis"

	"github.com/chrisconley/go-ddd/internal/voscan"
)

var exclude string

// Analyzer reports non-comparable value objects that lack an Equal method.
var Analyzer = &analysis.Analyzer{
	Name: "comparability",
	Doc:  "value objects that are not Go-comparable must have an Equal(X) bool method",
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
		voType := obj.Type()
		if types.Comparable(voType) {
			continue // == works; the "should still use Equal" case is equalitytest's
		}
		if hasEqualMethod(voType) {
			continue
		}
		pass.Reportf(obj.Pos(), "value object %s is not Go-comparable (it has a slice, map, or func field), so == is unavailable; add an Equal(%s) bool method", name, name)
	}
	return nil, nil
}

// hasEqualMethod reports whether t's value method set contains an
// Equal(X) bool, where X is t itself (by value or pointer).
func hasEqualMethod(t types.Type) bool {
	ms := types.NewMethodSet(t)
	for i := 0; i < ms.Len(); i++ {
		fn, ok := ms.At(i).Obj().(*types.Func)
		if !ok || fn.Name() != "Equal" {
			continue
		}
		sig, ok := fn.Type().(*types.Signature)
		if !ok || sig.Params().Len() != 1 || sig.Results().Len() != 1 {
			continue
		}
		if !types.Identical(sig.Results().At(0).Type(), types.Typ[types.Bool]) {
			continue
		}
		p := sig.Params().At(0).Type()
		if types.Identical(p, t) || types.Identical(p, types.NewPointer(t)) {
			return true
		}
	}
	return false
}
