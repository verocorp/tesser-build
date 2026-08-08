// Command spike-totalreturn is a throwaway probe for one proposed rule:
//
//	"Every method on a domain object returns another domain object.
//	 No primitives. Not bool. Not an enum — enums are primitives here."
//
// It does not argue about the rule. It encodes the rule in its purest form
// (zero licensed exits) and runs it over this repo's own domain types, so the
// break list is measured rather than imagined.
//
// A "domain object" is any package-scope named type T that has a validating
// constructor NewT(...) (T, error) — the same signal internal/voscan uses,
// widened to include the entities and aggregates that voscan's exclude list
// subtracts, because the rule under test is about all three.
//
// Usage: go run ./examples/spike-totalreturn ./rationale/... ./examples/...
package main

import (
	"fmt"
	"go/token"
	"go/types"
	"os"
	"sort"
	"strings"

	"golang.org/x/tools/go/packages"
)

// modulePrefix marks a named type as ours rather than stdlib/vendor.
const modulePrefix = "github.com/verocorp/tesser-build/"

// verdict is how one result type fares under the pure rule.
type verdict string

const (
	// vDomain is the only verdict the pure rule permits.
	vDomain verdict = "DOMAIN"
	// vBasic is a Go builtin: string, int, float64, bool.
	vBasic verdict = "PRIMITIVE"
	// vNamedBasic is a named type over a builtin — the enum/type-code shape
	// the proposal explicitly declares primitive.
	vNamedBasic verdict = "ENUM"
	// vError is the error interface: idiomatic Go, but not a domain object.
	vError verdict = "ERROR"
	// vForeign is a named type from outside the module: time.Time, decimal.Decimal.
	vForeign verdict = "FOREIGN"
	// vIface is a non-error interface: a port, a strategy.
	vIface verdict = "INTERFACE"
	// vOther is func/chan/unsafe and anything else that fits no bucket.
	vOther verdict = "OTHER"
)

// finding is one exported method result measured against the rule.
type finding struct {
	pos    token.Position
	recv   string
	method string
	sig    string
	// results is the per-result verdict, in declaration order.
	results []verdict
}

// breaks reports whether this method violates the pure rule: any result that
// is not itself a domain object.
func (f finding) breaks() bool {
	for _, v := range f.results {
		if v != vDomain {
			return true
		}
	}
	return false
}

func main() {
	patterns := os.Args[1:]
	if len(patterns) == 0 {
		patterns = []string{"./..."}
	}
	cfg := &packages.Config{Mode: packages.NeedName | packages.NeedTypes | packages.NeedSyntax |
		packages.NeedTypesInfo | packages.NeedDeps | packages.NeedImports | packages.NeedFiles}
	pkgs, err := packages.Load(cfg, patterns...)
	if err != nil {
		fmt.Fprintln(os.Stderr, "load:", err)
		os.Exit(1)
	}

	// domainTypes is the module-wide set of types carrying a NewT constructor,
	// keyed by the type's fully qualified name, so a cross-package result
	// (ordersapp.Order returned from a repository) classifies correctly.
	domainTypes := map[string]bool{}
	for _, p := range pkgs {
		for _, name := range constructedTypes(p) {
			domainTypes[p.PkgPath+"."+name] = true
		}
	}

	var findings []finding
	for _, p := range pkgs {
		for _, name := range constructedTypes(p) {
			obj := p.Types.Scope().Lookup(name)
			if obj == nil {
				continue
			}
			findings = append(findings, measure(p, obj, domainTypes)...)
		}
	}
	sort.Slice(findings, func(i, j int) bool {
		if findings[i].pos.Filename != findings[j].pos.Filename {
			return findings[i].pos.Filename < findings[j].pos.Filename
		}
		return findings[i].pos.Line < findings[j].pos.Line
	})

	report(findings, len(domainTypes))
}

// constructedTypes returns the package-scope type names T for which a
// NewT(...) (T, error) exists — value objects, entities and aggregates alike.
func constructedTypes(p *packages.Package) []string {
	if p.Types == nil {
		return nil
	}
	var names []string
	scope := p.Types.Scope()
	for _, n := range scope.Names() {
		fn, ok := scope.Lookup(n).(*types.Func)
		if !ok || !strings.HasPrefix(n, "New") || len(n) == 3 {
			continue
		}
		sig, ok := fn.Type().(*types.Signature)
		if !ok || sig.Recv() != nil || sig.Results().Len() != 2 {
			continue
		}
		if !isError(sig.Results().At(1).Type()) {
			continue
		}
		want := strings.TrimPrefix(n, "New")
		if named, ok := deref(sig.Results().At(0).Type()).(*types.Named); ok && named.Obj().Name() == want {
			names = append(names, want)
		}
	}
	sort.Strings(names)
	return names
}

// measure classifies every result of every exported method on obj, over both
// the value and pointer method sets (a mutable entity's transitions live on the
// pointer receiver).
func measure(p *packages.Package, obj types.Object, domain map[string]bool) []finding {
	seen := map[string]bool{}
	var out []finding
	for _, t := range []types.Type{obj.Type(), types.NewPointer(obj.Type())} {
		ms := types.NewMethodSet(t)
		for i := 0; i < ms.Len(); i++ {
			fn, ok := ms.At(i).Obj().(*types.Func)
			if !ok || !fn.Exported() || seen[fn.Name()] {
				continue
			}
			seen[fn.Name()] = true
			sig, ok := fn.Type().(*types.Signature)
			if !ok {
				continue
			}
			f := finding{
				pos:    p.Fset.Position(fn.Pos()),
				recv:   obj.Name(),
				method: fn.Name(),
				sig:    types.TypeString(sig, func(pkg *types.Package) string { return pkg.Name() }),
			}
			// A method returning nothing has no result to break the rule on;
			// record it as such rather than silently passing.
			for j := 0; j < sig.Results().Len(); j++ {
				f.results = append(f.results, classify(sig.Results().At(j).Type(), domain))
			}
			out = append(out, f)
		}
	}
	return out
}

// classify places one result type in exactly one bucket. Slices and maps
// classify by their element type — the container is not what the rule is about.
func classify(t types.Type, domain map[string]bool) verdict {
	switch u := deref(t).(type) {
	case *types.Basic:
		return vBasic
	case *types.Slice:
		return classify(u.Elem(), domain)
	case *types.Array:
		return classify(u.Elem(), domain)
	case *types.Map:
		return classify(u.Elem(), domain)
	case *types.Interface:
		return vIface
	case *types.Signature, *types.Chan:
		return vOther
	case *types.Named:
		if isError(u) {
			return vError
		}
		o := u.Obj()
		if o.Pkg() == nil {
			return vOther
		}
		qualified := o.Pkg().Path() + "." + o.Name()
		if domain[qualified] {
			return vDomain
		}
		if !strings.HasPrefix(o.Pkg().Path(), modulePrefix) {
			return vForeign
		}
		// Ours, but no validating constructor. A named type over a builtin is
		// the enum/type-code shape; anything else is a struct without one door.
		if _, ok := u.Underlying().(*types.Basic); ok {
			return vNamedBasic
		}
		return vForeign
	}
	return vOther
}

func deref(t types.Type) types.Type {
	if p, ok := t.(*types.Pointer); ok {
		return p.Elem()
	}
	return t
}

func isError(t types.Type) bool {
	named, ok := t.(*types.Named)
	return ok && named.Obj().Pkg() == nil && named.Obj().Name() == "error"
}

// report prints the break list grouped by verdict, then the tally. The tally is
// the actual output of the probe: how much of the existing conformant corpus
// the pure rule condemns.
func report(findings []finding, domainCount int) {
	tally := map[verdict]int{}
	byVerdict := map[verdict][]finding{}
	broken := 0
	for _, f := range findings {
		if f.breaks() {
			broken++
		}
		for _, v := range f.results {
			tally[v]++
			if v != vDomain {
				byVerdict[v] = append(byVerdict[v], f)
			}
		}
	}

	order := []verdict{vBasic, vError, vForeign, vNamedBasic, vIface, vOther}
	for _, v := range order {
		fs := byVerdict[v]
		if len(fs) == 0 {
			continue
		}
		fmt.Printf("\n=== %s (%d results) ===\n", v, len(fs))
		for _, f := range fs {
			fmt.Printf("  %s:%d  %s.%s%s\n", trim(f.pos.Filename), f.pos.Line,
				f.recv, f.method, strings.TrimPrefix(f.sig, "func"))
		}
	}

	fmt.Printf("\n=== TALLY ===\n")
	fmt.Printf("  domain types (NewT constructor): %d\n", domainCount)
	fmt.Printf("  exported methods measured:       %d\n", len(findings))
	fmt.Printf("  methods breaking the pure rule:  %d (%.0f%%)\n",
		broken, 100*float64(broken)/float64(max(len(findings), 1)))
	for _, v := range append([]verdict{vDomain}, order...) {
		if tally[v] > 0 {
			fmt.Printf("    %-10s %d\n", v, tally[v])
		}
	}
}

func trim(path string) string {
	if i := strings.Index(path, "/tesser-build/"); i >= 0 {
		return path[i+len("/tesser-build/"):]
	}
	return path
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
