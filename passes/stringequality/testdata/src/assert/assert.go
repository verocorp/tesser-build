// Package assert is a local stand-in for testify's assert, so the testdata can
// exercise the assert.Equal(...) recognition without a module-mode dependency
// (analysistest runs in GOPATH mode). Only the call shapes matter — the analyzer
// is a syntactic scan.
package assert

func Equal(t interface{}, args ...interface{}) bool    { return true }
func Equalf(t interface{}, args ...interface{}) bool   { return true }
func NotEqual(t interface{}, args ...interface{}) bool { return true }
