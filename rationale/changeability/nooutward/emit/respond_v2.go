//go:build repv2

// The domain-emitted DTO assembly, v2 (post-migration, -tags repv2). The domain
// author was forced to update the domain's own mapping when the wire reshaped —
// itself part of the harm (the domain is dragged into the outward change).
package emit

import "github.com/verocorp/go-ddd/rationale/changeability/nooutward/pub"

func (m Maneuver) build() pub.ManeuverResponse {
	return pub.ManeuverResponse{
		ManeuverID:     m.inner.ID().String(),
		DurationMillis: m.inner.Burn().Millis(),
		ThrustMicroN:   m.inner.Thrust().MicroNewtons(),
	}
}
