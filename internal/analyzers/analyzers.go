// Package analyzers is the single registry of the DDD value-object analyzers.
// cmd/tessercheck composes All into its multichecker, and the meta-test iterates
// All to guarantee no analyzer ships without test coverage — so this slice is
// the one place an analyzer is enrolled.
package analyzers

import (
	"golang.org/x/tools/go/analysis"

	"github.com/verocorp/tesser-build/passes/comparability"
	"github.com/verocorp/tesser-build/passes/mustnew"
	"github.com/verocorp/tesser-build/passes/primitiveaccessor"
	"github.com/verocorp/tesser-build/passes/stringequality"
	"github.com/verocorp/tesser-build/passes/stringer"
	"github.com/verocorp/tesser-build/passes/voconstructor"
	"github.com/verocorp/tesser-build/passes/vofields"
)

// All is every analyzer tessercheck runs. Each is independently adoptable — a menu,
// not an all-or-nothing — but they share the value-object identification and
// .tesser-build.yaml exclude config in internal/voscan.
var All = []*analysis.Analyzer{
	mustnew.Analyzer,           // #4  paired MustNewX
	vofields.Analyzer,          // #1  no exported fields
	voconstructor.Analyzer,     // #2  validating constructor exists
	stringequality.Analyzer,    // #6use  no .String() equality in tests
	stringer.Analyzer,          // #6  String() string
	primitiveaccessor.Analyzer, // #6a/6b  no primitive accessors
	comparability.Analyzer,     // #7  == unavailable/unsafe VOs need Equal
}

// equalitytest (#8, Test*_Equality existence) was built (commit c571e38) then
// parked: it is only a name-existence tripwire, and porting it to go/analysis
// hit the source<->test package-variant problem. comparability (#7, widened to
// pointer/interface fields) covers the structural equality hazard instead. See
// docs/design-ddd-vet-migration.md "Parked" for the revisit conditions.
