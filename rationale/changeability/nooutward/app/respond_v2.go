//go:build repv2

// Respond, v2 mapping (post-migration, -tags repv2). The one site updated by the
// outward-representation migration: it now assembles DurationMillis from the same
// domain value object (m.Burn().Millis()). The domain did not move.
package app

import (
	"github.com/verocorp/go-ddd/rationale/changeability/nooutward/domain"
	"github.com/verocorp/go-ddd/rationale/changeability/nooutward/pub"
)

func respond(m domain.Maneuver) pub.ManeuverResponse {
	return pub.ManeuverResponse{
		ManeuverID:     m.ID().String(),
		DurationMillis: m.Burn().Millis(),
		ThrustMicroN:   m.Thrust().MicroNewtons(),
	}
}
