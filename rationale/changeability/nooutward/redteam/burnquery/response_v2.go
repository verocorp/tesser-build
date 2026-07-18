//go:build repv2

// The query facade's single mapping site, v2 (post-migration): the one edit the
// migration forces, exactly like app.respond. Downstream callers of BurnSeconds do
// not change. AUTHORED BY THE ADVERSARY (Codex, read-only, 2026-07-13) — verbatim.
package burnquery

import "github.com/verocorp/tesser-build/rationale/changeability/nooutward/pub"

func responseBurnSeconds(response pub.ManeuverResponse) int64 {
	return response.DurationMillis / 1000
}
