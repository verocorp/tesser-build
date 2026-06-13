// Package analyzers is the single registry of the DDD value-object analyzers.
// cmd/ddd-vet composes All into its multichecker, and the meta-test iterates
// All to guarantee no analyzer ships without test coverage — so this slice is
// the one place an analyzer is enrolled.
package analyzers

import (
	"golang.org/x/tools/go/analysis"

	"github.com/chrisconley/go-ddd/passes/comparability"
	"github.com/chrisconley/go-ddd/passes/equalitytest"
	"github.com/chrisconley/go-ddd/passes/mustnew"
	"github.com/chrisconley/go-ddd/passes/primitiveaccessor"
	"github.com/chrisconley/go-ddd/passes/stringequality"
	"github.com/chrisconley/go-ddd/passes/stringer"
	"github.com/chrisconley/go-ddd/passes/voconstructor"
	"github.com/chrisconley/go-ddd/passes/vofields"
)

// All is every analyzer ddd-vet runs. Each is independently adoptable — a menu,
// not an all-or-nothing — but they share the value-object identification and
// .go-ddd.yaml exclude config in internal/voscan.
var All = []*analysis.Analyzer{
	mustnew.Analyzer,           // #4  paired MustNewX
	vofields.Analyzer,          // #1  no exported fields
	voconstructor.Analyzer,     // #2  validating constructor exists
	equalitytest.Analyzer,      // #8  Test*_Equality coverage
	stringequality.Analyzer,    // #6use  no .String() equality in tests
	stringer.Analyzer,          // #6  String() string
	primitiveaccessor.Analyzer, // #6a/6b  no primitive accessors
	comparability.Analyzer,     // #7  non-comparable VOs need Equal
}
