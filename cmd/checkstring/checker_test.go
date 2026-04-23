package main

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestIsStringAccessorTest(t *testing.T) {
	tests := []struct {
		name string
		fn   string
		want bool
	}{
		{"accessor test", "TestCustomerID_String", true},
		{"accessor test with subtype", "TestMoneyAmount_String", true},
		{"equality test", "TestCustomerID_Equality", false},
		{"other test", "TestCustomerID_NewCustomerID", false},
		{"helper function", "helperString", false},
		{"not a test", "String", false},
		{"Test prefix but no String suffix", "TestFoo_ToString", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, isStringAccessorTest(tt.fn))
		})
	}
}

func TestCheckPackageDir_NoStringCalls(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type CustomerID struct{ value string }
`,
		"types_test.go": `package testpkg

import "testing"

func TestCustomerID_Equality(t *testing.T) {
	// no .String() here
}
`,
	})

	violations, err := CheckPackageDir(dir)
	require.NoError(t, err)
	assert.Empty(t, violations)
}

func TestCheckPackageDir_StringInAccessorTest(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types_test.go": `package testpkg

import "testing"

func TestCustomerID_String(t *testing.T) {
	var id CustomerID
	_ = id.String()
}
`,
	})

	violations, err := CheckPackageDir(dir)
	require.NoError(t, err)
	assert.Empty(t, violations)
}

func TestCheckPackageDir_StringOutsideAccessorTest(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types_test.go": `package testpkg

import "testing"

func TestCustomerID_NewCustomerID(t *testing.T) {
	var id CustomerID
	_ = id.String()
}
`,
	})

	violations, err := CheckPackageDir(dir)
	require.NoError(t, err)
	require.Len(t, violations, 1)
	assert.Equal(t, "TestCustomerID_NewCustomerID", violations[0].FuncName)
}

func TestCheckPackageDir_MultipleViolations(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types_test.go": `package testpkg

import "testing"

func TestFoo(t *testing.T) {
	var f Foo
	_ = f.String()
}

func TestBar(t *testing.T) {
	var b Bar
	_ = b.String()
}
`,
	})

	violations, err := CheckPackageDir(dir)
	require.NoError(t, err)
	require.Len(t, violations, 2)

	funcNames := map[string]bool{}
	for _, v := range violations {
		funcNames[v.FuncName] = true
	}
	assert.True(t, funcNames["TestFoo"])
	assert.True(t, funcNames["TestBar"])
}

func TestCheckPackageDir_MixedAllowedAndViolation(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types_test.go": `package testpkg

import "testing"

func TestFoo_String(t *testing.T) {
	var f Foo
	_ = f.String()
}

func TestFoo_NewFoo(t *testing.T) {
	var f Foo
	_ = f.String()
}
`,
	})

	violations, err := CheckPackageDir(dir)
	require.NoError(t, err)
	require.Len(t, violations, 1)
	assert.Equal(t, "TestFoo_NewFoo", violations[0].FuncName)
}

func TestCheckPackageDir_MultipleCallsInOneFunc(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types_test.go": `package testpkg

import "testing"

func TestFoo(t *testing.T) {
	var f Foo
	_ = f.String()
	var b Bar
	_ = b.String()
}
`,
	})

	violations, err := CheckPackageDir(dir)
	require.NoError(t, err)
	require.Len(t, violations, 2)
	// Both should report the same enclosing function.
	for _, v := range violations {
		assert.Equal(t, "TestFoo", v.FuncName)
	}
}

func TestCheckPackageDir_ExternalTestPackage(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types_test.go": `package testpkg_test

import "testing"

func TestFoo(t *testing.T) {
	var f Foo
	_ = f.String()
}
`,
	})

	violations, err := CheckPackageDir(dir)
	require.NoError(t, err)
	require.Len(t, violations, 1)
	assert.Equal(t, "TestFoo", violations[0].FuncName)
}

func TestCheckPackageDir_NoTestFiles(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types.go": `package testpkg

type Foo struct{}
`,
	})

	violations, err := CheckPackageDir(dir)
	require.NoError(t, err)
	assert.Empty(t, violations)
}

func TestCheckPackageDir_IgnoresToStringMethod(t *testing.T) {
	dir := writeTestPackage(t, map[string]string{
		"types_test.go": `package testpkg

import "testing"

func TestFoo(t *testing.T) {
	var f Foo
	_ = f.ToString()
}
`,
	})

	violations, err := CheckPackageDir(dir)
	require.NoError(t, err)
	assert.Empty(t, violations)
}

// --- helpers ---

func writeTestPackage(t *testing.T, files map[string]string) string {
	t.Helper()
	dir := t.TempDir()
	for name, content := range files {
		err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0644)
		require.NoError(t, err)
	}
	return dir
}
