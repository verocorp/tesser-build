// Package webhookpayload models a common outbound adapter mistake: a downstream
// webhook payload is assembled from the domain-emitted public DTO instead of from
// domain value objects or an application-layer mapper.
//
// Evidence for skills/ddd/application-services.md: Respond belongs in the
// application service; a domain object emitting a DTO lets outward field names
// spread into ordinary dependents.
//
// AUTHORED BY THE ADVERSARY (Codex, read-only, 2026-07-13) — transcribed verbatim.
// See ../../adversary_provenance.md.
package webhookpayload

import "github.com/verocorp/go-ddd/rationale/changeability/nooutward/emit"

type ManeuverWebhook struct {
	ID           string
	BurnSeconds  int64
	ThrustMicroN int64
}

func Build(m emit.Maneuver) ManeuverWebhook {
	response := m.ToResponse()
	return ManeuverWebhook{
		ID:           response.ManeuverID,
		BurnSeconds:  response.BurnSeconds,
		ThrustMicroN: response.ThrustMicroN,
	}
}

func ShouldBatch(payload ManeuverWebhook) bool {
	return payload.BurnSeconds >= 5
}
