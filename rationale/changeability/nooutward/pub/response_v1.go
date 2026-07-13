//go:build !repv2

// ManeuverResponse v1 — the pre-migration public wire shape. BurnSeconds is the
// field the migration reshapes away. Building with -tags repv2 replaces this with
// response_v2.go (DurationMillis), modelling an outward-representation migration
// inside one committed tree. Dumb bag of primitives: no methods, no constructor.
package pub

type ManeuverResponse struct {
	ManeuverID   string
	BurnSeconds  int64 // v1: whole seconds — reshaped to DurationMillis in v2
	ThrustMicroN int64
}
