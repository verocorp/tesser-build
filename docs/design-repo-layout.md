# Repo layout — every directory says what it is, and a check enforces it

Two files and one check. A checkable tree marks itself with a `.tesser-root`
file at its root; `manifest.json` says what every top-level directory is; and
the layout app (`layout/`) fails when the directories on disk and those files
disagree in either direction.

## The problem this solves

Three related holes, all of the same shape — coverage was implicit:

1. **A tessercheck run inferred its subject.** `python -m tessercheck <dir>`
   walked whatever it was pointed at. Run at the repo root, it would treat
   every unrelated tree as one and report nonsense; run on a random
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
`.tesser-root` file at its root. The file allows exactly four things, and
anything else is a finding by default — the same move as TB069:

```
app
skip testdata
export tesser
import money_kernel
```

The first line is the kind (`app` is the only one — see "Everything is an
app"). Every further line is one of: a `skip <dir>` directive naming a
directory the walk ignores for this tree; an `export <dir>` directive naming
the tree's **exported kernel** (at most one line — a tree has one exported
kernel, because the export is the package's import name and a package has
one name; see `docs/design-kernels.md`); an `import <package>` directive
naming an external kernel this tree's pure roles and kernels may import; or
a `stdlib <module>` directive adding a stdlib module to the pure stdlib the
domain role and kernels may import (`docs/design-kernels.md`). This is where repo-specific configuration lives:
**the analyzer carries nothing specific to any repo** (maintainer ruling
2026-08-14) — tessercheck-py's own fixture directory is skipped by *its*
declaration, not by a hardcoded name in the reader. The universal skip set
(`.git`, `__pycache__`, venvs, caches, `build`/`dist`) stays in the reader
because it is universal, not repo-specific.

The declaration state is a fact the reader reports and the domain rules judge:

- no `.tesser-root` → `TB044` — the tree is not declared;
- unreadable (not UTF-8 text, or not a regular file) → `TB044`;
- unrecognized first line or directive → `TB044`;
- a second `export` line, an export naming no package at the tree root, or
  an export taking the name of `kernel` or an app-shell package → `TB044`;
- a `.tesser-root` *below* the root → `TB044` — a run covers one declared
  tree; run the nested tree directly;
- a **symlinked directory** inside the tree → `TB045` — `os.walk` does not
  follow symlinks, so a symlink would smuggle unwalked code into a
  zero-findings gate; the walk reports what it cannot cover.

When a TB044 or TB045 finding fires, it is the only finding reported —
findings about a tree that never claimed to be a tree, or that the analyzer
could not fully see, are noise. Run at the repo root, tessercheck reports one
line per declared tree below it instead of treating the separate trees as
one. TB044/TB045 report on files that cannot carry a Python comment, so they
are the one family an inline debt marker can never suppress.

**The repo declares its shape: `manifest.json`.** Every top-level directory
and every `examples/` subdirectory has a row. There are exactly two kinds,
because **everything is an app** (maintainer ruling 2026-08-14: there is no
library concept — a "library" is an app that does no IO but still exposes a
client and coordinates its domain through an application service; revisit only
when someone has a real performance problem):

- `app` — a Python tree that `scripts/verify` runs. Every app row now
  carries the tessercheck step, `tesser-py` included: its `.tesser-root`
  declares `export tesser`, and the analyzer governs the distribution under
  the shells rows (`docs/design-kernels.md`). (`examples/vobase` was an app
  row until 2026-08-15; its real purpose — showing that mutmut sees through
  `ts.ValueObject` but skips a dataclass — is now an ecosystem test in
  `tesser-py/tests/ecosystem/mutmut/`, so the tree retired.)
- `ungated` — not part of the Python gates (Go directories are covered by the
  Go jobs; docs and skills by their own checks; `tessercheck-cli` by the
  packaging job, below).

`tessercheck-cli` is the one `ungated` row that holds production Python, and
it is worth saying why rather than leaving it to look like an oversight. It is
the console entry point for the analyzer — the `tessercheck-check` command a
consumer repo installs. It cannot be part of `tessercheck-py`, because the
analyzer's own host is `srv/cli/main.py` and it imports `app.loader` and
`protocol.cli`: TB040 mandates those names, every tesser app has its own set,
and a wheel that put them in site-packages would give a consumer two of each,
resolved by working directory. So the wheel ships the component and its
client, the entry point ships separately under a name nothing collides with,
and the shim holds one composition root and no domain rules — there is nothing
for tessercheck to check.

The gap that leaves is real, and `scripts/verify-packaging` closes it. Every
tree gate runs from a checkout with `PYTHONPATH` pointed at the source, which
means a module missing from a wheel's package list — or one importing a
package the wheel cannot ship — passes every gate in this repo. Both have
happened. The packaging job builds the three distributions from a pristine
copy (setuptools does not prune `build/lib`, so a package dropped from
`pyproject.toml` still ships from the stale duplicate), installs them into a
clean virtualenv with no source tree on the path, imports everything shipped,
and runs `tessercheck-check` for real against a clean tree and a dirty one.

Earlier drafts had eleven kinds; nine were labels that nothing read, so they
could rot without anything noticing. And a word in a file can be typo'd, so
the check does not rely on the words alone — every kind is backed by a
cross-check on something real.

## The check

The layout app (`layout/`) holds these. It is itself a full tesser app —
because everything is an app, including the tool that checks that everything
is an app: the rules live in `layout/repo/domain/rules.py` as a `Repo`
aggregate, a filesystem reader adapter feeds it, a client exposes `check` and
`trees`, and `srv/cli/check.py` / `srv/cli/trees.py` are the entry points
(`cd layout && PYTHONPATH=.:../tesser-py python3 -m srv.cli.check <root>`).
It needs only the in-repo `tesser-py` on the path, so a bare CI checkout can
run it with system Python. What it holds:

1. top-level directories on disk == manifest rows, both directions;
2. `examples/*` directories == manifest rows, both directions;
3. a tree carries `.tesser-root` **exactly when** its `scripts/verify` steps
   run tessercheck — changing either side alone fails (and deleting a
   `.tesser-root` can't quietly un-check a tree anyway: the analyzer itself
   fails via TB044);
4. every `app` row has a `scripts/verify` case arm and a CI job step
   `run: scripts/verify <tree>`, and no two app rows share a directory name
   (verify picks its steps by that name);
5. every directory holding a `requirements-dev.txt` — **anywhere in the
   repo, at any depth** — is an `app` row, so a Python tree cannot be filed
   under a kind that drops its gates;
6. a symlinked top-level or `examples/*` directory is a failure; deeper
   symlinks inside declared trees are the analyzer's TB045.

The app is tested at four tiers, each reaching only what its placement
allows: the rules have a test per failure case beside them
(`layout/repo/domain/test_rules.py`, built specs, no filesystem); the service
is tested in isolation through a fake of its reader port and the
DTO-to-domain translation alone (`repo/application/test_service.py`,
`test_mapping.py`); the real reader runs against real filesystems asserting
on port DTOs (`repo/adapters/repositories/test_file_repository.py` — states,
symlinks, skip dirs); and `layout/tests/` keeps a small wired suite proving
everything is hooked up end to end. A bug that made the check always pass
would be caught at the tier that owns it. The app is gated like every tree:
tessercheck zero findings, mypy --strict, pytest.
`scripts/` holds only bash after this — `verify` and `install-dev`, dispatch
with no logic of their own.

`scripts/verify` runs the check as step 0 and **asks the layout app for its
tree list** (`srv/cli/trees.py`) — the hand-maintained `TREES` array is gone,
and if the list comes back empty or the read fails, verify stops with an
error instead of reporting green over nothing. A manifest tree with no `run_*` arm fails as "unknown
tree". A new top-level directory without a manifest row fails CI before any
other job runs.

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
- Every checked example tree was already a complete app, and there is no
  library case to serve: everything is an app (see above), so a partial-tree
  mode would exist for trees that should instead be finished.

So: every checked tree is a whole app, every unchecked tree says what it is
instead, and the invocation carries no opinions.

## What consumers must do on upgrade

This is a breaking change for consumer repos (certus, metron, quanta, the
pilot): after upgrading the analyzer, a tessercheck run on an undeclared tree
produces a `TB044` finding. The migration is one file: add `.tesser-root`
containing `app` at each checked tree root. The manifest and check-layout
are this repo's own machinery, not part of the analyzer; consumers may copy
the pattern but nothing requires it.
