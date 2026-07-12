# Python worked example

The verified Python rendering of the `skills/ddd` mechanics — the peer of the
Go examples (`examples/ddd`, `examples/lending`, `examples/running`). Every
pattern `skills/ddd/python.md` teaches is backed by runnable code here, gated
by `mypy --strict` and `pytest` in CI.

## Layout

- **The running arc** (top-level packages) — a link-campaign HTTP service, the
  full vertical slice:
  - `campaign/` — the domain: value objects, the `ShortLink` entity, the
    `Campaign` aggregate.
  - `campaignapp/` — the application service + the repository `Protocol`.
  - `linkcampaign/` — the public contract: the `Client` `Protocol` + DTOs.
  - `linkcampaignimpl/` — the concrete implementation: in-memory repository, and
    the `new_client` seam that satisfies `Client` structurally.
  - `transport/` — the HTTP handler (depends only on `Client`).
  - `main.py` — the composition root (`wire()`), plus a runnable `main()`.
- **`catalog/`** — the two value-object shapes the running arc doesn't need: a
  compound VO (`Money`, `decimal.Decimal`) and a collection VO (`Labels`), with
  a `Product` entity holding them.
- `tests/` — the test suite for both.

## Run it

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

# type-check (must be clean under --strict)
MYPYPATH=. mypy --strict campaign campaignapp linkcampaign linkcampaignimpl transport catalog main.py tests conftest.py

# tests
pytest -q

# run the service
python main.py   # serves the link-campaign API on :8080
```

No packaging step: `conftest.py` puts this directory on `sys.path` so the
top-level packages import directly (plain `venv`, standard-library only).
