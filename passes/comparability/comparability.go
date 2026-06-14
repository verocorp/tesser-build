// Package comparability enforces value-object requirement #7: equality must be
// well-defined and a value comparison. A value object must define an
// Equal(X) bool method whenever Go's == is either unavailable or semantically
// wrong:
//
//   - Not Go-comparable: a slice, map, or func field (or a [0]func() blocker)
//     means == is a compile error. types.Comparable catches these.
//   - Comparable but unsafe: a pointer field (== compares identity, not value)
//     or an interface field (== compares the dynamic value and can panic at
//     runtime), anywhere in the field tree. == compiles but is not a value
//     comparison.
//
// In both cases callers need an Equal method to compare by value, so this
// analyzer flags such a value object when it lacks one. A value object whose
// fields are all comparable scalars/value-structs has a correct == and is left
// alone — requiring Equal there is a taste call, not a structural hazard.
//
// Value objects are identified by their NewX(...) (X, error) constructor.
package comparability

import (
	"go/types"

	"golang.org/x/tools/go/analysis"

	"github.com/chrisconley/go-ddd/internal/voscan"
)

var exclude string

// Analyzer reports value objects whose == is unavailable or unsafe and which
// lack an Equal method.
var Analyzer = &analysis.Analyzer{
	Name: "comparability",
	Doc:  "value objects whose == is unavailable (slice/map/func) or unsafe (pointer/interface) must have an Equal(X) bool method",
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
		reason := unsafeReason(voType)
		if reason == "" {
			continue // == is available and a correct value comparison
		}
		if hasEqualMethod(voType) {
			continue
		}
		pass.Reportf(obj.Pos(), "value object %s %s; add an Equal(%s) bool method", name, reason, name)
	}
	return nil, nil
}

// unsafeReason returns why == is unavailable or semantically wrong for t, or ""
// if == is both available and a correct value comparison.
func unsafeReason(t types.Type) string {
	if !types.Comparable(t) {
		return "is not Go-comparable (it has a slice, map, or func field), so == is unavailable"
	}
	switch unsafeField(t, map[types.Type]bool{}) {
	case "pointer":
		return "has a pointer field, so == compares identity, not value"
	case "interface":
		return "has an interface field, so == compares the dynamic value and can panic at runtime"
	}
	return ""
}

// unsafeField walks t's field tree and returns "pointer" or "interface" if a
// field of that kind makes == unsafe, or "" if none. It recurses through value
// structs and arrays; a pointer or interface is terminal (the hazard), so the
// walk never follows a pointer and cannot cycle. The seen set is a defensive
// guard against pathological types.
func unsafeField(t types.Type, seen map[types.Type]bool) string {
	if seen[t] {
		return ""
	}
	seen[t] = true
	switch u := t.Underlying().(type) {
	case *types.Pointer:
		return "pointer"
	case *types.Interface:
		return "interface"
	case *types.Struct:
		for i := 0; i < u.NumFields(); i++ {
			if kind := unsafeField(u.Field(i).Type(), seen); kind != "" {
				return kind
			}
		}
	case *types.Array:
		return unsafeField(u.Elem(), seen)
	}
	return ""
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
