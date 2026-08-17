# Bootstrap — the composition root + app config + lifecycle

<!-- tb-status: full -->

The **composition root** is the single place that wires the app: it
**constructs** the concrete services and repositories, **composes** them to
satisfy each context's public `Client`, and hands the wired graph to the hosts
(`srv.md`) that inject it into handlers. Composition root is Mark Seemann's term
(*Dependency Injection*, ch. 4) for the one place an application wires its object
graph; it is what the vero prior art calls `init` / `registry`, and what the
settled app anatomy names `bootstrap` (`map.md`).

`bootstrap` is **service-owned code, not a toolkit import** — a composition root
inherently knows all the app's concretes, so it cannot be a library. The shape
the toolkit prescribes is minimal: `bootstrap` exposes a source-agnostic
constructor `new(cfg Config) → App` that validates the config fail-fast, builds
the object graph **once per process**, and returns an `App` that owns cleanup
(`App.close()`). **It takes a `Config` in and never reads the environment
itself** — reading the environment is the host's job, at the edge (`srv.md`).

## Is this a composition root?

**Test:** *Am I in the one place that chooses concrete implementations and wires
them together — not a service and not a handler?* Yes → composition root.

**Near-misses that are NOT a composition root:**
- An **application service** — coordinates a use case; it *receives* its
  repository injected, it does not choose which one.
- A **handler** — *receives* the `Client` injected; it constructs nothing
  (`handlers.md`).
- A **context's wiring** (`component.md`) — builds *one context's* graph from that
  context's config. The composition root *calls* the per-context wiring and owns
  the app-wide assembly, not every construction in the program.
- A **repository / adapter constructor** (`New*`) — builds *one* concrete. The
  composition root *calls* these; it owns the **choice** of which to wire in.

## Rules

1. **Returns / injects public interfaces, never raw domain objects.** This is a
   *boundary* rule: what crosses **out** of the composition root is the `Client`
   (and its DTOs), never an aggregate or value object. Inside the
   implementation, richer domain types are correct — the rule is about what
   leaves.
2. **The only place that CHOOSES the concrete implementation.** Not "no `New*`
   anywhere else" — repositories, fakes, and adapters have their own
   constructors. The composition root owns *which* one the app wires in;
   swapping a database repo for an in-memory one is a **one-site** change, here.
3. **Takes a `Config` in; never reads the environment.** `new(cfg)` validates
   and builds; the env → `Config` decoding is an edge concern that belongs to
   the host's `main` (`srv.md`). Impl selection follows the **resource
   coordinate** (empty DSN → in-memory, real DSN → SQL), never a magic
   `APP_ENV`-style enum — a name can lie about where a connection goes; the
   coordinate cannot.
4. **Builds the graph once per process, and owns its teardown.** `new(cfg)`
   returns an `App` with a `close()`; hosts call it once at startup, never per
   request. Constructed resources register cleanup as they are built, so a
   half-built graph unwinds cleanly on a construction failure.
5. **Keep the reasoning — the *why* is the product.** One wiring site, no domain
   leak past the boundary, contract decoupled from build. Those three are what
   the layer buys; a composition root that abandons them is just a `main` with
   the imports in one file.

## Shape

```
app/                             ← service-owned, app-level
  config.py                      ← ts.Spec + ts.Config: nested from per-component Configs
  repository.py                  ← ts.ConfigRepository: reads the environment, decodes a Config
  app.py                         ← ts.App: App(cfg) builds the components; close() closes them
  loader.py                      ← ts.Loader + the one @ts.load function

class App(ts.App):
    def __init__(self, cfg: config.Config) -> None:
        linkpolicy = linkpolicy_wire.LinkPolicy(cfg.linkpolicy)      # per-component construction
        try:
            campaign = campaign_wire.Campaign(cfg.campaign, policy)  # cross-component edge
        except Exception:
            linkpolicy.close()                                       # a half-built app never exists
            raise
        ...

    def close(self) -> None:
        self.reports.close()                                         # each closes what it made
        self.campaign.close()
        self.linkpolicy.close()
```

The impl-selection site (an in-memory vs a database-backed repository) is inside
the per-context wiring the root calls, driven by that context's slice of the
config — the only place that changes when you swap infrastructure. Construction
mechanics: `go.md#the-composition-root`, `python.md#the-composition-root`;
verified impl: `examples/python-app/app/`.

## App config

`Config` is a **service-owned concrete struct, nested from per-context
`Config`s** — each context owns its own `Config` in its `wiring`
(`component.md`); the app `Config` composes them, and `bootstrap` slices
`cfg.campaign` down to the campaign wiring. Spec-shaped: frozen/primitive
leaves, no constructor logic, no methods. The toolkit prescribes the nesting
pattern and per-context ownership, never the fields — config contents are
irreducibly per-service.

The conventions the nesting carries:

- **Each context sees only its own slice.** `bootstrap` passes
  `cfg.campaign` to campaign's wiring — never the whole `Config`. A context
  that receives the app config can grow a dependency on a sibling's
  coordinate without anyone choosing that.
- **One shared `from_env` loader, but no `from_env` *method* on `Config`.**
  A single `from_env(getenv)` module function (`bootstrap/config.py`) decodes
  env → `Config`, and every host calls it (`srv.md`); `Config` itself stays a
  dumb spec. What's banned is a `from_env` *classmethod on `Config`* — that
  would make the type a second env authority and hide the deploy surface inside
  it. The loader is a pure function (`getenv` injected), not a method, so env is
  read in exactly one place and the per-host `Config` literal never drifts.
- **Validation lives in `new(cfg)`, not in `Config`.** The struct is dumb by
  design; `bootstrap.new` (via each wiring's fail-fast) is where an absent
  coordinate becomes a loud error. Two layers of validation drift apart.
- **A context with nothing to configure still owns an (empty) `Config`** —
  the nesting stays total, and a future coordinate lands in the context's
  wiring instead of as a bootstrap special case (verified impl:
  `examples/python-app/reports/component/config.py`).

## Lifecycle

Deliberately minimal, and owned by whoever holds the resource. A **component**
constructs its own infrastructure from its config slice and its `close()`
releases exactly that; the **app** builds the components and its `close()`
closes each one; the **host** mandates a `Host` (`run(stop)`) run under a
runner that installs SIGTERM and calls the app's `close` in a `finally`
(`srv.md`). Health, readiness, drain, and observability are the host's fill-in
above that minimum — the shape leaves room to do them *properly* without the
template mandating them (see the ops-deferral notice in `SKILL.md`).

What the mandated minimum requires:

- **Ownership is strict.** A component releases only what it constructed, and
  nothing else reaches into it. That is what makes teardown order free: no
  component's `close()` depends on another still being open, so there is no
  reverse-order doctrine to get right. A component that holds no
  infrastructure has an empty `close()`, and that is honest rather than
  ceremonial.
- **Partial construction unwinds.** If a later component's construction fails,
  the app closes the ones it already built before the error propagates — not
  because of a leak argument, but because a half-built app is an invalid
  object and a single validating constructor never leaves one behind (verified
  impl: `examples/python-app/app/app.py`, locked by
  `examples/python-app/app/test_app.py`).
- **Nothing travels.** A closeable is never a return value, a tuple element, or
  a stack entry — each object holds what it made, in its own type. A release
  contract that has to be *passed* is the sign that ownership is unclear.
- **The app is built, never run.** `App` has no `run`; hosts run. The runner
  takes a host and a callable to invoke when it stops, so it needs to know
  nothing about apps at all.

## Decisions you must make

1. **Which implementation does the wiring choose?** Driven by the resource
   coordinate in that context's config slice — an empty coordinate selects the
   in-memory implementation (tests, early use), a real one the backed
   implementation; both satisfy the **same repository interface**
   (`repositories.md`), so the choice is local and cheap. (In-memory is **not
   doctrine** — a test can substitute its own *because* the repository is an
   interface, not because of any bootstrap rule.)
2. **Convention, or compiler-enforced?** "Only the composition root (and the
   wiring it calls) imports the concretes" is a **convention** in this cut. Go's
   `internal/` directory makes it compiler-enforced — a package under
   `internal/` cannot be imported from outside its parent. That is a later
   addition (footnoted, not required here); without it the boundary is a
   discipline review upholds, not a guarantee.
3. **Hand-wired or a DI framework?** Hand-wired ("Pure DI") is what this skill
   teaches: `bootstrap` / `Config` / `App` are concrete service types the
   compiler (or mypy) fully checks. Wire/fx-style frameworks are a documented
   graduation path when the graph outgrows a readable `new` — the concepts are
   identical.

## How the machine sees it

**Partially machine-checked.** The env-edge rule is enforced in the verified
impl by a linter config, not a bespoke walk: `examples/python-app/ruff.toml`
bans `os.getenv`/`os.environ` (and `sys.exit`/`os._exit`) as `TID251`
banned-api, lifted by `per-file-ignores` only for `srv/*/main.py`. Ruff catches
the `from os import getenv` alias form an attribute-only check would miss. A
generalized `tessercheck` check is scheduled follow-on work, not yet shipped. The wiring-boundary rules
remain **review, not the compiler**. The tells a reviewer looks for:
- an **`os.getenv` / `os.Getenv` inside `bootstrap` or below** — the env edge
  has leaked inward (`srv.md`);
- a **`New<concrete>` call outside the root/wiring** that selects an impl —
  scattered wiring;
- a **per-request `bootstrap` call** — the graph must be built once per process;
- a **handler holding a concrete field** instead of `Client` — coupling to
  internals (`handlers.md`).

As with the other boundaries, layer and intent decide; a `New*` inside the
root/wiring is correct, the same call in a handler is the leak.

## Tests you must write

- **The composition root wires end-to-end:** build the app through
  `bootstrap.new(cfg)`, call a `Client` method, assert the result — the object
  graph is connected and a real use case runs through it.
- **A test substitutes its own repository:** the wiring (or the test) provides a
  fake repository that satisfies the repository interface, and the use case runs
  against it — framed as "a test provides its own repo impl", **not** as an
  in-memory-vs-real doctrine.
- **Bootstrap never reads the environment:** `bootstrap.new` builds from a
  `Config` it is handed; env decoding is `bootstrap.config.from_env(getenv)`,
  which consumes an *injected* getter and never calls `os.getenv` itself. The
  gate fails on `os.getenv`/`os.environ` access outside the hosts' `main`
  modules (verified impl: `examples/python-app/ruff.toml`, with
  injected-violation teeth in `tests/test_architecture_teeth.py`).
- **The graph is built once:** a host calls `bootstrap.new` exactly once
  (verified impl: `examples/python-app/tests/test_bootstrap_once.py`).

## Common mistakes

- **Wiring scattered across the app.** A service or handler calls
  `NewPostgresRepo(...)` to build its own dependency. The **choice** of impl
  belongs in the composition root's wiring; everything else receives it injected.
- **A service-locator handler.** The handler reaches into the root to "obtain"
  the `Client`. Inject it through the handler's constructor instead — the
  dependency is *pushed in*, not *pulled out*.
- **`bootstrap` reads the environment.** A `getenv` with a hidden default deep
  in a provider means the deploy surface is invisible and a typo'd var silently
  selects a default. Env → `Config` decoding happens at the host edge, once,
  loudly (`srv.md`).
- **Impl selection by environment name.** `if APP_ENV == "prod"` choosing the
  database is the corruption bug waiting to happen — the name says prod, the
  coordinate points at staging. Select on the resource coordinate itself.
- **Per-request wiring.** Rebuilding the graph per HTTP request leaks clients
  and destroys tail latency. Once per process, in the host's startup.

## Now build it

- Go: `go.md#the-composition-root`
- Python: `python.md#the-composition-root` — hand-wired construction backed by
  the `examples/python-app/` worked example (`bootstrap/`, per-context
  `wiring/`).
