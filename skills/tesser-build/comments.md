# Norm: comments

<!-- tb-status: full -->

**v0 of the comments norm is zero: constructed-app code carries no comments
and no docstrings.** Not "few", not "only good ones" — none. The baseline is
deliberately absolute so that every future exception is an explicit,
principled carve-out added to this file from observed evidence, never a
judgment call made inline at write time (Chris ruling 2026-07-19).

## The norm

1. **No code comments.** No line comments, no block comments, no doc
   comments — in domain code, seams, adapters, wiring, hosts, and tests
   alike. There is no test exemption: the norm covers the whole tree.
2. **No docstrings.** A Python docstring and a Go doc comment are the same
   thing under this norm: prose attached to code. The name, the signature,
   the types, and the tests carry the meaning; prose that restates them
   drifts from them.
3. **Machine directives are exempt.** A directive is an instruction to a
   tool, not prose for a reader. The v0 ledger:
   - Python: shebang (`#!`), coding lines, `# type: ...` (mypy),
     `# noqa...` (a reason may ride the directive), `# tessercheck:ignore`,
     the roadmap marker grammar (`tb-cell` / `tb-status` /
     `tb-allow-missing` lines, `docs/skill-authoring.md`), `# pragma...`, and formatter/linter controls
     (`# fmt:`, `# isort:`, `# ruff:`).
   - Go: `//go:` directives, build constraints (`// +build`), `//line`,
     `//nolint...`, `//export` / `//extern` / `//sys`, the roadmap marker
     grammar (same three, `//`-wrapped), and generated files (`// Code generated ... DO NOT EDIT.` — skipped
     wholesale; a generator's output is the generator's business).
4. **Explanation moves up a layer, it doesn't disappear.** What a comment
   wanted to say belongs in one of the places that can't silently rot
   against the code: the identifier (rename it), the type (make the
   constraint a value object — `value-objects.md`), a test (assert the
   behavior), the commit message (the why of the change), or the skill/docs
   layer (a convention worth teaching). A constraint real enough to write
   down is real enough to live where it is checked or reviewed.

## Why zero, not "good comments only"

- **A comment is a silent site.** It references code that changes without
  it; nothing fails when it goes stale, so it lies with the confidence of
  documentation. This is the same changeability axis the whole toolkit is
  built on (silent-site count) — a wrong comment costs more than a missing
  one.
- **"Good judgment" doesn't survive many hands.** This toolkit's code is
  written by agents and humans over many sessions; a judgment-call norm
  produces a different judgment every time. Zero is the only baseline that
  is mechanically checkable today and consistent by construction.
- **The teaching layer already exists.** This repo separates code from
  explanation deliberately: skill docs teach, examples are clean templates
  cloned into real services, `rationale/` argues. Inline prose in a template
  gets cloned as noise into every consumer.

## Where the norm applies

- **Constructed-app code** — what the skill routes you to build in a
  consumer repo, at every layer (domain, application, adapters, wiring,
  bootstrap, srv, tests).
- **The example trees** (`examples/`) — they are production templates and
  the norm's verified impls; they conform and are gated in CI.
- **Not the toolkit's own internals** (analyzers, generator, rationale
  arms) and **not prose surfaces** (`.md` files, commit messages, PR
  bodies) — those are the layers explanation moves *to*.

## Carve-outs: how an exception gets in

v0 ships with the directive ledger only. A new carve-out is added when real
use (Chris's own, or a de-identified rhema relay) surfaces a case where the
right fix is genuinely a comment — not a rename, not a type, not a test,
not a doc. Each carve-out lands in this file with:

1. the **case** (what kept needing prose at the code site),
2. the **principle** (the rule that makes it recognizable next time),
3. the **enforcement update** (the checkers' exemption ledgers extended in
   the same change — `passes/comments/` and
   `tessercheck-py/tessercheck/comments_check.py`).

Until a case is in this file, it is not an exception. `# tessercheck:ignore`
/ `//nolint:comments` exist for the one-off emergency; a suppression that
recurs is a carve-out candidate to bring here, with its evidence.

## How the machine sees it

- **Python: `TB020` (no-comments)** flags every non-directive comment and
  every docstring, test files included. Suppress a line with
  `# tessercheck:ignore` (itself a directive).
- **Go: the `comments` analyzer** in `tessercheck` flags every
  non-directive comment; generated files are skipped.
- CI gates the norm on the example trees (`examples/ddd` via `tessercheck`;
  `examples/python` via the tessercheck-py acceptance gate;
  `examples/python-app` and `examples/errorspy` via `--select TB020`).

## Common mistakes

- **The apology comment.** `# this is a bit hacky` — the comment is a TODO
  wearing a disguise; fix it or file it where work is tracked.
- **The narrated step.** `# validate the slug` above `slug.validate()` —
  restates the code; deletes for free.
- **The load-bearing comment.** `# NOTE: must run before X` — a real
  constraint living where nothing checks it. Encode the ordering (a type, an
  assertion, a test) or teach it (docs); the comment is the least reliable
  home it could have.
- **Docstring-as-API-docs.** If a seam's contract needs prose, that is the
  public interface doc's job (`public-interface.md`) or a future carve-out
  argued from evidence — not a default.
