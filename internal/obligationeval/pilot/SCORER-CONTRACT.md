# Bounded obligations evaluator implementation

Deliver a small Go package and CLI, following the repository's existing Go
tooling pattern: `internal/obligationeval` and `cmd/tesser-obligations`. Do not
build a generic model runner, prompt optimizer, architecture generator, or
reuse the unrelated code-mutation trial engine on the existing unmerged
`capy/v0600-feat-add-bounded` branch. This tool validates records and computes
arithmetic; independent agents/people supply semantic judgments.

Use the supplied case, gold, candidate and review schemas rather than inventing
semantic matching. It is acceptable to wrap one case's four inputs in an
explicit versioned input envelope. Support a bounded list of such records so
the output reports per-case vectors and separate per-candidate, per-split
aggregates: micro commitment recall and macro per-case commitment recall, with
denominators and N/A where appropriate. Reject duplicate candidate/case pairs.
Keep raw candidate text so malformed JSON can be reported as candidate failure,
not silently repaired into a new first output. Accept explicit final review
records; do not claim that `complete` proves independence or correct entailment.
The harness/run manifest, not the scoring code, establishes the review process.

The frozen rubric and CALIBRATION-DECISION.md define the metrics. Required U is
the default when `required` is absent in the authored gold; optional U carries
`required:false`. Preserve all explicit schema fields, including accepted kinds,
conditions and review notes, without using preferred text as a matcher. Source
quotes must be nonempty verbatim substrings, candidate fragments must occur in
the referenced item, IDs and enums must validate, references must be complete
and unique, duplicate links must point backward, and all candidate items must
be accounted for by review claims. Valid quoting never proves entailment.
Treat malformed/incomplete review, disagreement, or over-budget input as
unscorable, never as a pass; do not truncate. Invalid candidate shape is a
candidate failure. Invalid evaluator envelope/gold is an input error. Make
these states visibly different in versioned deterministic JSON and use nonzero
exit status for malformed evaluator input. A scored failing candidate is a
valid evaluation result, not a parser error.

Use canonical flag enums `material_role_error`, `nonmaterial_role_mismatch`,
and `omnibus`. Do not silently ignore unknown flags or duplicate flags. Claim
verdicts and reference/ambiguity enums are in RUBRIC.md. Count duplicates
separately and exclude them from precision; keep unsupported/contradicted raw
counts visible. The model-output budget is 40 items and the reviewer budget is
100 claims. Unresolved/invalid review cases must not disappear from aggregate
denominators as though every evaluated case succeeded: publish case counts by
status and identify the scored-only denominators.

Tests must cover the six adopted calibration controls, full/partial/missing
coverage, N/A, budget/unresolved states, invented claims with real quotes,
omnibus full coverage, duplicate discounting, invalid IDs/enums/links/quotes,
missing required fields, unknown JSON fields, malformed candidate text,
incomplete review, split/candidate aggregation, and CLI JSON/error exits.
Include a synthetic complete positive record so all weak controls failing is
not mistaken for evidence that the tool can recognize a passing record.

The parent owns the live candidate runs, raw evidence and final dataset/prompt
publication. You may use only D01 calibration inputs and the rubric supplied
to your task. Do not inspect private datasets or other agents' outputs. Do not
ship scratch paths or fabricated live performance. Keep the CLI thin, document
exact invocation/schema and limitations, and validate related Go tests/vet/
formatting plus the repository's layout metadata gate. No new top-level dir.
