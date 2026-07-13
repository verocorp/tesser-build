//go:build !repv2

// The domain-emitted DTO assembly, v1. This is the application service's Respond
// step done on the domain object — the decision-3 violation. Split by build tag
// only so this package stays compilable across the migration; the harm is that
// DEPENDENTS reach the emitted DTO's fields (see coupled/fanout).
package emit

import "github.com/verocorp/go-ddd/rationale/changeability/nooutward/pub"

func (m Maneuver) build() pub.ManeuverResponse {
	return pub.ManeuverResponse{
		ManeuverID:   m.inner.ID().String(),
		BurnSeconds:  m.inner.Burn().Seconds(),
		ThrustMicroN: m.inner.Thrust().MicroNewtons(),
	}
}
