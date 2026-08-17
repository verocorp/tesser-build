# Context wiring

<!-- tb-status: full -->

A context's **own construction**: the one module inside the context that builds
its object graph — picks the concrete repository/adapter implementations from
the context's config, composes the application service behind the public
`Client` (`public-interface.md`), and hands back the built `Client` plus
whatever must be closed. The app-level composition root (`bootstrap.md`)
*calls* each context's wiring; it never reaches into a context to assemble the
pieces itself. Wiring is the context-local half of Seemann's composition-root
idea (*Dependency Injection*, ch. 4): the *choice* of concretes stays in
exactly two places — the root (which contexts, in what order) and the
context's own wiring (which implementation of its own ports).

## Is this what I'm building?

**Test:** *Am I building THIS context's object graph — choosing its concrete
implementations from its config and composing them behind its `Client`?*
Yes → the context's wiring.

**Near-misses that are NOT context wiring:**
- The **composition root** (`bootstrap.md`) — app-wide assembly: calls every
  context's wiring in dependency order, constructs cross-context adapters, owns
  each component's teardown. Wiring is one context; the app is all of them.
- An **application service** — *receives* its repository injected
  (`application-services.md`); it never chooses which implementation.
- A **repository/adapter constructor** — builds *one* concrete. Wiring calls
  these; it owns the **choice** among them.
- A **test fixture** building a service with a fake repo — legitimate, and not
  wiring: a test substitutes its own implementation *because* the port is an
  interface, not through any wiring privilege.

## Rules

1. **Each app context owns a `wiring` role.** Required for app contexts, absent
   for library contexts (`map.md#app-vs-library`) — a library exports types and
   is constructed by its caller; an app context must be buildable by
   `bootstrap` through one uniform build contract.
2. **One uniform construction contract: a component class taking one `Config`.**
   Every context exposes the same shape — `ts.Component` with a validating
   `__init__`, a `client`, and a `close()` — so the app composes components
   without special cases. A component with no infrastructure has an empty
   `close()`, which is honest rather than ceremonial; the analyzer requires the
   method, not a resource.
3. **The context's `Config` lives in its wiring, never on the public interface.**
   `wiring/config` is spec-shaped: a frozen struct, primitive leaves, no
   methods, no constructor logic. The app `Config` nests the per-context ones
   (`bootstrap.md#app-config`); the public `Client` package never mentions
   construction config — consumers of the interface must not see how it is built.
4. **Impl selection is coordinate-driven and fail-fast.** The resource
   coordinate in the config (a DSN, a `"memory"` marker) selects the
   implementation. An **absent coordinate is an error**, never a silent fall
   into an in-memory default — a silent default is the volatile-storage bug
   shipping quietly. An unknown coordinate is equally an error naming the
   value.
5. **Cross-context dependencies arrive injected.** Wiring takes the peer-facing
   port (e.g. a `TargetPolicy`) as a `build` parameter; it never constructs
   the adapter over a peer's `Client` — only the composition root knows two
   contexts at once (`gateway-cross-context.md`). A context that imports a
   peer inside its wiring has re-coupled what the boundary decoupled.

## Shape

```
<context>/wiring/
  config.py                 ← ts.Spec + ts.Config: the component's own slice
  wire.py                   ← ts.Component: __init__(cfg, deps), client, close()

class Campaign(ts.Component):
    def __init__(self, cfg: Config, policy: TargetPolicy) -> None:
        self._repo = self._repo_for(cfg)         # coordinate-driven, fail-fast
        self.client: Client = CampaignService(self._repo, policy)

    def close(self) -> None:
        self._repo.close()                       # only what it constructed
```

`_repo_for` is the impl-selection site — the only place that changes when the
context swaps infrastructure. Construction mechanics:
`python.md#the-composition-root`; verified impl:
`examples/python-app/campaign/wiring/` (full case, with an injected
cross-context port), `examples/python-app/reports/wiring/` (minimal case: no
resources, empty config, uniform build contract kept).

## Decisions you must make

1. **What is the coordinate vocabulary?** Service-owned, per-backend: a DSN
   whose scheme maps to the SQL repo, `"memory"` for the in-process one. The
   toolkit prescribes *coordinate-driven and fail-fast*, never the vocabulary —
   config fields are irreducibly per-service.
2. **What does `close()` release?** Whatever this component constructed — a
   pool, a client, nothing. Ownership is strict: a component never reaches
   into a peer's infrastructure, which is what makes teardown order free
   (`bootstrap.md#lifecycle`).
3. **Where do injected peer ports come from?** Always constructor parameters,
   constructed by the composition root. If you are tempted to construct one in
   wiring "just for now", you are moving the two-contexts-at-once knowledge
   out of the one place allowed to have it.

## How the machine sees it

The `wiring/` role directory is part of the prescribed anatomy asserted by the
verified impl's shape checks (`examples/python-app/tests/test_shape.py`), and
the analyzer walks every context and judges each module's declared role
(`python -m srv.cli.main <tree>`, run from `tessercheck-py/`, TB040/TB043).
Coordinate-driven selection and the fail-fast are locked beside each component
(`examples/python-app/campaign/wiring/test_wire.py`,
`examples/python-app/linkpolicy/wiring/test_wire.py`): the `"memory"` coordinate
builds, an absent one errors at construction. The review-side tells:
- a **default coordinate** (`cfg.storage or "memory"`) — the silent fall
  rule 4 bans;
- a **peer import inside `wiring/`** — cross-context construction leaked out
  of the root;
- **config on the public interface** — a construction `Config` exported next to
  the `Client`.

## Tests you must write

- **The coordinate builds the implementation it names:** constructing the
  component with the in-memory coordinate exposes a working `Client` (verified
  impl: `examples/python-app/campaign/wiring/test_wire.py`).
- **An absent coordinate fails at construction** — assert the error, not a
  fallback.
- **The component closes what it built:** teardown is the component's own
  `close()`, reaching only the infrastructure it constructed (verified impl:
  `examples/python-app/bootstrap/test_app.py` locks that the app closes each
  component it built).

## Common mistakes

- **The silent in-memory fall.** `if not cfg.storage: repo = InMemory...` — a
  deploy typo now ships volatile storage. Absent coordinate = loud error.
- **Config on the public interface.** A construction `Config` on the consumer
  surface; consumers start depending on how the context is built.
- **Wiring builds its peers.** `wire.py` importing a sibling context to
  construct its own adapter — the root's two-contexts knowledge duplicated
  into a context; dependency-direction rot follows.
- **A special-cased minimal context.** "reports has no resources, skip its
  wiring" — now bootstrap grows an if-branch per context and the uniform build contract
  is gone. Keep the empty config + no-op closeable.

## Now build it

<!-- tb-allow-missing: examples/app -->

- Python: `python.md#the-composition-root` — the per-context `build` contract and
  the root that calls it, backed by `examples/python-app/*/wiring/`.
- Go: not yet materialized — the settled anatomy's Go mirror (`examples/app`)
  is pending; note the gap, don't invent a convention. Mirror the Python
  arc's structure (same roles, same build contract) with
  `go.md#the-composition-root`'s interface mechanics.
