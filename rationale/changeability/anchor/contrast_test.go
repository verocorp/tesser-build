// The public-interface changeability contrast on change C1 (backend migration).
// Per ../SCORING.md the proof is the DELTA between arms at matched N, taken with
// PER-PACKAGE builds (a whole-module `go build ./...` stops early and undercounts):
//
//	at N = 8:   decoupled forced-edits = 0   |   coupled forced-edits = 8
//	at N = 16:  decoupled forced-edits = 0   |   coupled forced-edits = 16
//
// The decoupled arm flat at 0 across N is O(1); the coupled arm tracking N is
// O(dependents). C1 alone is TIED by the red-team facade with less ceremony —
// substitution_test.go carries C2, where the interface actually earns its place.
package anchor_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"testing"
)

// armPkgs returns the relative build paths of the generated consumer packages
// under relDir, sorted, so a prefix [:k] is a stable N=k sample.
func armPkgs(t *testing.T, relDir string) []string {
	t.Helper()
	entries, err := os.ReadDir(relDir)
	if err != nil {
		t.Fatalf("read %s: %v (run `go generate ./rationale/changeability/anchor`)", relDir, err)
	}
	var pkgs []string
	for _, e := range entries {
		if e.IsDir() {
			pkgs = append(pkgs, "./"+filepath.Join(relDir, e.Name()))
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

// forcedEdits counts, per package, how many of the first n dependents are FORCED
// to change (fail to build) after the migration C1 — the forced-edit count at N=n.
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

// assertBaseline is the mandatory pre-swap positive control: every dependent
// builds BEFORE the migration, so a post-swap failure is meaningful.
func assertBaseline(t *testing.T, pkgs []string, arm string) {
	t.Helper()
	for _, p := range pkgs {
		if !buildsClean(t, p, false /*pre-swap*/) {
			t.Fatalf("pre-swap baseline build failed for %s (%s arm)", p, arm)
		}
	}
}

func TestDecoupledArm_SurvivesBackendSwap(t *testing.T) {
	pkgs := armPkgs(t, "decoupled")
	if len(pkgs) < 16 {
		t.Fatalf("want >=16 decoupled consumers, got %d", len(pkgs))
	}
	assertBaseline(t, pkgs, "decoupled")
	for _, n := range []int{8, 16} {
		if got := forcedEdits(t, pkgs, n); got != 0 {
			t.Fatalf("decoupled arm forced %d edits at N=%d under the backend swap, want 0", got, n)
		}
	}
}

// The C1 contrast: at matched N the decoupled arm stays flat at 0 while the
// coupled arm tracks N. The delta — not the coupled count in isolation — is the
// O(1)-vs-O(dependents) proof.
func TestContrast_C1_DecoupledFlat_CoupledTracksN(t *testing.T) {
	decoupled := armPkgs(t, "decoupled")
	coupled := armPkgs(t, filepath.Join("coupled", "fanout"))
	if len(decoupled) < 16 || len(coupled) < 16 {
		t.Fatalf("want >=16 in each arm, got decoupled=%d coupled=%d", len(decoupled), len(coupled))
	}
	assertBaseline(t, coupled, "coupled")

	for _, n := range []int{8, 16} {
		dec := forcedEdits(t, decoupled, n)
		coup := forcedEdits(t, coupled, n)
		if dec != 0 {
			t.Errorf("N=%d: decoupled forced=%d, want 0 (O(1))", n, dec)
		}
		if coup != n {
			t.Errorf("N=%d: coupled forced=%d, want %d (O(dependents))", n, coup, n)
		}
		if coup <= dec {
			t.Errorf("N=%d: no contrast — coupled(%d) must exceed decoupled(%d)", n, coup, dec)
		}
	}
}
