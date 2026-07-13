//go:build repv2

// ManeuverResponse v2 — the post-migration public wire shape (build with
// -tags repv2). BurnSeconds is gone, reshaped into DurationMillis. Any dependent
// that reached the domain-emitted DTO to name BurnSeconds fails to compile here;
// a dependent that holds the domain object (its value objects) is untouched.
// Dumb bag of primitives: no methods, no constructor.
package pub

type ManeuverResponse struct {
	ManeuverID     string
	DurationMillis int64 // v2: milliseconds — replaces v1's BurnSeconds
	ThrustMicroN   int64
}
