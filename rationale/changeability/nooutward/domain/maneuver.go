// Package domain is the pure domain for the no-outward-representation decision
// (decision 3). It exposes only VALUE OBJECTS, never primitives, and imports
// NOTHING outward — no DTO package, no transport, no persistence. A domain object
// never emits its own outward representation; turning a domain object into a
// response DTO is the application service's Respond step, not a method here.
//
// A dependent that operates on a domain object (its value objects) is untouched
// when the outward representation (a public-interface DTO) is reshaped — the
// decoupled arm of decision 3. See ../../SCORING.md.
package domain

// ManeuverID is a value object: the identity of a maneuver. The domain exposes
// this, not a bare string.
type ManeuverID struct{ v string }

func NewManeuverID(v string) ManeuverID { return ManeuverID{v: v} }
func (id ManeuverID) String() string    { return id.v }

// Burn is a value object wrapping a burn duration in milliseconds. It is the
// domain's stable representation of the quantity that the OUTWARD telemetry format
// happens to render as whole seconds (v1) or milliseconds (v2). Because callers in
// the domain hold this VO, an outward-format change never reaches them.
type Burn struct{ millis int64 }

func NewBurn(millis int64) Burn { return Burn{millis: millis} }

// Millis and Seconds expose the leaf primitive of the VO — the value object is
// the boundary at which a primitive may surface, not the aggregate.
func (b Burn) Millis() int64  { return b.millis }
func (b Burn) Seconds() int64 { return b.millis / 1000 }

// Thrust is a value object wrapping thrust in micro-newtons.
type Thrust struct{ microN int64 }

func NewThrust(microN int64) Thrust  { return Thrust{microN: microN} }
func (t Thrust) MicroNewtons() int64 { return t.microN }

// Maneuver is the domain aggregate. Every accessor returns a value object; no
// primitive and no outward representation crosses this surface.
type Maneuver struct {
	id     ManeuverID
	burn   Burn
	thrust Thrust
}

// NewManeuver is the single construction path, built from value objects.
func NewManeuver(id ManeuverID, burn Burn, thrust Thrust) Maneuver {
	return Maneuver{id: id, burn: burn, thrust: thrust}
}

func (m Maneuver) ID() ManeuverID { return m.id }
func (m Maneuver) Burn() Burn     { return m.burn }
func (m Maneuver) Thrust() Thrust { return m.thrust }
