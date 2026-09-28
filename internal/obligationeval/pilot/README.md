# Frozen obligations-extraction pilot

One candidate prompt returned usable extractions for all six development and
four held-out requests under the adopted diagnostic. Two independent reviews
agreed on coverage, support and unresolved decisions. This is a ten-case,
single-run diagnostic, not evidence of production reliability or improvement
over another agent.

The candidate is [`candidate/AGENT.md`](candidate/AGENT.md). It extracts goals,
obligations, constraints, provisional assumptions and open questions, with
verbatim evidence. It does not choose an architecture or turn an undecided
detail into a requirement. Its author saw development requests and the public
output contract only. The prompt was frozen before any live run; no candidate
was tuned or rerun after seeing held-out results.

## Results

| Diagnostic | Development | Held out |
| --- | ---: | ---: |
| Strict case passes | 6 / 6 | 4 / 4 |
| Fully covered commitments | 29 / 29 | 18 / 18 |
| Goals | 6 / 6 | 4 / 4 |
| Source assumptions | 1 / 1 | 1 / 1 |
| Required uncertainties preserved | 6 / 6 | 6 / 6 |
| Unsupported or contradicted claims | 0 | 0 |

All 80 candidate evidence quotes are exact source substrings. That is a
grounding check, not an entailment test. Both reviewers found one nonmaterial
label mismatch: D06 calls the explicitly unrequired compression idea a
constraint, but does not promote it into a requirement or forbid it.

Claim segmentation changes the diagnostic denominators. Canonical reviewer A
records assertion precision 61/61 and six duplicates among 82 claims; reviewer
B records 75/75 and five among 95. Both preserve the added legal-hold behavior;
A separately counts its repeated agreed-exception status. The parent adopted
A's accounting and preserved B as a sensitivity check, rather than presenting
one segmentation as objective. See [`live/ADJUDICATION.md`](live/ADJUDICATION.md)
and both untouched reviews and notes.

The six authored calibration controls are **not live model outputs**. Empty,
invented, copied-whole-request and broadened-condition outputs fail for different
reasons. The copied request keeps semantic coverage but fails usability. The
two local positive controls earn their intended local credit without covering
the whole case. A separate synthetic complete positive passes the evaluator's
tests, so rejection of weak controls is not its only tested behavior.

## Replay

From the repository root:

```sh
go run ./cmd/tesser-obligations \
  < internal/obligationeval/pilot/live/replay-a.json > report.json
go test ./internal/obligationeval ./cmd/tesser-obligations
```

`replay-a.json` contains the exact first candidate text, case, gold and canonical
review for each case. The pilot regression also substitutes reviewer B's raw
judgments and checks both compact expected reports. Those reports omit only
the repeated input payload, which remains in the replay and source records.
The tests verify the frozen inputs' hashes and the first-output text hashes.
They replay validation/arithmetic, not model execution or semantic judging.

To run the candidate on another request, give an agent `candidate/AGENT.md` and
one `{case_id, request}` object. Preserve its first returned JSON before review.
Use [`RUBRIC.md`](RUBRIC.md), the adopted decisions and independent semantic
review to construct the evaluator envelope documented in the package README.
Do not ask the scoring program to infer meaning from matching words.

## Provenance and limits

[`LIVE-FROZEN.json`](LIVE-FROZEN.json) fixes the exact input/prompt bytes and
execution settings: `codex/gpt-6-astra`, high reasoning, one context per case.
Sampling used platform defaults; no seed or backend fingerprint was exposed.
Ordinary Capy/project instructions were also inherited. Case tasks were
instructed not to inspect files or other cases; the shared machine was not an
access-control sandbox. Both semantic reviews used the same model route, so
their agreement is not evidence of reviewer-model diversity.

The `private/` name is historical: its files were withheld from the candidate
author, but are now public provenance, not secrets. Original authoring mistakes,
their proposed repairs and the adopted gold are retained. Source files keep
their original authoring-status fields; the freeze manifest and adopted
decisions establish which bytes governed this run. Nothing here turns the
original author's expectations into independent review evidence.

These held-out requests were withheld from the candidate author; they are
public now. Further tuning on them is
regression work, not another held-out result. This pilot measures extraction on
short authored requests, not downstream application construction, and has no
unrun-baseline comparison, causal learning claim or confidence estimate.

Use this candidate as a reviewed requirements-extraction aid. A next bounded
option is a newly authored, separately withheld corpus of longer and more
ambiguous requests; that would address generalization. Expanding directly into
architecture generation would introduce additional unmeasured decisions, so
the extraction-first path is the recommended next experiment.
