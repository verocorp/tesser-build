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

Exit 0 when clean; exit 1 with one finding per line:

```
module.Class.method:line <specifics>; <normative clause>
```

The clause after the semicolon is the rule — the same text as its RULES.md
row.

## What to expect on an arbitrary tree

- **The target is parsed, never imported.** It needs nothing installed and
  nothing leaves the machine — pure AST analysis.
- **Classification is nominal.** A context is any package with role modules
  (`domain` / `application` / `client` / `adapters` / `wiring`, as modules or
  subtrees), and a class's kind is its declared `ts.*` base. A tree that
  declares nothing still answers to the rules that need no declaration. On
  unmigrated code the two loud families are **whole-tree totality** — every
  module must belong to a context, `srv`, `bootstrap`, or `tests`, so a
  module with no home is a finding — and **test totality**, where every
  `test_*.py` anywhere is held to the tests / `@ts.helper` / `@ts.fake`
  rules. The per-role rules (placement, imports, signatures) reach only the
  modules the layout already names as a role.
- **Point it at a source directory, not a repo root.** The spike-grade reader
  walks every `.py` under the root with no skip list — a `.venv` or
  `node_modules` in scope will be audited too.
- **All-or-nothing per run.** sigcheck has no `--exclude` flag and no built-in
  ratchet — a run audits the whole tree. Adoption is possible *around* the
  tool: freeze today's findings as a baseline and fail only on ones outside
  it. `examples/python-app` does exactly that in CI (`sigcheck-ratchet`, a
  finding set with line numbers stripped) while it burns its bill down. An
  in-tool incremental rollout arrives when these rules graduate into
  `tessercheck-py`.

## Verify this tree

```sh
PYTHONPATH=.:../../tesser-py python3 -m sigcheck .   # self-check: must be clean
python3 rules.py --check                             # RULES.md drift gate
MYPYPATH=.:../../tesser-py mypy --strict spike sigcheck digest tests rules.py
pytest -q
PYTHONPATH=.:../../tesser-py lint-imports --no-cache # the import contracts
```

CI runs the same five steps.
