# Independent live semantic review A

Reviewed the ten frozen first-returned candidates once, reading each request and candidate before consulting the supplied gold and review contract. Candidate label and gold version are `obligations-v1`. Only the permitted `review-input` directory and this output directory were read. No candidate was changed, rerun, or regenerated, and no other reviewer was contacted.

`judgments.json` contains one complete RUBRIC.md reviewer record per case. `complete` means this independent review is finished; it does not mean the parent has compared or adjudicated the two independent records. There is no case pass/fail decision or reliability claim here.

## Semantic observations

All 77 references are fully represented on this pass, and all 12 required uncertainties remain open or appropriately provisional. The six optional uncertainties also have explicit reference and ambiguity rows. No unsupported or contradicted assertion, material role error, omnibus item, or genuine gold defect was identified.

- D02 preserves both necessary conditions with `only if`; it does not make them sufficient. Its extra existing-payment-process item is source-supported even though it has no separate gold reference. H01 and H02 likewise preserve their necessary-only conditions.
- D04 preserves both naming demands and explicitly asks for a decision with no agreed exception. H03 preserves both unwaived policies, the legal-hold exception, and the unspecified post-hold deletion schedule. H03's conflict question is read with its explicitly named policies and the exception spelled out in I2/I6, not as silently repealing that exception.
- D06-I8 labels the tentative compression idea `constraint`, but its text explicitly keeps compression unrequired and future usefulness tentative. This is one `nonmaterial_role_mismatch`, not a material promotion or an invented compression prohibition.
- Six backward duplicate links record repeated conflict premises or exception status: two in D04-I6, three in H03-I5, and one in H03-I6. The substantive suspension behavior in H03-I6 adds the duration missing from I2's short exception qualifier, so that behavior is not itself counted as a complete duplicate. Compact refusal-plus-explanation and row-field items remain usable; they are not forced to match gold granularity.

There are no unresolved semantic uncertainties within this review, so no record requires `needs_adjudication` from reviewer A alone. Disagreements with another independent review remain unknown and must not be treated as already resolved. The context-sensitive H03 conflict summary, duplicate segmentation, and D06 label distinction are explicit above so the parent can compare the actual reasoning rather than infer agreement from coverage totals.

## Validation evidence

`validate_records.py` checks only record structure, identifiers, enums, links, row completeness, review budgets, and exact quote/fragment membership; it does not judge entailment or calculate scores. `validation.json` records zero errors across 10 cases, 72 candidate items, 80 candidate evidence quotes, 77 reference rows, 18 ambiguity rows (12 required), 82 claim fragments, 207 reviewer source quotes, six backward duplicate links, and one canonical item flag. Every item has claim accounting; material completeness and semantic rationales were assessed in the manual review, not inferred by that mechanical check.

Input `records.json` SHA-256: `7778996ec974adeb037996628bdbf7cc3cc6995fd60b8ff50d34d5a7ef81cd24`.

Judgments SHA-256: `c3e87641be09e0b40aaff47eb523fa87b93ceeeae7f3f8746277b60e556d215e`.

Next options: compare these untouched records with the other independent review, or leave the run unadjudicated if that review is unavailable. Recommend comparison: it resolves actual differences without tuning the frozen candidate or treating this single review as completed independent adjudication.
