# Prior-art anatomy — bounded-context structure + app wiring

Evidence base and settled model from the cross-repo excavation on 2026-07-17.
This is the *why* behind the bounded-context anatomy and the `srv`/`config`/
`bootstrap` model the wiring examples materialize. It exists so the excavation
is never re-run from scratch.

The five-repo sweep (rev, ridedar, flow, meters, certus/metron/quanta) plus two
Codex passes (a composition-root evaluation and a red-team of the settled
`srv`/`config`/`bootstrap` design) produced this. Where the settled model
**diverges** from what the prior art actually did, it says so — those are the
anti-patterns the excavation found, not conventions to keep.

---

## 1. The lineage (oldest → newest)

Anatomy did **not** monotonically improve. It forked on **application vs
library**, and each branch converged internally.

| Era | Repo | Anatomy it settled on | Boundary | Public seam | Composition |
|---|---|---|---|---|---|
| 2023–24 | **rev** (origin) | single-module layered hexagon (`app/{application, infra, interfaces, internal/domain}`, split `ports/{drivers,services}`) | `internal/` on **domain only** | none (API type + DTOs) | manual `srv/cli/main.go` |
| 2025-03 | **ridedar** (radical parallel) | `go.work`, **layer-per-module** hexagon | `internal/` **+ per-layer `go.mod`** | **first-class `Client`+DTOs** (invented here) | **DI registry + env provider factory** |
| 2025 (converged ~Jun) | **flow** (synthesis) | per-context, scaffold-generated: public root `client.go` → `internal/<agg>/{domain, *_port.go, actions}` → `internal/application/` → `internal/<agg>/infra/{spnnr,tmprl,adapter}` → `init/` Wire→Registry | `internal/` **+ per-layer/adapter `go.mod`** (60+ modules) | `Client`+DTOs (root pkg) | **Google Wire `init/` registry** |
| late-2025→2026 | **meters** (transition) | **flat** sibling packages, pure-function app layer | none (module edge only) | none | **wire-in-`integration/`-test** |
| 2026 | **certus** (library end-state) | **flat all-public**; VO-first; `recipes` = app-services; ports scattered by owner | none (private fields, not `internal/`) | root `credits` facade | **none — consumer wires** |
| 2026 | **metron** (spec-library) | `specs/` (data contracts + abstract func sigs) + `internal/` (whole engine sealed) | `internal/` seals everything; only `specs/` public | **data contracts, not behavior** | none (library) |
| 2026 | **quanta** | flat pure-math library, no contexts | none | whole package | none |

**Synthesis DNA:** rev contributed the layered/encapsulation instinct (its
Aug-2024 "struct-init hiding" campaign is the private-fields rule the tesser-build skill
now enforces). ridedar contributed the published-`Client` contract + DI-registry +
per-context shape. flow is the synthesis — rev's single-module `internal/`
discipline + ridedar's contract/registry ideas, minus ridedar's layer-per-module
ceremony — and it **converged** (materialized by `src/ctx-creator.sh` into the
`tmplt` template, stable ~June 2025 via the "client-json-client" refactor).

## 2. The anatomies found (the fork)

| Anatomy | Public surface | Hidden layer | Boundary | Exemplar |
|---|---|---|---|---|
| **Flat library** | whole package | none | none | quanta, certus |
| **Public-Client + internal** | a behavioral `Client` | impl in `internal/` | Go `internal/` | flow |
| **Public-spec + internal** | data contracts only | the whole engine | Go `internal/` | metron |

Which one a context uses is decided by **application vs library**: a library ships
the four roles but no wiring and no hosts (the consumer supplies them); an app has
both. The invariants that held across *both* branches — VO-first + `NewX`/`MustNewX`
+ constructor-only construction, ports-beside-consumer, primitive-leaved DTOs — are
exactly what the tesser-build skill already teaches.

---

## 3. Settled bounded-context anatomy (DECIDED)

A context has **four roles — all must be present; internal nesting/layout is
free** (presence required, organization not prescribed):

- **domain** — VOs / entities / aggregates + the outbound port interfaces it owns
  (repository, cross-context, event-publisher), defined beside their consumer.
- **application** — use-case services (Convert → Delegate → Persist → Respond);
  no business logic.
- **adapters** — sole top-level dir; **recommended (not enforced)** sub-dirs
  `handlers` (inbound: HTTP/CLI/event-consumer, translate wire↔`Client`) and
  `gateways` (outbound: repositories, ACLs, event-publishers, external clients).
  Handlers receive; gateways reach out.
- **wiring** — the context's own construction (its providers / `NewClient`).

The context's **top level is its public seam**: the `Client` interface + primitive
DTOs. There is **no separate "contract" role**.

**`internal/` is optional, not required.** The boundary is the public-vs-impl
package split, which stands on private fields + constructor-only construction.
`internal/` (Go) or `_internal` + `import-linter` (Python) is *optional*
enforcement over it.

**Anti-corruption is not a role** — it's a *purpose* an outbound gateway can have,
built as port + adapter like any other (see §5).

## 4. App-level wiring: `srv` / `config` / `bootstrap` (DECIDED)

Two things are **app-level, not per-context**: the composition root (`bootstrap`)
and the hosts (`srv/*`).

- **`bootstrap`** is **service-owned code, not a toolkit import** (a composition
  root inherently knows all concretes — it can't be a library). Shape:
  `New(cfg Config) (*App, error)` — a source-agnostic constructor that validates
  the config, builds the object graph **once**, and returns `*App` with `Close()`.
  The **only rule the toolkit enforces: there is a `bootstrap` that takes a
  `Config` in and does not read the environment itself.**
- **`Config`** is a **service-owned concrete struct** (industry name; Go-idiomatic),
  **nested from per-context `Config`s** — each context owns its own `Config`;
  `bootstrap` slices `cfg.Campaign` to the campaign providers (narrow per-provider
  config, not a god object). The toolkit prescribes the **nesting pattern + per-
  context ownership**, never the fields — config contents are irreducibly
  per-service.
- **Impl selection follows the resource coordinate, not a magic env enum**: empty
  DSN → in-memory repo, real DSN → SQL repo. `APP_ENV`, if used at all, is a
  behavior *class* only, validated *against* the resources — never the source of
  resource identity. (See §7 — this is a deliberate divergence.)
- **Reading the environment is an edge decoder** at the outermost `main` — a
  "process-launch inbound adapter": env → `Config` → `bootstrap.New`. Outside the
  app. The **deploy layer authors** the vars (Terraform/Helm/secret manager — out
  of scope for the app template); the app only **consumes**. There is **no
  `config.Load` service** inside the app.
- **`srv/`** is an app-wide dir of hosts, **one per delivery mechanism**
  (recommended subdirs `srv/{http,cli,wrk}`, not enforced). Each host's `main`
  calls `bootstrap.New(cfg)` **once** and mounts *its* mechanism's inbound handlers
  across all contexts, applies cross-cutting middleware (auth/logging/recovery),
  and owns the process lifecycle.
- **Static typing is total** because `bootstrap` / `Config` / `App` are all
  concrete service types — which is why **hand-wired ("Pure DI") beats fx/Wire on
  compile-time safety** here (fx = runtime reflection, missing dep = startup panic;
  Wire = codegen; hand-wired = plain Go the compiler fully checks).

**Governing philosophy (DECIDED):** guidelines must be **correct-by-construction
(don't force anti-patterns) but minimal (don't mandate full production
machinery).** Lifecycle stays minimal — `App` has `Close()`; the shape leaves room
to do health/readiness/shutdown/observability *properly* without requiring the
template to implement them.

**Alignment:** this is Seemann's **Composition Root**, and it maps onto Wire
(the generated `Initialize()`), fx (`fx.New` + lifecycle), Spring
(`ApplicationContext` + `@Profile`), and 12-factor (config from the environment).
Hand-wiring is Seemann's endorsed **"Pure DI"**, with a documented graduation path
to Wire/fx at scale.

## 5. Anti-corruption layer taxonomy

ACLs are almost always **implicit** (a port + adapter that happens to translate),
not a package named `acl`. Eight shapes found; the **true DDD ACLs** (defend the
domain from a model it doesn't own) are:

| Type | Defends against | Best exemplar |
|---|---|---|
| External-vendor compile/decompile | third-party billing schema | certus `compilers/{schematic,stripe}` (the textbook ACL) |
| External-vendor port+adapter | a vendor SDK | flow `bill/infra/stripe/…` |
| External-payload transformer | an untyped inbound event bag | meters `ingestion/ingestionconfig.go` |
| Cross-context translator | a sibling context's model | certus `dispatch.AmountQuerier`; flow `BillingACLActions` (only one *named*) |
| Domain→ledger port-adapter | another context's model + its errors | flow `order/infra/ledger_adapter/adapter.go` |
| Domain↔rule-engine | cel-go dynamic values | flow `order/infra/celit/cel_adapter.go` |

Not true ACLs: **persistence row↔domain** (ordinary repository adapter) and the
**spec↔VO boundary** (an anti-primitive-obsession seam within a model you own —
metron's `specs/`↔`internal/` is a publishing seam, direction inverted from an
ACL). **Legacy/migration ACLs do not exist** in any repo (only naming vestiges).

## 6. Transport: two layers, each one responsibility

Confirmed across flow/ridedar/rev — transport is a **split**, not a single layer:

- **Layer 1 — per-context handler** (`adapters/handlers`): translate wire↔`Client`
  for one context, one `Client` call, outside `internal/`.
- **Layer 2 — app-level host** (`srv/<mechanism>`): mount all contexts' handlers,
  apply cross-cutting middleware, own server config + lifecycle.

Rule of thumb: **inbound needs a server (something calls *in*); outbound doesn't
(it calls an external server).** HTTP/CLI/events are the same shape — inbound =
handler + host; outbound = gateway over a domain-owned port. Events aren't a new
role: publish = outbound gateway over an `EventPublisher` port; consume = inbound
handler + a worker/consumer host. (Prior art is thin on external pub/sub — flow
used Temporal, metron an in-process bus — so the pub/sub shape is reasoned by
symmetry with the well-evidenced HTTP path.)

Flow's per-context handler leaked cross-context coupling (`accounts` handler
importing `users.UserIDKey` for auth) — a **violation** of the split: auth is a
cross-cutting concern that belongs in the host's middleware, not a per-context
handler.

## 7. Deliberate divergences from the prior art (anti-patterns corrected)

The one place the settled model does **not** copy the prior art, because the
excavation + Codex found these to be bugs:

1. **`APP_ENV` as an impl selector → coordinate-driven config.** flow *and*
   ridedar switched impls on a named env enum; flow shipped the `prod →
   rw-flow-staging` corruption bug (the name said prod, the connection went to
   staging). The model makes the **resource coordinate** the source of truth, so
   the name can't lie about where it connects.
2. **Per-request `bootstrap.Initialize()` → build the graph once per process.**
   flow's `publicapi` re-built the whole graph on every HTTP request (leaked cloud
   clients, p99 blowups).
3. **nil-then-setter cycle break → acyclic hoist / events.** flow broke the
   accounts↔fulfillments cycle by passing `nil` then mutating. The model breaks a
   cycle by hoisting into a real orchestrator/saga **only when it's a genuine
   cross-context workflow**, else domain events; N-context cycles need events, not
   a third service. Never nil-then-setter.
4. **`log.Fatal` / env reads buried in providers → only the edge exits.**
   `config` reading and `log.Fatal` live at the outermost `main`, nothing below.
   (Codex flagged this should be a `tessercheck` check: ban `os.Getenv` outside the
   edge decoder, `log.Fatal` outside `srv/*/main`, `init` side effects.)

---

## Provenance

- Cross-repo anatomy + lineage: five parallel subagents over
  `~/workspace/{flow, ridedar, rev, meters, vero/certus, vero/metron, vero/quanta}`
  and worktrees, 2026-07-17.
- Composition-root evaluation + red-team of the `srv`/`config`/`bootstrap` design:
  two Codex (`gpt-5`-class) passes, read-only over the same repos.
- Repos inspected: `flow` (`rheadwest.com/flow`), `ridedar`
  (`gitlab.com/chrismconley/ridedar`), `rev` (`rheadwest.rev`), `meters`,
  `certus`/`meters-credits` (`github.com/chrisconley/stunning-octo-lamp`),
  `metron`/`metering-spec` (`github.com/chrisconley/metron`), `quanta`.
- The only two real composition-root implementations in the whole workspace are
  **flow** and **ridedar**; the current generation (certus/metron/quanta/meters)
  are domain libraries that deliberately have no composition root.
