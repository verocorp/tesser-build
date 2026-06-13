// Arm 2 of the changeability comparison. Each test proves the inconsistent
// arm (a mixture of primitives and non-conforming value objects) reopens a
// silent site the consistent value object (arm 3, ../valueobject) closes —
// the executable form of "inconsistent VOs ≈ no VOs on the change-speed axis."
//
// Three contenders, same domain:
//
//	../primitive    arm 1 — bare primitives
//	./inconsistent  arm 2 — mixture of primitives + inconsistent VOs  (THIS)
//	../valueobject  arm 3 — consistent value objects
package changeability_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chrisconley/go-ddd/rationale/inconsistent"
	"github.com/chrisconley/go-ddd/rationale/valueobject"
)

// --- Non-conformance 1: partial adoption reopens type confusion ------------

// The rate got wrapped; the altitude did not. A feet altitude passes straight
// into the bare-float64 slot, compiles clean, and returns a wrong number — the
// Mars bug the value-object arm makes impossible, reopened through the one slot
// that stayed primitive. Wrapping SOME concepts bought nothing.
func TestPartialAdoption_InconsistentAdmitsWrongUnit(t *testing.T) {
	altitudeInFeet := 10000.0 // = 3048 m
	got := inconsistent.TimeToImpact(altitudeInFeet, inconsistent.NewMetersPerSecond(50))
	if got != 200.0 {
		t.Fatalf("setup error, got %v", got)
	}
	// 200s looks fine and is wrong — the real altitude is 3048m -> 60.96s.
}

// --- Non-conformance 2: scattered validation -------------------------------

// 2a: no single construction path, so the builder that forgot the rule admits a
// bad value silently — while the consistent VO rejects it at its one gate.
func TestScatteredValidation_InconsistentAdmitsBadValue(t *testing.T) {
	bad := inconsistent.AltitudeForTelemetry(-100) // the builder that forgot the check
	if bad >= 0 {
		t.Fatalf("setup error, got %v", bad)
	}
	// The negative altitude flowed through. The consistent VO has one gate and
	// rejects it:
	if _, err := valueobject.NewAltitude(-100); err == nil {
		t.Fatal("consistent VO should reject a negative altitude at construction")
	}
}

// 2b: the changeability cost. The invariant lives in N places in arm 2 but ONE
// place in arm 3, so changing the rule is an N-site edit (miss one -> silent)
// vs a one-site edit. We count the marked invariant sites in each package's
// source — this is the silent-site thesis at fixture scale; case-study.md
// carries the real magnitude (a slot left raw across 43 call sites).
func TestScatteredValidation_RuleLivesInManyPlaces(t *testing.T) {
	const marker = "//ALT_INVARIANT"
	inconsistentSites := countMarker(t, "inconsistent", marker)
	consistentSites := countMarker(t, "valueobject", marker)

	if consistentSites != 1 {
		t.Fatalf("consistent VO should hold the altitude invariant in exactly 1 site, got %d", consistentSites)
	}
	if inconsistentSites <= consistentSites {
		t.Fatalf("inconsistent arm should duplicate the invariant across more sites than the consistent VO; got inconsistent=%d consistent=%d", inconsistentSites, consistentSites)
	}
	// inconsistentSites edits to change the rule, any one missable; consistent = 1.
}

// --- Non-conformance 3: equality via String() (what checkstring forbids) ---

// Same physical temperature in two scales, reported unequal because equality
// compares the display form. The bare-float == bug in a value object's clothes;
// the consistent VO's Equal() (TestEquality_ValueObjectIsRight) gets it right.
func TestEqualityByString_InconsistentIsWrong(t *testing.T) {
	c := inconsistent.NewTempCelsius(0)
	k := inconsistent.NewTempKelvin(273.15)
	if c.EqualByString(k) {
		t.Fatal("expected display-string equality to (wrongly) report 0°C and 273.15K as unequal")
	}
}

// countMarker counts occurrences of a marker comment across a package's .go
// source. Tests run with CWD at the rationale/ package dir, so pkgDir is a
// direct subdirectory (e.g. "inconsistent", "valueobject").
func countMarker(t *testing.T, pkgDir, marker string) int {
	t.Helper()
	files, err := filepath.Glob(filepath.Join(pkgDir, "*.go"))
	if err != nil {
		t.Fatalf("glob %s: %v", pkgDir, err)
	}
	n := 0
	for _, f := range files {
		b, err := os.ReadFile(f)
		if err != nil {
			t.Fatalf("read %s: %v", f, err)
		}
		n += strings.Count(string(b), marker)
	}
	return n
}
