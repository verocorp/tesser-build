# The mutmut ecosystem gate

Not a mutation-score gate. The claim under test is that building a value
object on `ts.ValueObject` leaves it fully visible to mutmut, while the
obvious alternative construction (a frozen dataclass) is skipped by mutmut
wholesale — hand-written methods included — so its behavior silently escapes
mutation testing. Both fixtures are the same `Amount` value object; only the
construction differs (`test_fixtures_stay_in_lockstep` enforces that
everything except `vo/amount.py` is byte-identical). mutmut is invoked
through its public CLI, pinned exact in `requirements-dev.txt`, because the
assertions describe observed behavior of that version: if an upgrade changes
either outcome, this test is the place that finds out. The pin is
best-effort — mutmut's own dependencies (libcst generates the mutants,
pytest runs them) float, so an upstream release can also move these
assertions; a red run here with no repo change means the ecosystem moved,
which is exactly what this test is for.

## Why the harness is shaped the way it is

- **Fixture copies exclude run leftovers** (`mutants/`, caches):
  `shutil.copytree` preserves mtimes, and mutmut reuses a `mutants/` tree
  that is newer than its source — a stale, gitignored `mutants/` in the
  fixture dir would freeze this test green against a snapshot forever.
- **Subprocesses run in their own session and the group is killed on
  timeout**: mutmut forks workers; without this, a hung worker outlives the
  test.
- **The inner pytest env is an allowlist**: the control run and mutmut's
  forked runner must not inherit the outer session's pytest/coverage
  configuration. The `"."` on `PYTHONPATH` resolves against the fixture
  project cwd (and, inside mutmut's runner, against `mutants/` — where
  mutmut chdirs; an internal but pinned behavior).
- **Each fixture suite first proves itself under plain pytest**: mutmut
  reports "no test case for any mutant" for an empty suite too, so without
  the control run the dataclass assertions would hold vacuously.
- **`mutmut run` exit 0 is a crash check only** — a suite that kills nothing
  still exits 0 (verified). Survivor accounting is `results_output()`'s job,
  and `mutmut results` exits 1 with empty stdout on missing state, so its
  return code is asserted before its emptiness means anything.
