package inconsistent

// --- Non-conformance 5: NAMING DRIFT --------------------------------------
//
// Flight-phase discriminators as bare string constants — no type, no single
// definition of the naming convention. Different authors used different
// separators: PhaseTouchdown drifted to an underscore while its siblings use
// hyphens. Naming drift is silent — the compiler sees four strings and a string
// is a string. A format-wide change (or a lookup that assumes one convention)
// silently misses the outlier.
//
// Anchor: the operation-type registry where `revert_earn` used an underscore
// while every sibling value used a hyphen (certus realized-harm report) — the
// drift was "itself a tell."
const (
	PhasePreLaunch = "pre-launch"
	PhaseInOrbit   = "in-orbit"
	PhaseDescent   = "descent"
	PhaseTouchdown = "touch_down" // drifted: underscore where the rest use hyphens
)

// AllPhases is what a dispatcher or a rename pass would range over.
var AllPhases = []string{PhasePreLaunch, PhaseInOrbit, PhaseDescent, PhaseTouchdown}
