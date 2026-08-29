# asyncpg repositories — pool ownership and the store / repository split

This is the design record for database-backed repositories in Python, settled
2026-08-29 after `examples/asyncpg` landed (#139). The shipped tree is the
starting state; the two increments below are the plan. Rules are carved out
after each increment's example is right, not before.

## Settled

### App loading

- The runner (`scripts/verify`, CI, a deploy) supplies the environment —
  `ALPHA_STORAGE`, `BETA_STORAGE`. Tests never write `os.environ`.
- A root-tier e2e is host-shaped: one `loader.load()`, then the app is used
  through its clients only, then `close()`. It never reads the database
  directly and never loads twice to prove persistence.
- Consequence: a context's client must be observable — every write use case
  needs a read on the same client. `alpha` grew `find` for this reason.

### Pool ownership

- One `asyncpg.Pool` per distinct database, created by the **app** before the
  components and closed after them. The app derives which pools to create from
  the components' config coordinates (dedupe the DSNs); there is no "ask each
  component what it needs" round trip, because the config is the requirement.
- The component receives the pool it needs and constructs its store from it.
  The component's `close()` releases nothing it didn't build.

### Store / transaction / repository

- A ports module declares two protocols. `WidgetStore(ts.Port)` is long-lived
  and has one method, `transaction()`, returning an async context manager.
  `WidgetRepository(ts.Port)` is what it yields: connection-bound, short-lived,
  carrying the one-`ts.Request`-in / one-`ts.Response`-out methods
  (`load_widget`, `save_widget`).
- The word *repository* goes on the object with the methods (Evans' collection);
  *store* is the thing that opens a transaction on it.
- The service holds the store and writes the boundary, never the mechanics:

  ```python
  async with self._widget_store.transaction() as widget_repository:
      load_widget_response = await widget_repository.load_widget(MapToLoadWidgetRequest(request))
  ```

- A transaction is scoped to one store, so one aggregate per transaction —
  Vernon's rule (IDDD ch. 10) enforced by the types. Two repositories in one
  transaction is unwritable; if two rows must change atomically they are one
  aggregate and one repository decomposes it (`repositories.md` rule 1).
- Every access goes through `transaction()`; there are no direct methods on
  the store. A lone read opens a trivial transaction. One shape.
- Adapters: `PostgresWidgetStore(pool)` acquires a connection, opens a
  transaction, yields `PostgresWidgetRepository(connection)`; commit on exit,
  rollback on exception. `MemoryWidgetStore()` snapshots its dict and restores
  on exception, so the memory backend has real rollback.

### Rejected

- **General unit of work** with several repositories on it (Cosmic Python's
  `UnitOfWork`). Its headline benefit — atomicity across repositories — is the
  thing the one-aggregate rule forbids. Held in reserve for a transactional
  outbox if domain events get a real design; that is the case the pattern was
  named for.
- **Querier / connection as a per-call parameter** (the Go `DBTX` shape). Breaks
  the one-request port signature (TB081) and the ports-only service dependency
  (TB081) at once.
- **Ambient transaction in a contextvar** (Vernon's `session()`, spelled in
  asyncio). Every rule stays green, which is the problem: nothing in any
  signature says a repository method must be called inside a transaction.
- **Repository holding a DSN and building its own pool** — what `#139` ships.
  Can't share a pool or a transaction; the lazy pool-init block is duplicated
  per method because TB051 forbids a private helper.

### Noted, not chosen

- **Optimistic versioning on the aggregate** (Vernon's preference): each
  repository call is its own transaction, `save` writes
  `WHERE version = expected`, a stale write is `errors.conflict`. Removes the
  spanning transaction entirely. The store/transaction shape is for the cases
  it doesn't cover — a lock held across domain logic, or several reads that
  must be consistent with each other.

## The plan

`#139` is increment 1 and is merged. Increments 2 and 3 are independent of
each other; this order keeps each PR's rulings separate.

### Increment 2 — pool ownership

The app creates pools from config, components receive them, repositories take
a pool instead of a DSN.

- `app/app.py`: dedupe the DSN coordinates across `cfg.alpha.storage` and
  `cfg.beta.storage`; one `asyncpg.create_pool` per distinct DSN, created before
  the components (lazily, on first use inside the running loop, since `App` is
  constructed synchronously), closed after them in `close()`.
- `alpha/component/component.py`, `beta/component/component.py`: take the pool
  as a constructor parameter; `"memory"` builds the memory repository, a pool
  builds the Postgres one; the component's `close()` releases nothing.
- `PostgresWidgetRepository(pool)`, `PostgresKeyRepository(pool)`: drop the DSN
  and the lazy pool-init; each method does
  `async with self._pool.acquire() as connection, connection.transaction():`
  around its own query.
- Ports, services, clients, tests above the adapter tier: untouched.

Ruling this forces:

- The pool as a component constructor parameter versus `app.md`'s "nothing
  travels — a release contract that has to be passed is the sign that ownership
  is unclear." The candidates are injected infrastructure (the pool is a
  parameter, like an injected peer port, and the app owns its close) or a
  database component (`Database(cfg)` owning the pool, built first and closed
  last, injected like `beta.client` is today).

### Increment 3 — store / repository split

Ports gain the store and the connection-bound repository; adapters split;
services open the transaction.

- `alpha/application/ports/widget_repository.py`: `WidgetStore` with
  `transaction()`; `WidgetRepository` with `load_widget` / `save_widget`; the
  request and response records for each.
- `alpha/adapters/repositories/postgres.py`: `PostgresWidgetStore(pool)` and
  `PostgresWidgetRepository(connection)`.
- `alpha/adapters/repositories/memory.py`: `MemoryWidgetStore()` with snapshot
  rollback and `MemoryWidgetRepository(part_by_name)`.
- `alpha/application/alpha_service.py`: holds the store; every use case opens
  `async with self._widget_store.transaction() as widget_repository:`.
- Same for `beta` (`KeyStore` / `KeyRepository`).
- Fakes in tests implement the store and yield a fake repository.

Rulings this forces:

- **TB052 one port per module** now sees a store and its repository in one
  module. Candidate: "one port and its transaction kind."
- **TB081 port-method shape**: `transaction()` takes no `ts.Request` and
  returns a context manager, not a `ts.Response`. Candidate: a new `ts.Store`
  kind so the checker sees it, rather than a carve-out by method name.
- **Parameter names shadowing the ports module**: `widget_repository` the
  instance versus `widget_repository` the module. Settle once (alias the
  module, or name the parameter for its kind) rather than per file.
- **A cross-context call inside an open transaction**: `alpha.add`'s `HELD`
  arm calls `beta_check` while a row lock is held. Either that is allowed and
  visible on the page, or the service loads, decides, closes, then calls out.

## Sources

- Evans, *Domain-Driven Design*, ch. 6 — repository as the illusion of an
  in-memory collection; transaction control left to the client.
- Vernon, *Implementing Domain-Driven Design*, ch. 10 (one aggregate per
  transaction; optimistic concurrency) and ch. 12 (collection- vs
  persistence-oriented repositories; transactions managed by the application
  layer, not the repository).
- Percival & Gregory, *Architecture Patterns with Python* — the general
  `UnitOfWork`, rejected above as the default.
