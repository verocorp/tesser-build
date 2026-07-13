// Package burnsort models reporting/UI code that sorts domain objects by fields
// on a domain-emitted outward representation.
//
// Evidence for skills/ddd/application-services.md: if the domain exposes
// ToResponse(), ordinary read-side code starts treating the wire shape as the
// domain's inspection API.
//
// AUTHORED BY THE ADVERSARY (Codex, read-only, 2026-07-13) — transcribed verbatim.
// See ../../adversary_provenance.md.
package burnsort

import (
	"sort"

	"github.com/verocorp/go-ddd/rationale/changeability/nooutward/emit"
)

func ByBurnSeconds(maneuvers []emit.Maneuver) {
	sort.SliceStable(maneuvers, func(i, j int) bool {
		left := maneuvers[i].ToResponse()
		right := maneuvers[j].ToResponse()
		if left.BurnSeconds == right.BurnSeconds {
			return left.ManeuverID < right.ManeuverID
		}
		return left.BurnSeconds < right.BurnSeconds
	})
}

func LongestBurnSeconds(maneuvers []emit.Maneuver) int64 {
	var longest int64
	for _, maneuver := range maneuvers {
		burn := maneuver.ToResponse().BurnSeconds
		if burn > longest {
			longest = burn
		}
	}
	return longest
}
