# tessercheck-py

The tesser-build construction analyzer for Python — the declare-then-verify
engine that grew up as **sigcheck** in `examples/spike-shells` and graduated
here. `tesser-py`'s shell classes (`ts.ValueObject`, `ts.AggregateRoot`,
`ts.ApplicationService`, `ts.Handler`, …) carry no behavior — subclassing one
is a *declaration* of what a class is — and tessercheck verifies everything
against its declaration. It is written in the idiom it checks and runs over
its own tree in CI.

The full rule set is [`RULES.md`](RULES.md) — generated from the
implementation by `srv/cli/rules.py`, never hand-edited; one row per
normative clause, with a family code and exact fixture coverage.
`PYTHONPATH=.:../tesser-py python3 -m srv.cli.rules --check` (and a test)
fails when it drifts.

The pre-merge analyzer (the frozen-dataclass-era `TB001`–`TB033` checks with
the structural classifier) is gone: every example tree now declares its
blocks with `ts.*` shells, and this analyzer validates all of them. Its one
surviving artifact is the reviewed `TB031` fixture pair
([`testdata/tb031/`](testdata/tb031/)), which fixes that unshipped checker's
contract.

## Running tessercheck on any tree

The analyzer is stdlib-only at check time (the target is parsed, never
imported). It is an app, so it runs through its own host — `srv/cli/main.py`,
from this directory — and takes the tree to check as its argument. The only
things it needs on `PYTHONPATH` are this directory and `tesser-py` (the shells
the analyzer itself is built from):

```sh
cd /path/to/tesser-build/tessercheck-py
PYTHONPATH=.:../tesser-py python3 -m srv.cli.main /path/to/tree
```

Run it from here rather than from the tree being checked: `-m` resolves
against the working directory first, and a checked tree may well have an `srv`
package of its own.

The target declares itself: a checkable tree carries a `.tesser-root` file at
its root. The declaration has a total grammar — first line `app`, then only
`skip <dir>` lines naming directories the walk ignores for this tree (this is
where repo-specific configuration lives; the analyzer hardcodes nothing about
any repo). An undeclared, unreadable, or unrecognized root, or a
`.tesser-root` nested below the root, is a `TB044` finding; a symlinked
directory inside the tree is `TB045`, because the walk never follows symlinks
and must say what it could not see. When a TB044 or TB045 fires it is the only
finding reported, so pointing the analyzer at a directory that never claimed
to be a tree reports that fact instead of walking it — and these findings land
on files that cannot carry a Python comment, so an inline ignore can never
silence them.

Exit 0 when clean; exit 1 with one finding per line, flake8-style:

```
path/to/file.py:line: TB0xx <module.Class.method> <specifics>; <normative clause>
```

The clause after the semicolon is the rule — the same text as its RULES.md
row — and the `TB0xx` code names the rule family (RULES.md's Code column).
Codes are reporting affordances, not an adoption mechanism: CI is always
zero-findings, and the only opt-out is per instance, at the site. A trailing
`# tessercheck:ignore` suppresses the findings *reported at* that line (for
a signature finding that is the `def` line); `# tessercheck:ignore TB052`
suppresses exactly that family on the line (several codes may follow,
space- or comma-separated); `# tessercheck:ignore-file TB040` anywhere in a
file suppresses the family module-wide — the file form **requires** codes,
because a blanket module switch is not a per-instance opt-out. An ignore
that suppresses nothing is itself a finding (TB090), TB090 itself cannot be
ignored, and the grammar is strict: a typo in the marker word or a token
that is not a `TB0xx` code makes the comment inert, so the finding it meant
to hide stays visible. TB043 reader findings (unparseable, unreadable, or
twice-defined files) are never inline-suppressible — a file the parser
cannot read cannot carry a working marker, so those are fixed, not excused.

### From an install, outside a checkout

A consumer repo cannot depend on a checkout being there, and the host is not
shippable: `srv/cli/main.py` imports `app.loader` and `protocol.cli`, and
`app`, `srv`, and `protocol` are the names TB040 mandates — every tesser app
has its own, so a wheel that put them in site-packages would give the consumer
two of each. The wheel therefore ships what a distribution can honestly ship,
the component and its client, and the console entry point lives in its own
distribution, [`tessercheck-cli`](../tessercheck-cli/):

```sh
tessercheck-check /path/to/tree
```

Same exit codes, same one-finding-per-line output. `tessercheck-check` is a
distinct command from the pre-graduation `python -m tessercheck --app-root .`,
so a repo migrating off the old analyzer can install both without either
shadowing the other. Installation, and why all three distributions are named
in one `pip install`, are in that directory's README.

`scripts/verify-packaging` is the gate on all of this: it builds the three
distributions from a pristine copy, installs them into a clean virtualenv with
no source tree on the path, imports every shipped module, and runs
`tessercheck-check` for real. The checkout gates cannot see packaging defects —
they run with `PYTHONPATH` pointed at the source, where a module missing from
a wheel's package list imports perfectly well.

## What to expect on an arbitrary tree

- **The target is parsed, never imported.** It needs nothing installed and
  nothing leaves the machine — pure AST analysis.
- **Classification is nominal.** A context is any package with role packages
  (`domain` / `application` / `client` / `adapters` / `wiring`), and a
  class's kind is its declared `ts.*` base. A tree that declares nothing
  still answers to the rules that need no declaration: whole-tree totality
  (every module belongs to a context, `srv`, `bootstrap`, `tests`, or the
  protocol package), the import rows (every module carries one, keyed on
  where it sits — a root module and a `conftest` are leaves that import
  nothing from the tree), test totality, and the universal norms (comments,
  test doubles, shadowed builtins, string-form equality).
- **The reader prunes tooling directories** (`.venv`, `node_modules`,
  `build`, `__pycache__`, and the rest of the standard skip set) and fails
  soft per file: an unparseable module, a non-UTF-8 file, or a module
  defined twice is a TB043 finding, never a crashed run.
- **Whole-tree per run, opt-out per instance.** There is no `--exclude` and
  no code-family off switch. A finding is either fixed or carries a
  site-level `# tessercheck:ignore` (see above) — every gated tree,
  `examples/python-app` included, runs at zero findings with its
  ruling-blocked sites carrying coded ignores that TB090 keeps honest.

## Verify this tree

```sh
PYTHONPATH=.:../tesser-py python3 -m srv.cli.main .  # self-check: must be clean
python3 -m srv.cli.rules --check                     # RULES.md drift gate
MYPYPATH=.:../tesser-py mypy                         # --strict via pyproject
pytest -q
PYTHONPATH=.:../tesser-py lint-imports --no-cache    # the import contracts
```

CI runs the same five steps (`scripts/verify tessercheck-py`).
