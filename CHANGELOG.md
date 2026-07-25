# Changelog

All notable changes to tesser-build are documented here.
Versions follow the 4-digit `MAJOR.MINOR.PATCH.MICRO` format. (This file
versions the toolkit repo as a whole; `tessercheck-py/pyproject.toml`
carries the analyzer package's own version — separate streams.)

## [0.0.9.0] - 2026-07-23

The host↔handler responsibility split. `srv/*/host.py` is a router; a handler
is a transform. Every endpoint is now `(HttpRequest) -> Response` — the host
matches a route, fills the request DTO with what it parsed, calls the endpoint,
and serializes what comes back, with nothing in between.

### Added

- **`HttpRequest` / `Response` DTOs** in `httpwire.py`, named after
  FastAPI/Starlette and stripped to what a hand-written host needs:
  `path_params`, `query_params`, `headers`, a decoded `body`; `status_code`,
  `body`, `headers`. Plus `redirect()` (standing in for `RedirectResponse`),
  `decode_body`, `path_param`, `object_field`, `string_field`.
- **`srv/http/router.py`**: `Route(method, pattern, endpoint)` and `match()` —
  path patterns, `{param}` extraction, percent-decoding, query parsing. The
  only component that knows a URL has structure. Tested in `tests/test_router.py`.
- **One route table** (`srv/http/host.py:routes_for`) naming the whole URL
  surface, including `POST /links/deactivate` — a handler method that existed
  with no route to reach it.
- **A third AST check** (`tests/test_enforcement.py`): the HTTP host imports
  nothing from a context except its `adapters.handlers`. A `client`,
  `application`, or `domain` import in the host is the router reaching past
  the transform.

### Fixed

- **`GET /r/{slug}` is a real redirect.** It returned `302` with the
  destination as a JSON body field (`{"location": ...}`) and no `Location`
  header, so nothing followed it. Response headers made the fix expressible;
  `tests/test_serialization_edges.py` locks it.
- **Malformed request bodies get a problem document.** JSON decoding moved to
  the host (symmetric with the `json.dumps` it already did) and the host's
  whole request path runs through the same `respond` table, so a bad body is a
  400 problem object rather than a handler-specific guard.

### Changed

- **Handlers take a request DTO.** No raw body strings, no loose `campaign_id:
  str` pulled from the URL by the host, no `self.path`. A handler can't reach
  transport state, so its tests build one value and assert on another.
- **`handlers.md`**: new rule 2 (total transform; the host owns format + URL,
  the handler owns shape) and decision 5 (the route table belongs to the host);
  rules renumbered 2-6 → 3-7 and cross-references updated.
- **`srv.md`**: rule 4 restated as router-vs-transform with the host's exact
  four-step request path; new rule 5 (one app-level route table).
- **`python.md`, example README**: rewritten around the split. skill-version
  19 → 20.
- The CLI host is deliberately untouched — its commands still translate
  inline, and `python.md` now says so explicitly rather than leaving a reader
  to assume the HTTP shape applies.

## [0.0.8.0] - 2026-07-23

The reports context gets its inbound edge. `reports` was served over HTTP but
owned no handler — the host built its response body inline — and the docs
justified the gap with an argument about the *outbound* direction. The two
directions are independent: composing peers through injected `Client`s says
nothing about the inbound edge.

### Added

- **`reports/adapters/handlers/http.py`** in `examples/python-app`: the
  cross-context read model translates its own `Client` DTOs to the wire, like
  every other exposed context. The host now routes to it.
- **`examples/python-app/httpwire.py`**: the HTTP mechanism's shared wire
  vocabulary (`Response`, `BadRequest`, `problem`, `respond`), lifted out of
  campaign's handler so a second context serving the same mechanism doesn't
  import a sibling's adapter internals.
- **Two AST checks** in `tests/test_enforcement.py`, replacing a hardcoded
  name allowlist in `test_shape.py`: every context a host reaches owns a
  handler role, and the HTTP host never calls a context `Client`. Both proven
  on injected violations, including the aliased form (`reports = app.reports`)
  that a naive attribute check misses — the exact shape of the defect fixed
  here.

### Changed

- **`handlers.md`**: new rule 5 (a context a host exposes owns a handler —
  `adapters` is optional only while a context has no edge) and decision 4
  (where the shared wire vocabulary lives); "the host translates" added to
  common mistakes.
- **`srv.md`**: dropped the carve-out sanctioning a read-model rendered inline
  instead of via a handler — it was written to describe this defect, not a
  rule. The CLI's single-command inline dispatch (`handlers.md` decision 2)
  is untouched and remains the one genuine carve-out.
- **`map.md`, `python.md`, `examples/python-app/README.md`**: the
  cross-context read model needs no *gateways*; it owns a *handler* the moment
  a host serves it. `python.md`'s handler block now shows the shared
  `httpwire` module it actually imports. skill-version 18 → 19.

## [0.0.7.0] - 2026-07-22

The host-lifecycle wave: who owns starting the hosts, and how. Gives the
worked example a real process lifecycle and a single config loader, reconciles
the anatomy docs to match, and drops the word "seam" from the vocabulary.
Merged as #31 (unversioned) and reconciled here after a Codex coherence
challenge on the skills + example.

### Added

- **Host lifecycle in `examples/python-app`.** A `Host` protocol (`run(stop)`);
  `srv/http/host.HttpHost` (serve in a thread, drain on stop); and
  `srv/run.run_until_signal`, which installs SIGINT/SIGTERM and calls
  `App.close()` in a `finally`. The load-bearing fix: a bare
  `finally: app.close()` does not survive Python's default SIGTERM, so the old
  host leaked the graph on a container stop.
- **One config loader** (`bootstrap/config.from_env(getenv)`): the single place
  the app reads the environment; `getenv` injected, so it stays pure and
  testable. Reinstates the shared decoder the docs had wrongly banned. A bad
  `HTTP_PORT` fails fast with a named error.
- **`App.close_errors`**: the errors `CleanupStack` collects are retained
  instead of dropped.

### Changed

- **Anatomy docs reconciled** (`srv.md`, `bootstrap.md`, `map.md`, `python.md`;
  skill-version 18): the one-loader rule (reverses "no shared decoder"), the
  `Host`/runner lifecycle and the plain SIGTERM truth, the rule-5
  platform-sidecar carve-out (which also reconciled `map.md` with `srv.md`), and
  `App.close_errors`.
- **Coherence pass (Codex-verified).** Six doc-vs-example overclaims corrected:
  the host mounts handlers for the contexts it exposes (a single read-model is
  rendered inline, as the example does); `from_env`'s env-read precision in
  `srv.md`/`bootstrap.md`; the static-bundle host reconciled with rule 5; and
  the runner's `close()` now cited to its own test.
- **"seam" removed** from all skill docs (it named no specific boundary):
  → "public interface" / "build contract" / "respond path" / "boundary".

## [0.0.6.0] - 2026-07-21

The serialization wave: how a domain object is built, and how its primitive
gets out. Seven commits across six pull requests, landing a new norm document,
four new Python checks, and the worked examples that prove them.

### Added

- **The serialization norm** (`skills/tesser-build/serialization.md`): one
  document covering how a value object, entity or aggregate crosses an edge.
  Its core is the **parts pattern** — a per-context module in the application
  layer owning the single decompose walk into a total, typed, domain-named
  record. Edges own their wire keys; goldens live on edges only. This is the
  only direction-legal home: both the application service's `Respond` and the
  adapters consume it, and adapters may import application but never the
  reverse.
- **A leaf value object's canonical exit is pinned, and pinned once.** Each
  backing type has exactly one conversion dunder (`__str__`/`__int__`/
  `__float__`/`__bytes__`) delegating to one policy helper, so a consumer's
  tenth datetime value object cannot drift from the format. `Decimal` exits as
  a scientific string; `datetime` as UTC-normalized ISO-8601 at microsecond
  precision, with naive datetimes refused. Compounds, entities and aggregates
  have no primitive exit at all — they decompose structurally, and `repr` is
  the debug surface.
- **Four new checks.** `TB015` stops a domain object serializing itself (no
  spec-returning method, no emit-a-sink, no second or mismatched exit, and no
  conversion dunder at all on a structured type). `TB016` governs what a value
  object is built from — compounds hold child value objects, and `bool`/
  `complex` are not value-object material. `TB017` enforces ONE construction
  door: any classmethod or staticmethod returning its own type is a second
  door, whatever it is named. `TB018` requires each canonical exit to be a
  one-line delegation to its policy helper.
- **`examples/serdepy`**, a worked example covering every serialization case:
  all four exits, the Decimal and datetime policies including their accepted
  edges, a zero-dunder compound, and a parts record with a derived field that
  proves parts are not specs.
- **`web/presentation` is a named app-level role** in the anatomy, so a UI or
  SPA has a stated home rather than being placed by taste.

### Changed

- **A compound value object now holds child value objects, not bare
  primitives** — `Money` is `MoneyAmount` + `MoneyCurrency`, and each rule
  lives on the type that owns it, so no construction path can skip one.
- **One door per type, uniformly** (2026-07-21). A value object constructs
  through its own `__init__` and nothing else. This swept in the collection
  value object's `new`/`require` pair, which had looked like an exception and
  turned out to be the case that settled it: two doors with different
  invariants mean the type's guarantee depends on which door the caller
  picked, so it guarantees nothing. When you need a stricter set, that is a
  different type.
- Repositories store reconstructable rows rather than live objects, so a load
  rebuilds a value-equal, non-identical aggregate with its invariants re-run.
- `python.md`, `go.md`, `handlers.md` and the check catalogs were reconciled
  to the above; `skill-version` is now 16.

### Fixed

- A campaign's short link could never be deactivated: the domain supported the
  state but no use case reached it, leaving the guard that reads it dead. The
  use case is now wired end to end.
- The analyzer no longer aborts a whole tree scan on one pathological file — a
  deep string annotation raised an error the parser guard did not catch,
  losing every finding for every other file and exiting with a traceback.
- `TB018` no longer reports the module-qualified spelling
  (`serialization.canonical_str(x)`) as hand-rolled; both import idioms are the
  same delegation.

## [0.0.5.0] - 2026-07-20

### Added

- **A testing norm.** `skills/tesser-build/testing.md` is the cross-cutting
  layer the eleven per-component "Tests you must write" sections assumed but
  never had: how a test is written, what it must prove, and what a test double
  may be. Two rules carry teeth, six are guidance, and everything still
  undecided (test layout, grouping, table tests, coverage stance) is listed as
  open rather than smuggled in as prose.
- **`TB030` — the fakes-only test-double check.** A test double is a
  hand-written fake, so mocking libraries are out: `unittest.mock` and its
  submodules in every import shape, the `mock` backport, pytest-mock's `mocker`,
  and `MonkeyPatch` from either `pytest` or its private home. It catches the
  `import unittest` → `unittest.mock.patch` reach-through too. Import detection
  is tree-wide — domain code has no business importing a mock library either —
  while the fixture-parameter rule fires only inside a pytest-shaped function,
  so a production parameter that happens to be named `monkeypatch` stays clean.
  A test that must patch a seam it cannot inject through declares it with
  `# tessercheck:ignore`, matched as a real comment token (marker text inside a
  string cannot silently suppress anything) and honoured across a
  formatter-wrapped import's whole span. The syntactic holes it does not close —
  aliased module imports, dynamic import, `request.getfixturevalue` — are
  documented in the checker itself rather than left implied.
- **The reviewed contract for `TB031` (construction completeness).** Every
  spec-constructed type gets one test that builds a valid instance and asserts
  every spec field round-tripped to its accessor — compared against the spec,
  never a hardcoded literal, so a field added to the spec but never asserted
  stops being a silent gap. The `good_tree`/`bad_tree` fixture pair lands
  first, per the fixtures-first discipline; the checker follows.

### Changed

- The `norm-testing` row goes from the emptiest in the roadmap matrix (every
  column ❌) to a documented norm with a live Python checker.

## [0.0.4.0] - 2026-07-19

### Added

- `--exclude` on the tessercheck-py CLI: declare root-level packages out of
  both the totality guard and the checked file set — scratch/demo packages
  that will never be contexts, or contexts not yet adopted. This is the
  incremental-adoption ratchet the first consumer run showed was missing:
  a repo can now put the guard in CI on the contexts that conform today
  and drive the exclusion list to zero, while exit-2 teeth stay total over
  everything not explicitly declared. An exclusion wins even over an
  explicitly-passed path, so discovery and the checks can never disagree.
- The no-primitive-escape ruling for value objects (2026-07-19): an
  accessor that hands the wrapped primitive straight back — a compound
  component (`rect.x` returning `"1"`) or a leaf `value` property — is the
  public field with extra steps. TB010 now flags the passthrough-accessor
  shape (including the one-alias disguise `v = self._x; return v` and
  `Optional`/union-wrapped primitives), components are exposed as value
  objects, and `__str__` stays the sole primitive exit. The design doc's
  earlier "safe single-representation accessor" allowance is closed with
  dated amendments; the Go-side mirror analyzer is queued in TODOS.md.

### Changed

- TB001's total scope is now stated, not implied: every dataclass is
  frozen — specs and adapter DTOs included, because frozen costs an inert
  carrier nothing and a non-frozen dataclass is invisible to the VO
  classifier. The finding message and docs say exactly that instead of
  the domain-scoped wording that invited pushback.
- The totality guard distinguishes "you have no seam" from "your seam
  isn't surfaced": a context whose `client.py` exists but isn't
  re-exported gets the precise three-line fix message.
- `value-objects.md` / `python.md` reconciled to the strengthened norm:
  the stale public-field `EmailAddress` example hidden, the compound-VO
  construction REVISIT narrowed to the two sanctioned shapes, and the
  field-hiding construction-break warning added (hiding a field renames
  the dataclass `__init__` parameter — construct through the spec), the
  friction the first consumer migration actually hit (skill-version 12).

### Fixed

- TB003 no longer flags the spec-taking `__init__` of a
  `@dataclass(frozen=True, init=False)` assigning its own declared fields
  — the construction shape TB013 itself prescribes had no conformant way
  to assign fields, so the norm penalized code for following another norm
  (the first consumer's entire TB003 count was this false-positive class).
  The exemption is deliberately narrow: `__delattr__`, ordinary methods,
  non-field names, and an undeclared hand-written `__init__` stay flagged.
- `frozen`/`init` dataclass keywords are read by constant truthiness,
  matching runtime semantics: `init=0` is a valid spec-init shape and
  `frozen=1` freezes — no more false positives on runtime-valid code.

## [0.0.3.0] - 2026-07-19

### Added

- The comments norm, v0 (`skills/tesser-build/comments.md`): constructed-app
  code carries **zero comments, docstrings, or bare string-literal
  statements** — machine directives (shebang, PEP 263 coding lines,
  `type:`/`noqa`/`pragma`, formatter controls, Go `//go:` directives, build
  constraints, cgo preambles, roadmap markers, generated files) are the
  only exemptions, and new carve-outs enter only from observed evidence,
  each with its case, principle, and enforcement update in the same change.
  Enforced in both languages from day one: `TB020` (no-comments) in
  tessercheck-py and the `comments` analyzer in tessercheck, with the
  example trees stripped to conform (they are production templates — what
  they carry gets cloned) and CI gates on every example tree.
- App-level anatomy doctrine materialized: `wiring.md`, `srv.md`,
  `handlers.md`, and `bootstrap.md` are now full docs (uniform
  `build(cfg, deps) → (Client, Closeable)` seam, host-is-the-env-edge,
  the one respond seam for wire errors, cleanup-stack lifecycle), with
  `python.md` reworked to the settled bootstrap + per-context-wiring shape
  and a new "Inbound handlers and hosts" mechanics section — the
  previously agent-decided pieces of the anatomy now have a bare-minimum
  convention an agent must follow instead of invent (skill-version 11).

### Fixed

- The zero-comment checks survived their own adversarial round: the coding
  exemption is anchored to PEP 263's lines 1-2 (prose containing
  "coding=" no longer escapes), a bare string literal mid-body is flagged
  as a smuggled comment, a tokenize failure is loud instead of silently
  comment-blind, cgo preambles and `/*line*/` directives are exempt so the
  analyzer can't tell a consumer to delete compile-critical code, and
  every directive in both exemption ledgers now has an exercising test
  (the analyzer sits at 100% statement coverage).

## [0.0.2.0] - 2026-07-19

### Added

- Context discovery in tessercheck-py (`--app-root`): bounded contexts are
  discovered by their `Client` seam, and the totality guard fails loudly —
  naming the package and the fix — on any root-level package that is
  neither app-level plumbing nor a Client-bearing context, so a context
  that forgot its `Client` can't hide from the checks. `--app-level`
  extends the app-level set by declaration. CI now runs the discovery gate
  on the verified impl (`examples/python-app`) with zero configuration.
- Typed roadmap registry rows: `kind: rule` rows render a second "Pay-now
  rules" table (rule / taught in / enforced by / status) with
  existence-checked `taught_in` paths, validated `#anchor`s, and honest
  "enforcer declared" status wording; a malformed `kind` is a named
  file:line error. First rule row: dependency direction (acyclic, inward),
  enforced by consumer-side import-linter contracts.

### Fixed

- Discovery survives absolute app roots under hidden ancestor directories
  and prunes vendored trees during the walk; a dead, `TYPE_CHECKING`-only,
  or nested `Client` binding no longer counts as a context seam (both
  found by the cumulative cross-model review round).

## [0.0.1.0] - 2026-07-19

### Added

- `docs/field-audit-checklist.md` — the consumer-side field-audit runbook:
  how to run a one-day friction audit inside any consumer repo behind an IP
  wall, classify each friction with the two-leg deferral test into the
  pay-now bins, and relay only de-identified, pattern-shaped findings back.
  Includes IP-wall guardrails (no verbatim consumer text, raw log stays
  behind the wall, identifiability self-check) and a worked relay entry.
