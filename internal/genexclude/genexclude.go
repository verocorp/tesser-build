// Package genexclude is the engine behind `ddd-vet -gen-excludes`: it scans
// constructor-bearing types in a set of loaded packages and classifies each as
// an entity/aggregate (which the value-object heuristic would wrongly match) so
// it can be written to a starter .go-ddd.yaml for a human to review.
//
// Why generate-and-review and not pure runtime auto-classification: a wrong
// "this is an entity" guess makes the checkers SILENTLY skip a real value
// object — the exact silent gap this toolkit exists to prevent. A generated,
// version-controlled, human-ratified list keeps every exclusion explicit. The
// generator removes the blank-page toil; the human keeps the domain call.
//
// Signals, strongest first:
//   - Identity: an ID() method, or a field named id / ID / <Type>ID. Value
//     objects have no identity — this is the strongest entity signal.
//   - Mutability: a pointer-receiver method that assigns to a field (a setter or
//     state transition). Value objects are immutable.
//   - Child collections: a slice/map field whose element is another domain
//     (named struct) type — the shape of an aggregate root.
package genexclude

import (
	"fmt"
	"go/ast"
	"go/types"
	"sort"
	"strings"

	"golang.org/x/tools/go/packages"

	"github.com/chrisconley/go-ddd/internal/voscan"
)

// Entry is one classified type: the name to exclude and a one-line reason.
type Entry struct {
	Name   string
	Reason string
}

// Classify scans the packages for constructor-bearing types and returns, sorted
// by name, those that look like entities or aggregates. A type matching none of
// the signals is assumed to be a value object and is omitted (not excluded).
func Classify(pkgs []*packages.Package) []Entry {
	var entries []Entry
	for _, pkg := range pkgs {
		// Constructor-bearing type names in this package (NewX(X,error)).
		ctorTypes := voscan.VOTypeNames(pkg.Syntax, nil)
		if len(ctorTypes) == 0 {
			continue
		}
		mutators := pointerMutators(pkg.Syntax)
		for name := range ctorTypes {
			if reason, ok := classifyType(pkg, name, mutators[name]); ok {
				entries = append(entries, Entry{Name: name, Reason: reason})
			}
		}
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].Name < entries[j].Name })
	return entries
}

// classifyType applies the signals to a single named type, returning the reason
// for the first (strongest) match.
func classifyType(pkg *packages.Package, name, mutatorMethod string) (string, bool) {
	obj := pkg.Types.Scope().Lookup(name)
	if obj == nil {
		return "", false
	}
	named, ok := obj.Type().(*types.Named)
	if !ok {
		return "", false
	}

	// Identity (strongest): an ID() method.
	for i := 0; i < named.NumMethods(); i++ {
		if named.Method(i).Name() == "ID" {
			return "has ID() method            (entity)", true
		}
	}

	st, _ := named.Underlying().(*types.Struct)

	// Identity: an id / ID / <Type>ID field.
	if st != nil {
		for i := 0; i < st.NumFields(); i++ {
			f := st.Field(i)
			if isIdentityField(f.Name(), name) {
				return fmt.Sprintf("field: %s %s    (entity)", f.Name(), typeString(f.Type())), true
			}
		}
	}

	// Mutability: a pointer-receiver method that assigns to a field.
	if mutatorMethod != "" {
		return fmt.Sprintf("mutated by (*%s).%s()  (aggregate)", name, mutatorMethod), true
	}

	// Child collections: a slice/map field of another domain (named struct) type.
	if st != nil {
		for i := 0; i < st.NumFields(); i++ {
			f := st.Field(i)
			if elem, ok := childCollectionElem(f.Type()); ok {
				return fmt.Sprintf("holds child collection %s []%s  (aggregate)", f.Name(), elem), true
			}
		}
	}
	return "", false
}

// isIdentityField reports whether a field name signals identity: id / ID, or
// <Type>ID (e.g. TransactionID on Transaction).
func isIdentityField(field, typeName string) bool {
	return field == "id" || field == "ID" || field == typeName+"ID"
}

// childCollectionElem reports whether t is a slice or map whose element is a
// named struct type (another domain object), returning that element's name.
func childCollectionElem(t types.Type) (string, bool) {
	var elem types.Type
	switch u := t.Underlying().(type) {
	case *types.Slice:
		elem = u.Elem()
	case *types.Map:
		elem = u.Elem()
	default:
		return "", false
	}
	named, ok := elem.(*types.Named)
	if !ok {
		return "", false
	}
	if _, ok := named.Underlying().(*types.Struct); !ok {
		return "", false
	}
	return named.Obj().Name(), true
}

// pointerMutators returns, per type name, the name of one pointer-receiver
// method that assigns to a receiver field (a setter / state transition).
func pointerMutators(files []*ast.File) map[string]string {
	out := map[string]string{}
	for _, f := range files {
		for _, d := range f.Decls {
			fn, ok := d.(*ast.FuncDecl)
			if !ok || fn.Recv == nil || len(fn.Recv.List) != 1 || fn.Body == nil {
				continue
			}
			star, ok := fn.Recv.List[0].Type.(*ast.StarExpr)
			if !ok {
				continue
			}
			typeName := baseTypeName(star.X)
			if typeName == "" {
				continue
			}
			if _, seen := out[typeName]; seen {
				continue
			}
			recv := ""
			if len(fn.Recv.List[0].Names) > 0 {
				recv = fn.Recv.List[0].Names[0].Name
			}
			if recv == "" || recv == "_" {
				continue
			}
			if assignsToReceiverField(fn.Body, recv) {
				out[typeName] = fn.Name.Name
			}
		}
	}
	return out
}

// assignsToReceiverField reports whether body assigns to recv.<field> (via = or
// ++/--), the mark of a mutating method.
func assignsToReceiverField(body *ast.BlockStmt, recv string) bool {
	found := false
	ast.Inspect(body, func(n ast.Node) bool {
		if found {
			return false
		}
		switch s := n.(type) {
		case *ast.AssignStmt:
			for _, lhs := range s.Lhs {
				if isReceiverFieldSelector(lhs, recv) {
					found = true
				}
			}
		case *ast.IncDecStmt:
			if isReceiverFieldSelector(s.X, recv) {
				found = true
			}
		}
		return !found
	})
	return found
}

func isReceiverFieldSelector(e ast.Expr, recv string) bool {
	sel, ok := e.(*ast.SelectorExpr)
	if !ok {
		return false
	}
	id, ok := sel.X.(*ast.Ident)
	return ok && id.Name == recv
}

// baseTypeName returns the type name from a receiver base expression, handling
// plain identifiers and generic receivers (T[P]).
func baseTypeName(e ast.Expr) string {
	switch x := e.(type) {
	case *ast.Ident:
		return x.Name
	case *ast.IndexExpr:
		return baseTypeName(x.X)
	case *ast.IndexListExpr:
		return baseTypeName(x.X)
	}
	return ""
}

// typeString renders a field type compactly for the generated reason comment.
func typeString(t types.Type) string {
	if named, ok := t.(*types.Named); ok {
		return named.Obj().Name()
	}
	return types.TypeString(t, func(*types.Package) string { return "" })
}

// Render produces .go-ddd.yaml content from the classified entries. The date is
// passed in (not read from the clock) so the output is testable.
func Render(entries []Entry, date string) string {
	var b strings.Builder
	fmt.Fprintf(&b, "# Generated by `ddd-vet -gen-excludes` on %s. Review and edit — each entry\n", date)
	b.WriteString("# is a type the checkers SKIP (treated as an entity/aggregate, not a value\n")
	b.WriteString("# object). A wrong entry silently hides a real value object, so curate this.\n")
	b.WriteString("exclude:\n")
	if len(entries) == 0 {
		b.WriteString("  []\n")
		return b.String()
	}
	width := 0
	for _, e := range entries {
		if len(e.Name) > width {
			width = len(e.Name)
		}
	}
	for _, e := range entries {
		fmt.Fprintf(&b, "  - %-*s  # %s\n", width, e.Name, e.Reason)
	}
	return b.String()
}
