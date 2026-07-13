// The decision-3 changeability contrast on an outward-representation migration
// (-tags repv2, the public response DTO's BurnSeconds -> DurationMillis). Per
// ../SCORING.md the proof is the DELTA between arms at matched N, taken with
// PER-PACKAGE builds (a whole-module `go build ./...` stops early and undercounts):
//
//	at N = 8:   decoupled forced-edits = 0   |   coupled forced-edits = 8
//	at N = 16:  decoupled forced-edits = 0   |   coupled forced-edits = 16
//
// The decoupled arm (operates on the domain object's VALUE OBJECTS) flat at 0
// across N is O(1); the coupled arm (reaches the DOMAIN-EMITTED DTO's raw field)
// tracking N is O(dependents). The single correct mapping site is the application
// service's Respond (package app), which a migration forces once — that O(1) is
// what the domain-emitting violation trades for O(N).
//
// There is no import-cycle guard here: a dumb DTO imports nothing, so the domain
// importing it would never be a cycle. The rule is a convention the compiler does
// not enforce; the fan-out below is what justifies it.
package nooutward_test

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
		t.Fatalf("read %s: %v (run `go generate ./rationale/changeability/nooutward`)", relDir, err)
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

// buildsClean reports whether `go build [-tags repv2] pkg` succeeds — one
// per-package build, the unit SCORING.md counts.
func buildsClean(t *testing.T, pkg string, migrated bool) bool {
	t.Helper()
	args := []string{"build"}
	if migrated {
		args = append(args, "-tags", "repv2")
	}
	args = append(args, pkg)
	out, err := exec.Command("go", args...).CombinedOutput()
	if err != nil {
		t.Logf("build %v failed:\n%s", args, out)
	}
	return err == nil
}

// forcedEdits counts, per package, how many of the first n dependents are FORCED
// to change (fail to build) after the migration — the forced-edit count at N=n.
func forcedEdits(t *testing.T, pkgs []string, n int) int {
	t.Helper()
	forced := 0
	for _, p := range pkgs[:n] {
		if !buildsClean(t, p, true /*migrated*/) {
			forced++
		}
	}
	return forced
}

// assertBaseline is the mandatory pre-migration positive control: every dependent
// builds BEFORE the migration, so a post-migration failure is meaningful.
func assertBaseline(t *testing.T, pkgs []string, arm string) {
	t.Helper()
	for _, p := range pkgs {
		if !buildsClean(t, p, false /*pre-migration*/) {
			t.Fatalf("pre-migration baseline build failed for %s (%s arm)", p, arm)
		}
	}
}

func TestDecoupledArm_SurvivesRepMigration(t *testing.T) {
	pkgs := armPkgs(t, "decoupled")
	if len(pkgs) < 16 {
		t.Fatalf("want >=16 decoupled consumers, got %d", len(pkgs))
	}
	assertBaseline(t, pkgs, "decoupled")
	for _, n := range []int{8, 16} {
		if got := forcedEdits(t, pkgs, n); got != 0 {
			t.Fatalf("decoupled arm forced %d edits at N=%d under the rep migration, want 0", got, n)
		}
	}
}

// The contrast: at matched N the decoupled arm stays flat at 0 while the coupled
// arm tracks N. The delta — not the coupled count in isolation — is the
// O(1)-vs-O(dependents) proof.
func TestContrast_DecoupledFlat_CoupledTracksN(t *testing.T) {
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
