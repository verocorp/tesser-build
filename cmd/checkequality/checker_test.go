package main

import (
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestMatchVOConstructor(t *testing.T) {
	tests := []struct {
		name     string
		src      string
		excluded map[string]bool
		wantType string
		wantOK   bool
	}{
		{
			name:     "VO constructor matches",
			src:      `package p; func NewCustomerID(value string) (CustomerID, error) { return CustomerID{}, nil }`,
			wantType: "CustomerID",
			wantOK:   true,
		},
		{
			name:   "factory does not match — return type differs from suffix",
			src:    `package p; func NewCollect(spec CollectSpec) (Operation, error) { return Operation{}, nil }`,
			wantOK: false,
		},
		{
			name:   "infallible constructor does not match — no error return",
			src:    `package p; func NewDecimalFromInt64(i int64) Decimal { return Decimal{} }`,
			wantOK: false,
		},
		{
			name:     "excluded type does not match",
			src:      `package p; func NewLedger(spec LedgerSpec) (Ledger, error) { return Ledger{}, nil }`,
			excluded: map[string]bool{"Ledger": true},
			wantOK:   false,
		},
		{
			name:   "method receiver does not match",
			src:    `package p; func (l Ledger) NewEntry(spec EntrySpec) (Entry, error) { return Entry{}, nil }`,
			wantOK: false,
		},
		{
			name:   "lowercase after New does not match",
			src:    `package p; func Newfoo(s string) (foo, error) { return foo{}, nil }`,
			wantOK: false,
		},
		{
			name:   "just New does not match",
			src:    `package p; func New() (error) { return nil }`,
			wantOK: false,
		},
		{
			name:     "generic constructor with single type param matches",
			src:      `package p; func NewFilter[D any](s string) (Filter[D], error) { return Filter[D]{}, nil }`,
			wantType: "Filter",
			wantOK:   true,
		},
		{
			name:     "generic constructor with multiple type params matches",
			src:      `package p; func NewConverter[In, Out any](s string) (Converter[In, Out], error) { return Converter[In, Out]{}, nil }`,
			wantType: "Converter",
			wantOK:   true,
		},
		{
			name:   "generic factory does not match — return type differs from suffix",
			src:    `package p; func NewMake[D any](s string) (Result[D], error) { return Result[D]{}, nil }`,
			wantOK: false,
		},
		// Return type expression coverage — verify all ast.Expr subtypes
		// that can appear in a return position are handled correctly.
		{
			name:   "pointer return type does not match",
			src:    `package p; func NewFoo(s string) (*Foo, error) { return nil, nil }`,
			wantOK: false,
		},
		{
			name:   "qualified return type does not match",
			src:    `package p; import "pkg"; func NewFoo(s string) (pkg.Foo, error) { return pkg.Foo{}, nil }`,
			wantOK: false,
		},
		{
			name:   "slice return type does not match",
			src:    `package p; func NewFoo(s string) ([]Foo, error) { return nil, nil }`,
			wantOK: false,
		},
		{
			name:   "map return type does not match",
			src:    `package p; func NewFoo(s string) (map[string]Foo, error) { return nil, nil }`,
			wantOK: false,
		},
		{
			name:   "func return type does not match",
			src:    `package p; func NewFoo(s string) (func(), error) { return nil, nil }`,
			wantOK: false,
		},
		{
			name:   "chan return type does not match",
			src:    `package p; func NewFoo(s string) (chan Foo, error) { return nil, nil }`,
			wantOK: false,
		},
		{
			name:   "interface return type does not match",
			src:    `package p; func NewFoo(s string) (interface{ String() string }, error) { return nil, nil }`,
			wantOK: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			fn := parseSingleFunc(t, tt.src)
			if fn == nil {
				if tt.wantOK {
					t.Fatal("expected a function declaration")
				}
				return
			}

			excluded := tt.excluded
			if excluded == nil {
				excluded = map[string]bool{}
			}

			gotType, gotOK := matchVOConstructor(fn, excluded)
			assert.Equal(t, tt.wantOK, gotOK)
			if tt.wantOK {
				assert.Equal(t, tt.wantType, gotType)
			}
		})
	}
}

func TestCheckPackageDir_AllCovered(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type CustomerID struct{ value string }

func NewCustomerID(value string) (CustomerID, error) {
	return CustomerID{value: value}, nil
}
`,
		"types_test.go": `package testpkg

import "testing"

func TestCustomerID_Equality(t *testing.T) {
	// equality tests here
}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	assert.Empty(t, violations)
}

func TestCheckPackageDir_MissingEquality(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type CustomerID struct{ value string }

func NewCustomerID(value string) (CustomerID, error) {
	return CustomerID{value: value}, nil
}
`,
		"types_test.go": `package testpkg

import "testing"

func TestCustomerID_NewCustomerID(t *testing.T) {
	// constructor tests but no equality
}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	require.Len(t, violations, 1)
	assert.Equal(t, "CustomerID", violations[0].TypeName)
	assert.Equal(t, "NewCustomerID", violations[0].FuncName)
}

func TestCheckPackageDir_EqualityInDifferentTestFile(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type Amount struct{ value string }

func NewAmount(value string) (Amount, error) {
	return Amount{value: value}, nil
}
`,
		"amount_test.go": `package testpkg

import "testing"

func TestAmount_Equality(t *testing.T) {
	// equality tests here
}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	assert.Empty(t, violations)
}

func TestCheckPackageDir_SkipsFactories(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"factory.go": `package testpkg

type Operation struct{}
type CollectSpec struct{}

func NewCollect(spec CollectSpec) (Operation, error) {
	return Operation{}, nil
}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	assert.Empty(t, violations)
}

func TestCheckPackageDir_SkipsExcluded(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"ledger.go": `package testpkg

type Ledger struct{}

func NewLedger(spec string) (Ledger, error) {
	return Ledger{}, nil
}
`,
	})

	excluded := map[string]bool{"Ledger": true}
	violations, err := CheckPackageDir(dir, excluded)
	require.NoError(t, err)
	assert.Empty(t, violations)
}

func TestCheckPackageDir_SkipsConstructorsInTestFiles(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"helpers_test.go": `package testpkg

type TestHelper struct{}

func NewTestHelper(s string) (TestHelper, error) {
	return TestHelper{}, nil
}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	assert.Empty(t, violations)
}

func TestCheckPackageDir_MultipleViolations(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type Foo struct{}
type Bar struct{}

func NewFoo(s string) (Foo, error) { return Foo{}, nil }
func NewBar(s string) (Bar, error) { return Bar{}, nil }
`,
		"types_test.go": `package testpkg

import "testing"

func TestFoo_Other(t *testing.T) {}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	require.Len(t, violations, 2)

	typeNames := map[string]bool{}
	for _, v := range violations {
		typeNames[v.TypeName] = true
	}
	assert.True(t, typeNames["Foo"])
	assert.True(t, typeNames["Bar"])
}

func TestCheckPackageDir_MixedCoverageAndViolation(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type Good struct{}
type Bad struct{}

func NewGood(s string) (Good, error) { return Good{}, nil }
func NewBad(s string) (Bad, error) { return Bad{}, nil }
`,
		"types_test.go": `package testpkg

import "testing"

func TestGood_Equality(t *testing.T) {}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	require.Len(t, violations, 1)
	assert.Equal(t, "Bad", violations[0].TypeName)
}

func TestCheckPackageDir_ExternalTestPackage(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type ID struct{ value string }

func NewID(value string) (ID, error) {
	return ID{value: value}, nil
}
`,
		"types_test.go": `package testpkg_test

import "testing"

func TestID_Equality(t *testing.T) {
	// tests using external test package
}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	assert.Empty(t, violations)
}

func TestCheckPackageDir_NoTestFiles(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type ID struct{ value string }

func NewID(value string) (ID, error) {
	return ID{value: value}, nil
}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	require.Len(t, violations, 1)
	assert.Equal(t, "ID", violations[0].TypeName)
}

func TestCheckPackageDir_GenericConstructorMissingEquality(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type Filter[D any] struct{ value D }

func NewFilter[D any](s string) (Filter[D], error) {
	return Filter[D]{}, nil
}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	require.Len(t, violations, 1)
	assert.Equal(t, "Filter", violations[0].TypeName)
	assert.Equal(t, "NewFilter", violations[0].FuncName)
}

func TestCheckPackageDir_GenericConstructorWithEquality(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type Filter[D any] struct{ value D }

func NewFilter[D any](s string) (Filter[D], error) {
	return Filter[D]{}, nil
}
`,
		"types_test.go": `package testpkg

import "testing"

func TestFilter_Equality(t *testing.T) {
	// equality tests here
}
`,
	})

	violations, err := CheckPackageDir(dir, map[string]bool{})
	require.NoError(t, err)
	assert.Empty(t, violations)
}

// --- helpers ---

func parseSingleFunc(t *testing.T, src string) *ast.FuncDecl {
	t.Helper()
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, "test.go", src, 0)
	require.NoError(t, err)

	for _, decl := range f.Decls {
		if fn, ok := decl.(*ast.FuncDecl); ok {
			return fn
		}
	}
	return nil
}

func writeTestPackage(t *testing.T, files map[string]string) string {
	t.Helper()
	dir := t.TempDir()
	for name, content := range files {
		err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0644)
		require.NoError(t, err)
	}
	return dir
}
