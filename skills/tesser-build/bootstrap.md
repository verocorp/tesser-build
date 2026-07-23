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
- A **context's wiring** (`wiring.md`) — builds *one context's* graph from that
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
bootstrap/                       ← service-owned, app-level
  config.py / config.go          ← app Config: nested from per-context Configs
  bootstrap.py / bootstrap.go    ← new(cfg Config) → App   (validate, build once)

def new(cfg: Config) -> App:
    policy_client, closer  = linkpolicy_wire.build(cfg.linkpolicy)   # per-context wiring
    campaign_client, closer = campaign_wire.build(cfg.campaign, checker)
    ...
    return App(campaign_client, policy_client, ..., stack)           # App owns close()
```

The impl-selection site (an in-memory vs a database-backed repository) is inside
the per-context wiring the root calls, driven by that context's slice of the
config — the only place that changes when you swap infrastructure. Construction
mechanics: `go.md#the-composition-root`, `python.md#the-composition-root`;
verified impl: `examples/python-app/bootstrap/`.

## App config

`Config` is a **service-owned concrete struct, nested from per-context
`Config`s** — each context owns its own `Config` in its `wiring`
(`wiring.md`); the app `Config` composes them, and `bootstrap` slices
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
  `examples/python-app/reports/wiring/config.py`).

## Lifecycle

Deliberately minimal, split across the two layers that own it: **bootstrap
mandates** a `Closeable` shape (one `close()` method —
`examples/python-app/lifecycle.py`) and an `App.close()` that tears the graph
down; the **host mandates** a `Host` (`run(stop)`) run under a runner that
installs SIGTERM and calls `App.close()` (`srv.md`). Health, readiness,
graceful-shutdown *ordering*, drain, and observability are the host's fill-in
above that minimum — the shape leaves room to do them *properly* without the
template mandating them (see the ops-deferral notice in `SKILL.md`).

What the mandated minimum requires:

- **A cleanup stack, pushed in construction order, closed in reverse.** As
  `new(cfg)` builds each context it pushes that context's closeable; teardown
  pops. Reverse order is the dependency order run backwards — a consumer
  closes before what it consumes.
- **A close that raises must not orphan the rest.** The stack attempts every
  close and collects errors; one leaky pool cannot leak the others. `App.close`
  **retains** those errors on `App.close_errors` rather than dropping them, so a
  host or test can see a partial teardown (verified impl:
  `CleanupStack.close_all` + `App.close_errors`, locked by
  `examples/python-app/tests/test_cleanup.py`).
- **Partial construction unwinds.** If a later context's build fails,
  `new(cfg)` closes what it already built before the error propagates — a
  failed boot must not leak connections (same test).
- **`close()` is idempotent.** Hosts call it in `finally`; a double close is
  a no-op, not a crash.
- **Every wiring returns a closeable, even a no-op** (`wiring.md` rule 2) —
  the stack's uniformity is what makes the four guarantees above hold by
  construction rather than per-context vigilance.

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
impl: `examples/python-app/tests/test_enforcement.py` fails on an environment
read outside `srv/*/main` and on a non-edge exit; a generalized `tessercheck`
check is scheduled follow-on work, not yet shipped. The wiring-boundary rules
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
- **Bootstrap never reads the environment:** an enforcement test that fails on
  env access outside the hosts' `main` modules (verified impl:
  `examples/python-app/tests/test_enforcement.py`).
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
