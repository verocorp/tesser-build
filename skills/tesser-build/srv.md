# srv — the hosts

<!-- tb-status: full -->

An app-wide directory of **hosts, one per delivery mechanism** (recommended
subdirs `srv/{http,cli,wrk}`, not enforced). A host's `main` is the outermost
edge of the app: it decodes the environment into the app `Config`, calls
`bootstrap.new(cfg)` **once**, mounts *its* mechanism's inbound handlers for
the contexts it exposes — every one of them, however small its surface
(`handlers.md`, rule 6) — applies cross-cutting middleware
(auth/logging/recovery), and owns the process lifecycle. Everything a host
does is edge work — the moment logic appears in a host that isn't
env-decoding, mounting, middleware, or lifecycle, it belongs somewhere below.

## Is this what I'm building?

**Test:** *Am I writing the process entry point for one delivery mechanism —
the `main` that reads the environment, builds the app once, and serves?*
Yes → a host.

**Near-misses that are NOT a host:**
- A **handler** (`handlers.md`) — per-context wire↔`Client` translation. The
  host *mounts* handlers; a handler never owns the server, the middleware, or
  the process.
- The **composition root** (`bootstrap.md`) — builds the object graph from a
  `Config`; it never reads the environment and never serves. The host calls
  it; it is not it.
- A **worker loop / consumer** that polls a queue — that *is* a host
  (`srv/wrk`): same edge duties, different mechanism.
- A **test fixture** that builds the app — tests construct via
  `bootstrap.new(cfg)` with a literal `Config`; they are not an env edge and
  never read one.

## Rules

1. **The host is the env edge; it calls the one loader.** Each `srv/*/main`
   passes its own `os.getenv` to the single `from_env(getenv)` loader
   (`bootstrap/config.py`), which decodes the environment into the spec-shaped
   app `Config` — app config **and** the host's own launch config (the listen
   addr, the worker cadence) — and hands it to `bootstrap.new`, which validates
   fail-fast. The host's `os.getenv` is the **only environment reference**, and
   `from_env` is the **one decoder that consumes it** — nothing else below the
   host calls `os.getenv`/`os.environ` (locked by
   `examples/python-app/tests/test_enforcement.py`). It stays a pure function —
   `getenv` is injected, and it is a module function, not a `Config` method — so
   it is testable with a dict and never a second, hidden config authority. One
   loader, called by every host, is what keeps the per-host `Config` literal
   from drifting.
2. **Only the edge exits.** Exit/fatal calls live in `srv/*/main`, nothing
   below (same enforcement test) — a library that exits takes the process
   away from the one place entitled to decide that.
3. **One graph per process; the host owns the lifecycle.** The host calls
   `bootstrap.new` once at startup (build-once locked by
   `examples/python-app/tests/test_bootstrap_once.py`; the runner's guaranteed
   `close()` by `examples/python-app/tests/test_run.py`) and runs its `Host`
   (`run(stop)` — serve, then drain on stop) under a runner that installs
   SIGINT/SIGTERM and calls `App.close()` in a `finally`
   (`examples/python-app/srv/run.py`, `srv/http/host.py`). Installing the signal
   handler is **load-bearing**: a bare `finally: app.close()` does *not* survive
   the default SIGTERM (the process dies without unwinding), so a container stop
   would leak the graph. Drain ordering, readiness, and health are the host's
   fill-in above this minimum.
4. **Two-layer transport split: the host routes, the handler transforms.**
   The host owns the *mechanism* — the socket, the route table, bytes ↔ JSON,
   status lines and headers on the wire, and cross-cutting middleware. The
   per-context handler owns the *shape* — request DTO ↔ `Client` DTOs
   (`handlers.md`). Concretely, a host's request path is: match `(method,
   path)` in the route table, put what it parsed into the request DTO
   (`path_params`, `query_params`, `headers`, decoded `body`), call the
   endpoint, serialize the response DTO it gets back. **Nothing between those
   steps.** No field names, no `Client` call, no business branch — if the host
   knows what a field is called, the split has already failed. Auth *policy*,
   logging, recovery, and rate limits are host middleware, never inside a
   context's handler — a handler that imports another context to do auth has
   leaked a host concern into a context adapter.
5. **The route table is the host's, and it is one table.** URLs are an
   app-level decision: the host declares `(method, pattern, endpoint)` for
   every exposed context in one place, so the whole URL surface is readable
   at once and a context can be mounted, prefixed, or versioned without
   editing it. Pattern matching and parameter extraction are the router's
   (`srv/http/router.py`) — the one component allowed to know that
   `/campaigns/{campaign_id}` has a parameter in it.
6. **One long-running thing per process — with one carve-out.** Two delivery
   mechanisms are two processes; they share the composition root and the
   contexts, not memory. A CLI host runs against its *own* `App`; if two
   mechanisms must see one state, that state lives behind a context's
   repository, not in a host. **The carve-out:** a health/metrics listener a
   platform *requires* — a worker host that must answer an HTTP readiness probe
   to run on its target — is not a second delivery mechanism; it is part of the
   one host it reports on, owned by that host, not a reason to fold two
   mechanisms into one process.

## Shape

```
srv/
  run.py             ← run_until_signal(host, app): install SIGTERM, close in finally
  http/router.py     ← Route(method, pattern, endpoint) + match(): URL knowledge, nothing else
  http/host.py       ← HttpHost implements Host: the route table, the server, (de)serialization
  http/main.py       ← from_env(os.getenv), new(cfg) once, run the host
  cli/main.py        ← from_env(os.getenv), new(cfg) once, run command, close

def main() -> None:
    cfg = from_env(os.getenv)                 # the ONE loader; app + launch config
    app = new(cfg)                            # once per process; validates fail-fast
    host = HttpHost((cfg.http.host, cfg.http.port), app)
    run_until_signal(host, app)               # SIGTERM installed; close() guaranteed

def routes_for(app: App) -> tuple[Route, ...]:            # the whole URL surface, one place
    campaign = CampaignHandler(app.campaign)              # one handler per exposed context
    reports = ReportsHandler(app.reports)
    return (
        Route("POST", "/campaigns", campaign.create_campaign),
        Route("GET", "/campaigns/{campaign_id}", campaign.get_campaign),
        Route("GET", "/reports/links-by-verdict", reports.links_by_verdict),
    )
```

A missing app-config var stays an empty coordinate and `bootstrap.new` fails
fast on it — the host never invents a default for someone else's config; a
host's own launch knobs (a listen port) may default locally, inside `from_env`.
Construction mechanics: `python.md#inbound-handlers-and-hosts`; verified impl:
`examples/python-app/srv/` (`run.py`, `http/host.py`, `http/main.py`,
`cli/main.py`).

## Decisions you must make

1. **Which mechanisms get a host?** One per delivery mechanism actually
   served — `http`, `cli`, `wrk` are the recommended names, not a quota. A
   mechanism you don't serve gets no stub.
2. **Where does secret resolution happen?** Resolving secret *references*
   (Vault/AWS/GCP) is a legitimate host-side, launch-time concern — it is
   part of env → `Config` decoding at the edge, never a lazy fetch below it.
   The template deliberately doesn't build the loader.
3. **How much lifecycle?** The template mandates build-once, a `Host` with
   `run(stop)`, and a runner that installs SIGTERM and closes in `finally`.
   Graceful-shutdown *ordering*, drain, and readiness are the host's fill-in —
   do them properly at the edge when the service needs them (see the
   ops-deferral notice in `SKILL.md`).

## How the machine sees it

Machine-checked in the verified impl (`tests/test_enforcement.py`, real `ast`
checks with injected-violation teeth): env reads (`os.getenv`/`os.environ`)
only in `srv/*/main`; exits only in `srv/*/main`; no import-time side
effects in contexts or bootstrap. Build-once is locked by
`tests/test_bootstrap_once.py`. A generalized tessercheck check is scheduled
follow-on work, not yet shipped. Review-side tells:
- an **env read anywhere below `srv/`** — the deploy surface went invisible;
- a **second `bootstrap.new` call** in request/command handling — per-request
  wiring;
- **domain logic in a host** — the host is routing + transport + middleware; a
  `for`-loop over domain objects here belongs in an application service;
- a **context import in the host that isn't `adapters.handlers`** — a `client`,
  `application`, or `domain` import means the router reached past the
  transform (locked for `srv/http` by `tests/test_enforcement.py`);
- **a branch per endpoint** in the request path instead of a route table —
  endpoints that don't share one signature, so they can't be routed uniformly.

## Tests you must write

- **Env reads only at the edge** — an enforcement test that walks the tree
  and fails on `getenv`/`environ` outside `srv/*/main` (verified impl:
  `test_enforcement.py`; prove it has teeth on an injected violation).
- **Exits only at the edge** — same walk, `sys.exit`/`os._exit`.
- **The graph is built once and closed** — a host-shaped test that calls
  `bootstrap.new` once, exercises a `Client`, and `close()`s (idempotently)
  (verified impl: `test_bootstrap_once.py`).

## Common mistakes

- **A host that re-reads env instead of calling the loader.** An `os.getenv`
  for app config inside a host body — or a `Config.from_env` classmethod — is a
  second env authority. There is exactly one loader, the `from_env(getenv)`
  module function, and every host calls it, passing its own `os.getenv`.
- **Defaulting a peer's coordinate.** `os.getenv("CAMPAIGN_STORAGE") or
  "memory"` at the host — the silent volatile-storage fall, moved up a
  layer. Empty coordinate in, fail-fast in `bootstrap.new`.
- **Auth in a handler.** Token checking inside a context's handler — auth
  policy is host middleware; the handler receives an authenticated request.
- **Per-request construction.** Building the app (or a repository) inside
  the request path — once per process, at startup.
- **The host doing a context's translation.** Calling a `Client` from the
  route and shaping the body inline because that context's surface is one
  read — the host now owns a wire format it has no business knowing, and that
  route skips the handler's `respond` path (`handlers.md`, rule 6). Mount a
  handler; the host maps path → handler method and serializes the result.
- **A serve loop with no signal handling.** `finally: app.close()` alone does
  not survive SIGTERM — the container stop skips it and leaks every pool the
  graph holds. Run the host through the runner that installs the handler.

## Now build it

<!-- tb-allow-missing: examples/app -->

- Python: `python.md#inbound-handlers-and-hosts` — the host `main` shape,
  backed by `examples/python-app/srv/`.
- Go: not yet materialized — the settled anatomy's Go mirror
  (`examples/app`) is pending; note the gap, don't invent a convention.
  Mirror the Python arc's structure (one `FromEnv(getenv)` loader, build once,
  a `Host` with `Run(ctx) error`, a runner over `signal.NotifyContext` that
  `Close()`s the app).
