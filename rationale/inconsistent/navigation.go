// Package inconsistent is ARM 2 of the changeability comparison: a MIXTURE of
// bare primitives and inconsistently-built "value objects" — the realistic
// state of a codebase where "use value objects" was adopted without a STANDARD.
// Some concepts are left as primitives, some are wrapped, and the wrapped ones
// are wrapped different ways by different authors.
//
// The thesis this package exists to prove: arm 2 reopens the same silent sites
// the consistent value objects (../valueobject) close. Inconsistent VOs behave
// like NO VOs on the change-speed axis — so the dividend is bought by the
// standard, not by the pattern.
//
// Every non-conformance below is anchored to a real shape found in production
// history (see ../../docs/design-three-contender-changeability.md).
package inconsistent

import "fmt"

// --- Non-conformance 1: PARTIAL ADOPTION (the mixture) ---------------------
//
// Anchor: a slot that stayed a bare string across 43 call sites while its value
// object already existed (CreditAmount.CreditType, certus 3c4de62). Here, the
// descent RATE got wrapped but the ALTITUDE did not — one argument typed, one
// left primitive. The unprotected slot is the Mars Climate Orbiter hole,
// reopened: wrapping the other argument bought nothing.

// MetersPerSecond got wrapped.
type MetersPerSecond struct{ v float64 }

func NewMetersPerSecond(v float64) MetersPerSecond { return MetersPerSecond{v: v} }

// TimeToImpact wrapped the rate but left altitude a bare float64. A caller with
// a FEET altitude passes it straight into the metric slot; it compiles clean
// and returns a confidently wrong number — exactly like ../primitive, and
// exactly what ../valueobject makes a compile error.
func TimeToImpact(altitudeMeters float64, descentRate MetersPerSecond) float64 {
	return altitudeMeters / descentRate.v
}

// --- Non-conformance 2: SCATTERED VALIDATION (construction leaks out) ------
//
// Anchor: the nil-check asymmetry / "parent validates child" anti-pattern from
// the pricing primitive-obsession postmortem (2026-03-05) — validation copied
// across parent constructors instead of living in one type's constructor.
//
// Altitude is "a value object" by intent (a named type) but has NO single
// constructor. The "altitude must be >= 0" invariant is re-implemented at every
// builder. Each //ALT_INVARIANT below is one site a rule change must touch — and
// AltitudeForTelemetry shows the failure mode: a later author built one without
// the check, and nothing in the type forced them to.
type Altitude float64

func AltitudeForDescent(raw float64) (Altitude, error) {
	if raw < 0 { //ALT_INVARIANT
		return 0, fmt.Errorf("altitude must be >= 0")
	}
	return Altitude(raw), nil
}

func AltitudeForApproach(raw float64) (Altitude, error) {
	if raw < 0 { //ALT_INVARIANT
		return 0, fmt.Errorf("altitude must be >= 0")
	}
	return Altitude(raw), nil
}

func AltitudeForOrbit(raw float64) (Altitude, error) {
	if raw < 0 { //ALT_INVARIANT
		return 0, fmt.Errorf("altitude must be >= 0")
	}
	return Altitude(raw), nil
}

// AltitudeForTelemetry is a code path whose author didn't know about the
// invariant — there is no constructor that would have carried it. A negative
// altitude flows through silently. (No //ALT_INVARIANT marker: the rule is
// simply absent here, and the compiler never asked.)
func AltitudeForTelemetry(raw float64) Altitude {
	return Altitude(raw)
}
