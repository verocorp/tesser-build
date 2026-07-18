// Package changeability_test verifies, with executable tests, that typed value
// objects turn three classes of silent bug into either a compile error or a
// rejected construction. Each risk class has a pair of tests: one proving the
// bug is ADMISSIBLE under the primitive representation, one proving it is
// CAUGHT under the value object. The wins are asserted, not narrated.
//
// Domain: spaceflight navigation — the Mars Climate Orbiter unit-confusion
// catastrophe is the anchor.
//
// Run: go test ./...
package changeability_test

import (
	"os/exec"
	"strings"
	"testing"

	"github.com/verocorp/tesser-build/rationale/primitive"
	"github.com/verocorp/tesser-build/rationale/valueobject"
)

// --- Risk class 1: type confusion (Mars Climate Orbiter) -------------------

// Primitive: a Feet value used where meters are expected still compiles and
// returns a confidently wrong result.
func TestTypeConfusion_PrimitiveAdmitsWrongUnit(t *testing.T) {
	// The caller has an altitude of 10000 FEET (= 3048 m) but the function
	// wants METERS. Both are float64, so nothing complains; the descent time
	// comes out ~3.3x too large. Mars Climate Orbiter, in one line.
	altitudeInFeet := 10000.0
	descentRate := 50.0 // m/s
	got := primitive.TimeToImpact(altitudeInFeet, descentRate)
	if got != 200.0 {
		t.Fatalf("setup error, got %v", got)
	}
	// 200s looks fine and is wrong — the real altitude is 3048m -> 60.96s.
}

// Value object: the SAME wrong-unit call fails to compile. swap_bug.go holds a
// Feet-where-Meters call behind the changeability_bug build tag.
func TestTypeConfusion_ValueObjectRejectsWrongUnit(t *testing.T) {
	cmd := exec.Command("go", "build", "-tags", "changeability_bug", "./valueobject")
	out, err := cmd.CombinedOutput()
	if err == nil {
		t.Fatalf("expected the Feet-where-Meters call to fail compilation, but it built:\n%s", out)
	}
	if !strings.Contains(string(out), "cannot use") {
		t.Fatalf("build failed, but not with the expected type error:\n%s", out)
	}
	// Win verified: the unit mismatch the primitive admitted silently is a
	// compile error here.
}

// Sanity: the correct typed call compiles and runs, and feet must be converted.
func TestTypeConfusion_ValueObjectCorrectCallWorks(t *testing.T) {
	altitude := valueobject.NewFeet(10000).ToMeters() // explicit conversion
	got := valueobject.TimeToImpact(altitude, valueobject.NewMetersPerSecond(50))
	if got < 60.9 || got > 61.0 { // 3048m / 50 = 60.96s
		t.Fatalf("got %v, want ~60.96", got)
	}
}

// --- Risk class 2: equality (scale collision) ------------------------------

// Primitive: == reports the same temperature in two scales as unequal.
func TestEquality_PrimitiveIsWrong(t *testing.T) {
	if primitive.TempEqual(0.0 /*°C*/, 273.15 /*K*/) {
		t.Fatal("setup error: expected primitive == to report 0°C and 273.15K as unequal")
	}
	// Demonstrated: same physical temperature, different number, == says "no".
}

// Value object: Equal() compares physical value, so the scales agree.
func TestEquality_ValueObjectIsRight(t *testing.T) {
	c, _ := valueobject.FromCelsius(0)
	k, _ := valueobject.FromKelvin(273.15)
	if !c.Equal(k) {
		t.Fatal("expected 0°C and 273.15K to be equal under the value object")
	}
}

// --- Risk class 3: validation (absolute zero) ------------------------------

// Primitive: a temperature below absolute zero flows through unchecked.
func TestValidation_PrimitiveAdmitsBadInput(t *testing.T) {
	got := primitive.AsKelvin(-5) // physically impossible
	if got != -5 {
		t.Fatalf("setup error, got %v", got)
	}
	// -5K flowed through silently.
}

// Value object: the impossible temperature is rejected at construction.
func TestValidation_ValueObjectRejectsBadInput(t *testing.T) {
	if _, err := valueobject.FromKelvin(-5); err == nil {
		t.Fatal("expected a sub-absolute-zero temperature to be rejected")
	}
}
