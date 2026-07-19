# The field-audit checklist — friction day, classification, relay

Generic and consumer-agnostic: run it inside any consumer repo, behind
whatever IP wall applies. Nothing consumer-specific comes back — only
de-identified patterns in the relay format below. This file is deliberately
**delta-only**: it carries what the audit adds (classification prompts + the
relay format) and points at existing doctrine for everything else — the
anatomy walk is `skills/tesser-build/map.md`'s gap survey, and the
classification applies the repo's changeability thesis (the silent-site
metric, `docs/design-three-contender-changeability.md`). Both pointers are in
this public repo — read them on GitHub from the other side of the wall.

The audit's ordering authority comes from the Wave 3R plan (the gstack-side
design doc, not in this repo): its Phase-1 queue — the pay-now doctrine +
check queue — is what the relayed list orders.

## 1. Run the day

- One prospective working day of real work in the consumer repo. Don't
  manufacture exercises — log frictions as they interrupt actual tasks.
- Seed the log up front with frictions you already remember before the day
  starts; mark them `remembered` vs `observed`.
- **The raw log never leaves the consumer repo.** It will be full of domain
  nouns — that's fine behind the wall. Only section-3 entries, de-identified,
  ever cross.
- A **friction** is any moment the construction conventions failed you:
  you didn't know where code belonged, an agent improvised structure, a
  change fanned out further than it should have, a convention existed but
  wasn't followed, or a convention was missing outright.
- For "where does this belong" frictions, walk the gap survey in
  `skills/tesser-build/map.md` (name the pieces → survey what exists → the
  gap is the finding). Log which anatomy piece was involved — that's the
  doctrine file (or recorded gap, for stub rows) the fix lands in.

## 2. Classify each friction — the deferral test

Two legs, asked in order:

1. **Findability** — are violations of the underlying rule mechanically
   findable, or do they *hide*? Findable means a checker could enumerate
   every site **without domain knowledge**; if recognizing a site takes
   judgment (leaks into signatures, scatters across callers, vanishes into
   call chains), it hides — even when individual instances look greppable.
2. **Fix-locality** — once a violation is found, is the fix a local
   sweep-edit (rename, wrap, per-site touch-up), or *structural* (moving
   code across boundaries, unwinding a baked-in cycle)?

**Defer only when BOTH legs hold** (findable AND local): the property that
makes a rule mechanically checkable later is the property that makes its
retrofit cheap. **Pay now when EITHER leg fails**: violations hide, or the
fix is a restructure.

Calibration anchors: perfect VO wrapping passes both legs → defer.
Dependency direction is findable but a flagged wrong-direction import is a
restructure, not a sweep → pay now.

### The pay-now universe

Every pay-now classification lands in one of five bins — the audit orders
and prunes *within* them. Each bin names its rule; the rule's content lives
in the pointed-at doctrine, not here:

1. **Context boundaries + seams** — which contexts exist, and each seam
   intact (`skills/tesser-build/public-interface.md`,
   `strategic-design.md`).
2. **Dependency direction** — acyclic, inward (`map.md`
   "How contexts connect"; enforcement: import-linter declared contracts,
   consumer-side).
3. **No representation leaks** — domain objects escaping outward
   (`public-interface.md`, `handlers.md`).
4. **Single construction path per type** — exactly one public construction
   path exists (`value-objects.md`, `entities.md`). How the path is
   *shaped* — spec-idiom purity, canonicalization — is defer-category.
5. **Env/exit edge discipline** — buried `getenv`s are hidden sites by
   definition (`srv.md`).

A finding that fits none of the bins but still classifies **pay-now under
the test** (either leg fails) is a candidate **sixth bin**: relay it flagged
as such. Adding a bin is a deliberate amendment to the plan doc, never
silent queue drift. (The plan's parenthetical names the hiding leg; this
checklist admits either failed leg, matching the sharpened test — flag which
leg failed in the relay.)

## 3. Relay the findings — de-identified

De-identification rules:

- No business/domain nouns, no file paths, no identifiers — replace with
  anatomy role names (`context A`, `aggregate X`, `gateway G`, `handler H`).
- **No verbatim consumer text of any kind** — code, error messages, config,
  log lines. Reconstruct the shape from scratch in anatomy vocabulary with
  invented nouns; never rename-and-paste.
- Two self-checks per entry: (a) does the pattern survive the renaming? If
  not, it wasn't pattern-shaped. (b) Could a reader guess the industry,
  vendor, or client from what remains (distinctive workflows, cadences,
  integration shapes)? If yes, coarsen until they can't.
- A pay-now friction that can't be de-identified is NOT dropped: it stays
  logged behind the wall, and only its bin + a count crosses ("bin 5, +1").

One entry per friction:

```
- pattern:    <generic shape, anatomy vocabulary only>
- anatomy:    <piece(s) from map.md's table that the friction touched>
- seen:       remembered | observed | both   (+ times observed that day)
- class:      pay-now <bin 1-5 | candidate-6th (+ which leg failed)> | defer
- check idea: <defer only: the check that would enumerate it later>
- cost shape: <what the retrofit looks like if deferred: N-site sweep,
               signature fan-out, boundary restructure, ...>
```

Worked example (invented, granularity anchor):

```
- pattern:    handler H builds aggregate X inline from request primitives,
              bypassing X's constructor; validation re-implemented at H
- anatomy:    handlers.md, aggregates.md
- seen:       observed (2)
- class:      pay-now bin 4
- cost shape: per-handler sweep today; silent divergence of the two
              validation paths if deferred
```

The relayed output is an **ordered pay-now list** (your priority order —
this list IS the plan's Phase-1 queue) plus the defer pile, each defer item
carrying its `check idea:` so it can become a named check later. Check
misfires ride the same channel: reconstruct the minimal synthetic shape that
confused the check (invented nouns, never renamed consumer code) with
expected-vs-actual behavior; the fixture and check get corrected
toolkit-side.
