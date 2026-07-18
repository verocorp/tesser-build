//go:build !repv2

// The query facade's single mapping site, v1. AUTHORED BY THE ADVERSARY (Codex,
// read-only, 2026-07-13) — transcribed verbatim. See ../../adversary_provenance.md.
package burnquery

import "github.com/verocorp/tesser-build/rationale/changeability/nooutward/pub"

func responseBurnSeconds(response pub.ManeuverResponse) int64 {
	return response.BurnSeconds
}
