// The SUBSTITUTION axis (change C2 in SCORING.md) of the public-interface
// decision. The backend-migration change (contrast_test.go) is tied by the
// red-team facade with less ceremony — a facade survives a backend swap too. The
// interface earns its place here instead: a dependent that receives orders.Client
// swaps in a fake with ZERO edits (testable in isolation, O(1)); a facade
// dependent bound to the global has no seam, so making it testable is a forced
// edit (O(N) across N such dependents). See adversary_provenance.md.
package anchor_test

import (
	"context"
	"os/exec"
	"testing"

	"github.com/verocorp/tesser-build/rationale/changeability/anchor/decoupled/consumer00"
	"github.com/verocorp/tesser-build/rationale/changeability/anchor/testfake"
)

// The interface WIN: a decoupled dependent is unit-testable against a fake with
// no change to its source — it already accepts orders.Client.
func TestInterfaceDependent_SubstitutesForFree(t *testing.T) {
	if err := consumer00.Use(context.Background(), testfake.New()); err != nil {
		t.Fatalf("decoupled consumer did not run against the fake client: %v", err)
	}
	// Zero source edits to the consumer were needed to inject the substitute:
	// that is the O(1) substitutability the public interface buys.
}

// The facade COST: to make the facade dependent testable you must inject a
// substitute, but the facade exposes no seam — subst_bug.go names an injection
// API that does not exist, so the package fails to build under -tags subst. The
// compile error is the forced edit the substitution axis exacts on the facade.
func TestFacadeDependent_CannotSubstituteWithoutEdit(t *testing.T) {
	cmd := exec.Command("go", "build", "-tags", "subst", "./redteam/facadeconsumer")
	out, err := cmd.CombinedOutput()
	if err == nil {
		t.Fatalf("expected the facade dependent to fail the substitution build (no injection seam), but it built:\n%s", out)
	}
	// Win verified: the interface dependent substitutes at 0 edits; the facade
	// dependent cannot be made testable without editing the boundary.
}
