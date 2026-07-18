// Package domain is the pure domain for the no-outward-representation decision
// (decision 3). It exposes only VALUE OBJECTS, never primitives, and imports
// NOTHING outward — no DTO package, no transport, no persistence. A domain object
// never emits its own outward representation; turning a domain object into a
// response DTO is the application service's Respond step, not a method here.
//
// A dependent that operates on a domain object (its value objects) is untouched
// when the outward representation (a public-interface DTO) is reshaped — the
// decoupled arm of decision 3. The types here follow the toolkit's own
// conventions (validating constructors + Must* helpers for value objects; the
// spec pattern for the aggregate) so tessercheck is clean on this package.
// See ../../SCORING.md.
package domain

import "fmt"

// ManeuverID is a value object: the identity of a maneuver. The domain exposes
// this, not a bare string.
type ManeuverID struct{ value string }

// NewManeuverID validates and constructs a ManeuverID.
func NewManeuverID(value string) (ManeuverID, error) {
	if value == "" {
		return ManeuverID{}, fmt.Errorf("maneuver id must not be empty")
	}
	return ManeuverID{value: value}, nil
}

// MustNewManeuverID panics on invalid input; use only with known-valid literals.
func MustNewManeuverID(value string) ManeuverID {
	id, err := NewManeuverID(value)
	if err != nil {
		panic(err)
	}
	return id
}

// String is the display form and the sole string accessor.
func (id ManeuverID) String() string { return id.value }

// Burn is a value object wrapping a burn duration in milliseconds. It is the
// domain's stable representation of the quantity that the OUTWARD telemetry format
// happens to render as whole seconds or milliseconds. Because callers in the
// domain hold this VO, an outward-format change never reaches them.
type Burn struct{ millis int64 }

// NewBurn validates and constructs a Burn; a burn duration is never negative.
func NewBurn(millis int64) (Burn, error) {
	if millis < 0 {
		return Burn{}, fmt.Errorf("burn duration must not be negative: %d", millis)
	}
	return Burn{millis: millis}, nil
}

// MustNewBurn panics on invalid input; use only with known-valid literals.
func MustNewBurn(millis int64) Burn {
	b, err := NewBurn(millis)
	if err != nil {
		panic(err)
	}
	return b
}

// Millis and Seconds surface the value for a mapper to read. The value object is
// the boundary at which a primitive may surface, not the aggregate; neither is a
// To* representation-leak accessor.
func (b Burn) Millis() int64  { return b.millis }
func (b Burn) Seconds() int64 { return b.millis / 1000 }

// String is the display form.
func (b Burn) String() string { return fmt.Sprintf("%dms", b.millis) }

// Thrust is a value object wrapping thrust in micro-newtons.
type Thrust struct{ microN int64 }

// NewThrust validates and constructs a Thrust; thrust is never negative here.
func NewThrust(microN int64) (Thrust, error) {
	if microN < 0 {
		return Thrust{}, fmt.Errorf("thrust must not be negative: %d", microN)
	}
	return Thrust{microN: microN}, nil
}

// MustNewThrust panics on invalid input; use only with known-valid literals.
func MustNewThrust(microN int64) Thrust {
	t, err := NewThrust(microN)
	if err != nil {
		panic(err)
	}
	return t
}

// MicroNewtons surfaces the value for a mapper to read.
func (t Thrust) MicroNewtons() int64 { return t.microN }

// String is the display form.
func (t Thrust) String() string { return fmt.Sprintf("%duN", t.microN) }

// ManeuverSpec carries construction data across the layer boundary: primitive
// leaves only, never assembled value objects. The application service builds this
// from a request DTO (Convert) and hands it to NewManeuver (Delegate).
type ManeuverSpec struct {
	ManeuverID   string
	BurnMillis   int64
	ThrustMicroN int64
}

// Maneuver is the domain entity: identity is by ManeuverID, and every accessor
// returns a value object — no primitive and no outward representation crosses this
// surface.
type Maneuver struct {
	id     ManeuverID
	burn   Burn
	thrust Thrust
}

// NewManeuver validates spec and constructs a Maneuver, building each child value
// object through its own constructor and adding error context. Entities carry
// real construction risk, so there is no Must* helper — the error is handled.
func NewManeuver(spec ManeuverSpec) (Maneuver, error) {
	id, err := NewManeuverID(spec.ManeuverID)
	if err != nil {
		return Maneuver{}, fmt.Errorf("invalid maneuver id: %w", err)
	}
	burn, err := NewBurn(spec.BurnMillis)
	if err != nil {
		return Maneuver{}, fmt.Errorf("invalid burn: %w", err)
	}
	thrust, err := NewThrust(spec.ThrustMicroN)
	if err != nil {
		return Maneuver{}, fmt.Errorf("invalid thrust: %w", err)
	}
	return Maneuver{id: id, burn: burn, thrust: thrust}, nil
}

func (m Maneuver) ID() ManeuverID { return m.id }
func (m Maneuver) Burn() Burn     { return m.burn }
func (m Maneuver) Thrust() Thrust { return m.thrust }

// Equal is identity equality: two maneuvers are the same when their identities
// match, regardless of attributes (the entity, not value-object, rule).
func (m Maneuver) Equal(other Maneuver) bool { return m.id == other.id }
