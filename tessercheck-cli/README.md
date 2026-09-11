# tessercheck-cli

The console entry point for the analyzer, packaged so it can be installed and
run outside a tesser-build checkout:

```
tessercheck-check <tree>
```

Exit codes are the checkout host's: `0` clean, `1` findings (one per line on
stdout), `2` usage. An unexpected error raises — a consumer debugging a crash
in CI wants the traceback, not a swallowed exit code.

## Why this is a second distribution and not part of tessercheck-py

`tessercheck-py`'s own host is `srv/cli/main.py`, and it imports `app.loader`
and `protocol.cli`. Those names are not incidental: TB040 mandates that every
module belong to a context, a kernel, `srv`, `app`, `tests`, or `protocol`, so
the analyzer tree cannot rename them. They also cannot be shipped. A consumer
of the analyzer is typically a tesser app itself, with its own top-level
`app/`, `srv/`, and `protocol/` packages; putting those three names into its
site-packages gives its type checker, test runner, and import linter two
candidates for each, resolved by working directory. That is a silent site,
which is the cost this repo exists to measure.

So the wheel ships what a distribution can honestly ship — the component and
its client — and the entry point lives here, in a package name nothing
collides with. This directory is `ungated` in `manifest.json`: it is packaging,
not an app, and it holds no domain rules to check. `scripts/verify-packaging`
is what keeps it honest, by installing the three distributions into a clean
virtualenv and running the console script for real.

## Installing

The distributions are not on PyPI, and `tessercheck-py` depends on `tesser` by
name, so all three are named in one command and pip resolves them against each
other:

```
pip install \
  "tesser @ git+https://github.com/<owner>/tesser-build@<rev>#subdirectory=tesser-py" \
  "tessercheck-py @ git+https://github.com/<owner>/tesser-build@<rev>#subdirectory=tessercheck-py" \
  "tessercheck-cli @ git+https://github.com/<owner>/tesser-build@<rev>#subdirectory=tessercheck-cli"
```

Pin all three to the same rev. `tessercheck-check` is a distinct command from
the old `python -m tessercheck --app-root .`, so a repo mid-migration can carry
both without either shadowing the other.

## The post-write hook

`tessercheck-hook` is a Claude Code `PostToolUse` hook. It reads the event
Claude Code puts on stdin, and on an `Edit` or `Write` of a `.py` file under a
declared tree it runs the analyzer over that tree and reports the findings on
the written file only — CHECK-ONE: every module is parsed, so cross-module
rules see the whole universe, but the rule pass runs for the written module
alone, and an equivalence test in `tessercheck-py` asserts the answer matches
the whole-tree run filtered to that file. On a `Skill` load of `tesser-build`
or a `Read` under `.claude/skills/tesser-build/` it records a guidance event
for the session instead.

Wire it through a committed wrapper so the venv path lives in one file and a
non-Python write never starts an interpreter:

```sh
#!/bin/sh
# scripts/tesser-hook — the one file that knows where the venv is
event=$(cat)
case "$event" in
  *'"tool_name": "Skill"'*|*'"tool_name":"Skill"'*|*'"tool_name": "Read"'*|*'"tool_name":"Read"'*|*.py\"*) ;;
  *) exit 0 ;;
esac
printf '%s' "$event" | exec "$CLAUDE_PROJECT_DIR/.venv/bin/tessercheck-hook"
```

```json
{
  "hooks": {
    "PostToolUse": [
      {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/scripts/tesser-hook", "timeout": 20}]},
      {"matcher": "Skill|Read", "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/scripts/tesser-hook", "timeout": 5}]}
    ]
  }
}
```

Two modes, chosen per machine by a gitignored `.tesser/hook.conf` next to the
repo root (`mode=advisory|feedback`, `enabled=true|false`; a missing or
malformed file means advisory and enabled):

- **advisory** (the default) answers with `hookSpecificOutput.additionalContext`
  naming the findings on the written file, exit 0.
- **feedback** writes the findings to stderr behind a one-line preamble and
  exits 2, so Claude self-corrects on its next turn.

The hook never blocks the write, never shows a traceback, and fails open: the
analysis runs in a child process with a 15-second budget
(`TESSERCHECK_HOOK_BUDGET` overrides it), and a timeout or an error is a log
line, not output. Every run appends one line to the gitignored
`.tesser/changes.jsonl`:

```
{actor, session_id, ts, relpath, source: "write", placement: governed|skipped|outside|undeclared,
 findings: ["TB0xx:relpath", ...], findings_count, mode, guidance: ["skill:tesser-build", "read:python.md", ...],
 status: ok|timeout|error|disabled, exit_code, duration_ms}
```

`guidance` is the list of guidance events recorded so far in the session
(`.tesser/sessions/<session_id>.jsonl`, pruned after seven days), in order.
It says which guidance paths had loaded before the write and nothing more.
A green line is file-local: a write can create findings on other files, which
the whole-tree run at commit or in CI reports. `scripts/verify-packaging`
drives the installed hook through every case above.
