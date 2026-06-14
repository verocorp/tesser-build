package inconsistent

import "fmt"

// --- Non-conformance 4: MUST-HELPER REIMPLEMENTATION ----------------------
//
// Anchor: nine ad-hoc `must*` helpers spawned across five test files, each
// reimplementing the same panic-on-error construction independently (certus
// e7a470c — the provenance for the mustnew rule). Without ONE provided
// `MustNew` helper, every author rolls their own — and they don't even agree on
// what "must" means when the input is bad. The three below each claim to be the
// construct-or-die helper for Altitude; they behave three different ways on the
// same negative value. (This is reimplementation, not type drift: the cost is a
// missing shared utility, so callers diverge.)

// MustAltitude panics on a bad value — one author's reading of "must."
func MustAltitude(raw float64) Altitude {
	if raw < 0 {
		panic(fmt.Sprintf("altitude must be >= 0, got %v", raw))
	}
	return Altitude(raw)
}

// ForceAltitude ignores the invariant — to this author "must" only meant "no
// error return." A bad value flows through silently.
func ForceAltitude(raw float64) Altitude {
	return Altitude(raw)
}

// AltitudeOrZero clamps instead of panicking — a third reading of "must."
func AltitudeOrZero(raw float64) Altitude {
	if raw < 0 {
		return 0
	}
	return Altitude(raw)
}
