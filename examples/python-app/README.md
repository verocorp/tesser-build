# examples/python-app — the composition-root / bounded-context wiring template (Python)

A runnable, CI-gated Python **application** that materializes the settled
bounded-context anatomy and the `srv` / `config` / `bootstrap` model. It is the
Python mirror of `examples/app` (Go) and a shape a real service can clone. It is a
**production reference template**, not a teaching toy: a mistake here replicates
into every service cloned from it, so the example **enforces itself** (see below).

## The scenario — two contexts, two moments they touch

- **`campaign`** — short links: create + resolve (owns the redirect).
- **`linkpolicy`** — our OWN destination-policy context (allowed schemes, blocked
  hosts). A peer context we own, reached by an ordinary cross-context port — *not*
  a third-party feed (that would be a vendor ACL, a different shape).

1. **Moment 1 — a cross-context CALL.** Creating a short link must vet its
   destination: `campaign → linkpolicy`, **synchronous and fail-closed**. A policy
   rejection *or* a linkpolicy outage makes `create_link` fail and create nothing
   — the honest error propagates. campaign owns the `TargetChecker` port; the
   adapter over `linkpolicy.Client` lives in `campaign/adapters/gateways`, so the
   dependency runs one way and `linkpolicy` stays ignorant of `campaign`.
2. **Moment 2 — a cross-context READ.** "links by policy verdict" needs the link
   (campaign) + the verdict (linkpolicy). It belongs to neither, so it lives in a
   root-level `reports` orchestrator above both — putting it in `linkpolicy` would
   close a `linkpolicy → campaign` cycle. Demonstrated **in-process** on one `App`.

```
campaign  ──▶ linkpolicy      (Moment 1, via campaign.TargetChecker)
reports   ──▶ campaign  ┐
reports   ──▶ linkpolicy┘     (Moment 2: reads both, lives above both)
linkpolicy ──▶ (nobody)
```

## Anatomy

Each context has the four roles — `domain`, `application`, `adapters`
(`handlers` inbound, `gateways` outbound), `wiring` — with the public `Client`
Protocol + primitive DTOs at its top level. A context's own config lives in its
`wiring`, never on the public seam.

App-level: `config.py` is the single env edge (a shared pure `from_env` decoder the
hosts call); `bootstrap` is the service-owned composition root (`new(cfg) -> App`,
builds the graph once with a cleanup stack, `App.close()`); `srv/{http,cli}` are
the hosts, one per delivery mechanism, each calling `bootstrap.new` once.

## Run it

```
CAMPAIGN_STORAGE=memory LINKPOLICY_STORAGE=memory python -m srv.http.main
CAMPAIGN_STORAGE=memory LINKPOLICY_STORAGE=memory python -m srv.cli.main create-link promo https://ok.example/x
```

## Gate

```
pip install -r requirements-dev.txt
MYPYPATH=. mypy --strict errors.py lifecycle.py config.py campaign linkpolicy reports bootstrap srv tests conftest.py
pytest -q
```

`mypy --strict` + `pytest` are the same bar the other examples meet. The
`tests/test_enforcement.py` checks (env read only at the config edge; only the edge
exits; no import-time side effects) and `tests/test_direction.py` (linkpolicy never
imports campaign) are **executable spec** — they fail on the violations the template
exists to prevent, and a clone inherits them by copying the tree. The general
`ddd-vet` analyzer that generalizes these checks across repos is a separate
follow-on.
