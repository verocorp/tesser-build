// Package emit is the COUPLED (violation) domain for decision 3: a domain object
// that EMITS its own outward representation. ToResponse() returns pub.ManeuverResponse
// — the Respond step that belongs to the application service, done on the domain
// object instead — so this "domain" imports the public DTO package and invites
// dependents to obtain the DTO through the domain and read its wire fields.
//
// A dependent that reaches m.ToResponse().BurnSeconds is bound to the outward
// format and breaks when it migrates — the coupled arm of decision 3's fan-out.
// The DTO assembly is split by build tag (respond_v1.go / respond_v2.go) so this
// package itself compiles under both states; only the DEPENDENTS naming the
// reshaped field are forced. See ../../SCORING.md.
package emit

import (
	"github.com/verocorp/go-ddd/rationale/changeability/nooutward/domain"
	"github.com/verocorp/go-ddd/rationale/changeability/nooutward/pub"
)

// Maneuver wraps the domain aggregate but leaks its outward representation
// through ToResponse() — the pattern decision 3 keeps in the application service.
type Maneuver struct{ inner domain.Maneuver }

func NewManeuver(id string, burnMillis, thrustMicroN int64) Maneuver {
	return Maneuver{inner: domain.NewManeuver(
		domain.NewManeuverID(id),
		domain.NewBurn(burnMillis),
		domain.NewThrust(thrustMicroN),
	)}
}

// ToResponse emits the domain object's outward DTO directly — the leak.
func (m Maneuver) ToResponse() pub.ManeuverResponse { return m.build() }
