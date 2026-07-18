# examples/python-app — the composition-root / bounded-context wiring template (Python)

<!-- tb-allow-missing: examples/app -->


A runnable, CI-gated Python **application** that materializes the settled
bounded-context anatomy and the `srv` / `config` / `bootstrap` model — a shape a
real service can clone. (A Go mirror, `examples/app`, is planned but does not
exist yet; this is currently the only worked app example.) It is a
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
<!-- Cross-context read placement was ratified as taught doctrine during
     map.md drafting (Wave 2, 2026-07-18): see
     skills/tesser-build/map.md#how-contexts-connect, incl. the guardrail that a
     read belonging to ONE peer stays in that peer — the new-context move is
     only for composition that belongs to neither. -->
2. **Moment 2 — a cross-context READ.** "links by policy verdict" needs the link
   (campaign) + the verdict (linkpolicy). It belongs to neither peer, so it is
   **its own (small) bounded context** — `reports` — sitting ABOVE both and
   composing their public `Client`s. There is no special "orchestrator role":
   reports has the same anatomy as its siblings (its domain owns the
   join/ordering semantics; adapters are optional because it reaches peers only
   through the injected `Client`s). The cycle is avoided by **dependency
   direction** — reports reads both, nothing imports reports; putting the read
   in `linkpolicy` would force `linkpolicy → campaign` and close a cycle.
   Demonstrated **in-process** on one `App`.

```
campaign  ──▶ linkpolicy      (Moment 1, via campaign.TargetChecker)
reports   ──▶ campaign  ┐
reports   ──▶ linkpolicy┘     (Moment 2: its own context, reads both, above both)
linkpolicy ──▶ (nobody)
```

## Anatomy

Each context has the roles that define it — `domain`, `application`, `wiring`
required; `adapters` (`handlers` inbound, `gateways` outbound) where the context
touches the outside — with the public `Client` Protocol + primitive DTOs at its
top level. `reports` shows the minimum: a context that reaches its peers only
through injected `Client`s needs no adapters of its own. A context's own config
lives in its `wiring`, never on the public seam (`reports/wiring/config.py` is
an empty spec today — the uniform seam a real coordinate would land in).

App-level: **the host is the env edge** — each `srv/*/main` populates the
spec-shaped application `Config` (`bootstrap/config.py`: frozen dataclass,
primitive leaves, no constructor logic, no methods) directly with `os.getenv`
calls, including its own launch config (e.g. the HTTP addr), and hands it to
`bootstrap.new`, which validates fail-fast. `bootstrap` is the service-owned
composition root (`new(cfg) -> App`, builds the graph once with a cleanup stack,
`App.close()`); `srv/{http,cli}` are the hosts, one per delivery mechanism, each
calling `bootstrap.new` once.

## Run it

```
CAMPAIGN_STORAGE=memory LINKPOLICY_STORAGE=memory python -m srv.http.main
CAMPAIGN_STORAGE=memory LINKPOLICY_STORAGE=memory python -m srv.cli.main create-link promo https://ok.example/x
```

## Gate

```
pip install -r requirements-dev.txt
MYPYPATH=. mypy --strict errors.py lifecycle.py campaign linkpolicy reports bootstrap srv tests conftest.py
pytest -q
```

`mypy --strict` + `pytest` are the same bar the other examples meet. The
`tests/test_enforcement.py` checks (env calls only in `srv/*/main`; only the edge
exits; no import-time side effects) and `tests/test_direction.py` (linkpolicy never
imports campaign) are **executable spec** — they fail on the violations the template
exists to prevent, and a clone inherits them by copying the tree. Contexts are
**discovered, not enumerated** (`tests/discovery.py`: any root package exposing a
`Client`), so a new context is checked by construction; the totality guard fails
on any root package that classifies as neither an app-level piece nor a
`Client`-bearing context, so a context that forgot its `Client` cannot hide. The general
`tessercheck` analyzer that generalizes these checks across repos is a separate
follow-on.
