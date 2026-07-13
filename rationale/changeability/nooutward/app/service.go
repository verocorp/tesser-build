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

	"github.com/verocorp/go-ddd/rationale/changeability/nooutward/domain"
	"github.com/verocorp/go-ddd/rationale/changeability/nooutward/pub"
)

type service struct{}

// New returns the service typed as the public Client.
func New() pub.Client { return service{} }

func (service) DescribeManeuver(_ context.Context, req pub.DescribeManeuverRequest) (pub.ManeuverResponse, error) {
	// Convert — request DTO (primitives) -> domain value objects.
	id := domain.NewManeuverID(req.ManeuverID)
	// Delegate — the domain work (fixture: construct a representative aggregate).
	m := domain.NewManeuver(id, domain.NewBurn(4200), domain.NewThrust(9800))
	// Respond — domain object -> response DTO. The one mapping site.
	return respond(m), nil
}
