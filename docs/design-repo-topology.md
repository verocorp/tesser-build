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
`.tesser-root` file at its root. The file has a total grammar — anything
outside it is a finding by default, the same move as TB069:

```
app
skip testdata
```

The first line is the kind (`app` is the only one — see "Everything is an
app"). Every further line is a `skip <dir>` directive naming a directory the
walk ignores for this tree. This is where repo-specific configuration lives:
**the analyzer carries nothing specific to any repo** (maintainer ruling
2026-08-14) — tessercheck-py's own fixture directory is skipped by *its*
declaration, not by a hardcoded name in the reader. The universal skip set
(`.git`, `__pycache__`, venvs, caches, `build`/`dist`) stays in the reader
because it is universal, not repo-specific.

The declaration state is a fact the reader reports and the domain rules judge:

- no `.tesser-root` → `TB044` — the tree is not declared;
- unreadable (not UTF-8 text, or not a regular file) → `TB044`;
- unrecognized first line or directive → `TB044`;
- a `.tesser-root` *below* the root → `TB044` — a run covers one declared
  tree; run the nested tree directly;
- a **symlinked directory** inside the tree → `TB045` — `os.walk` does not
  follow symlinks, so a symlink would smuggle unwalked code into a
  zero-findings gate; the walk reports what it cannot cover.

A declaration or walk-integrity finding short-circuits every other rule:
findings about a tree that never claimed to be a tree — or that could not be
walked in full — are noise. Run at the repo root, tessercheck reports one line
per declared tree below — a map, not a smoosh. TB044/TB045 report on files
that cannot carry a Python comment, so they are the one family an inline
ignore can never suppress.

**The repo declares its shape: `manifest.json`.** Every top-level directory
and every `examples/` subdirectory has a row. There are exactly two kinds,
because **everything is an app** (maintainer ruling 2026-08-14: there is no
library concept — a "library" is an app that does no IO but still exposes a
client and coordinates its domain through an application service; revisit only
when someone has a real performance problem):

- `app` — a Python tree gated by `scripts/verify`. `tesser-py` and
  `examples/vobase` are app rows whose arms run mypy + pytest today and gain
  the tessercheck step when their trees are migrated to conform — a config
  change, not an ontology change.
- `ungated` — not a subject of the Python gate system (Go directories are
  covered by the Go jobs; docs and skills by their own checks).

Earlier drafts had eleven kinds; nine were labels nothing read — prose wearing
a schema. The word is not the guard. The witnesses are.

## The guard

`scripts/check-topology` (stdlib Python, no venv needed) holds the witnesses:

1. top-level directories on disk == manifest rows, both directions;
2. `examples/*` directories == manifest rows, both directions;
3. a tree carries `.tesser-root` **exactly when** its `scripts/verify` arm
   runs tessercheck — demoting either side alone goes red (and deleting a
   declaration can't demote a checked tree anyway: the analyzer itself goes
   red via TB044);
4. every `app` row has a `scripts/verify` case arm and a CI job step
   `run: scripts/verify <tree>`, and app basenames are unique (verify
   dispatches by basename);
5. every directory holding a `requirements-dev.txt` — **anywhere in the
   repo** — is an `app` row, so a Python tree cannot be filed under a kind
   that drops its gates, at any depth;
6. a symlinked top-level or `examples/*` directory is a failure; deeper
   symlinks inside declared trees are the analyzer's TB045.

The guard has its own pytest suite (`scripts/test_check_topology.py`) pinning
every failure mode against a synthetic repo root — run by the topology CI job,
so "the guard regressed to always-pass" is itself catchable.

`scripts/verify` runs the guard as step 0 and **derives its tree list from the
manifest** — the hand-maintained `TREES` array is gone, and an empty or failed
derivation fails closed rather than reporting green over nothing. A manifest
tree with no `run_*` arm fails as "unknown tree". A new top-level directory
without a manifest row fails CI before any other job runs.

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
