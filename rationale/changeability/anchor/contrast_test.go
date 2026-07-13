// Verifies the DECOUPLED half of the public-interface changeability contrast:
// dependents on orders.Client are forced to change 0 times by the backend A->B
// migration, at any N. Per ../SCORING.md the count is taken PER PACKAGE (a
// whole-module `go build ./...` stops early and undercounts).
//
// This is the O(1) side plus the pre-swap positive control. The coupled arm and
// the full 0-vs-N contrast at matched N land with the adversary step (T3/T4);
// green here means "the decoupled scaffold survives the swap", not "the anchor
// is proven".
package anchor_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"testing"
)

// decoupledPkgs returns the relative build paths of the generated decoupled
// consumer packages, sorted, so a subset [:k] is a stable N=k sample.
func decoupledPkgs(t *testing.T) []string {
	t.Helper()
	entries, err := os.ReadDir("decoupled")
	if err != nil {
		t.Fatalf("read decoupled/: %v (run `go generate ./rationale/changeability/anchor`)", err)
	}
	var pkgs []string
	for _, e := range entries {
		if e.IsDir() {
			pkgs = append(pkgs, "./"+filepath.Join("decoupled", e.Name()))
		}
	}
	sort.Strings(pkgs)
	return pkgs
}

// buildsClean reports whether `go build [-tags swap] pkg` succeeds — one
// per-package build, the unit SCORING.md counts.
func buildsClean(t *testing.T, pkg string, swap bool) bool {
	t.Helper()
	args := []string{"build"}
	if swap {
		args = append(args, "-tags", "swap")
	}
	args = append(args, pkg)
	out, err := exec.Command("go", args...).CombinedOutput()
	if err != nil {
		t.Logf("build %v failed:\n%s", args, out)
	}
	return err == nil
}

// forcedEdits counts, per package, how many of the first n dependents fail to
// build after the migration — the forced-edit count at N=n.
func forcedEdits(t *testing.T, pkgs []string, n int) int {
	t.Helper()
	forced := 0
	for _, p := range pkgs[:n] {
		if !buildsClean(t, p, true /*swap*/) {
			forced++
		}
	}
	return forced
}

func TestDecoupledArm_SurvivesBackendSwap(t *testing.T) {
	pkgs := decoupledPkgs(t)
	if len(pkgs) < 16 {
		t.Fatalf("want >=16 decoupled consumers, got %d", len(pkgs))
	}

	// Positive control: every dependent builds BEFORE the migration. Without
	// this, a dependent that never compiled would "pass" the swap assertion.
	for _, p := range pkgs {
		if !buildsClean(t, p, false /*pre-swap*/) {
			t.Fatalf("pre-swap baseline build failed for %s", p)
		}
	}

	// O(1): the decoupled arm's forced-edit count is 0 at N=8 and N=16 — flat in
	// N, because no dependent names anything the migration removed.
	for _, n := range []int{8, 16} {
		if got := forcedEdits(t, pkgs, n); got != 0 {
			t.Fatalf("decoupled arm forced %d edits at N=%d under the backend swap, want 0", got, n)
		}
	}
}
