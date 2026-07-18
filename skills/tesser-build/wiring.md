# Context wiring

<!-- tb-status: stub -->

A context's **own construction**: the one module inside the context that builds
its object graph — picks the repository implementation from the context's
config, composes the application service behind the public `Client`, and hands
back the built `Client` (plus whatever must be closed). The app-level
composition root (`bootstrap.md`) *calls* each context's wiring; it never
reaches into a context to assemble the pieces itself.

> **Status: stub — not yet materialized.** Note the gap, don't invent a
> convention; the verified impl is `examples/python-app/campaign/wiring/`
> (`wire.py` + `config.py`), with `examples/python-app/reports/wiring/` as the
> minimal case.

What the verified impl locks, pending the full doc:

- **Each context owns a `wiring` role** (required for app contexts, absent for
  library contexts — `map.md#app-vs-library`).
- **The context's `Config` lives in its wiring, never on the public seam**
  (`wiring/config.py`: spec-shaped, primitive leaves). The app `Config` nests
  the per-context ones (`bootstrap.md#app-config`).
- **Impl selection is coordinate-driven and fail-fast** — an absent coordinate
  is an error, never a silent fall into an in-memory default.
- **Cross-context dependencies arrive injected.** `campaign`'s wiring takes the
  `TargetChecker` as a parameter; it does not build the adapter over the peer —
  only the composition root knows two contexts at once
  (`gateway-cross-context.md`).
