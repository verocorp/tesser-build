// Package voconstructor enforces value-object requirement #2: a value object's
// only construction path is a validating constructor NewX(...) (X, error). The
// other analyzers identify a value object BY that constructor; this one checks
// for its ABSENCE, so it cannot use the same signal. Instead it flags a type
// that is value-object SHAPED but has no such constructor.
//
// A candidate is an exported, package-level struct with at least one field and
// no exported fields. All-unexported fields signal encapsulation — the value
// object intent — and make the type unconstructable from outside without a
// constructor; the missing constructor is the gap. (Structs with exported
// fields are directly constructable and are the encapsulation-leak concern of
// the vofields analyzer, not this one.) The exclude list carries the
// aggregates, entities, and deliberate zero-value types that share this shape;
// because the heuristic is structural, that list is where the domain call
// lives. Whether the constructor body validates is semantic and stays the
// test's job.
package voconstructor

import (
	"go/ast"
	"go/types"

	"golang.org/x/tools/go/analysis"

	"github.com/chrisconley/go-ddd/internal/voscan"
)

var exclude string

// Analyzer reports value-object-shaped structs with no NewX(...) (X, error).
var Analyzer = &analysis.Analyzer{
	Name: "voconstructor",
	Doc:  "value-object-shaped structs must have a validating constructor NewX(...) (X, error)",
	Run:  run,
}

func init() {
	Analyzer.Flags.StringVar(&exclude, "exclude", "", "comma-separated type names exempt (aggregates/entities)")
}

func run(pass *analysis.Pass) (any, error) {
	excluded := voscan.CombinedExcludes(pass, exclude)

	// Types that already have an error-returning constructor. Exclusion is not
	// applied here — we want the true set of constructed types, and apply
	// exclusion only when deciding what to flag.
	hasConstructor := map[string]bool{}
	for _, f := range pass.Files {
		for _, d := range f.Decls {
			fn, ok := d.(*ast.FuncDecl)
			if !ok {
				continue
			}
			if name, ok := voscan.MatchVOConstructor(fn, nil); ok {
				hasConstructor[name] = true
			}
		}
	}

	scope := pass.Pkg.Scope()
	for _, name := range scope.Names() {
		obj, ok := scope.Lookup(name).(*types.TypeName)
		if !ok || !obj.Exported() || excluded[name] || hasConstructor[name] {
			continue
		}
		st, ok := obj.Type().Underlying().(*types.Struct)
		if !ok || st.NumFields() == 0 {
			continue // non-struct or empty marker: not the shape this rule covers
		}
		if hasExportedField(st) {
			continue // directly constructable; the leak is vofields' concern
		}
		pass.Reportf(obj.Pos(), "value object %s has no validating constructor New%s(...) (%s, error); make a constructor the only construction path", name, name, name)
	}
	return nil, nil
}

func hasExportedField(st *types.Struct) bool {
	for i := 0; i < st.NumFields(); i++ {
		if st.Field(i).Exported() {
			return true
		}
	}
	return false
}
