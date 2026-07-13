// Package burnquery is a red-team query facade over the application service. It
// gives consumers the scalar they need without exposing either the public response
// DTO or the domain value-object graph.
//
// Evidence for skills/ddd/application-services.md: this is a sanctioned
// application/outward mapper. It challenges the benchmark's decoupled arm on
// ceremony, not by making the domain emit its own representation.
//
// AUTHORED BY THE ADVERSARY (Codex, read-only, 2026-07-13) — transcribed verbatim.
// See ../../adversary_provenance.md.
package burnquery

import (
	"context"

	"github.com/verocorp/go-ddd/rationale/changeability/nooutward/app"
	"github.com/verocorp/go-ddd/rationale/changeability/nooutward/pub"
)

func BurnSeconds(ctx context.Context, maneuverID string) (int64, error) {
	return BurnSecondsWith(ctx, app.New(), maneuverID)
}

func BurnSecondsWith(ctx context.Context, client pub.Client, maneuverID string) (int64, error) {
	response, err := client.DescribeManeuver(ctx, pub.DescribeManeuverRequest{
		ManeuverID: maneuverID,
	})
	if err != nil {
		return 0, err
	}
	return responseBurnSeconds(response), nil
}
