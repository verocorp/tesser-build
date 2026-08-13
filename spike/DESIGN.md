# Classifier totality — the exploration behind the v0.0.30.0 refactor

This branch (`spike/classifier-totality`) preserves the exploration that
picked the shipped design. It is not meant to merge. The shipped version —
hardened tests, no spike artifacts — went to main via the classifier-totality
PR (v0.0.30.0).

What is here:

- **Option B (classify-first seam)** and **Option C (totality corpus)** are
  the first two commits in this branch's history, as originally built.
- **Option A (runtime mirror guard)** is `spike/option-a-mirror-guard.patch`
  — kept as a patch because it was rejected and never hardened.
- **The evaluation harness** is `spike/probe_corpus.py` — it builds a
  synthetic tree of weird module shapes, each carrying an import that is
  illegal from almost anywhere, runs the shipped analyzer over it, and
  reports any shape that produced zero findings (a silent leak).

## The problem

Every hole ever found in the module walk was the same defect: a module shape
nobody enumerated fell through the dispatch in
`tessercheck/domain/checks.py` and produced zero findings — which is exactly
what conformance produces. The v0.0.29.0 review cycle hit three in one week
(deep `__main__`, tier-less `test_*.py`, exempt `conftest`), all found by
adversarial review, none by the design.

## The options and the evidence

All options were run against the full suite, a 34-shape probe corpus, and
three simulations.

- **A — runtime mirror guard**: a second "does this module match a governed
  location" pass emitting a finding on mismatch. Rejected on evidence: it
  double-flags modules the ladder already governs (+6 findings of noise on
  the probe tree), and it caught neither simulation — the historical bugs
  were handlers that classified fine and then forgot a rule internally,
  which a location-keyed mirror cannot see.
- **B — classify-first seam**: `_module_violations` splits into `_locate`
  (pure, total: name + is-package → exactly one location token) and a token
  dispatcher, guarded by two meta-tests (every token has a dispatch arm;
  every token appears in a readable classification table). In the future-bug
  simulation — a new `bench_*.py` convention added with a lazy `return ()`
  handler — B was the only option that failed by name: "_locate can return
  tokens the classification table never exercises: ['bench']".
- **C — totality corpus**: the probe corpus as a committed fixture test.
  Cheap and end-to-end, but measured blind two ways: it missed the
  future-bug simulation (a corpus only knows enumerated shapes), and it
  missed the replay of the v0.0.29.0 tier-less-test bug because the bait
  import tripped an incidental form rule — "any finding at all" masks
  *partial* silence. The clause-exact fixtures from the v0.0.29.0 review
  caught that replay; the corpus did not. Corpus complements clause
  fixtures; it does not replace them.
- **D — B and C together** (what shipped): analyzer output byte-identical on
  every tree, all gates green, three complementary nets — the locate table
  (routing totality), the corpus (total-silence net on known shapes), and
  the standing clause-exact-fixture discipline (partial-silence net).

## What is deliberately left uncovered

No static mechanism forces a dispatch arm to do work: a diligently routed
token whose handler is a lazy `return ()` passes every net (measured, third
simulation). The structure converts that from a silence problem into a
review problem — the laziness is three conspicuous lines in a diff (a named
token, table rows, a bare `return ()` arm) instead of an invisible
fall-through.

## The rule going forward

Routing lives in `_locate` and nowhere else. A new module kind is a new
token, a dispatch arm, table rows in `test_locate.py`, and (if it carries
rules) clause-exact fixtures in `test_checks.py` plus corpus rows in
`test_totality_corpus.py`. A basename or path check added anywhere else in
the walk is the old bug class being reintroduced — flag it in review.
