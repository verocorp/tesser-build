# srv — the hosts

<!-- tb-status: stub -->

An app-wide directory of **hosts, one per delivery mechanism** (recommended
subdirs `srv/{http,cli,wrk}`, not enforced). A host's `main` is the outermost
edge of the app: it decodes the environment into the app `Config`, calls
`bootstrap.new(cfg)` **once**, mounts *its* mechanism's inbound handlers across
all contexts, applies cross-cutting middleware (auth/logging/recovery), and owns
the process lifecycle.

> **Status: stub — not yet materialized.** Note the gap, don't invent a
> convention; the verified impl is `examples/python-app/srv/` (`http/main.py`,
> `cli/main.py`).

What the verified impl locks, pending the full doc:

- **The host is the env edge.** Each `srv/*/main` populates the spec-shaped app
  `Config` directly from the environment — including its own launch config
  (e.g. the HTTP addr) — and hands it to `bootstrap.new`, which validates
  fail-fast. Nothing below the host reads the environment (locked by
  `examples/python-app/tests/test_enforcement.py`).
- **Only the edge exits.** Exit/fatal calls live in `srv/*/main`, nothing below
  (same enforcement test).
- **One graph per process.** The host calls `bootstrap.new` once at startup
  (locked by `examples/python-app/tests/test_bootstrap_once.py`), and owns
  shutdown via `App.close()`.
- **Two-layer transport split.** The per-context handler translates wire ↔
  `Client` (`handlers.md`); the host mounts handlers and owns the
  server + middleware. Auth policy and other cross-cutting concerns belong
  here, never inside a context's handler.
