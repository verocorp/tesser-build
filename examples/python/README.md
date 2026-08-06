# Python worked example

The verified Python rendering of the `skills/tesser-build` mechanics — the peer of the
Go examples (`examples/ddd`, `examples/lending`, `examples/running`). Every
pattern `skills/tesser-build/python.md` teaches is backed by runnable code here, gated
by `mypy --strict` and `pytest` in CI.

## Layout

- **`campaign/`** — the domain: value objects, the `ShortLink` entity, the
  `Campaign` aggregate.
- **`catalog/`** — the two remaining value-object shapes: a compound VO
  (`Money`, `decimal.Decimal`) and a collection VO (`Labels`), with a
  `Product` entity holding them.
- `tests/` — the test suite for both.

The application arc that used to live here (service + interface-package
public contract + HTTP transport + composition root) was dropped: the
two-package `linkcampaign`/`linkcampaignimpl` interface pattern is superseded
by the per-context `client.py` anatomy, whose full worked example is
`examples/python-app/`.

## Run it

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

# type-check (must be clean under --strict)
MYPYPATH=. mypy --strict campaign catalog serialization.py tests conftest.py

# tests
pytest -q
```

No packaging step: `conftest.py` puts this directory on `sys.path` so the
top-level packages import directly (plain `venv`, standard-library only).
