// Package app is the APPLICATION SERVICE behind pub.Client: the only place that
// knows both worlds. It accepts and returns DTOs (dumb primitives) and converts
// them to and from domain objects (value objects), so the domain and repositories
// operate on domain objects only. The four-step shape is Convert -> Delegate ->
// Persist -> Respond; Respond (domain object -> response DTO) is the SINGLE
// mapping site, and it is the only code an outward-representation migration forces
// to change (respond_v1.go / respond_v2.go, -tags repv2). Contrast that O(1) with
// the coupled arm, where the domain emits the DTO and every dependent pays.
//
// See ../../SCORING.md (decision 3).
package app

import (
	"context"

	"github.com/verocorp/tesser-build/rationale/changeability/nooutward/domain"
	"github.com/verocorp/tesser-build/rationale/changeability/nooutward/pub"
)

type service struct{}

// New returns the service typed as the public Client.
func New() pub.Client { return service{} }

func (service) DescribeManeuver(_ context.Context, req pub.DescribeManeuverRequest) (pub.ManeuverResponse, error) {
	// Convert — request DTO (primitives) -> a domain spec (primitives). The burn
	// and thrust are fixed here only because this fixture has no repository to load
	// from; a real service would load the aggregate by id in Delegate.
	spec := domain.ManeuverSpec{ManeuverID: req.ManeuverID, BurnMillis: 4200, ThrustMicroN: 9800}
	// Delegate — the domain work: construct the aggregate through its constructor,
	// which owns validation. The service never builds value objects itself.
	m, err := domain.NewManeuver(spec)
	if err != nil {
		return pub.ManeuverResponse{}, err
	}
	// Respond — domain object -> response DTO. The one mapping site.
	return respond(m), nil
}
