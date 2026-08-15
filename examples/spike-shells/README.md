# spike-shells — the declare-then-verify spike

The totality architecture as running code: `tesser-py`'s shell classes
(`ts.ValueObject`, `ts.AggregateRoot`, `ts.ApplicationService`, `ts.Handler`,
…) carry no behavior — subclassing one is a *declaration* of what a class is —
and the analyzer verifies everything against its declaration. Two worked
contexts live here (`spike/`, a note service, and `digest/`, which reaches
spike only through its client — the one legal cross-context edge).

The analyzer itself grew up in this tree as **sigcheck** and graduated to
[`tessercheck-py/`](../../tessercheck-py/) as **tessercheck**, taking
its rule set ([`RULES.md`](../../tessercheck-py/RULES.md)), its generator, and
its tests with it. This tree stays what it was built to be — the worked
example — and is gated at zero findings by the analyzer it hatched.

## Verify this tree

```sh
(cd ../../tessercheck-py && PYTHONPATH=.:../tesser-py python3 -m srv.cli.main ../examples/spike-shells)
MYPYPATH=.:../../tesser-py mypy --strict spike digest
pytest -q
PYTHONPATH=.:../../tesser-py lint-imports --no-cache # the import contracts
```

CI runs the same four steps (`scripts/verify spike-shells`).
