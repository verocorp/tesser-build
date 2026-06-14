package valueobject

import "fmt"

// Meters and Feet are distinct length types; the compiler will not let one be
// used where the other is expected. Crossing unit systems is possible only
// through an explicit, named conversion — the exact guardrail the Mars Climate
// Orbiter navigation code lacked.
type Meters struct{ v float64 }

func NewMeters(v float64) Meters { return Meters{v: v} }
func (m Meters) Float() float64  { return m.v }

type Feet struct{ v float64 }

func NewFeet(v float64) Feet  { return Feet{v: v} }
func (f Feet) Float() float64 { return f.v }

// ToMeters is the only sanctioned way to cross from imperial to metric.
func (f Feet) ToMeters() Meters { return Meters{v: f.v * 0.3048} }

// MetersPerSecond is a distinct rate type — not interchangeable with a Meters
// distance, so altitude and descent rate cannot be swapped.
type MetersPerSecond struct{ v float64 }

func NewMetersPerSecond(v float64) MetersPerSecond { return MetersPerSecond{v: v} }
func (r MetersPerSecond) Float() float64           { return r.v }

// TimeToImpact takes typed quantities. Passing Feet where Meters is expected,
// or swapping altitude and descent rate, does not compile. See swap_bug.go.
func TimeToImpact(altitude Meters, descentRate MetersPerSecond) float64 {
	return altitude.v / descentRate.v
}

// Altitude is a consistent value object: the "altitude must be >= 0" invariant
// lives in exactly ONE place — the constructor. Changing the rule is a one-site
// edit, and there is no way to build an Altitude that skips it. Compare
// ../inconsistent, where the same rule is copied across every builder, so a
// rule change is an N-site edit and a missed site silently admits a bad value.
type Altitude struct{ meters float64 }

// NewAltitude is the single construction path; the invariant lives here and
// nowhere else.
func NewAltitude(meters float64) (Altitude, error) {
	if meters < 0 { //ALT_INVARIANT
		return Altitude{}, fmt.Errorf("altitude %.1fm is below ground", meters)
	}
	return Altitude{meters: meters}, nil
}

func (a Altitude) Meters() float64 { return a.meters }

// MustNewAltitude is the single canonical panic-on-error helper. Tests and
// known-valid literals use it. Because exactly ONE is provided, no author has to
// hand-roll their own — compare ../inconsistent, where three divergent "must"
// helpers appeared because none was supplied. The mustnew analyzer mandates this pairing.
func MustNewAltitude(meters float64) Altitude {
	a, err := NewAltitude(meters)
	if err != nil {
		panic(err)
	}
	return a
}
