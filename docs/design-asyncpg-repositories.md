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

- One `asyncpg.Pool` per distinct database, owned by the **app** and closed by
  it after the components. The app derives which pools it owns from the
  components' config coordinates (dedupe the DSNs); there is no "ask each
  component what it needs" round trip, because the config is the requirement.
- `App.__init__` is synchronous and `asyncpg.create_pool` returns a pool that
  refuses `acquire()` until it is awaited, so the app does not hold a pool —
  it holds **databases**, opened in an explicit async step before the first
  request. The lifecycle is construct → `open()` → serve → `close()`:
  `App(cfg)` builds everything without awaiting; `await app.open()` opens
  every database (the pool is created there, and an unreachable database
  fails *here*, at startup, not on the first request); `acquire()` on a
  database that is not open is refused. No lazy initialisation.
- Each component's `Config` derives a `DatabaseRequest` value object from its
  storage coordinate (`None` for `"memory"`; a non-Postgres coordinate is
  refused at config construction). The app builds one `Databases` object from
  the components' requests — one `Database` per distinct request — and hands
  each component `databases.database(cfg.<context>.database)` directly. The
  app never loops and never touches a primitive; `Databases.open()` and
  `Databases.close()` do the iterating.
- The component receives the database it needs and constructs its store from
  it. The component's `close()` releases nothing it didn't build.
- Closing is bounded: `Pool.close()` waits for acquired connections, so the
  database's `close()` wraps it in a timeout and falls back to
  `Pool.terminate()`. A request cancelled inside an open `transaction()` rolls
  back and releases its connection (asyncpg's context managers do this; the
  release is shielded), and that path is tested.
- Schema ownership moves with the pool: today each repository runs its
  `CREATE TABLE IF NOT EXISTS` when it creates its pool. After the split, the
  **store** runs it, once, on first use. Migrations proper stay out of scope.

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
  Vernon's rule (IDDD ch. 10). The types make a transaction that spans two
  stores unwritable; if two rows must change atomically they are one aggregate
  and one repository decomposes it (`repositories.md` rule 1). The types do
  **not** stop a service method from opening two transactions in sequence, or
  nesting them; that is a checker rule (below), not a type.
- **One `transaction()` per service method, and nothing crosses a context
  while it is open.** A cross-context gateway call inside an open transaction
  is a deadlock: alpha holds a connection and a row lock, calls beta, beta
  needs a connection from the same deduped pool. With a pool of one it hangs;
  under load it exhausts the pool. So the service loads and decides inside the
  transaction, and calls out after it closes — or before it opens. This is a
  rule, not an open question.
- Every access goes through `transaction()`; there are no direct methods on
  the store. A lone read opens a trivial transaction. One shape.
- Adapters: `PostgresWidgetStore(database)` acquires a connection, opens a
  transaction, yields `PostgresWidgetRepository(connection)`; commit on exit,
  rollback on exception. `MemoryWidgetStore()` holds an `asyncio.Lock` for
  the length of a transaction and snapshots its dict inside it, restoring on
  exception — the lock is what makes the snapshot correct when two
  transactions interleave, and it serialises the way `FOR UPDATE` does.

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

`#139` is increment 1 and is merged. Increment 3 depends on increment 2: the
store is constructed from the database the app owns, so the database has to
exist first. The order also keeps each PR's rulings separate.

### Ruling required before increment 2

The database as a component constructor parameter collides with two things the
skill says today: `component.md` rule 2 (a component constructs from one
`Config`) and `app.md`'s lifecycle section ("nothing travels — a release
contract that has to be passed is the sign that ownership is unclear"). This
is decided before increment 2 is built, not during. The candidates:

- **Injected infrastructure.** The database is a constructor parameter beside
  the config, like an injected peer port; the app owns its `close()`; the
  component never closes it. Smallest change; amends both rules.
- **A database component.** `Database(cfg)` is its own `ts.Component` kind,
  built first and closed last by the app, injected like `beta.client` is
  today. Keeps "a component releases what it constructed" exact; adds a
  component kind that is not a bounded context, and moves the DSN out of the
  context's config into an app-level `databases` table with the context naming
  which one it uses.

Either way, the app is choosing *which database* a context gets, not *which
implementation* — the coordinate still selects memory versus Postgres inside
the component.

### Increment 2 — pool ownership

The app owns the databases; components receive them; repositories take a
database instead of a DSN.

- `app/app.py`: `Databases(cfg.alpha.database, cfg.beta.database)` — one
  database per distinct request — built before the components; each component
  is handed its own database directly; `open()` opens them all; `close()`
  closes the components, then the databases (bounded, as above).
- `alpha/component/config.py`, `beta/component/config.py`: `Config` derives
  `database: DatabaseRequest | None` from the storage coordinate.
- `alpha/component/component.py`, `beta/component/component.py`: take the
  database as decided above; no request builds the memory repository, a
  database builds the Postgres one, a request with no database is refused;
  the component's `close()` releases nothing.
- `srv/cli/main.py` and every root-tier test: `app = loader.load()`, then
  `await app.open()`, then use, then `await app.close()`.
- `PostgresWidgetRepository(database)`, `PostgresKeyRepository(database)`:
  drop the DSN and the lazy pool-init; each method does
  `async with self._database.acquire() as connection, connection.transaction():`
  around its own query. `CREATE TABLE IF NOT EXISTS` runs once per repository
  on first use, until increment 3 moves it to the store.
- Ports, services, clients, tests above the adapter tier: untouched.
- Tests added: two contexts on one DSN share one pool; the app closes the pool
  once; a request cancelled mid-query releases its connection.
- **Where `Database` lives is an open gap.** Shared infrastructure has no
  governed home in a tree: every module belongs to a context, kernel, srv,
  app, tests, or protocol (TB040); an app module holds only app kinds
  (TB052); a kernel holds only domain kinds. The example puts it in
  `pgdatabase/` under `skip pgdatabase` — the same stand-in `minimal` used for
  `memoryclient` — meaning "this would be an installed package." The real
  choices are to ship it in `tesser-py` (a `tesser.adapters.Database` every
  asyncpg tree imports) or to keep treating it as third-party code. Not ruled.

### Increment 3 — store / repository split

Ports gain the store and the connection-bound repository; adapters split;
services open the transaction.

- `alpha/application/ports/widget_repository.py`: `WidgetStore` with
  `transaction()`; `WidgetRepository` with `load_widget` / `save_widget`; the
  request and response records for each.
- `alpha/adapters/repositories/postgres.py`: `PostgresWidgetStore(database)`
  and `PostgresWidgetRepository(connection)`; the store runs the schema
  statement once on first use.
- `alpha/adapters/repositories/memory.py`: `MemoryWidgetStore()` with the lock
  and snapshot rollback, and `MemoryWidgetRepository(part_by_name)`.
- `alpha/application/alpha_service.py`: holds the store; every use case opens
  `async with self._widget_store.transaction() as widget_repository:`, and
  `add`'s `HELD` arm calls `beta_check` **after** the transaction closes.
- Same for `beta` (`KeyStore` / `KeyRepository`).
- Fakes in tests implement the store and yield a fake repository.
- Tests added: a second `transaction()` on the same store while one is open
  waits (Postgres) or blocks on the lock (memory); a memory transaction that
  raises restores exactly the state before it opened, with another
  transaction's commit in between preserved.

Rulings this forces — all in the ports and service rules, none in the app:

- **A `ts.Store` kind.** `transaction()` takes no `ts.Request` and returns a
  context manager, not a `ts.Response`, so TB081's port-method shape cannot
  admit it by accident. A named kind lets the checker see: a store declares
  exactly `transaction()`; the thing it yields is a repository port; a service
  may depend on a store (TB081's "depends only on ports" widens to "ports and
  stores"); and the request/response records stay in the same leaf module
  without breaking TB067.
- **TB052 one port per module** becomes "one store and the repository it
  yields, or one port."
- **One `transaction()` per service method**, and no gateway or client call
  inside it — the deadlock rule above, checked in the service body the way
  TB082 checks branching.
- **Parameter names shadowing the ports module**: `widget_repository` the
  instance versus `widget_repository` the module. Settle once (alias the
  module, or name the parameter for its kind) rather than per file.

## Sources

- Evans, *Domain-Driven Design*, ch. 6 — repository as the illusion of an
  in-memory collection; transaction control left to the client.
- Vernon, *Implementing Domain-Driven Design*, ch. 10 (one aggregate per
  transaction; optimistic concurrency) and ch. 12 (collection- vs
  persistence-oriented repositories; transactions managed by the application
  layer, not the repository).
- Percival & Gregory, *Architecture Patterns with Python* — the general
  `UnitOfWork`, rejected above as the default.
