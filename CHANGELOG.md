# Changelog

All notable changes to tesser-build are documented here.
Versions follow the 4-digit `MAJOR.MINOR.PATCH.MICRO` format. (This file
versions the toolkit repo as a whole; `tessercheck-py/pyproject.toml`
carries the analyzer package's own version — separate streams.)

## [0.0.16.0] - 2026-08-06

The import-totality wave: sigcheck's rulebook grows from 41 to 56 rules
so that every `.py` file in a governed tree answers for its imports —
what it may import, in what form, and whether it has a home at all.

Four new rule families, each ruled in-session and landed with exact
fixture coverage. The tesser shell import is exactly once, as `ts`: a
role module imports precisely its role's shell package in the
`import tesser.<role> as ts` form — no duplicates, no other alias, no
member imports — and a test module imports only `tesser.testing`, at
most once (exactly-once arrives when tests declare themselves).
Whole-tree totality: a module whose top-level package is not a context,
`srv`, `bootstrap`, or `tests` is homeless; a tests package holds only
test modules and conftest; srv and bootstrap gain statement totality
(declared functions, Final constants, `tesser.context` as their shell —
a class there flags, surfacing the still-open host-vocabulary
question); a role `__init__` only re-exports from its own role. The
pure-core allowlist: domain, client, and application import only their
context, their shell, and a small pure-stdlib set (exact dotted entries
supported), so ambient IO — filesystem, network, environment, entropy —
is a violation by default rather than by enumeration; adapters, wiring,
and the hosts stay free. Module-only imports: a context module is
imported as an aliased module, never its members — the alias
requirement is what keeps qualified access classifiable — with
stdlib from-imports untouched and direction-illegal edges never
double-flagged for form.

The ship reviews made the walker honest before landing: relative
imports now resolve against the module's package (previously invisible
to every import rule — a relative domain import could walk a domain
object through an adapter signature unseen), and classification is
module-level-only, so a function-local import neither satisfies
presence nor shadows the alias table. The live spike, digest, and
sigcheck trees practice the idiom they enforce; `sigcheck` itself runs
over its own tree in CI, and a new gate on `examples/python-app` holds
its 173-finding conformance bill as a fail-closed, self-tightening
finding-set ratchet (new findings fail even at an equal count; entries
that stop firing fail as stale) until the conformance wave burns it
down. RULES.md gains a Named exemptions section — conftest, `__main__`,
and tooling modules are visible carve-outs now, not silent ones — and a
rule can no longer ship without a fixture: an uncovered clause is a
suite failure, not a NONE cell.

Also in this release (landed on main by the python-app migration, PR
#50, between versions): the tessercheck-py analyzer's TB003 now treats
a `tesser.domain.ValueObject` subclass `__init__` as a sanctioned
construction site, alongside the frozen-dataclass forms.

## [0.0.15.0] - 2026-08-05

The declare-then-verify spike: `examples/spike-shells` explores the
totality/superclasses direction as running code. `tesser-py` grows shell
packages (`tesser.context`, `tesser.application`, `tesser.adapters`, and
companions to `tesser.domain`) whose classes — `Request`, `Response`,
`Spec`, `Entity`, `AggregateRoot`, `ApplicationService`, `Parts`, `Port`,
`Repository` — carry no behavior:
subclassing one is a *declaration* of what a class is, and everything else
verifies against that declaration. The spike app (`spike/`) is a note
service wired entirely through the shells, and `sigcheck` is the verifier —
itself written in the declared idiom it checks, and run over its own tree.

What sigcheck enforces, each rule ruled in-session and landed with fixtures
plus a live violation-injection run: an aggregate constructs from exactly
one `ts.Spec`; a public service method takes exactly one request DTO and
returns a response DTO; a service method body is at most 10 source lines,
branches one level deep (an `elif` chain is one level, distinguished from a
nested `else: if` by column offset), and satisfies every if-condition and
match-subject with one domain call — no comparisons, no boolean
composition, no attribute tests; and a service inlines its logic — no
delegation to sibling methods or same-module functions, any prefix, checked
in every method including privates. Import direction is contracts, not an
AST walk: four generic import-linter contracts (domain → tesser.domain
only; client DTOs → tesser.context only; application never reaches
adapters; adapters read parts, never domain).

The spike documents itself: `rules.py` derives `RULES.md` from the
implementation — one row per normative clause (the tail every violation
message must end with, a convention the generator itself enforces), holes
rendered as reader names via a totality-guarded map, parameterized messages
instantiated from their call-site literals, and fixture coverage computed
as an exact clause-containment join rather than a heuristic. A drift test
makes a stale RULES.md a suite failure. Deliberately spike-scoped: no CI
job, no analyzer integration, and the open rulings (lines vs statements,
negated single calls, ternary/comprehension evasions, the Go `err != nil`
rendering) stay open — this lands the exploration, not the norm.

## [0.0.14.0] - 2026-08-01

mutmut silently skips any class that carries any decorator — the whole body,
methods included — so the frozen-dataclass value-object idiom yields zero
mutants: mutation testing is blind to exactly the code the conventions care
most about. Measured on a Money example, the dataclass rendering produced no
mutants in its own module while an undecorated rendering produced over a
hundred, nearly all in real validation and domain logic.

So the repo grows its first runtime artifact: `tesser-py/`, shipping
`tesser.domain.ValueObject`. Subclasses get type-exact `__dict__` equality, a
derived hash, a generic repr, and a frozen guard; every stored field joins
equality automatically, so adding a field stays a one-site edit and the
dropped-field equality defect is not expressible per class. The base defends
its own contract: `__init_subclass__` rejects `__slots__` anywhere in the MRO
(a slotted co-base silently collapses every instance into one equality class)
and rejects `__eq__`/`__hash__`/`__setattr__`/`__delattr__` overrides.
`examples/vobase/` is the worked example — catalog's Money ported to
`class Money(ts.ValueObject)` — and both trees are CI-gated at mypy --strict
+ pytest and carry mutmut configs that run clean (the one surviving mutant is
a verified-equivalent Decimal format flag).

The port is deliberately harder than the original, because four adversarial
review rounds attacked it and every round found something mutation testing
could not: amounts are plain ASCII decimal strings within ±40 orders of
magnitude with one canonical zero, `add` runs in a pinned decimal context and
raises rather than silently rounding, currency codes are exactly three
uppercase letters, and the canonical decimal exit bounds its output instead
of amplifying an 11-character exponent into a 50MB string. The catalog
original still carries the gaps this port closed — that follow-up, plus
teaching the analyzer to classify the new shape, is queued in TODOS.md.

This is a candidate successor shape under evaluation, not the taught
convention: the skill and `examples/python` still render the frozen-dataclass
idiom, and `examples/vobase` is deliberately not tessercheck-gated until the
classifier learns the shape.

## [0.0.13.1] - 2026-07-26

A quoted annotation is the same annotation — `_value: "str"` names `str`
exactly as the bare form does — but the analyzer read the two differently,
because the annotation-name walk existed as five diverged copies and only the
newest resolved string forward references. The divergence cut both ways on
conformant code: quoting a leaf's backing field made every leaf value object
in every example tree misread as *structured* and its one legitimate `__str__`
exit flag as an illegal dunder (TB015), while the same quote *hid* a primitive
from the accessor ban (TB010) and a held aggregate root from the boundary rule
(TB012). A trap for conformant code and an escape hatch for non-conformant
code, from one missing behavior.

### Fixed

- One shared walk in `astutil` now serves the classifier and every
  annotation-reading check: forward references resolve everywhere, fail closed
  on unparseable content (crediting no name), and are depth-capped only on
  quote-in-quote re-entry — plain generic nesting resolves at any depth.
- `Literal["Warehouse"]` values and `Annotated[X, ...]` metadata are values,
  not forward references — a tagged-union discriminator no longer reads as
  holding the type its string happens to spell. Strings there are left alone
  while everything else is walked, so a codebase with its *own* `Literal`
  class keeps its checks.
- TB017 no longer calls a `-> type[Slug]` classmethod a second construction
  door, and an annotation that cleanly names another type is taken at its
  word even when a `type[...]`/`Callable[...]` slot beside it holds garbage.
- Nested quoted annotations no longer re-parse per visiting level — the
  forward-reference parse is memoized, removing a measured 12–33x wall-clock
  amplification on quote-dense input. On ordinary code the unified walk is
  about twice as fast per annotation as the copies it replaced.

### Added

- A metamorphic guard: quoting every annotation in every Python example tree
  and every check fixture must change no finding. The example trees catch a
  finding appearing (the false-positive direction); the fixture corpus, which
  carries findings across every registered code, catches one disappearing
  (quoting as an escape hatch). Trees are discovered, not enumerated.
- A direct contract table pinning the shared walk across twenty annotation
  shapes, and regression tests for every behavior above.

## [0.0.13.0] - 2026-07-26

Agent-written tests come out over-DRY. Setup gets factored until the thing that
makes each test *that* test is buried in shared machinery, and you can no longer
read a test and know what it claims. That was named as a harness artifact, not a
style preference: DRY reads as a virtue everywhere else, and nothing in the norm
told anyone that test code inverts the trade. Production code pays repetition to
buy a single point of change; a test's job is the opposite.

So `testing.md` gains rule 9 — a helper builds a **spec or a DTO** and nothing
else — and `TB032` enforces it. TB032 is the analyzer's first **totality** check,
and the shape is the interesting part: every other check hunts a known-bad
pattern and stays quiet otherwise, which is the wrong instrument when the failure
mode is *variety*. There is no single bad helper to match. So this one inverts
it: every module-level function in a test module must classify as something
sanctioned, and everything else is reported. The output is a worklist, not an
accusation — 23 functions across four example trees, all now conformant.

`TB033` arrives from a question that got answered by rejecting its premise.
The open question was whether the builtin-shadowing ban should target spec
**field** names or helper **parameter** names. Running both cases settled it:
a dataclass field named `id` costs nothing (the builtin stays callable in methods
and `__post_init__`), while a parameter named `id` genuinely breaks. But no site
in the repo had that bug, so a name-based ban would have taxed 12 sites to
prevent something occurring at none of them — two of which are
`BaseHTTPRequestHandler.log_message` overrides that cannot legally be renamed.
TB033 therefore targets the **collision, not the name**: a builtin bound in a
scope that the same scope then calls. Ruff's `A001`/`A002` already ship the name
ban; nothing off the shelf checks the call shape.

### Added
- **`TB032` (test-helper-totality)** — every module-level function in a test
  module must classify as a spec/DTO-returning helper or a `@pytest.fixture`.
  What cannot be decided structurally declares itself with
  `# tesser-category: <spec|dto|fixture>`, a closed set. Scope is deliberately
  module-level: every non-test *method* on a class in a test file is a
  hand-written double, which the fakes-only norm *requires*.
- **`TB033` (shadowed-builtin-called)** — a builtin name bound in a scope
  (parameter or local) that the same scope then calls. `TypeError` if the binding
  runs first, `UnboundLocalError` if it does not; order carries no signal,
  because Python scopes per function.
- **`testing.md` rule 9**, with the four consequences derived rather than listed:
  never return a constructed domain object, never call, defaults in keyword
  arguments, and spec fields hold primitives or child specs.
- A shared `# tesser-category:` marker vocabulary read by both the comments norm
  and TB032 through one parser, so the two cannot disagree about what a marker is.

### Changed
- Test helpers across `examples/python`, `examples/python-app`,
  `examples/serdepy` and `examples/errorspy` now conform. Three different fixes,
  because "not a helper" has more than one cause: a helper returning a domain
  object returns the spec instead and the test constructs at the call site; a
  helper that *calls* something was never a helper and its work moves into the
  test; a helper that is a pure rename is deleted.
- `skill-version` 24 → 25.

### Removed
- `examples/python-app/tests/wire.py` — `json_body` was a pure alias for
  `decode_body(resp.body)`, supplying no default and saving no reader anything.
  Its 14 call sites now name `httpwire` directly.

### Fixed
Adversarial review found ten issues; eight were real and are fixed. Two were
false positives, which is the expensive class for an analyzer that runs in other
people's CI:
- A forward-reference annotation (`-> "LinkSpec"`) carries no name node at all,
  so a conformant spec helper was reported. Quoted annotations are ordinary
  Python.
- A parameter default is evaluated in the *enclosing* scope, so
  `def f(len=len("ab"))` calls the builtin and must not be flagged.
- A production class with a `test_*` method (`Client.test_connection`) made the
  whole module a test module and dragged the production functions beside it into
  TB032's scope. Detection now mirrors pytest's own collection rules, including
  `unittest.TestCase` subclasses whatever they are named.
- A decorated helper's trailing `# tesser-category:` marker was never read.
- The comments norm exempted a bare category prefix, letting prose ride through
  a directive as cover.
- Lambda and class-body scopes were never judged by TB033 — the class-body case
  executes at import time and breaks the module for every importer.
- `except E as name` binds a name, but the alias is not a name node and was missed.
- `global`/`nonlocal` rebinds are now left alone rather than flagged; which
  target the call reaches depends on execution order, which one AST pass cannot
  decide.

## [0.0.12.0] - 2026-07-26

Four of the seven hand-written architecture detectors in `examples/python-app`
were re-deriving what two off-the-shelf tools already decide. They are now
config. The split is by **who can decide the rule**, not by taste: ruff and
import-linter take the generic import and API hygiene, and the three rules that
encode this toolkit's own doctrine stay hand-written, because no tool covers
them.

The interesting residue is which three survived — no import-time side effects,
host-routes-never-translates, and context discovery. Those are exactly the rules
`srv.md` and `handlers.md` are named after. Generic architecture hygiene has
tools; doctrine does not.

One config decision is load-bearing and worth stealing: import-linter's
`forbidden` contract is **transitive by default**, so
`srv.http.main -> bootstrap.bootstrap -> linkpolicy` reads as a violation when
it is precisely what a composition root is for. Every contract sets
`allow_indirect_imports = true`. Without it the contracts are unusably red.

### Added

- **`examples/python-app/ruff.toml`** — the environment is read only in
  `srv/*/main.py` and only the edge exits, as `TID251` banned-api plus
  `per-file-ignores`; bare `exit`/`quit` via `PLR1722`, never lifted; and `F401`
  so the tree consumers copy carries no dead imports. Ruff is strictly stronger
  than the detector it replaced: it also catches `from os import getenv`, which
  an attribute-only walk missed.
- **`examples/python-app/.importlinter`** — three `forbidden` contracts: a host
  reaches a context only through its `adapters.handlers`, linkpolicy imports no
  peer, campaign never imports reports.
- **`tests/test_architecture_teeth.py`** — a config is code, so it gets teeth.
  Injects violations, runs each linter, asserts it still fails. Drilled against
  five rot vectors (a deleted ban, `per-file-ignores` widened to `srv/**`, a
  handler ignore widened to `campaign.**`, `allow_indirect_imports` removed,
  `PLR1722` deselected) — each fails the test that owns it. Without this, any of
  the five disables a rule with the suite green.
- **A totality guard over the contracts** (`tests/test_discovery.py`): the
  `.importlinter` *enumerates* contexts while this app *discovers* them, so a new
  context would have been silently unguarded. The guard asserts every discovered
  context appears in `root_packages` and in the host contract's
  `forbidden_modules`, with teeth for an omission from either.
- Two CI steps and two dev dependencies (`ruff`, `import-linter`). The analyzer
  in `tessercheck-py` stays zero-dependency; these gate the example.

### Changed

- `bootstrap.md`, `srv.md`, `handlers.md`, `gateway-cross-context.md`, and
  `map.md` cite the config that now enforces each rule.
  `srv.md#tests-you-must-write` says to **declare** the env and exit rules in
  ruff and then test the config, rather than to hand-write the AST walk.
  skill-version 23 → 24.
- `roadmap/registry.json`: four component rows and the dependency-direction rule
  row point at what actually enforces them.

### Removed

- `tests/test_direction.py` entirely, and `_env_reads`, `_exits`,
  `_env_offenders`, `_is_env_edge`, `_context_imports`, `_py_files` plus their
  tests from `tests/test_enforcement.py`.
- Two dead imports the new `F401` rule surfaced (`cliwire.py`,
  `tests/test_canonical.py`).

## [0.0.11.1] - 2026-07-25

A regression guard, not a feature. Streaming is deliberately **not** on the
roadmap — the example teaches enough that a reader can derive it (and auth,
content negotiation, …) from the existing DTOs. What matters is that those DTOs
stay faithful HTTP request/response objects so that remains true.

### Added

- **HTTP-DTO fidelity tests** (`tests/test_httpwire.py`): lock that `HttpRequest`
  keeps method / path / params / headers + an **opaque `bytes` body**, and
  `Response` keeps `status_code` / headers + an **opaque `bytes` body**. The
  guard exists to catch the one drift that would foreclose deriving streaming
  and friends — collapsing the body back to a decoded `dict` for convenience.
- `handlers.md` states the fidelity contract explicitly and points at the lock.
  skill-version 22 → 23.

## [0.0.11.0] - 2026-07-25

The CLI host gets the same router/transform split as HTTP — proving the anatomy
is mechanism-independent, and fixing a real defect: the inline CLI had no error
table, so a bad argument or a domain rejection printed a Python traceback and
exited 1 instead of a clean message and a meaningful code. It also reached
straight into a context's `Client` DTOs, the reach-past-the-handler the HTTP
host now forbids.

### Added

- **`cliwire.py`** — the CLI mechanism's shared vocabulary, the analog of
  `httpwire.py`: `CliRequest(args)`, `CliResponse(exit_code, stdout, stderr)`,
  `respond()` (the error table), and `UsageError` / `arg` / `no_extra_args`
  helpers.
- **`campaign/adapters/handlers/cli.py`** — one `(CliRequest) -> CliResponse`
  transform per command, sibling to the HTTP handler over the same `Client`. No
  `argv`, no `print`, no `sys.exit`: unit-testable by constructing one value.
- **`errors.exit_code_for(kind)`** — the CLI's error mapper: the same closed
  domain `Kind` set mapped to an exit code (validation → 2, not_found/conflict →
  1), exhaustive via `assert_never`, exactly as `status_for` maps it to an HTTP
  status. One taxonomy, two total edge mappers.
- **`tests/test_cli.py`** — the handler transforms (success, domain rejection →
  exit 2 not a traceback, usage errors), the `respond` table per failure class
  (incl. no-leak-on-unexpected), and the dispatcher's routing (known / unknown /
  no command).

### Changed

- **`srv/cli/main.py` is now a dispatcher.** It builds a command route table
  (`commands_for`), matches `argv[0]`, hands the rest to the handler as a
  `CliRequest`, prints `stdout`/`stderr`, and `sys.exit`s the `exit_code`. It
  imports only `campaign.adapters.handlers.cli`, never the context's `Client`.
- **The host-boundary enforcement now covers every host, not just HTTP.**
  `test_enforcement.py`'s "routes and never translates" and "imports only
  handlers from contexts" checks were generalized from `srv/http` to all of
  `srv/`, so the CLI host is held to the same rule.
- **Docs**: `handlers.md` decision 2 rewritten (single-command inline stands;
  multiple commands earn the split — the CLI shows the grown form); `srv.md`
  shape + a mechanism-parallel note; `python.md` CLI section rewritten with the
  `cliwire`/dispatch shape (resolving the prior "is a CLI DTO the right shape?"
  open question); example README run-command fixed (`create-link` → a real
  command) with a CLI-parallel paragraph; `rationale/coverage.md` row.
  skill-version 21 → 22.

### Fixed

Four review-cycle catches on the HTTP edge (`/ship` lightweight review +
a Codex adversarial pass):

- **Response-splitting via the redirect `Location` (security).** `TargetURL`
  accepted a URL with embedded control characters (`urlparse` only checks
  scheme + host), and `http.server`'s `send_header` does not sanitize CRLF, so a
  stored `https://…/\r\nX-Injected: yes` target injected headers on
  `GET /r/<slug>`. Fixed at the value object — `TargetURL` now rejects any
  control character, closing it for every consumer, not just the redirect path.
- **A malformed `Content-Length` returns 400, not 500.** A non-numeric header
  (`Content-Length: abc`) raised `ValueError` from `int()`, caught only by
  `respond`'s catch-all → a 500 for a client framing error. `content_length`
  now raises `BadRequest`.
- **An invalid-UTF-8 body returns 400, not 500.** `decode_body` caught
  `json.JSONDecodeError` but not `UnicodeDecodeError` (`json.loads(b"\xff")`
  raises the latter) → a 500. Now caught as `malformed_request`.
- **Header framing is case-insensitive, as HTTP requires.** The host copied
  headers into a case-sensitive dict, so a client sending lowercase
  `content-length` / `transfer-encoding` defeated the body read and the 411
  guard. The host now lowercases header keys and `content_length` matches
  case-insensitively.

All four locked by tests (`test_httpwire.py`, `test_roundtrip_law.py`).

### Boundary (documented, not built)

- Piped **stdin** is the CLI's "body" and reopens the buffered-vs-stream
  question; no command reads it, so it stays a named boundary.

## [0.0.10.0] - 2026-07-25

The edge goes content-type-agnostic. The host stops parsing bodies: `req.body`
and `Response.body` are raw `bytes`, the handler decodes and serializes and owns
its `Content-Type`, and the host only moves bytes and copies headers. A `.png`
in or out is now expressible without touching the host — the reason the parsing
belonged in the handler all along.

### Changed

- **`HttpRequest.body` and `Response.body` are `bytes`.** The host reads the
  declared body off the socket as raw bytes and writes the response bytes back;
  it no longer calls `json.loads`/`json.dumps` or sets a hardcoded
  `Content-Type`. Handlers call `decode_body(req.body)` for JSON and return
  `json_response(...)` / `redirect(...)`, which serialize and set the type.
- **`httpwire`**: `json_response()` (encode + `Content-Type: application/json`,
  used by every handler and every problem doc), `content_length()` (the framing
  guard, below), and `decode_body()` now takes `bytes`. `respond()` returns
  `json_response`.

### Added

- **Framing guards at the host, decided from the headers before a handler runs:**
  a body over a 1 MiB buffer cap → **413**; a `Transfer-Encoding: chunked`
  (streaming) body the buffering host won't read → **411** with a message
  pointing at the boundary. Both render through the same `respond`/`problem`
  vocabulary as every other error, so the whole process speaks one error format.
  `content_length()` is a pure function of the headers, unit-tested in
  `tests/test_httpwire.py` (declared size reads; chunked → 411; over-cap → 413),
  alongside `json_response`, `redirect`, `decode_body`, and the full `respond`
  table.
- **`tests/wire.py`** — `json_request(obj)` / `json_body(resp)` test helpers, now
  that request and response bodies are bytes.

### Boundary (documented, not built)

- **Streaming and non-JSON payloads.** The impl buffers: fine for JSON, a form
  post, or a single bounded file. A live/large stream isn't a value and can't
  ride in a frozen request DTO — it needs the request to expose a `stream()`
  pull-source and the host to de-chunk the wire, a different shape named in
  `handlers.md` / `srv.md` and marked not-built (same discipline as the worker
  host and SQL backend). The 411 is the honest in-code marker. The docs point at
  a framework as the moment the hand-rolled host has earned its replacement.

### Docs

- `handlers.md` rule 2 (host owns transport, handler owns content) + decision 6
  (buffered vs streamed) + mistakes ("the host parsing the body"); `srv.md` rule
  4 restated with the bytes split + framing guards; `python.md` and the example
  README rewritten; `rationale/coverage.md` row. skill-version 20 → 21.

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
