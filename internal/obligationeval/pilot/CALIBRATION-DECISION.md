# Calibration decision, before any live candidate run

The parent compared both untouched independent judgments, their rationales, the
six authored responses, their source request, and the original author's weak
fixtures. These are calibration controls, not agent-performance observations.

Both independent reviewers agree on all 42 reference-coverage decisions, all
six required-ambiguity decisions, all 16 segmented claim verdicts, the duplicate
link, the material-role error, and the omnibus item. Every supplied source quote
and candidate fragment was independently replayed for exact membership. This
checks grounding and record integrity, not entailment by itself.

The difference between six and eight ambiguity rows is entirely optional U2:
B explicitly records its unauthorized resolution in calibration_02 and its
preservation in calibration_03; A assesses those same meanings through the
reference and claim rows. Optional rows are permitted, but excluded from the
required-ambiguity denominator. B's `nonmaterial_role_error` and A's
`nonmaterial_role_mismatch` name the same nonmaterial label mismatch. Use
`nonmaterial_role_mismatch` in the canonical schema. Preserve both raw reviews.

Adopt reviewer A's records as the effective calibration records. There is no
unresolved scoring disagreement. B's extra optional rows may remain in its raw
record; dropping them from a canonical record does not erase an unsupported
promotion, which is counted in the claim and material-role dimensions.

The initial author's expectations are not the final oracle. They combine the
invented-reminder sentence into one unsupported claim, where both reviewers
distinguish four independently added commitments/parameters; and combine the
lost-condition sentence into one unsupported claim, where both reviewers
distinguish supported FIFO selection from unsupported scope broadening. Adopt
the independently agreed segmentation. The original author's partial coverage
for the optional reminder uncertainty also overcredits the reminder topic:
the candidate does not preserve its unagreed status, so the reference is
missing. None of these changes makes an authored weak response pass.

The copied request has full literal semantic coverage and valid quotes but
fails the separate omnibus/usability requirement. A different label does not
erase explicit meaning. Quotes alone do not support invented requirements.
Keep these decisions in tests rather than forcing one aggregate ranking.

For this bounded pilot adopt the rubric's proposed conservative case pass as a
diagnostic: valid candidate, completed/adjudicated review, all O/G/A references
fully covered, all required U preserved, no unsupported or contradicted claims,
no material role error, no omnibus item, and valid grounding per item. Duplicates
are reported but not alone a failure. Zero denominators are N/A. A response over
40 items or a review over 100 claims needs adjudication, with no truncation or
pass/fail result. This is a parent technical decision, not a user-approved
production acceptance threshold or a reliability claim.

Freeze one candidate before live execution. Run each of the six development
and four held-out cases once. Do not tune after seeing held-out results. Review
every live output independently twice, preserve both records and resolve any
real dispute explicitly; unresolved cases are unscorable. Candidate authoring
sees development requests and the output contract only, never held-out requests,
private gold, calibration expectations, or reviewer records. Case execution
sees its own request and the frozen prompt only. No comparison to an unrun
baseline, confidence estimate, or causal learning claim is licensed.

Recommended use is a bounded diagnostic plus replayable validation/arithmetic.
The alternative, a production-readiness claim or automated semantic judge,
would require evidence and capabilities this ten-case pilot does not supply.
