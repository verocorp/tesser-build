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
