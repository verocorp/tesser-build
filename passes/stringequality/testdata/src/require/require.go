// Package require is a local stand-in for testify's require (see the assert
// stub for why). Only the call shapes matter — the analyzer is a syntactic scan.
package require

func Equal(t interface{}, args ...interface{}) bool { return true }
