# Deterministic obligations evaluation, v1

This package validates supplied extraction records and computes the diagnostic
arithmetic adopted for the bounded pilot. It does **not** extract requirements,
run a model, match preferred reference text, infer entailment, or establish
reviewer independence. A harness and independent semantic reviewers own those
responsibilities. `complete` is a supplied review state, not proof of that
process. Even complete records cannot mechanically prove that every material
assertion was segmented or that a rationale is correct.

Build and invoke the thin host from the repository root:

```sh
go build -o /tmp/tesser-obligations ./cmd/tesser-obligations
/tmp/tesser-obligations < envelope.json > report.json
```

The package entry point is `Evaluate([]byte) (Report, error)`. It has no filesystem,
process, clock, or network dependencies. The CLI reads stdin and writes JSON to
stdout; it accepts no arguments. Exit 0 means a valid evaluation result, including
failing candidates and unscorable reviews. Malformed evaluator input/gold or CLI
usage exits 2 with a versioned JSON error on stderr and no stdout report:
`{"schema_version":"obligations-eval-v1","status":"input_error","error":"…"}`.
Output I/O failure exits 1 with the same error shape and `status:"output_error"`.

## Envelope

The root is exactly:

```json
{
  "schema_version": "obligations-eval-v1",
  "records": [
    {
      "candidate_label": "frozen_candidate",
      "case": {"case_id": "D01", "split": "development", "request": "Source text."},
      "gold": {
        "gold_version": "obligations-v1",
        "case_id": "D01",
        "references": [],
        "review_notes": []
      },
      "candidate_raw": "{\"case_id\":\"D01\",\"items\":[]}",
      "review": null
    }
  ]
}
```

This minimal example is unscorable, not a passing extraction. Supply 1–1000
records. Candidate/case pairs must be unique. Splits are `development` and
`held_out`. IDs and candidate labels match `[A-Za-z0-9][A-Za-z0-9_.-]*`; gold
reference IDs additionally start with the case ID and `-`. All fields shown
below are required except `condition` and `required` on a gold reference.
Unknown fields, duplicate object keys, null in nonnullable fields, wrong types,
and trailing JSON are rejected. Empty arrays are allowed where their semantic
constraints permit them; arrays are never replaced with null.

Each gold reference contains `id`, `type` (`goal`, `commitment`, `assumption`,
`uncertainty`), nonempty `accepted_kinds`, nonempty `text`, nonempty `evidence`,
optional `condition` (nonempty string or null), and optional boolean `required`.
`required` applies only to uncertainty references and defaults to true.
Accepted kinds use the candidate enum below and may not repeat. Conditions,
accepted kinds, gold text and review notes are preserved, never matched against
candidate text to manufacture semantic decisions.

`candidate_raw` is the untouched first output as a JSON **string**, even when
the text inside it is not valid JSON. The decoded candidate shape is
`{case_id, items:[{id,kind,text,evidence}]}`. Kinds are `goal`, `obligation`,
`constraint`, `assumption`, `question`. Item IDs are unique; text and any quote
must be nonempty. Evidence is an array of verbatim source substrings. An item
without a valid quote fails grounding. Any invalid quote fails grounding even
if the item also contains a valid one. Empty items is a valid shape but never
a pass. More than 40 items is unscorable, not truncated.

`review` is null or the supplied final object:

* `case_id`, `candidate_label`, and `gold_version` must match their inputs.
* `review_status` is `complete` or `needs_adjudication`.
* `reference_judgments` contains exactly one row for every reference, including
  optional U: `{reference_id,item_ids,coverage,rationale,source_quotes}`.
  Coverage is `full`, `partial`, or `missing`; full/partial require item IDs.
  Missing may name items the reviewer considered, but earns no credit.
* `claim_judgments` contains
  `{claim_id,item_id,candidate_fragment,verdict,duplicate_of,rationale,source_quotes}`.
  Claim IDs are unique, fragments occur in the named item's text, and
  `duplicate_of` is null or an earlier claim ID. Verdicts are `supported`,
  `unsupported`, `contradicted`, `explicit_proposal`, `open_question`.
  Every item needs at least one claim judgment; the reviewer remains responsible
  for completeness of the material assertions within it. More than 100 claims
  is unscorable, not truncated.
* `ambiguity_judgments` contains
  `{reference_id,item_ids,status,rationale,source_quotes}` for every required U,
  and optionally for optional U. Status is `preserved`, `lost`, or
  `resolved_without_authority`. The latter and preserved require item IDs.
* `item_flags` contains `{item_id,flag,rationale,source_quotes}`. Flags are
  `material_role_error`, `nonmaterial_role_mismatch`, `omnibus`. A repeated
  item/flag pair is invalid; different flags on one item are allowed.
* `disagreements` is an array of preserved review-process records. Any nonempty
  array makes the record unscorable. Resolved disputes belong in the harness's
  append-only history; pass the explicitly resolved final review here.

All review rows require a nonempty rationale and nonempty exact source quotes.
Item/reference links must exist and lists cannot repeat an ID. Quotes prove
membership only; invented claims with real quotes remain unsupported when the
review says so. Source-provisional claims and ordinary questions can earn credit
without a literal gold-kind match; material role mistakes are review flags.

## Output and arithmetic

Output uses the same version and preserves inputs on each result, including
`candidate_raw`, optional gold fields and the complete review. JSON whitespace
outside the candidate string is not a byte-for-byte archive; preserve original
envelopes and all raw judgments in the harness.

Each result has `status`, nullable `pass`, `reasons`, `candidate_format_valid`,
nullable `grounding` and nullable `metrics`:

* `candidate_failure`: malformed candidate shape, invalid IDs/enums, or invalid
  grounding. No semantic metrics/pass are emitted.
* `unscorable`: over budget, malformed/incomplete review, explicit adjudication
  status or unresolved disagreement. No semantic metrics/pass are emitted.
* `scored`: structurally valid candidate and complete valid review, with a
  diagnostic boolean pass. Empty candidates are scored failures.

Shape failure is checked first, then item budget, review validity, and grounding.
An invalid review therefore cannot turn into a pass/fail decision just because
grounding also fails. Grounding is still visible when candidate shape is valid.
Envelope/gold errors reject the entire input before scoring any record.

Ratios publish `numerator`, `denominator`, and `value` (null for N/A).
Commitment, goal and assumption coverage count full references only, with
separate partial/missing counts. Partial earns zero primary credit. Required
ambiguity counts preserved required U only. Precision is nonduplicate supported
claims over nonduplicate supported/unsupported/contradicted claims; proposals
and questions are excluded. Duplicates have a count and rate over all claims.
Raw unsupported/contradicted counts include duplicates. Material role errors,
nonmaterial role mismatches and omnibus items remain separate counts. Grounding
counts valid source quotes over all evidence quotes, plus items lacking one.

A diagnostic pass requires a nonempty candidate, full O/G/A coverage, all
required U preserved, no unsupported/contradicted claims, no material role error,
no omnibus item, and valid grounding for every item. Harmless duplicates alone
do not fail. This is a conservative **pilot diagnostic**, not an empirically
validated production-readiness threshold or a reliability estimate.

`by_candidate`, `by_split` and `by_candidate_split` are sorted aggregates. Each
publishes total/scored/candidate_failure/unscorable/passed/failed case counts;
passed/failed refer only to scored cases. Recall metrics explicitly say
`scored_only`: micro sums covered and total commitment references; macro sums
per-case recall over scored cases with a nonzero commitment denominator.
Unscorable cases remain in status counts, never disappear into a success rate.
No composite semantic score is produced. Caller-owned dataset/run manifests
must establish consistent case/gold versions across comparisons.

## Verification and provenance

`testdata/{case,gold,responses,judgments}.json` are the six authored D01 controls
and adopted reviewer A records supplied for calibration. They are not live
candidate outputs. Both independent calibration reviews agreed on effective
metrics; raw reviewer B and the original author's expectations stay in the
parent's evidence archive. Tests also author a synthetic complete positive;
recognizing it does not establish reviewer correctness or live reliability.

Run bounded behavior checks with
`go test -count=1 ./internal/obligationeval ./cmd/tesser-obligations` and static
checks with `go vet ./internal/obligationeval ./cmd/tesser-obligations`.
The CLI test builds and executes the real command in a temporary directory.
No generated artifact, new analyzer registration or Python app is involved.

## Frozen candidate pilot

[`pilot/README.md`](pilot/README.md) carries a reusable extraction prompt, the
six-development/four-held-out run, both independent semantic reviews, adopted
decisions and replayable results. The tests verify the frozen inputs and both
reviewers' arithmetic. The cases are public now; later tuning on them is
regression work, not another held-out evaluation.
