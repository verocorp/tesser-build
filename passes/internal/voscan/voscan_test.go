package voscan

import (
	"go/ast"
	"go/parser"
	"go/token"
	"testing"
)

// parseFunc parses a single function declaration and returns it.
func parseFunc(t *testing.T, src string) *ast.FuncDecl {
	t.Helper()
	f, err := parser.ParseFile(token.NewFileSet(), "x.go", "package p\n"+src, 0)
	if err != nil {
		t.Fatalf("parse %q: %v", src, err)
	}
	for _, d := range f.Decls {
		if fn, ok := d.(*ast.FuncDecl); ok {
			return fn
		}
	}
	t.Fatalf("no func decl in %q", src)
	return nil
}

func TestMatchVOConstructor(t *testing.T) {
	excluded := map[string]bool{"Excluded": true}

	tests := []struct {
		name     string
		src      string
		wantName string
		wantOK   bool
	}{
		{"VO constructor matches", `func NewFoo(v string) (Foo, error) { return Foo{}, nil }`, "Foo", true},
		{"factory does not match — return type differs from suffix", `func NewCollect(v string) (Operation, error) { return Operation{}, nil }`, "", false},
		{"infallible constructor does not match — no error return", `func NewFoo(v string) Foo { return Foo{} }`, "", false},
		{"excluded type does not match", `func NewExcluded(v string) (Excluded, error) { return Excluded{}, nil }`, "", false},
		{"method receiver does not match", `func (r Recv) NewFoo() (Foo, error) { return Foo{}, nil }`, "", false},
		{"lowercase after New does not match", `func Newfoo() (foo, error) { return foo{}, nil }`, "", false},
		{"just New does not match", `func New() (X, error) { return X{}, nil }`, "", false},
		{"generic constructor with single type param matches", `func NewBox(v any) (Box[any], error) { return Box[any]{}, nil }`, "Box", true},
		{"generic constructor with multiple type params matches", `func NewPair(a, b any) (Pair[any, any], error) { return Pair[any, any]{}, nil }`, "Pair", true},
		{"generic factory does not match — return type differs from suffix", `func NewCollect(v any) (Operation[any], error) { return Operation[any]{}, nil }`, "", false},
		{"pointer return type does not match", `func NewFoo() (*Foo, error) { return nil, nil }`, "", false},
		{"qualified return type does not match", `func NewFoo() (pkg.Foo, error) { return pkg.Foo{}, nil }`, "", false},
		{"slice return type does not match", `func NewFoo() ([]Foo, error) { return nil, nil }`, "", false},
		{"map return type does not match", `func NewFoo() (map[string]Foo, error) { return nil, nil }`, "", false},
		{"func return type does not match", `func NewFoo() (func() Foo, error) { return nil, nil }`, "", false},
		{"chan return type does not match", `func NewFoo() (chan Foo, error) { return nil, nil }`, "", false},
		{"interface return type does not match", `func NewFoo() (interface{ Foo() }, error) { return nil, nil }`, "", false},
		{"single return value does not match", `func NewFoo() Foo { return Foo{} }`, "", false},
		{"three return values do not match", `func NewFoo() (Foo, int, error) { return Foo{}, 0, nil }`, "", false},
		{"second return not error does not match", `func NewFoo() (Foo, bool) { return Foo{}, false }`, "", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotName, gotOK := MatchVOConstructor(parseFunc(t, tt.src), excluded)
			if gotOK != tt.wantOK || gotName != tt.wantName {
				t.Errorf("MatchVOConstructor() = (%q, %v), want (%q, %v)", gotName, gotOK, tt.wantName, tt.wantOK)
			}
		})
	}
}

func TestVOTypeNames(t *testing.T) {
	src := `package p
func NewFoo() (Foo, error) { return Foo{}, nil }
func NewBar() (Bar, error) { return Bar{}, nil }
func NewSkip() (Skip, error) { return Skip{}, nil }
func makeThing() (Foo, error) { return Foo{}, nil }
`
	f, err := parser.ParseFile(token.NewFileSet(), "x.go", src, 0)
	if err != nil {
		t.Fatal(err)
	}
	got := VOTypeNames([]*ast.File{f}, map[string]bool{"Skip": true})
	want := map[string]bool{"Foo": true, "Bar": true}
	if len(got) != len(want) {
		t.Fatalf("VOTypeNames() = %v, want %v", got, want)
	}
	for name := range want {
		if !got[name] {
			t.Errorf("VOTypeNames() missing %q", name)
		}
	}
}

func TestParseExcludes(t *testing.T) {
	got := ParseExcludes("  Foo , Bar ,, Baz ")
	want := map[string]bool{"Foo": true, "Bar": true, "Baz": true}
	if len(got) != len(want) {
		t.Fatalf("ParseExcludes() = %v, want %v", got, want)
	}
	for name := range want {
		if !got[name] {
			t.Errorf("ParseExcludes() missing %q", name)
		}
	}
}
