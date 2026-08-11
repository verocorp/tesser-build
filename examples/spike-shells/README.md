# spike-shells — the declare-then-verify spike

The totality architecture as running code: `tesser-py`'s shell classes
(`ts.ValueObject`, `ts.AggregateRoot`, `ts.ApplicationService`, `ts.Handler`,
…) carry no behavior — subclassing one is a *declaration* of what a class is —
and **sigcheck** is the verifier that checks everything against its
declaration. Two worked contexts live here (`spike/`, a note service, and
`digest/`, which reaches spike only through its client — the one legal
cross-context edge), and sigcheck is itself written in the idiom it checks and
runs over its own tree in CI.

The full rule set is [`RULES.md`](RULES.md) — generated from the
implementation by `rules.py`, never hand-edited; one row per normative
clause, with exact fixture coverage. `python3 rules.py --check` (and a test)
fails when it drifts.

## Running sigcheck on any tree

sigcheck is stdlib-only. The only things it needs on `PYTHONPATH` are this
directory (its own package) and `tesser-py` (the shells sigcheck itself is
built from):

```sh
PYTHONPATH=/path/to/go-ddd/examples/spike-shells:/path/to/go-ddd/tesser-py \
  python3 -m sigcheck /path/to/tree
```

As a shell function:

```sh
sigcheck() {
  PYTHONPATH=~/workspace/vero/go-ddd/examples/spike-shells:~/workspace/vero/go-ddd/tesser-py \
    python3 -m sigcheck "${1:-.}"
}
```

Exit 0 when clean; exit 1 with one finding per line, flake8-style:

```
path/to/file.py:line: TB0xx <module.Class.method> <specifics>; <normative clause>
```

The clause after the semicolon is the rule — the same text as its RULES.md
row — and the `TB0xx` code names the rule family (RULES.md's Code column).
Codes are reporting affordances, not an adoption mechanism: CI is always
zero-findings, and the only opt-out is per instance, at the site. A trailing
`# tessercheck:ignore` suppresses that line's findings;
`# tessercheck:ignore TB052` suppresses exactly that family on the line; a
`# tessercheck:ignore-file TB040` anywhere in a file suppresses the family
module-wide. An ignore that suppresses nothing is itself a finding (TB090),
so opt-outs cannot outlive their reason.

## What to expect on an arbitrary tree

- **The target is parsed, never imported.** It needs nothing installed and
  nothing leaves the machine — pure AST analysis.
- **Classification is nominal.** A context is any package with role modules
  (`domain` / `application` / `client` / `adapters` / `wiring`, as modules or
  subtrees), and a class's kind is its declared `ts.*` base. A tree that
  declares nothing still answers to the rules that need no declaration. On
  unmigrated code the two loud families are **whole-tree totality** — every
  module must belong to a context, `srv`, `bootstrap`, `tests`, or a wire
  module (a top-level `*wire.py`), so a module with no home is a finding —
  and **test totality**, where every
  `test_*.py` anywhere is held to the tests / `@ts.helper` / `@ts.fake`
  rules. The per-role rules (placement, imports, signatures) reach only the
  modules the layout already names as a role.
- **The reader prunes tooling directories** (`.venv`, `node_modules`,
  `build`, `__pycache__`, and the rest of the standard skip set) and fails
  soft per file: an unparseable module, a non-UTF-8 file, or a module defined
  twice (`domain.py` beside `domain/__init__.py`) is a TB043 finding, never a
  crashed run.
- **Whole-tree per run, opt-out per instance.** sigcheck audits everything
  under the root; there is no `--exclude` and no code-family off switch.
  A finding is either fixed or carries a site-level
  `# tessercheck:ignore` (see above). `examples/python-app` still runs the
  transitional CI ratchet (`sigcheck-ratchet`, a finding set with line
  numbers stripped) while it burns its bill down; the ratchet retires when
  these rules graduate into `tessercheck-py` and the remaining debt becomes
  inline opt-outs.

## Verify this tree

```sh
PYTHONPATH=.:../../tesser-py python3 -m sigcheck .   # self-check: must be clean
python3 rules.py --check                             # RULES.md drift gate
MYPYPATH=.:../../tesser-py mypy --strict spike sigcheck digest tests rules.py
pytest -q
PYTHONPATH=.:../../tesser-py lint-imports --no-cache # the import contracts
```

CI runs the same five steps.
