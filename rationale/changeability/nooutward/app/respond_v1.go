//go:build !repv2

// Respond, v1 mapping (pre-migration). Reads the domain object's value objects
// and assembles the v1 response DTO. This is the single site that names the
// outward field BurnSeconds; the migration to v2 changes only this file.
package app

import (
	"github.com/verocorp/tesser-build/rationale/changeability/nooutward/domain"
	"github.com/verocorp/tesser-build/rationale/changeability/nooutward/pub"
)

func respond(m domain.Maneuver) pub.ManeuverResponse {
	return pub.ManeuverResponse{
		ManeuverID:   m.ID().String(),
		BurnSeconds:  m.Burn().Seconds(),
		ThrustMicroN: m.Thrust().MicroNewtons(),
	}
}
