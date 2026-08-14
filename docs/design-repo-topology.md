# Repo topology — declared tree roots and the manifest guard

Two declarations, one guard. A checkable tree declares itself with a
`.tesser-root` file at its root; the repo declares what every top-level
directory is in `manifest.json`; and `scripts/check-topology` fails when disk
and declarations disagree in either direction.

## The problem this solves

Three related holes, all of the same shape — coverage was implicit:

1. **A tessercheck run inferred its subject.** `python -m tessercheck <dir>`
   walked whatever it was pointed at. Run at the repo root, it would happily
   smoosh nine unrelated trees into one and report nonsense; run on a random
   directory, it would report "clean" about a thing that was never a tesser
   tree at all. Nothing distinguished "this directory is a checked app" from
   "nobody ever looked here."
2. **The gate list was hand-maintained.** `scripts/verify` carried a literal
   `TREES=(...)` array, and the CI workflow carried one job per tree. Adding a
   tree meant remembering both; forgetting meant a tree that exists but is
   gated by nothing, silently.
3. **Nothing stopped a new top-level directory.** An agent (or a person) could
   create one and no check anywhere would ask what it is or who gates it.

## The declarations

**A tree declares itself: `.tesser-root`.** A checkable tree carries a
`.tesser-root` file at its root containing `app`. The declaration state is a
fact the reader reports and the domain rules judge (`TB044`):

- no `.tesser-root` → `TB044` — the tree is not declared;
- unrecognized content → `TB044` — the one recognized kind is `app`;
- a `.tesser-root` found *below* the root → `TB044` — a run covers one
  declared tree; run the nested tree directly.

A declaration finding short-circuits every other rule: an undeclared tree gets
exactly the declaration findings and nothing else, because walk findings about
a tree that never claimed to be a tree are noise. Run at the repo root today,
tessercheck reports one line per declared tree below — a map, not a smoosh.

**The repo declares its shape: `manifest.json`.** Every top-level directory
and every `examples/` subdirectory has a row naming its kind — `python-app`,
`python-library`, `go`, `docs`, `skills`, `scripts`, `hybrid`, `config`,
`spike`, `meta`, `examples`. The interesting property is what a *kind* buys:

- `python-app` — a declared tesser tree; gated by `scripts/verify` with
  tessercheck at zero findings. The manifest row and the `.tesser-root` file
  must agree, both ways.
- `python-library` — gated by `scripts/verify` (mypy + pytest), deliberately
  not a tessercheck subject (`tesser-py`, `examples/vobase`). The decision not
  to check a tree is now written down, not implied by absence.
- everything else — named so its coverage story is visible (`go` is covered by
  the Go gates, `spike` is explicitly ungated, and so on).

## The guard

`scripts/check-topology` (stdlib Python, no venv needed) holds four equalities:

1. top-level directories on disk == manifest rows, both directions;
2. `examples/*` directories == manifest rows, both directions;
3. the set of `.tesser-root` files in the repo == the set of `python-app`
   rows, and each declares `app`;
4. every `python-app`/`python-library` row has a CI job invoking
   `scripts/verify <tree>`.

`scripts/verify` runs the guard as step 0 and **derives its tree list from the
manifest** — the hand-maintained `TREES` array is gone. A manifest tree with
no `run_*` arm fails as "unknown tree" rather than silently not running. A new
top-level directory without a manifest row fails CI before any other job runs.

## Why there is no "run this dir as domain" flag

The alternative considered was an invocation mode: `tessercheck --as domain
<dir>` for checking partial trees. Rejected by derivation, not taste:

- The repo's placement rules exist because **where a thing sits fixes what it
  is** — placement is declared in the tree, once, and every reader of the tree
  sees the same truth. A mode flag moves that truth into the invocation:
  two people (or two CI jobs) running different flags on the same directory
  get different findings, which is the configuration-drift failure the
  zero-findings gate exists to prevent.
- Every enforced rule is keyed on a module's position in a full tree (role,
  tier, context). A partial-tree mode would need a synthetic context around
  the fragment — a second interpretation of every placement rule, maintained
  forever, for the benefit of trees that could instead just be complete.
- All six checked example trees were already complete apps; the only
  non-conforming trees were libraries, and `python-library` in the manifest
  covers them as a declared kind rather than a mode.

So: every checked tree is a whole app, every unchecked tree says what it is
instead, and the invocation carries no opinions.

## What consumers must do on upgrade

This is a breaking change for consumer repos (certus, metron, quanta, the
pilot): after upgrading the analyzer, a tessercheck run on an undeclared tree
produces a `TB044` finding. The migration is one file: add `.tesser-root`
containing `app` at each checked tree root. The manifest and check-topology
are this repo's own guard, not part of the analyzer; consumers may copy the
pattern but nothing requires it.
