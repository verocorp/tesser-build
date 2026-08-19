# Changelog

All notable changes to tesser-build are documented here.
Versions follow the 4-digit `MAJOR.MINOR.PATCH.MICRO` format. (This file
versions the toolkit repo as a whole; `tessercheck-py/pyproject.toml`
carries the analyzer package's own version — separate streams.)

## [0.0.67.0] - 2026-08-19

Nothing raw from the wire reaches a port. A new TB082 clause says so, and two
contexts gained the domain object they were missing in order to satisfy it.

### Added
- **`a value crossing into a port has passed through a domain type`** (TB082).
  A service method may not put a field of its request into a port call. The
  value goes through a value object or an aggregate first, which is where
  validation lives. Measured before it was written: 21 sites across every tree
  but one, each an unvalidated lookup key handed to a repository.
- **`checks.TreeRoot` (tessercheck-py) and `rules.RepoRoot` (layout).** Both
  carry the invariants a *given* location has and a *reported* one does not —
  non-empty, no trailing separator. Existence stays in the reader: a value
  object that stats the disk stops being a value.

### Changed
- **`root` becomes `tree` throughout tessercheck-py.** The analyzer's own rules
  say "the checked tree" in four places and its code said `root`, which is the
  reader's word. The correction runs through the client DTO, both port requests,
  and the adapters. `ReadSourcesResponse.root: RootForm` keeps its name — that is
  the parsed `.tesser-root` declaration, a different concept.
- **`root` becomes `repo_root` throughout layout**, where the missing piece was
  the type rather than the word: `Repo` is an aggregate with no ID value object,
  which TB012 would have wanted.
- **`get_campaign` reads through the query port.** It validates the id with
  `values.CampaignID` — 16 lowercase hex — before the lookup, so a malformed id
  is a validation error rather than a not-found. `required_campaign` and
  `campaign_view` lose their last caller on this path.
- **`add_link` maps instead of delegating.** The two guard functions
  (`ensure_target_allowed`, `ensure_slug_available`) fold into
  `MapToShortLinkSpec`, which reads both measured outcomes and raises, so the
  spec cannot be built unless both checks pass. `MapToCampaignSpecFromRecord`
  replaces `required_campaign` on the write path; `MapToCheckTargetRequest` and
  `MapToSlugTakenRequest` take a domain value object and expose the primitive
  their port speaks, so no `str()` call remains in the service.

### Ignored, not fixed
Twelve sites carry a site-level ignore for the new clause — errorspy 3, llmport
5, ports 2, python-app 2. Every one is an unvalidated lookup key. `ports` is the
exemplar tree for the ports convention and should be fixed rather than
suppressed; it is the first thing to pick up next.

`create_campaign` and `get_campaign` carry **no ignore of any kind**. `add_link`
carries one, for body length, by ruling.

## [0.0.66.0] - 2026-08-18

A helper builds any construction data, not just a spec — and the constant that
made the old rule hard to widen is split into the two concepts it was serving.

### Changed
- **`DTO_BLOCKS` splits into `DECLARATION_BLOCKS` and `DATA_BLOCKS`.** Three call
  sites asked it two different questions: *is this module nothing but
  declarations?* (which wants `client`, `port`, and `protocol_port` in the set)
  and *is this call building a data carrier?* (which must not, because a Protocol
  cannot be constructed). The tell was already in the code — both construction
  sites wrote `built in DTO_BLOCKS or built == "spec"`, patching a set that was
  missing a member its callers needed. `DATA_BLOCKS` carries the spec family, and
  the `or` is gone from both.
- **`a helper builds a spec` becomes `a helper builds a spec or a DTO`** (TB073),
  checked against `DATA_BLOCKS`. A helper may return a request, a response, a
  port DTO, a protocol record, or any spec. It still may not return a Protocol —
  that is what `@ts.fake` is for — and it may not return a domain object, by
  ruling: a test that wants an aggregate builds it from a spec so the
  construction path runs.
- **The mapper's constructs-what-it-maps-to clause narrows with it.** Under the
  old set it would have flagged a mapper constructing a `Client` or a port. No
  mapper does, so nothing was wrong, but the rule said something it did not mean.

### Removed
- **Two `# tessercheck:ignore TB073` comments in `layout/`.** `_empty_response`
  and `_response` build a `ReadRepoResponse` and were suppressing the
  spec-only rule. The widening made both legal, TB090 flagged the now-empty
  ignores, and they are deleted — the ignore set shrinking on its own is the
  gate working.
- **Three inlined `FindCampaignViewResponse` literals** in
  `campaign/application/test_service.py`, back behind
  `_found_campaign_view()` and `_missing_campaign_view()` where they belong.

## [0.0.65.0] - 2026-08-18

`create_campaign` reads its response back through a query port instead of
deriving it from the aggregate it just built. The write side and the read side
are now separate ports, satisfied by one repository.

### Added
- **`campaign_queries.CampaignQueries` — the read port.** `find_view` answers
  with view-shaped rows (`CampaignViewRow`, `LinkViewRow`) and a measured
  `CampaignViewLookup` outcome, the same shape rules every other port follows.
  `InMemoryCampaignRepository` satisfies it alongside `CampaignRepository`: one
  repository, two ports.

### Changed
- **`MapToCampaignView` maps a query answer, not an aggregate.** It takes the
  request and the response, reads the outcome with `match` + `assert_never`, and
  raises `not_found` on `MISSING`. Both sides are flat records now, so the mapper
  contains no `str()` call and never touches the domain — the `match` that used
  to live in `views.required_campaign`, a module function, has a home.
- **`CampaignService` takes a fourth dependency**, the query port. The component
  passes the repository for both.

### Fixed
- **Two false positives in the originates-nothing clause.** A literal used as a
  subscript index (`campaigns[0]`) and a literal inside a `raise` (an error code
  and its message) are not values a mapper exposes. Both are exempt now, pinned
  by `test_an_index_and_an_error_message_are_not_originated_data`. The clause got
  sharper from contact rather than collecting ignores.

## [0.0.64.0] - 2026-08-18

A campaign's links become a domain object. `ShortLinks` owns the rules the
aggregate was hand-rolling around a bare `list`, and `CampaignSpec.links` becomes
a child spec like `budget` already was.

### Added
- **`ShortLinks` and `ShortLinksSpec` (`campaign/domain/short_links.py`).** The
  collection holds what a collection knows: uniqueness by slug on construction
  and on add, index-aware error wrapping (`invalid short link at index 1`),
  find-and-deactivate by slug, and the defensive copy on read. Seven tests cover
  it directly, including that its accessor hands back copies.

### Changed
- **`Campaign` drops 24 lines and gains 5.** The build loop, the clone-on-read
  comprehension, the find-by-slug scan, and the duplicate check are all gone from
  the aggregate; three methods became one-line delegations. `Campaign` is now
  three value objects and three delegations.
- **`CampaignSpec.links` is a `ShortLinksSpec`, not a `tuple[ShortLinkSpec, ...]`.**
  It now matches `budget`, which was already a child spec, and satisfies TB080's
  "a spec field is a primitive, a value object, or a child spec" by naming rather
  than by structure. The aggregate stops re-wrapping a tuple it was handed one
  line after receiving it.
- **`MapToCampaignSpec` takes and exposes the child spec**, so the mapper's
  whole-objects rule is satisfied by a named kind instead of a bare tuple. The
  empty stays visible at the call site as `ShortLinksSpec(links=())`.

### Removed
- **`_admit`.** The duplicate-slug invariant lived in a module function because
  the collection had a rule and nowhere to put it. It is a private method on
  `ShortLinks` now, and one of the repo's module functions retires with it.
- **`campaign.py`'s `tesser.errors` import.** All four of `DomainError`,
  `conflict`, `invalid`, and `not_found` went unused — every error the aggregate
  raised was collection logic. The aggregate raises nothing of its own; its value
  objects do.

## [0.0.63.0] - 2026-08-18

The mapper stops being a convention and becomes a rule. Five TB080 clauses give
`ts.Mapper` a shape the analyzer can hold, and one TB082 clause locks the naming
norm the mapper wave established. `examples/python-app`'s five mappers pass every
one of them unchanged — the shape was dogfooded before it was enforced.

### Added
- **`a mapper is named for what it maps to`.** A mapper class starts with
  `MapTo`. Its parameters already say what it maps from, so the name carries only
  the target — `MapToCampaignSpec`, not `MapCreateCampaignRequestAndIssuedIdentityToCampaignSpec`.
- **`a mapper takes whole objects, never a field already pulled off one`.** No
  `__init__` parameter is a primitive. A mapper is handed the request, the
  aggregate, the issued response — not `budget_amount: str`.
- **`a mapper originates nothing — every value it exposes comes from what it was
  given`.** No literal in the class body (`None` and the `...` of a tuple
  annotation excepted). This is the rule that sent `links=()` back to the call
  site: a mapper that invents a value hides it.
- **`a mapper holds only __init__ and the accessors it exposes`.** Every other
  member is a `@property`. A mapper with a method is doing work the caller cannot
  see.
- **`a nested mapper accessor ends in _mapper, so the reader knows to keep
  dotting`.** A property whose return type is another mapper says so in its name
  — `budget_mapper.amount`, never `budget.amount`, which would read as a value.
- **`a mapper exposes the parts and the caller assembles them, so every field is
  named where it is read`.** A mapper never constructs the DTO or spec it maps
  to. Two sites carry an ignore: `MapToSaveCampaignRequest` and
  `MapToCampaignView` build their collection *elements* (`LinkRecord`,
  `LinkView`), which the clause does not yet distinguish from the top-level
  construction it is aimed at.
- **`a service method names what it computes, and reads an accessor where it is
  used`** (TB082). An assignment whose right-hand side is a bare name or
  attribute chain with no call is a finding. Zero sites in the repo today; the
  clause keeps it that way.
- **`a service method names what it computes in a local, and passes a name, a
  reader, or a declared kind`** (TB082). A call in an argument position is a
  finding — a construction of a declared kind is not, which is what lets
  `self._repo.save(SaveCampaignRequest(...))` stand.
- **`a declared kind is assembled from the accessors of one mapper`** (TB082).
  When a service constructs a DTO or spec, every attribute-access argument
  shares one base. `create_campaign` satisfies it already: the spec reads from
  `campaign_spec_mapper`, the record from `save_request_mapper`, the view from
  `campaign_view_mapper`.

### Deferred, and visible

The two argument-position clauses land with **27 site-level ignores** rather than
a refactor: 10 in python-app, 9 in llmport, 4 in errorspy, and one each in ports,
layout, and tessercheck-py, plus the 2 mapper-element sites above. Every one is a
service method that computes inside an argument — the shape `create_campaign` was
converted away from, and the shape every unconverted `views.py` caller still has.
`create_campaign` itself needs no ignore for any of the three: it is the worked
example the clauses were written from. Burning an ignore is the refactor; TB090
keeps the set honest in the meantime.

## [0.0.62.0] - 2026-08-17

TB082's body-length rule stops counting formatting. A service method body is now
at most **10 statements**, not 10 source lines.

### Changed
- **`_body_violations` counts statements.** `sum(1 for node in ast.walk(fn) if
  isinstance(node, ast.stmt)) - 1` — every statement including nested block
  bodies, so the count cannot be gamed by wrapping work in a `for` or an `if`.
  The clause text is the rule, so `RULES.md` regenerates from it. Statement count
  is always <= line count (a statement occupies at least one line and this
  codebase never uses `;`), so the change can only turn a finding into a pass —
  no green tree could go red.
- **`create_campaign` drops its `# tessercheck:ignore TB082`.** Seven statements
  over 34 source lines: it failed the line rule on its argument-per-line
  formatting and passes the statement rule on its actual shape. The ignore landed
  in v0.0.61.0 purely to hold the gate open until this change; nothing else in
  the repo carried one for TB082.
- **A fixture pins the difference.** `test_a_body_spread_over_many_lines_is_counted_by_its_statements`
  builds a two-statement method spread over 20+ lines and asserts no finding —
  the case the old counter got wrong. The existing 12-statement fixture still
  fires, so both directions are covered.

## [0.0.61.0] - 2026-08-17

`create_campaign` stops calling module functions. The translation the service
used to delegate to `views.py` now lives in **mappers** — classes that take
whole objects and expose the parts of a DTO, which the service then assembles
in the open. One method of the worked example is converted; the rules that
would force the same shape elsewhere are not written yet.

### Added
- **`ts.Mapper` in `tesser.application`.** A plain marker base, the same shape
  as `ts.ApplicationService` — no behavior, no `__slots__`, nothing for a
  subclass to satisfy. The convention it carries: a mapper takes whole objects,
  derives nothing of its own, and exposes one accessor per field of its target.
- **`mapper` joins the kind table.** `("tesser.application", "Mapper")` maps to
  the `mapper` block, `KIND_NAME` reads "a mapper", and `KIND_ROLE` puts its
  home in `application`, so a mapper in any other role is a TB052 finding —
  pinned by `test_a_mapper_lives_only_in_the_application_role`.
- **`CampaignIdentity` — a port for minting a campaign's identity.**
  `secrets.token_hex(8)` left `campaign.application.service` for a gateway
  (`SecretsCampaignIdentity`), injected into `CampaignService` and constructed
  by the campaign component. The service's `# tessercheck:ignore TB062` for
  `secrets` is deleted with it: the pure-core allowlist candidate resolved by
  injection, which is what its TODOS entry predicted.

### Changed
- **`create_campaign` reads as five statements.** A mapper per boundary
  crossing — `MapToCampaignSpec` (with a nested `MapToMoneySpec`),
  `MapToSaveCampaignRequest` (with a nested `MapToMoneyRecord`), and
  `MapToCampaignView` — then the service constructs `CampaignSpec`,
  `SaveCampaignRequest`, and `CampaignView` itself, naming every field. No
  `str()` call and no string literal remains in the method.
- **`LinkView` reports a status string, not an `active` bool.** The bool forced
  every translator to compare against the literal `"active"`; the string is a
  pass-through of the domain's `values.LinkStatus`. The HTTP link payload is
  now `{"slug": ..., "target_url": ..., "status": "active"}`.

### Removed
- **`campaign_repository.LinkStatus`.** The port enum re-encoded a string as
  itself: `LinkRecord.status` is a plain `str`, and the branch that mapped
  domain status to enum collapsed to `str(link.status)`. Lookup-outcome enums
  (`CampaignLookup`, `SlugAvailability`) are untouched — those encode an answer
  shape, which this never did.

## [0.0.60.0] - 2026-08-17

The directory names catch up with the kinds. `wiring/` becomes `component/` and
`bootstrap/` becomes `app/`, in every tree and in the rules that read them.

### Changed
- **`<context>/wiring/` → `<context>/component/`,** and `wire.py` →
  `component.py`. The role held a `build()` that wired things together; it now
  holds a component that owns infrastructure. `ROLES`, `KIND_ROLE`,
  `ROLE_TESSER_PACKAGE`, `NORM_IMPORTS`, `SAME_CONTEXT_IMPORTS`,
  `TEST_TIER_HOME`, and the import matrix follow.
- **`bootstrap/` → `app/`,** with `APP_PACKAGES` and the placement `shell-app`.
  Every clause that named the old directory is reworded: "an app module's tesser
  imports are…", "an app function declares itself with @ts.load", "only an app,
  an app loader, an app config, an app config spec, and a config repository live
  in an app module".
- **`skills/tesser-build/wiring.md` → `component.md`, `bootstrap.md` →
  `app.md`,** with every cross-reference and the roadmap registry rows.

### Added
- **`app` joins the reserved tree-root names.** A bounded context can no longer
  be called `app`, the way one already cannot be called `srv`, `tests`,
  `protocol`, or `kernel`. This surfaced through the analyzer's own fixtures,
  whose context was named `app` and began classifying as the shell.

### Fixed
- **A generated clause read "a app constant is Final".** The template took an
  article it could not vary, so it is now article-free: "app constants are
  Final", "kernel constants are Final". Same for the tier label the placement
  message interpolates, which now reads "a test placed in an app".

## [0.0.59.0] - 2026-08-17

### Fixed
- **`MoneyAmount` rejects a non-finite amount.** In the tree the skill points at
  as the verified impl, `MoneyAmount("Infinity")` was accepted — `Decimal("Infinity") < 0`
  is False — and `MoneyAmount("NaN")` escaped as `decimal.InvalidOperation`
  rather than a `DomainError`. Both are now `invalid_budget_amount`.

  The leak was not where the old note assumed. `Decimal("NaN")` parses happily;
  it is the `parsed < 0` comparison on the next line that signals, and that line
  sits outside the try. A finiteness check before the comparison fixes both
  symptoms at once, because the value that cannot be compared is exactly the
  value that is not finite.

## [0.0.58.0] - 2026-08-17

`@ts.function` becomes `@ts.do_not_use_function`. Declaring a module function
should look like what it is.

### Changed
- **The decorator every module function carries is renamed at all five
  placements** — `tesser.domain`, `tesser.application`, `tesser.adapters`,
  `tesser.context`, `tesser.srv`. The kind it declares is unchanged; only the
  name consumers write moves. 132 call sites across every tree, and every
  clause that names it: "a kernel function declares itself with
  @ts.do_not_use_function", and the same for srv, protocol, bootstrap's peer,
  and context modules.
- `ts.load` keeps its name. It marks the one no-argument function an app is
  meant to have, which is the opposite of a thing to discourage.

The rename is the point rather than a side effect: a module function is legal
where the rules still allow one, and reading `@ts.do_not_use_function` at the
top of it is meant to be uncomfortable.

## [0.0.57.0] - 2026-08-17

`helper` and `fake` move to where the analyzer already thought they lived, and
the module nobody should import says so in Python.

### Changed
- **`tesser.testing` owns `helper` and `fake`.** The kind table has keyed them
  to `tesser.testing` since the decorators existed; only the runtime lagged,
  re-exporting them from `tesser.declared`. Each now has its own module and its
  own sibling test.
- **`tesser.declared` becomes `tesser.do_not_use_declared`,** holding only
  `function` and `load` — the two decorators six shells re-export. The name is
  the instruction: a reader who reaches for it has already been told not to,
  and an underscore only says that to readers who know the convention.

### Added
- **A `do_not_use_` module is not a consumer namespace.** The namespace
  totality rule skips that prefix rather than demanding the module be something
  a consumer imports. It is not a loophole: `tesser.do_not_use_declared` is in
  no placement's allowed imports, so a tree reaching for it is a finding on the
  import rules regardless.

## [0.0.56.0] - 2026-08-16

The rules catch up with the shells. A component must release, a config must
construct from a spec, and the lifecycle package retires.

### Added
- **TB081: a component releases what it constructed.** `ts.Component` was a
  marker, so a component with no `close()` was legal — the one thing standing
  between the base and what it was introduced to mean.
- **TB080: a config constructs from exactly one `ts.Spec`,** at both levels.
  Configs were spec-shaped by discipline; now they are spec-shaped by rule, the
  same clause a domain constructor already answers to.

### Removed
- **`tesser.lifecycle`.** Nothing travels any more: a component holds what it
  made in its own type, the app holds its components, and the runner takes a
  callable. With no return value to type, the shared release contract had no
  remaining job. The kind row, its TB052 production-base clause, and its TB072
  fake grant go with it.
- `srv/test_run.py`'s `FakeAppSpy` — the runner takes a callable, so the
  recorder is a list, and it doubles no contract to be a fake of.

### Changed
- `wiring.md` teaches the component contract rather than
  `build(cfg, deps) → (Client, Closeable)`; `python.md`'s impl-selection example
  is a private method. skill-version 44.

## [0.0.55.0] - 2026-08-16

The design gets its own shells. `tesser.app` and `tesser.component` name the two
levels the app/component shape needs, and `ts.Wiring` retires.

### Added
- **`tesser.app`** — `App`, `Loader`, `Config`, `Spec`, `ConfigRepository`, and
  the `@ts.load` decorator for the single no-arg module function a design may
  hold. `ConfigRepository` is generic in the config it yields, or a loader would
  hand every tree the shell's own `Config` back.
- **`tesser.component`** — `Component`, `Config`, `Spec`.
- Both packages export `Spec` and `Config`. The placement's own `ts` alias picks
  which, and the kind table keys on `(package, name)`, so the two levels carry
  different rules without inventing `AppConfig` and `ComponentConfig`.

### Removed
- **`ts.Wiring`.** It was the kind for anything in the wiring role — `Config`
  subclassed it too — which is why it could never require `close()`. Splitting
  it frees `Component` to mean "constructs infrastructure and releases it".

### Changed
- **A bootstrap module binds `tesser.app`, not `tesser.context`.** That import
  existed only to decorate module functions; the design has one, declared
  `@ts.load`. **A bootstrap module holds classes**, and TB052 rules which: only
  app kinds. The three ignores `examples/python-app` carried were asking for
  exactly this, and are gone.
- **A fake may double a config repository**, and a test module may name
  `tesser.app` so it can implement the contract.
- **Every config is spec-shaped** — one `ts.Spec` parameter, the same door
  TB080 already requires of a domain constructor.
- **The env edge is `bootstrap/repository.py`.** The reader encapsulates the
  environment rather than taking it, so `scripts/verify` supplies one for
  `python-app`'s pytest — the job a deploy does. Repositories are integration
  tested; nothing injects a mapping.
- Analyzer internals: the base resolver unwraps a subscripted base so
  `ts.ConfigRepository[Config]` classifies, and the `@ts.function` check moves
  out of the shared statement walk — left there, every placement derived a
  clause it could never fire.

## [0.0.54.0] - 2026-08-16

Apps and components. The composition root stops threading closeables through
return types: a component constructs its own infrastructure from its config
slice and closes exactly that, and the app builds the components and closes
them. Nothing runs — hosts run.

### Changed
- **`wire.build(cfg, deps) -> (Client, Closeable)` becomes a component class**
  with a validating `__init__` and a `close()`. `NoResources` and both tuple
  returns retire; a component that holds no infrastructure has an empty
  `close()`.
- **`bootstrap.py` + `from_env` become `config`, `repository`, `loader`, and
  `app`.** Reaching an app is `AppLoader(EnvConfigRepository(os.environ)).load()`,
  behind one module function, `load_app()`. The app loader coordinates a config
  repository and construction; the app it returns is what gets closed.
- **Every default is gone.** An absent environment variable is refused by name
  (`missing_env`) rather than silently backfilled — the `http` slice default,
  the `or ""` coordinate fallbacks, and the `8080` port fallback all go.
- **The env edge moves from the host to the loader.** `srv` reads no
  environment; the ruff ban moves with the edge rather than widening, and a new
  teeth test pins that only `bootstrap/loader.py` is exempt.
- **The runner takes a callable, not an app.** `run_until_signal(host, close)`
  needs to know nothing about apps.

### Removed
- **`CleanupStack`,** and with it reverse-order teardown and close-error
  aggregation. Under strict ownership no component's `close()` depends on
  another still being open, so ordering is free; `spanner.Client.Close()`
  returns nothing to aggregate. Partial-construction unwind survives, re-derived
  from "a single validating constructor never leaves an invalid object behind."
- **`tesser.lifecycle.Closeable` from python-app.** Its only job was letting a
  closeable travel — out of `build()`, into a stack, through a runner signature.
  Nothing travels now. It remains in the shells and the other trees.

## [0.0.53.0] - 2026-08-16

The toolkit stops shipping the one construction its own gate proves is
invisible. `ts.ValueObject` supersedes the frozen-dataclass idiom (Chris,
2026-08-16), and the distribution carries no dataclass.

### Changed
- **`tesser.errors` drops its last `@dataclass(frozen=True)`.** `FieldProblem`
  becomes a hand-rolled frozen carrier — local and deletable, rather than
  entangled with `tesser.srv.Record` or minting a new module for a type that is
  about to be redesigned. The mutmut ecosystem gate exists to prove the frozen
  dataclass is invisible to mutation testing; the shipped library was the last
  place still using it.
- **It is now `NeedsDesignFieldProblem`.** The name carries the smell rather
  than hiding it: the `domain → collect → application → edge` pass, the
  `collect()` aggregation itself, and a domain-facing type named for its RFC
  9457 destination are all unresolved design.
- **The record catches up.** README claimed the taught convention was still the
  frozen dataclass, contradicting the skill it points at.
  `docs/design-python-analyzer.md` reasons throughout about a dataclass
  substrate — VO identification by decorator, `dataclasses.replace()` as a
  construction door, accessors dropped because "dataclass fields are public by
  idiom" — and is marked superseded on that question, kept as the record of how
  the Python gate was planned. Both of the adoption TODO's open follow-ups were
  already satisfied in code: the classifier maps
  `("tesser.domain", "ValueObject")` to `valueobject`, so `TB010`–`TB014` and
  the serialization norm already see the shape.

### Removed
- The ValueObject-adoption TODO closes. What it carried splits into two real
  items: the repo's remaining dataclasses (each a design question, not a swap —
  the bootstrap configs need a legal home for a class, not a different base),
  and python-app's `Money`, whose bugs the old note filed under a path that no
  longer exists. Verified still live: `Infinity` is accepted, and `NaN` escapes
  as `decimal.InvalidOperation` instead of a `DomainError`.

## [0.0.52.0] - 2026-08-16

The tree that defines the conventions is now checked by them. `tesser-py`
declares `export tesser`, its verify arm runs tessercheck, and the run is
clean — the last unchecked tree in the repo closes.

### Added
- **The shells rows.** Kernel content rules are keyed on the `ts.*` bases,
  and the bases cannot subclass themselves, so one exported kernel routes
  differently: when a tree's export is `tesser`, its modules answer to
  namespace totality (modules *and* subpackages are exactly the namespaces
  consumers import), shell-stdlib purity (the distribution's measured
  external surface — a meta-test fails when either allowlist grants a name
  the distribution does not earn), and a `__init__` that only re-exports
  from the distribution. Its tests invert exactly two rules — any
  `tesser.*` import, and free module-level classes, because probe
  subclasses of the shells are the tests' method — and keep function
  totality, the comments norm, the mock ban, and placement.
- **A shape gate on the claim.** A tree exporting `tesser` holds exactly
  `tesser` and `tests` at its top level. Without it, any app could park a
  `tesser/` package beside its contexts, declare the export, and buy a
  content-rule-free region its governed domain code calls as `ts.*`.

### Changed
- **`tesser-py` conforms to TB074 rather than being excused from it**
  (maintainer ruling 2026-08-16: those shell classes will likely carry
  behavior later, and exemptions are reserved for true exemptions). All 25
  implementation modules gained sibling tests — the six behavior-carrying
  ones moved beside their code, the marker declarations gained tests that
  assert their actual contract (structural satisfaction for the protocol
  bases, inheritance for the derived records, no behavior of their own for
  the markers). The wheel-completeness check compares real members, so a
  test file can never stand in for a missing subpackage.

## [0.0.51.0] - 2026-08-16

The flagged kind-table entry resolves by ruling: **a port is for the
application; Closeable is not a port — it is the lifecycle contract, its
own kind.**

### Changed
- **`tesser.lifecycle.Closeable` drops its `ts.Port` base** — it is a plain
  structural Protocol now. The analyzer's kind table carries `"closeable"`
  as a distinct block instead of aliasing it to `"port"`, retiring the #86
  entry and the global widening it carried (any Closeable-extending class
  used to classify as a port).
- **TB072's clause becomes "a fake implements the contract it doubles"** —
  a fake may double a port, a client, a protocol port, or the lifecycle
  contract.
- **A production class declaring `Closeable` as a base is a finding**
  (TB052): production satisfies the contract structurally; only a test fake
  declares it.
- Two pins hold the ruling against drift: the runtime suite asserts `Port`
  is not in `Closeable.__mro__`, and the kind-table meta test asserts
  `closeable` has no `KIND_ROLE` home.

## [0.0.50.0] - 2026-08-16

The rule the whole arc served: **TB074 — every implementation module
carries exactly one sibling test file**, in both directions.

### Added
- **`TB074`**: an implementation module (role, kernel, srv, bootstrap,
  protocol places) with no sibling `test_<module>.py` is a finding, and a
  sibling test file naming no module beside it is a finding. Exempt by
  construction: `application/ports` modules, declaration-only modules
  (every class a declared DTO/Protocol block, methods stopping at
  `__init__` — `client.py` is the canonical case), `__init__.py`,
  `conftest`, and `tests/` packages (the wired tier pairs with the app, not
  a module). **No temporary exemptions**: the one module that genuinely
  cannot be tested — llmport's `srv/voice/agent.py`, bound to an
  uninstallable vendor SDK — carries a site-level ignore where the finding
  lands, as visible debt. Run over the repo, the rule fired on exactly that
  one module: the three pairing waves left nothing owed.

### Changed
- The checker's own spec fixtures gain their sibling pairs (the rule
  applies to the trees the tests build, too). TB074 joins the norm-testing
  roadmap row; `testing.md` and `CLAUDE.md` teach it. skill-version 41.

## [0.0.49.0] - 2026-08-16

Third and largest pairing wave: python-app reaches
one-implementation-file-one-test-file — 28 new sibling test files, 356 new
tests (137→509).

### Changed
- **Every implementation module in python-app has exactly one sibling test
  file.** campaign folds `test_roundtrip_law.py` into the leaf files whose
  laws it held; linkpolicy, reports, and the app shell gain their isolated
  tiers. `srv/http/main.py` is tested as a subprocess — env access and a
  real blocking server put it beyond in-process reach, and the subprocess
  is the honest door. Zero suppressions added anywhere; TB073 refused
  helpers wherever no `ts.Spec` existed to return.

## [0.0.48.0] - 2026-08-16

Second pairing wave: errorspy, layout, and tessercheck-py reach
one-implementation-file-one-test-file.

### Changed
- **errorspy** gains five sibling files (76 tests, 31→107): the RFC 9457
  status ladder end to end, the storage outage translated to `InfraError`
  with its cause kept, aggregated validation proven to touch no port.
- **layout** gains four sibling files and splits `srv/cli/test_check.py`,
  which had been doubling as `trees.py`'s test file (95 tests tree-wide).
- **tessercheck-py** gains ten sibling files (319 tests tree-wide) plus two
  structural moves: the flat `adapters/repositories.py` splits into the
  kind package (`repositories/source_reader.py` + `rulebook_sources.py`,
  classes byte-identical), and the three pure rulebook-derivation tests
  move from `tests/test_rules.py` to `domain/test_rulebook.py` beside their
  subject. RULES.md regenerates with zero diff.

## [0.0.47.0] - 2026-08-16

First pairing wave: serdepy, ports, and llmport reach
one-implementation-file-one-test-file ahead of the rule that will demand it.

### Changed
- **Every implementation module in the three trees has exactly one sibling
  test file named for it.** serdepy's four subjectless domain test files
  merge into `test_parcel.py`; llmport's `test_domain`/`test_application`
  rename to `test_scheduling`/`test_service`; ports gains six new sibling
  files, llmport seven. 97 new or moved tests (serdepy 46→55, ports 5→49
  collected, llmport 50→114), all behavioral, at the tier their placement
  carries.
- **The last two flat `adapters/` directories move to kind packages.**
  TB070 gives a sibling test no tier in an unkinded `adapters/`, so
  serdepy's `wire.py` and llmport's three adapters relocate into
  `gateways/`/`repositories/`/`handlers/` — the same shape the layout
  ruling already prescribed and every other tree already had.
- llmport's pytest `testpaths` widens to `protocol`/`scheduling`/`srv`
  (two new test files were outside the old collection path), and its verify
  mypy line gains `srv/voice/test_router.py`.

Named for the rule PR: llmport's `srv/voice/agent.py` (imports livekit,
outside the mypy crawl — no test can import it) needs an exemption ruling.

## [0.0.46.0] - 2026-08-16

### Changed
- **The nine sibling test files merge into one `domain/test_checks.py`
  beside `checks.py`** (197 tests). checks.py stays one file, so its tests
  become one file — the shape the coming
  one-implementation-file-one-test-file rule demands, and the merge chosen
  over splitting checks.py when the split turned out to mean seven duplicate
  `_spec` helpers. The merged file carries exactly one helper: the shared
  `_spec`, widened with the kernel file's knobs (`declared`, `exports`,
  `imports`, `stdlib`); the 31 kernel tests inline their kernel/money
  fixtures at each call site — duplication in tests is fine, a second helper
  is not.

## [0.0.45.0] - 2026-08-15

The last root module joins the app, and the allowance that excused it
retires — fired by the every-classification-earned test the moment nothing
earned it, which is that test doing exactly what it was built for.

### Changed
- **`rules.py` (the RULES.md generator) becomes part of the tessercheck
  app**, at every tier the anatomy prescribes: the pure derivation
  (Violation call sites → `RuleRow` value objects → rendered markdown) is
  `tessercheck/domain/rulebook.py`; reading `checks.py`, the test modules,
  and `.importlinter` is an application port with a filesystem repository;
  the use case is a service method behind the client; the CLI is a handler;
  `srv/cli/rules.py` is the host that owns `--check` and the file write.
  The drift gate calls `python3 -m srv.cli.rules --check`.
- `roadmap/generate.py` imports the rulebook as a package module for its
  check-code column (the old file-path load can't resolve a module that
  imports its own context).

### Removed
- **The root-module allowance.** With zero root modules in any tree, a
  top-level module is now purely a `TB040` finding ("every module belongs
  to a context, srv, bootstrap, tests, or the protocol package"), the
  `root` place moves to the finding list in the earned-classification test,
  and `TB065`'s root-module leaf rule — a rule only excused modules could
  ever reach — is deleted. This is a rule change: review it as one.

## [0.0.44.0] - 2026-08-15

Only bounded contexts have domains, and a context's domain is never
exported. What a domain couples to by direct import — no interface to
inject — now has a name and rules: **kernels**
(`docs/design-kernels.md`).

### Added
- **The kernel tier.** Two scopes, two promises: `kernel/` at the tree
  root (fixed name, discovered, shared across one app's bounded contexts,
  invisible outside) and the **exported kernel** (the package's public
  import name, declared `export <dir>` in `.tesser-root` — at most one per
  tree, because the export is the package's import name and a package has
  one name). Kernel content is domain content: every class declares its
  `ts.*` block, only domain kinds are legal, and the full identity
  taxonomy and serialization norm apply unchanged. A kernel module imports
  only its kernel, `tesser.domain` (as `ts`, plus the domain's norm
  grants), declared external kernels, and the domain pure stdlib — and
  nothing ever imports leftward into a kernel's consumers.
- **`import <package>` — the consumer-side declaration, validated as the
  purity waiver it is.** It never names this tree (not `kernel`, the app
  shell, or any walked package), never names the stdlib (`import
  subprocess` cannot be declared away), and must legalize at least one
  edge — an unused declaration is itself a finding, the same rule TB090
  applies to ignores. Kernel-target imports are trusted per *walked
  module*, so a `skip` line cannot smuggle unwalked code into the
  allowlist, and an export can never dissolve a bounded context — a
  context-shaped export is a finding reported before anything else.
- **The worked example**: `Slug` was duplicated byte-for-byte in
  python-app's campaign and reports contexts — the exact drift kernels
  exist to end. It now lives once in `kernel/slug.py`, consumed by both,
  with a companion test and an import-linter contract asserting the
  kernel imports no context. Money stays in `campaign/domain` (one
  consumer — the second consumer earns the move), and the three
  `TargetURL`s stay put (they validate differently; different rules are
  different types).
- **`kernels.md` joins the skill** (routing, placement, rules,
  skill-version 40), with the shells routing for `export tesser`
  designed and explicitly deferred to the next step.

## [0.0.43.1] - 2026-08-15

### Changed
- **errorspy's fake storage becomes a skipped vendored package.**
  `storage.py` stood in for an external SDK — the gateway imports it exactly
  as it would import a real driver — but sat as a root module with an
  ignore-file excuse. It is now the `storage/` package with a `skip storage`
  line in the tree's `.tesser-root`: present so the example runs with no
  infra, declared outside the checked tree the way site-packages would be.
  mypy still checks it; tessercheck now correctly does not. Uses only
  existing per-tree vocabulary — no analyzer change. One root module remains
  in the repo (`tessercheck-py/rules.py`, next PR) before the allowance
  itself can retire.

## [0.0.43.0] - 2026-08-15

The third and widest norm module goes live, and the root-module era of the
trees ends: no tree carries an `errors.py`, `lifecycle.py`, or
`serialization.py` copy anymore, and every site-level `TB062` ignore those
copies forced is gone.

### Added
- **`tesser.errors` grant**: domain, application, adapters, wiring,
  bootstrap, srv, and test modules may from-import it. A client module keeps
  importing only its own tesser package — DTOs carry no policy. The role
  call site becomes plain branches, one literal inventory clause per role,
  so the rules registry stays decidable.

### Removed
- **Both root `errors.py` copies** (python-app, errorspy): 38 modules move
  their imports to `tesser.errors`; the remaining site-level `TB062` ignores
  drop; errorspy's `DomainKind` renames to `Kind` — the name the skill docs
  teach. errorspy's `tests/test_errors.py` retires with its subject; the two
  behaviors tesser-py's suite lacked (two codes share one kind, chaining
  preserves cause and field) move there.

### Changed
- The tesser-py wheel gate now verifies flat modules ship too, not only
  subpackages (`errors.py`, `serialization.py`, `declared.py` were invisible
  to it).
- `python.md` excerpts import from `tesser.errors`; the transcription note
  about `TB062` markers shrinks to history; `handlers.md` names
  `tesser.errors.status_for` / `exit_code_for`. skill-version 40.
- `TODOS.md` gains the norm-module followup Chris flagged: the `Closeable`
  kind-table entry (#86) and the process gap it exposed — a rule-shaping
  analyzer change riding inside a migration PR — are to be revisited after
  the one-test-file workstream.

## [0.0.42.0] - 2026-08-15

The second norm module goes live the same way the first did: the grant and
the trees that earn it, one change.

### Added
- **`tesser.lifecycle` grant**: wiring, bootstrap, srv, and test modules may
  from-import it — the placements that build and tear down the object graph.
  `Closeable` joins the analyzer's kind table as a port, so a `@ts.fake`
  doubling it still satisfies the fake-implements-its-port rule after the
  move out of the trees.

### Removed
- **The two identical root `lifecycle.py` copies** (python-app,
  tessercheck-py): nine import sites move to `tesser.lifecycle`; the mypy
  target lists shrink to match.

### Changed
- `tesser.lifecycle` becomes a package (`lifecycle/closeable.py` behind a
  re-exporting `__init__`) like every other tesser area, which puts it under
  the wheel-completeness gate — a flat module was invisible to the
  subpackage check.
- `bootstrap.md` points its `Closeable` reference at the runtime.
  skill-version 39.

## [0.0.41.0] - 2026-08-15

The first norm module goes live end to end: the analyzer learns the grant
and the trees exercise it in the same change, so the allowance is earned the
moment it exists — no checker-only allowance, no migration waiting on a rule.

### Added
- **`NORM_IMPORTS`**: the tesser norm modules a placement may from-import
  beside its one ts-aliased package. First grant: `tesser.serialization` for
  domain and test modules — the two placements the trees' canonical exits
  exercise. A norm module is from-imported by name, never whole (the ts
  alias belongs to the placement's own package), and a norm import does not
  satisfy the package-presence rule. All other placements still reject it;
  protocol and ports are untouched.

### Removed
- **The three root `serialization.py` copies** (python-app, serdepy,
  errorspy — byte-identical): nine import sites move to
  `tesser.serialization` and seven site-level `TB062` ignores go with them.
  The mypy target lists in `scripts/verify` shrink to match.

### Changed
- `serialization.md` rule 3 names `tesser.serialization` as the one
  implementation site; `python.md`'s transcription note shrinks to the
  `errors` imports that still await their own move. skill-version 38.

## [0.0.40.0] - 2026-08-15

The generic halves of the trees' root modules move into the runtime. Four
trees carry near-identical copies of `errors.py`, `serialization.py`, and
`lifecycle.py` at their roots, each excused by a `tessercheck:ignore-file
TB040` and imported through 23 site-level TB062 ignores — the copies exist
only because there was no shared home. Now there is one. This is the first
slice: pure addition, no tree migrates yet. The analyzer allowance for the
new imports and the tree migrations ship separately.

### Added
- **`tesser.errors`** — the closed `Kind` set, `DomainError` (kind-as-field,
  optional `field`, collected `problems`), `InfraError`, the
  `invalid`/`not_found`/`conflict` constructors, `wrap`, `collect`, and the
  two total edge mappers `status_for` / `exit_code_for`. The superset of the
  copies: errorspy's fuller module under the names the skill docs already
  teach (`Kind`, not `DomainKind`).
- **`tesser.serialization`** — the `canonical_*` exit helpers, byte-identical
  across the three trees that carried them.
- **`tesser.lifecycle`** — the `Closeable` port.
- Tests for all three beside the existing tesser-py suite (16 tests: the
  taxonomy, the mappers' totality over `Kind`, `collect`'s
  gather-and-reraise contract, the canonical forms, the naive-datetime
  refusal, structural `Closeable`).

### Changed
- `requires-python` moves to `>=3.11`: `typing.assert_never` (used by the
  exhaustive kind mappers) landed in 3.11.

## [0.0.39.0] - 2026-08-15

Two trees stop being called what they are not. `examples/spike-shells` is
retired: its teaching role is fully covered by `examples/python-app` (the
bounded-context anatomy exemplar) and `examples/ports` (the application-ports
exemplar), and keeping a third exemplar meant keeping a third copy of every
convention current. `examples/spike-llmport` is no spike — it is a gated,
conformant tree — so it is now `examples/llmport`.

### Removed
- **`examples/spike-shells/` and its whole gate chain**: the tree, its
  `manifest.json` row, its `scripts/verify` arm, and its CI job. Live prose
  that pointed at it now points at the current exemplars
  (`skills/tesser-build/python.md` teaches the second exemplar from
  `examples/ports`). Historical records — CHANGELOG entries, the totalreturn
  findings, the application-ports migration measurements, and
  tessercheck-py's "grew up as sigcheck in spike-shells" origin note — keep
  the old name, because they describe the past.

### Changed
- **`examples/spike-llmport` → `examples/llmport`**: directory, manifest key,
  verify arm (`scripts/verify llmport`), CI job, and every live reference.
  `scripts/verify` runs all 8 trees green after the move.

## [0.0.38.0] - 2026-08-15

The checker's own tests move beside the rules they test, without changing a
line of the rules. Issue #75: before the big rules file can be split up, its
behavior had to be pinned at a finer grain than "run the whole checker over a
folder and read the output" — and it turned out the rules never needed the
folder: they are decidable from a built description of a tree (plain tuples
in, findings out).

### Changed
- **160 tests convert to that form and move next to `checks.py`**, one file
  per rule family: sorting (`test_locate.py`), file placement
  (`test_placement.py`), method and constructor shapes
  (`test_signatures.py`), the import rules (`test_imports.py`), test
  placement tiers (`test_tiers.py`), the comment/mock/value-object norms
  (`test_norms.py`), the ignore machinery (`test_ignores.py`), and ports
  (`test_ports.py`). Every assertion string moved verbatim. Because these
  tests sit beside a domain file, the import rules let them reach only the
  domain — which is the proof that each rule is decidable without the reader
  or the service.
- **`tests/test_checks.py` shrinks from 4,709 lines to 153.** The seventeen
  tests that remain are the ones that genuinely need a filesystem: the
  reader's walking behavior and the whole `.tesser-root` declaration family.
- `RULES.md`'s covering-test columns now point into the sibling files;
  `rules.py` scans both homes.
- **No helpers in test files, by rule**: each sibling file carries exactly
  one helper — a spec builder that satisfies the helper contract as written
  (defaulted parameters, one construction, returns the spec, no escape
  comments) — and every test constructs the checker and renders its findings
  inline. Duplication in tests is fine; indirection is not.
## [0.0.37.0] - 2026-08-15

The claim `tesser.domain.ValueObject` exists for — mutation testing sees
through it, while mutmut skips a decorated class wholesale — was declared in
three places and executed in none. Now it is a test that CI runs.

### Added
- **The mutmut ecosystem gate** (`tesser-py/tests/ecosystem/mutmut/`): the
  same `Amount` value object built twice — on `ts.ValueObject` and as a
  frozen dataclass — with an e2e test driving the real mutmut CLI (pinned
  `==3.7.0`) over each. The `ts.ValueObject` build must yield mutants inside
  its hand-written constructor and arithmetic (`value()` is a bare return —
  mutmut generates nothing for it) and every mutant must die; the dataclass
  build must yield none and abort, pinning the negative control so a future
  mutmut
  that stops skipping dataclasses turns the gate red instead of letting the
  docs overclaim. The gate is hardened against lying: fixture copies exclude
  run leftovers (a stale gitignored `mutants/` would otherwise freeze the
  test green against a snapshot), each fixture suite first proves itself
  under plain pytest so the "no test case for any mutant" abort cannot hold
  vacuously, and a lockstep test keeps everything but `vo/amount.py`
  byte-identical between the fixtures.
- **A strict mypy pass per fixture** in the tesser-py verify arm — the
  cross-package `ts.ValueObject` consumer check the retired vobase job used
  to provide.

### Removed
- **`examples/vobase`** (tree, manifest row, verify arm, CI job): its real
  purpose was this gate, and its mutmut dependency was declared but never
  run. The base-class mechanics (equality, hash, immutability, VO-typed
  fields) stay covered by `tesser-py/tests/test_valueobject.py`; the Money
  port's richer behavioral tests (Decimal canonicalization, precision
  traps) retire with it — that ground now has no gated example, recorded
  against the open ValueObject-shape TODO.
- **`tesser-py/setup.cfg`**: its only content was a `[mutmut]` section
  pointing at the shells that no gate ever ran. Running mutmut over
  `tesser/` itself is no longer configured anywhere — deliberate, until a
  gate exists that would actually read the result.

## [0.0.36.0] - 2026-08-15

The checker can no longer write itself exceptions. Issue #75's root cause was
that the file-sorting logic could grow a category serving only the checker's
own files — `context-main` lived that way for six releases because no example
tree ever exercised it and nothing noticed.

### Added
- **A test that makes every classification earn its place**
  (`test_locate.py`): it runs the sorter over every checked tree in the repo
  and fails if any category it can produce appears in none of them — unless
  the category is one of the five finding shapes a rule-following tree cannot
  legally contain, each pinned in the test by name. A new category now ships
  only together with a real example that earns it.
- **A worked example of the eval shape** — the one legal category no example
  earned. `examples/python-app` gains
  `campaign/adapters/gateways/eval_target_policy.py`: an eval lives in a
  gateway, reaches its own kind, its ports, and the foreign client it samples
  through a hand-written fake. Removing the file makes the new test fail by
  name.

## [0.0.35.0] - 2026-08-15

Protocol narrows to its speakers, and the layout app finishes its tests.

### Changed
- **`protocol/` is spoken only by srv and handlers** (`TB066` tightens): a
  context module may import `protocol` only when it holds a handler — keyed
  on the declared block, the same mechanism that already gates
  foreign-client imports. A repository reads `application/ports` and nothing
  else. The test tiers follow: a gateway- or repository-sibling test (and a
  gateway eval) no longer reaches `protocol`; handler-sibling tests keep it,
  and the context `tests/` package keeps it for transport tests. Zero
  migrations — nothing in the corpus ever used the wider grant.
- **The layout app's reader lives in its kind package**:
  `layout/repo/adapters/repositories/file_repository.py`, named for its
  implementation — a flat `repositories.py` had no legal home for a sibling
  test, since the test tiers only recognize kind packages.

### Added
- **The layout app is tested at every tier**: the service in isolation
  through a hand-written fake of its reader port
  (`application/test_service.py`), the DTO-to-domain translation alone
  (`application/test_mapping.py`), and the real reader against real
  filesystems, asserting on port DTOs
  (`adapters/repositories/test_file_repository.py` — manifest states, entry
  forms, the walk's skip list, BOM and undecodable declarations, symlinks
  never followed). The wired end-to-end suite slims from twelve cases to
  five — the tiers own their own edges.

## [0.0.34.0] - 2026-08-15

The layout check becomes an app. `scripts/` held a real Python program
wearing a script's clothes: the repo-layout check had rules, a filesystem
reader, and a test suite, while its directory's manifest row said "ungated"
and its CI job installed pytest by hand. The tool that polices app structure
was itself exempt from all of it. Everything is an app — including this.

### Added
- **`layout/` — the repo-layout check as a full tesser app.** The manifest
  rules live in a `Repo` aggregate (`layout/repo/domain/rules.py`); a reader
  port and filesystem adapter feed it; a two-method client (`check`, `trees`)
  fronts it; `srv/cli/check.py` and `srv/cli/trees.py` are the entry points,
  reached through a handler per the host rules. Gated like every other tree:
  its own manifest row, its own `.tesser-root`, tessercheck zero findings,
  mypy --strict, and 32 tests (a test per rule beside the rules, built from
  specs; whole-app tests against fake repos on disk through wiring and the
  client).

### Changed
- **`scripts/` holds only bash** — `verify` and `install-dev`, dispatch with
  no logic of their own. `scripts/check-layout` and its test file are
  deleted; `scripts/verify` runs the layout app as step 0 and asks it for
  the tree list, so the Python program embedded in the bash heredoc is gone.
- **JSON parsing moved out of the domain.** tessercheck flagged `json` in
  the new domain module: parsing a wire format is the boundary's job, so the
  adapter parses `manifest.json` and the domain judges the rows — the
  serialization norm doing its work on the checker's own checker.
## [0.0.33.0] - 2026-08-15

The analyzer's own entry point. `tessercheck/__main__.py` did two jobs the
conventions place in two different homes — it composed the app and it hosted
it — and the classifier carried a `context-main` place that existed to make
that one file legal. Exactly one file in the repo was ever classified that
way: the checker's own. The extraction and the deletion ship together, because
the self-check gates every change and one without the other turns the
checker's tree red. Issue #75, arc step 2.

### Added
- **`tessercheck-py` has the app shape its own skill prescribes**:
  composition in `tessercheck/wiring/` (the uniform
  `build(cfg) → (Client, Closeable)` contract), the CLI host in
  `srv/cli/main.py`, the composition root in `bootstrap/`, the CLI request and
  response records in `protocol/cli.py`, and a CLI handler in
  `tessercheck/adapters/handlers/cli.py` — a host reaches a context only
  through its handlers, which is what TB063 already said. The context gains a
  public `Client` interface next to its DTOs, and `lifecycle.py` carries the
  `Closeable` shape.
- **Tests beside their subjects** for every new module —
  `tessercheck/wiring/test_wire.py`,
  `tessercheck/adapters/handlers/test_cli.py`, and `srv/cli/test_main.py`,
  each reaching only what its placement allows.

### Changed
- **The analyzer is invoked as `python -m srv.cli.main <tree>`, run from
  `tessercheck-py/`.** `python -m tessercheck` is gone with the `__main__` it
  named. The run happens from the analyzer's own directory rather than the
  checked tree's, because `-m` resolves against the working directory first
  and a checked tree may have an `srv` package of its own — so the tree to
  check is an argument, never the working directory. Breaking for consumer
  repos: update the command.
- **`scripts/verify` calls the analyzer through one `tessercheck_tree`
  helper**, and `scripts/check-layout` recognizes a tessercheck-gated arm by
  that helper's name instead of by the old command string.
- `wiring.md` carries the new spelling; skill-version 34 → 35.

### Removed
- **The `context-main` classification** — the `_locate` branch, the place
  name, its import row, and `_main_violations`. A `<context>/__main__.py` now
  falls through to the stray-module fallthrough (`TB041`), like any other
  module in a context that is not one of its roles. `TB063` itself stays: it
  still carries the host's and the composition root's import rows.
- **`tessercheck-py`'s console-script entry point.** It named
  `tessercheck.__main__:main`, and the host that replaced it lives in the app
  shell (`srv/`), which cannot be shipped as a top-level distribution package
  without colliding with every app that has one of its own.

## [0.0.32.0] - 2026-08-14

Repo layout. Three holes of one shape — nothing said what was covered: a
tessercheck run walked whatever it was pointed at, the tree list in
`scripts/verify` was maintained by hand, and nothing stopped a new top-level
directory from appearing outside the gates. Now every directory says what it
is, and a check fails when the directories on disk and those files disagree.

### Added
- **A checkable tree marks itself with a `.tesser-root` file.** The file
  allows exactly two things — a first line `app`, then `skip <dir>` lines —
  and anything else is a finding. A missing, unreadable, or wrong
  `.tesser-root`, or one nested below the root, is a **`TB044`** finding; a
  **symlinked directory** inside a declared tree is **`TB045`**, because the
  walk never follows symlinks, so a symlink would let unchecked code sit
  inside a tree that reports zero findings. When one of these fires it is the
  only finding reported, and it lands on a file that cannot carry a Python
  comment, so no inline ignore can silence it. Pointing the analyzer at the
  repo root now prints one line per marked tree below it instead of treating
  nine separate trees as one. Breaking for consumer repos: on upgrade, each
  checked tree adds one `.tesser-root` file.
- **`skip <dir>` is where anything specific to one repo goes** — the analyzer
  hardcodes nothing about any repo. tessercheck-py's own fixture directory
  (`testdata`) moved out of the reader's built-in skip list and into its own
  `.tesser-root`.
- **`manifest.json` says what every top-level directory and every
  `examples/*` directory is** — two kinds only, `app` and `ungated`, because
  everything is an app; there is no library kind (a "library" is an app that
  does no IO). `tesser-py` and `examples/vobase` are app rows whose verify
  steps gain the tessercheck step once their trees are reworked to conform.
- **`scripts/check-layout`** cross-checks the words against real things, so a
  typo'd kind cannot quietly drop a tree's gates: directories on disk match
  manifest rows both ways at both levels; a tree has `.tesser-root` exactly
  when its `scripts/verify` steps run tessercheck; every app row has a verify
  arm, a CI job, and a directory name no other app row uses; a
  `requirements-dev.txt` at **any depth** must belong to an app row; a
  symlinked top-level or `examples/*` directory fails. It runs as
  `scripts/verify` step 0 and as its own CI job, which also runs the check's
  test suite (`scripts/test_check_layout.py` — a test per failure case,
  against a small fake repo).
- **`docs/design-repo-layout.md`** — the problem, the two files, the check,
  and why there is no `--run-as domain` flag: what a directory is gets
  written in the directory, never passed on the command line.

### Changed
- **`scripts/verify` reads its tree list from `manifest.json`** — the
  hand-maintained `TREES` array is gone, and if the list comes back empty or
  the read fails, verify stops with an error instead of reporting green over
  nothing.
- **The reader walks the tree once, skipping ignored directories as it goes**
  (symlinks never followed) instead of three separate full scans — the
  `.tesser-root`, nested roots, symlinks, and source files all come from one
  pass.
- `map.md` carries the `.tesser-root` convention; skill-version 33 → 34.

## [0.0.31.0] - 2026-08-13

Application ports. Adapters could import the whole `application` role, so a
gateway imported the service implementation it exists to be decoupled from.
Ports move to a leaf `application/ports/` package and adapters reach only that.
Which shape a port's answer takes was decided by measurement, not preference:
seven trees over one domain, scored on the repo's silent-site metric.

### Added
- **`application/ports/` is a role-internal leaf package**, enforced by a new
  ports rule family (`TB041`/`TB042`/`TB050`/`TB051`/`TB052`/`TB060`/`TB067`/
  `TB068`/`TB069`/`TB080`/`TB081` — see `tessercheck-py/RULES.md`). A ports
  module imports nothing from its tree, its own siblings included; holds
  exactly one port plus the requests and responses it speaks; and runs nothing
  at import. The leaf rule plus one-port-per-module makes two ports sharing a
  DTO unrepresentable rather than merely forbidden.
- **`TB069` gives the ports package a grammar instead of a denylist.** Anything
  outside the permitted shape is a finding by default, named by its AST node
  kind. Four review rounds had each found a different unenumerated slot
  (`AsyncFunctionDef`, `AnnAssign`, class keywords, `type_params`, return
  annotations, a `Call` nested in a base); enumerating forbidden syntax is not
  a winnable game, so the ports module now declares what it permits.
- **`TB068` flags a dynamic import**, which is an import the matrix cannot
  read. It resolves the module rather than the member, so a rebound local,
  `getattr`, `builtins.__import__` and a `sys.modules` lookup are all findings.
- **`examples/ports/`** — the canonical tree: one context, two ports, an enum
  outcome read with `match` + `typing.assert_never`, a collection answer as a
  tuple. Gated by `scripts/verify` and its own CI job.
- **`docs/design-application-ports.md`** — the measurements. Seven encodings of
  one two-outcome answer; `enum` is the only union-free encoding that scores
  zero silent sites when a third outcome arrives. The six rejected trees stay
  executable on the `spike/application-ports` branch.

### Changed
- **`ts.Parts` retires for `tesser.application.Request` / `Response`**, matching
  the client role's vocabulary. A port method takes exactly one request and
  returns exactly one response; a port DTO field is never a union (optional
  included), never a bare `bool`, never subclassed, and a ports enum is an
  `enum.Enum` rather than a `StrEnum`. Each of those four turns a measured
  result into a guarantee — without them the checker permitted both encodings
  the experiment had just measured as silent.
- **All five example trees plus `tessercheck-py` itself migrate.** Dogfooding
  charged the toll immediately: the checker's own `SourceReader` moved to a
  ports package, and two of its bools became enums — one of them in the value
  object this change had just added.
- **Every method rule now reads `async def`.** A one-keyword bypass applied to
  client, adapter, service, spec and value-object rules repo-wide, not only to
  ports.
- **An ignore whose payload does not parse as codes is a finding**, and
  `CLAUDE.md`'s documented `[TB0xx]` bracket form was itself one.
- Skill and doc renderings walked per `CLAUDE.md`: `map.md` moves ports off
  domain (a doc/checker contradiction that predates this change),
  `python.md` gains an application-ports section and loses its union-returning
  example, `serialization.md` reframes the parts module onto port DTOs, and
  `repositories.md`, `gateway-cross-context.md`, `public-interface.md`,
  `domain-return.md`, `application-services.md`, `prior-art-anatomy.md` and
  `design-python-domain-detection.md` drop the "port beside its consumer"
  language. `rationale/coverage.md` gains four rows; `skill-version` 32 -> 33.

### Known gaps
- **No Go mirror.** The ports rules are Python-only; the Go analyzer set does
  not know about ports (`TODOS.md`).
- **`TB068` is a speed bump, not a guarantee.** Reaching a module object at
  runtime is not a closed set; the static import matrix is the guarantee.
- Three encoding choices remain undecidable and are documented rather than
  enforced: a bare `str` outcome field, 0-or-1 cardinality used as an outcome,
  and a mandatory payload on an outcome arm that has none.

## [0.0.30.0] - 2026-08-13

Classifier totality: the module walk's routing becomes one inspectable,
machine-guarded decision, so the "unenumerated shape falls through silently"
bug class dies at dev time instead of surviving to adversarial review.
Analyzer output is byte-identical — this is structure, not new rules.

### Changed
- **`_locate` is now the single routing decision.** The dispatch ladder in
  `tessercheck-py/tessercheck/domain/checks.py` splits into a pure, total
  classification function (module name + is-package → exactly one location
  token) and a dispatcher over tokens. Behavior is unchanged on every tree;
  what changes is that routing is directly assertable without building bait
  trees.

### Added
- **Two meta-tests guard the routing layer**
  (`tessercheck-py/tessercheck/tests/test_locate.py`):
  every token `_locate` can return must have an equality dispatch arm —
  except `context-stray`, the dispatcher's unconditional final return, which
  the test names as the one exemption — and must appear in a 58-row
  classification table, asserted as set equality so a stale row and an
  unexercised token both fail. Adding a new module kind without declaring
  what it is fails the suite by name.
- **A totality corpus**
  (`tessercheck-py/tessercheck/tests/test_totality_corpus.py`): 44 module
  shapes spanning the full location taxonomy — including every shape that
  has produced a silent leak, plus package and `__init__` forms — each
  carrying an illegal import, asserting none is silent end-to-end, with a
  linkage assertion that every file-reachable `_locate` token has a corpus
  shape.

### Removed
- `rules.py`'s ungoverned-basename machinery (`UNGOVERNED_PROSE`,
  `ungoverned_basenames`, `ungoverned_bullets`) and its render bullet: it
  scanned `_module_violations` for basename exemption guards that
  structurally cannot exist there anymore, so it was inert by construction.
  The classification table and the dispatch-arm meta-test supersede it.

The exploration that picked this design — four options built and measured,
including the rejected runtime mirror guard — is preserved on the
`spike/classifier-totality` branch; the PR description records the
evidence. The rule going forward: module routing lives in `_locate` and
nowhere else — a basename or path check added elsewhere in the walk is the
old bug class returning. The one sanctioned second resolver is
`_test_tier`, which answers a different question (which reach tier a
test-shaped module gets) for modules `_locate` has already routed.

## [0.0.29.0] - 2026-08-12

Import totality: every module in a checked tree now carries an import row —
there is no location whose imports go unexamined (closes #71, widened by
ruling from "give root `tests/` a rule" to "no leaks anywhere").

### Added
- **The root `tests/` package gets its derived tier** (`TB070`): a test
  placed there — and any excused helper module beside it — reaches a context
  only through its wiring and client, the built app's public face;
  `bootstrap`, `protocol`, `srv`, the tests package itself, and root modules
  stay in reach, while a context's domain, application, and adapters never
  do. Before this, root tests were the one placement with no import rule.
- **Leaf rows for the tree's edges** (`TB065`): a root module
  (`errors.py`, `serialization.py`, `lifecycle.py`, …) is a leaf that
  imports nothing from its tree — the `ignore-file TB040` that excuses its
  homelessness no longer excuses its imports — and a tree-root `conftest`
  is the same kind of leaf. A `conftest` inside a tests location instead
  carries that location's row, exactly like a test placed there.
- **A context `__main__` is governed** (`TB063`): it composes from its own
  application, adapters, client, and wiring — never domain, never a foreign
  context, never the app shell. It was previously exempt by name.
- **The app-shell matrix closes** (`TB066`, plus a `TB064` clause): of the
  shell a context imports only `protocol`, and only from its adapters;
  production code never imports the tests package; bootstrap never imports
  `protocol`; a protocol module imports nothing else from its tree. Every
  test tier's shell reach now mirrors its subject's production row (srv
  tests see srv/bootstrap/protocol, bootstrap tests see bootstrap, sibling
  tests see none, adapter-kind and context tests see protocol), and a tier
  may reach itself — a context tests module may import its own tests
  package's conftest.

### Changed
- **The example trees migrate with the rules** (zero-failures policy —
  no baseline, rule and migration in one change): misplaced sibling tests
  move into their contexts across python-app, errorspy, serdepy, and
  spike-llmport; python-app's `test_cli.py` splits into a handler-sibling
  test and a `srv/cli` test that drives dispatch through
  `bootstrap.from_env`; errorspy's e2e files turn out to be single-context
  integration tests and live in `campaign/tests/` (no bootstrap needed);
  the analyzer's own tests move to `tessercheck-py/tessercheck/tests/`.
  Four deliberate survivors carry per-line `tessercheck:ignore` pins.
- **`RULES.md` loses its "ungoverned" carve-out bullets** because the
  carve-outs no longer exist: `TOOLING_MODULES` is deleted (`rules.py` is
  now just another root module with an `ignore-file TB040`, a leaf row, and
  the universal checks), and the conftest/`__main__` exemptions are gone.
  The roadmap registry claims `TB065`/`TB066` under the imports norm.

## [0.0.28.0] - 2026-08-12

The test-tier walk becomes total over in-context placements (#64).

### Fixed
- **A sibling test under `adapters/repositories/` was silently ungoverned**:
  the adapters branch of the tier walk recognized only `handlers` and
  `gateways`, so a repository's sibling test resolved to no tier and the
  placement rules never ran on it — zero findings from non-coverage,
  indistinguishable from conformance. `repositories` is now a tier mirroring
  the gateway row's derivation: home `adapters.repositories`, reach
  `application`, and no foreign row (a production repository fronts a backing
  store inside its own context and never reaches a neighbour).
- **A test under `wiring/` or `client/` crashed the whole run**: both roles
  resolved to a tier the reach table had no row for, so `TEST_TIER_REACH[tier]`
  raised `KeyError` and one misplaced test file took down the analyzer for the
  entire tree. Both rows now derive from the production import matrix — wiring
  reaches `application`, `adapters`, `client` plus a neighbour's client
  (mirroring `TB061`'s "gateways and wiring" rule); client reaches only its
  own client.
- **A test that resolves to no tier is now itself a TB070 finding** ("a
  sibling test lives in a role package or an adapter kind package") instead
  of silently escaping the placement rules — a flat `adapters/test_x.py`, an
  unrecognized adapters subrole, and a test under an unknown role package all
  report instead of passing. This closes the issue's stated failure mode for
  the next unrecognized directory name, not just the two it documented.
- **Tests under `bootstrap/` and `protocol/` were the same leak one level
  up** — a `test_*` basename diverts to the test-module rules before the app
  package rules run, and only `srv` had a test tier, so a test parked in
  either package escaped both rule sets. Both now mirror their production
  import rules: a bootstrap test reaches a context only through its wiring,
  client, and adapters (the TB063 rule); a protocol test reaches no context
  at all. A root-level `tests/` directory stays placement-free on purpose —
  it is the app tier, where the integration tests live.

## [0.0.27.0] - 2026-08-12

One analyzer, every tree: the last two frozen-dataclass examples move onto
the shells and the parked legacy analyzer retires.

### Changed
- **`examples/serdepy` migrated to `ts.*` shells** as a `parcel` context
  (`parcel/domain`, `parcel/application`, `parcel/adapters`): leaves on
  `ts.ValueObject` with the all-four-exits matrix intact, `ParcelSpec` on
  `ts.Spec`, `Parcel` on `ts.Entity`, `ParcelParts` on `ts.Parts`, the wire
  payload builder as `@ts.function`. The analyzer gained `bytes` in the
  construction-primitive set (with a pinned test) — `LabelDigest` exposed
  the gap.
- **`examples/errorspy` migrated to `ts.*` shells** as a `campaign` context.
  The local `Entity` prototype (the class the shipped `ts.Entity` grew from)
  is deleted in favor of the real thing; the service speaks client
  request/response DTOs over a parts-speaking `ts.Port`; the aggregated
  `errors.collect` validation moves from the handler into the service's
  convert step; the repository keeps the tree's unique lesson (StorageMiss →
  missing lookup, StorageUnavailable → InfraError) with the corrupted-record
  → InfraError translation at the application rebuild step; the RFC 9457
  problem mapping stays on the handler. Every norm-proof assertion survives
  unchanged; `main.py`'s demo is covered by `test_e2e` and deleted.
- **`roadmap/generate.py`'s Python column** now reads the graduated
  analyzer: `py_check_codes` loads `tessercheck-py/rules.py` by file path
  and uses the same `rule_rows` extraction `RULES.md` is generated from.
  The registry claims all 34 shipped codes (construction doors under
  value-objects, service signature/body under application-services,
  module/class structure under the map, import form and matrices under
  norm-imports, test totality under norm-testing; `TB090` exempted by name
  as the tool's own suppression hygiene), and the five dead
  frozen-dataclass-era codes (`TB001`, `TB003`, `TB013`, `TB014`, `TB032`)
  leave their rows.
- **`rationale/coverage.md`'s Python-enforcement section and
  `testing.md`'s rule-9 bullet** rewritten onto the shell-declared analyzer
  (declared bases instead of the structural classifier; `TB071`/`TB073` as
  `TB032`'s successors; dissolved checks named as dissolved).

### Removed
- **The `# tesser-category:` directive** — the marker only the legacy
  analyzer's TB032 read. Test-module members declare themselves with
  `@ts.helper`/`@ts.fake` now, so the comment form leaves the TB020
  exemption ledger (`comments.md` and the `CATEGORY_MARKER` pattern in
  `checks.py` together); writing one is an ordinary TB020 finding. The
  dead codes also leave every living doc surface — README's analyzer
  blurbs, `wiring.md`'s discovery pointer, `serialization.md`'s and
  `coverage.md`'s TB013 clauses, `domain-return.md`'s TB014 clause — and
  `roadmap/generate.py` loses its last two `CHECKS`-era artifacts (the
  `finding.py` universe probe and the stale error message).
- **`tessercheck-py-legacy/`** — with serdepy and errorspy on shells,
  nothing frozen-dataclass remained for the pre-merge analyzer to validate.
  Its verify tree and CI job go with it. The serdepy/errorspy verify gates
  gain the shipped analyzer's zero-findings step, so an example layout
  change still breaks loudly (the PR #56 lesson). The reviewed `TB031`
  fixture pair survives at `tessercheck-py/testdata/tb031/` with a
  divergence guard.

## [0.0.26.0] - 2026-08-12

The Python skill teaches what the analyzer enforces, from the code CI
verifies — and the frozen-dataclass founding example retires.

### Changed

- `skills/tesser-build/python.md` rewritten end to end onto the shell
  idiom: every code block mirrors `examples/python-app` (fidelity-audited
  block against file), the analyzer's family codes are cited inline, the
  construction-door ruling is recorded as revised for the shells (a value
  object's one door takes primitives and child VOs; entities and
  aggregates take exactly one spec), and the srv/wire vocabulary
  graduation is folded in. skill-version 30.
- `examples/python-app` gains the collection value object `Labels`
  (`campaign/domain/labels.py`): sorted-tuple canonicalization at the one
  door, duplicate keys and empty values rejected, entries read back as
  `LabelValue` value objects.

### Removed

- `examples/python` — the frozen-dataclass founding example. Its two
  unique derivations live on in the shell idiom (`Money` and the new
  `Labels`, both in python-app), every doc and registry reference is
  repointed, and the legacy analyzer's acceptance gate retired with it.

## [0.0.25.0] - 2026-08-12

The seven shape norms land on shells, under the ruling: value objects only
return other value objects — no tooling exemption. The analyzer now
enforces the full identity-and-serialization taxonomy on every `ts.*` tree,
itself included.

### Added

- **TB010** (a value object hides its representation), **TB011** (an
  accessor never hands back the backing collection), **TB012** (an
  aggregate is referenced by ID, never held), **TB015** (no spec-returning
  method; a leaf defines exactly its backing type's conversion dunder; a
  structured domain object has no primitive exit), **TB016** (bool/complex
  are not value-object material at any field count; a compound backs
  itself with child value objects), **TB017** (one construction door —
  `Self`, quoted, and unannotated factories included), **TB018** (a
  canonical exit is a one-line delegation to its `canonical_*` policy,
  module-qualified delegation accepted), **TB019** (a domain object's
  public behavior hands back domain objects; quoted annotations are no
  escape; the six comparison dunders are genuinely in scope).

### Changed

- The analyzer conforms to its own norms: `Violation` decomposes into
  `Path`/`Line`/`Code`/`Text` leaves with canonical policy exits, the
  finding renderer moves from the (banned) compound `__str__` into the
  application service, and the internal records model their former bool
  pairs as validated three-valued form leaves.
- spike-llmport's `Booking` exposes its `Step`/`CustomerName`/`Slot`
  leaves instead of label strings, with the boundary mapping in views.

## [0.0.24.0] - 2026-08-12

python-app reaches zero findings and the last ratchet retires — every
gated tree now holds the same bar: zero findings, with ruling-blocked
sites carrying coded site-level ignores that self-report when stale.

### Changed

- All ~104 member-form context imports in `examples/python-app` converted
  to aliased module imports; srv and bootstrap functions declared with
  `@ts.function`; the missing `tesser.*` imports added. The 20
  ruling-blocked sites (homeless root modules, host-machinery and
  bootstrap classes, the alias hard collisions, the `__main__` guards,
  the pure-core allowlist candidates) carry coded `# tessercheck:ignore`
  markers, each tied to its open TODOS.md ruling.
- The `test_parts_module_never_touches_specs` guard reads attribute
  references too, so the aliased-module style cannot slip a Spec past it.

### Removed

- `scripts/sigcheck-ratchet` and the accepted-debt baseline — and with
  them the branch-controlled-baseline soundness hole. The python-app CI
  step is a plain zero-findings gate.

## [0.0.23.0] - 2026-08-12

sigcheck graduates. The declare-then-verify engine that grew up in
`examples/spike-shells` is now the `tessercheck-py` package, run as
`python -m tessercheck` — one analyzer name for the toolkit's Python half.

### Changed

- The analyzer package renamed sigcheck → tessercheck and moved to
  `tessercheck-py/` with its rule set (RULES.md), generator, tests, and
  import contracts; `examples/spike-shells` returns to being the worked
  example, gated at zero findings by the analyzer it hatched.
- The pre-merge analyzer is parked byte-identical at
  `tessercheck-py-legacy/`, its four CLI gates intact, while
  `examples/python`, `serdepy`, `errorspy`, and `python-app`'s domain are
  still frozen-dataclass trees — no enforcement gap opens. The
  tree-migration wave deletes it.
- `scripts/verify` gains the legacy tree (ten trees total); the python-app
  ratchet drives the new binary with an unchanged baseline; CI jobs and the
  roadmap generator's registry import follow the moves.

## [0.0.22.0] - 2026-08-12

The first tessercheck→sigcheck check ports — the five whose semantics
survive the frozen-dataclass → shell substrate change unaltered, keeping
their original codes.

### Added

- **TB020, the comments norm**, now enforced by sigcheck tree-wide with no
  test exemption: no comments, docstrings, or bare string statements;
  machine directives exempt (shebang, coding cookies on lines 1-2,
  `type:`/`noqa`/`pragma`/formatter controls, `tessercheck:ignore`, and the
  exact `tesser-category:` marker grammar — prose trailing the marker is
  still a comment). sigcheck's own rationale comment blocks are deleted
  per the ruling: the rules live in RULES.md, the why lives in sessions
  and git history.
- **TB030, the fakes-only norm**: mocking-library imports in every shape
  (including the `import unittest` → `unittest.mock` chain), pytest
  `MonkeyPatch`, and `monkeypatch`/`mocker` fixture parameters in
  pytest-shaped functions. python-app's four existing seam markers are
  load-bearing again; their transitional TB090 baseline entries burned
  off.
- **TB033** (a builtin bound and then called in the same scope), **TB004**
  (equality with `str()` on both sides), and **TB002** (a value object's
  field must be hashable — including `MutableSet` and quoted forward-ref
  annotations) — all with tessercheck's scope semantics preserved and
  probe-verified against the reference implementations.

### Changed

- The remaining ports (TB010–TB012, TB015–TB019) are deliberately deferred
  to a named ruling: their core terms (field, leaf, canonical exit,
  primitive accessor) were derived on the frozen-dataclass substrate and
  collide with the shell idiom. TODOS.md carries the re-derivation
  question.

## [0.0.21.0] - 2026-08-11

The sigcheck harness wave — the consumer-facing prerequisites for
graduating the spike into tessercheck-py. A finding is now editor-clickable
(`path:line: TB0xx message; clause`), a broken file is a finding instead of
a crashed run, and the only opt-out mechanism is per instance, at the site.

### Added

- Family codes on every finding (TB040 totality through TB090 ignore
  hygiene), rendered as RULES.md's new Code column. Codes are reporting
  affordances: CI stays zero-findings and there is no code-level off
  switch.
- Inline opt-outs: a trailing `# tessercheck:ignore` suppresses the
  reported line, `# tessercheck:ignore TB052` exactly that family
  (several codes may follow, space- or comma-separated), and
  `# tessercheck:ignore-file TB040` the family module-wide — the file
  form requires codes. An ignore that suppresses nothing is itself a
  TB090 finding, TB090 cannot be ignored, and the grammar is strict: a
  typo'd marker or an unknown code token makes the comment inert rather
  than silently suppressing.
- Per-file reader isolation: an unparseable module, an unreadable file,
  or a module defined twice (`domain.py` beside `domain/__init__.py`) is
  a TB043 finding; the standard tooling directories (`.venv`, `build`,
  `node_modules`, …) are pruned; UTF-8-BOM files check normally.
- Optional construction data: `X | None` is accepted wherever `X` is, in
  specs, DTOs, and value-object constructors — and only that union
  shape (`str | int` stays a finding).

### Changed

- The finding format moved the line number out of the message text into
  the structured `path:line:` slot; message heads keep their dotted
  locators. The python-app ratchet baseline is regenerated for the new
  format and carries four named TB090 entries — python-app's existing
  bare markers aimed at tessercheck-py's TB030, transitional until that
  check ports into sigcheck.

## [0.0.20.0] - 2026-08-11

The sigcheck internal cleanup batch — the deferred pre-landing items from
TODOS.md, landed as the base for the tessercheck merge waves. Behavior on
every input is message-for-message identical (proven differentially and by
the ratchet holding at exactly 148/148); the one visible change is finding
*order* on a module whose body interleaves class and statement violations,
where class findings now print first.

### Changed

- One `_tesser_import_violations` replaces the five inline copies of the
  exactly-once-as-ts walk (bootstrap, srv, protocol, role, test), and one
  `_statement_violations` replaces the four statement-totality loops; each
  caller keeps only its own class handling. Clause texts ride as call-site
  literals because `rules.py` renders RULES.md rows from them.
- `ImportEdge` and `TesserImport` value objects replace the
  positionally-decoded 4-tuples for import edges. The alias slot is now
  `as_ts: bool`, honest for from-form imports.
- The cross-context legality sentinel (`len(found) == before`) is an
  explicit `denied` list in both import walkers.
- `Module` freezes every accessor collection once at construction.
- `rules.py` resolves call-site bindings before `HOLE_NAMES`, derives the
  conftest/`__main__` exemption bullets from the code's own AST guards (so
  governing either forces a RULES.md diff), and distinguishes a missing
  `TOOLING_MODULES` from a malformed one.

### Fixed

- Pre-landing review findings: a provably-dead sub-condition in the
  absent-imports guard, and direct test coverage for the paths the batch
  introduced (edge-record construction guards, a test module owing no
  `tesser.testing` import, a denied srv edge suppressing the form rule,
  and both new generator tripwires).

## [0.0.19.0] - 2026-08-08

The srv signature matrix, ruled by building it. Three questions had been
parked as named debt — do wire records carry behavior, what word covers a
tool declaration, and where does wire-record immutability come back — and
each was settled by building the candidate shapes and letting the code
and the checkers pick. Nothing here was decided in prose first.

### Added

- `tesser.srv.Record` — the frozen wire-record base, and the generic wire
  kind for wire data that is neither a request nor a response. `Request`
  and `Response` now subclass it. Construction is one-shot (a populated
  `__dict__` refuses a second `__init__`, which is what makes the freeze
  hold), fields land through a kwargs constructor checked against the
  class's own annotations, equality is by type and value, and records are
  unhashable — defining `__eq__` drops the inherited hash, which is the
  right default for wire data that can carry a header map. Subclasses
  may not take over `__eq__`/`__ne__`/`__hash__`/`__setattr__`/
  `__delattr__`, declare `__slots__`, or give a field a class-level
  default — each guard walks the MRO, so a mixin listed before the base
  cannot reopen the record.
- `wire_record` joins the sigcheck kind table, accepted in a wire module
  and refused in a context or `srv` module like its sibling wire kinds.
- `tesser.srv.Rejection` — the wire's own refusal word, and the
  `wire_rejection` sigcheck kind. Every protocol needed one (`BadRequest`/
  `PayloadTooLarge`/`StreamingUnsupported`, `UsageError`, `BadToolCall`)
  and all five were ratchet debt or unbuildable until the kind existed;
  the host maps rejections to statuses/exit codes/tool errors, the wire
  only names them.
- A meta-test resolves every `TESSER_BASE_BLOCKS` and `TESSER_DECORATORS`
  row against the real `tesser-py` export lists, so an analyzer row can no
  longer outlive the class it names.

### Changed

- **Wire records carry their behavior.** `httpwire`'s nine loose
  `@ts.function` module functions collapse to two public ones
  (`object_field`, `string_field`) plus a private JSON-object reader:
  `problem`/`json_response`/`redirect`/`respond` became `HttpResponse`
  classmethods (`problem` now returns the HttpResponse, folding away every
  `json_response(status, problem(...))` double call); `decode_body`/
  `path_param`/`content_length` became `HttpRequest` readers (`json_body`,
  `path_param`, `buffered_length`), with `HttpResponse` gaining the mirroring
  `json_body`. `cliwire`'s four go to zero the same way: `ok`/`respond` are
  `CliResponse` classmethods, `arg`/`no_extra_args` are `CliRequest`
  readers. The DTO-purity objection dissolves on the package-scoped kind
  grammar: `ts.srv.Request`/`Response` are distinct kinds from the context
  DTOs, which keep carrying data and nothing else.
- **The LLM tool call gets its request record.** `voicewire.ToolCall`
  (`ts.Request`: tool name + arguments, deep-copied at construction like
  `Tool.parameters`) replaces the bare `Mapping[str, object]` the voice
  host used to hand across the boundary — endpoints are now
  `(ToolCall) -> ToolTurn`, the exact shape of their HTTP and CLI
  siblings, and the handler reads arguments off a frozen record instead
  of livekit's live dict.
- **"Wire" left the ubiquitous language; the protocol package replaced
  it** (Chris rulings, 2026-08-08). The word named the wrong boundary — a
  `Route` never crosses any transport; the actual boundary is
  host/handler — and it collided with the settled `wiring` role. The
  concept is now the **protocol**: the app owns it, the handlers define
  it, the hosts conform to it. Concretely: `httpwire.py`/`cliwire.py`
  became `protocol/http.py`/`protocol/cli.py` and `voicewire.py` became
  `protocol/voice.py` — a governed top-level `protocol/` package per
  tree. sigcheck drops suffix detection for package membership
  (`PROTOCOL_PACKAGE`), which also closes the suffix hole where
  `tripwire.py` opted in and `serdepy/wire.py` collided: a stray
  `*wire.py` is now simply homeless. Kind keys renamed `wire_*` ->
  `protocol_*`; rule text, RULES.md, fixtures, and the python-app ratchet
  renamed with them (same 163 findings). `Record`'s runtime messages stop
  saying "wire record". Earlier the same day and in the same spirit,
  httpwire's `Response` became `HttpResponse` — message classes carry
  their protocol's name.
- **The three protocol stacks now share one skeleton** (conformance
  sweep, 2026-08-08). A wire module holds records with every constructor
  field stated (no defaults — the test-convenience defaults moved into the
  tests that wanted them), readers that raise the wire's own `ts.Rejection`,
  and no error policy; a handler method is exactly three jobs (map request,
  invoke the service, map response) — the per-method `respond` wrappers and
  their `def run()` closures are gone from every HTTP and CLI handler; the
  host owns the exception→response mapping (`srv/http/host.py` gained
  `respond` + `buffered_length` + the size cap, `srv/cli/main.py` gained
  `respond`, and the voice host now catches `BadToolCall` alongside domain
  `ValueError` — previously a non-string argument would have crashed the
  session instead of reaching the model). `ToolCall.text` moved the argument
  reader into the wire where `string_field`/`arg` already live. Verified
  against the live server: 400/422/201/411 byte-identical with the handler
  wrappers gone. python-app's sigcheck ratchet burned 176 -> 163 (wire
  exceptions declared, hosts import ts, srv functions declared, HttpHost
  declares ts.Host), shrink-only.
- **One binding table replaces three parallel chains.** `LlmToolHandler`
  keyed tool names in `TOOLS_FOR_STEP`, a `dispatch` if/elif, and a
  `_schema` if/elif — four hand-coordinated edit sites per tool. Dispatch
  and the offered schemas now derive from a single table, and a new tool
  is one entry plus its step row. The declaration itself became wire-side
  data (`voicewire.Tool`); the context-side tool CLASS turned out to be
  unbuildable inside the srv vocabulary, and the analyzer's refusals are
  recorded verbatim in the spike README as evidence for that ruling.

### Fixed

- **Request smuggling in the HTTP host.** Duplicate `Content-Length`
  headers collapsed into a dict framed the body on the last value, so a
  fronting proxy honoring the first would desync the connection.
  `buffered_length` now reads the raw header pairs and refuses conflicting
  declarations. Verified against the live server: the request that
  returned 201 with a smuggled body now returns 400.
- **Permissive body framing.** `int()` accepted `5_0` (framed as 50),
  `+50`, and surrounding whitespace; the length is now plain ASCII digits
  or a 400. The `Transfer-Encoding` guard matched the substring `chunked`,
  so `Transfer-Encoding: gzip` alongside a `Content-Length` was accepted —
  any transfer encoding now draws 411, since this host buffers.
- Smaller wire hardening: `HttpResponse.json` replaces rather than duplicates
  a caller-supplied `Content-Type`, `HttpResponse.redirect` refuses a control
  character in the target instead of trusting the domain, the host no
  longer emits `Content-Length` twice when a handler set one, and the
  request handler has a timeout so a declared-but-undelivered body cannot
  pin a thread.
- Wire records regained the immutability and value equality that the
  dataclass-to-shell migration dropped in 0.0.18.0 (recorded then as named
  debt for this ruling).

## [0.0.18.0] - 2026-08-07

The srv and wire vocabulary: hosts and the modules both sides of a wire
share now have declared kinds, and the two example trees that carried
that gap as ratchet debt conform to them. Every piece of this release
was derived from standing rulings rather than newly decided — the
package-scoped kind grammar the errors ruling set, the position-naming
precedent `Endpoint` established, and the spike's recorded
delete-option-A plan.

### Added

- `tesser.srv` — the host-side shell package: `Host`, `Port`
  (Protocol-shaped, a distinct kind from `tesser.application.Port` by
  the package-scoped grammar), `Request`, `Response`, and the
  `@ts.function` declaration. `tesser.app` (App/Config) is deliberately
  not included — a real open question, not bundled into a derived one.
- Wire-module governance in sigcheck: a top-level `*wire.py` is a
  governed home (name-as-declaration, the `test_*` precedent) — it
  imports `tesser.srv` exactly once as ts, holds only wire kinds
  (`wire_port`/`wire_request`/`wire_response`), and its ownership is
  enforced as import rules: context-generic, and never imports srv or
  bootstrap, so hosts and handlers can both import it without either
  leaking into the other. srv modules split from bootstrap (declared
  host classes, `tesser.srv` as their shell package); RULES.md grows
  57 → 74 rows, every clause fixture-covered, with the wire-suffix
  convention and the srv-kinds-placement-only carve-out rendered into
  the generated exemptions.
- A kind-map totality meta-test (every declared block has a name and a
  home) and a CI wheel-contents gate for tesser-py — the built wheel
  had silently omitted `tesser.testing`, and would have omitted
  `tesser.srv`, because every other job reaches the source via
  PYTHONPATH; packaging switched to discovery (`packages.find`) so a
  new shell package can never be forgotten.

### Changed

- `examples/spike-llmport` enacts the host/handler verdict: the wire
  protocol is renamed `ToolSurface` (the old name collided with the
  Handler block term), a concrete `ToolTurn` record (reply + tool
  schemas) replaces the state-generic `ToolHandler[S]`/`ToolState`
  machinery that produced the four-reviewer contravariance defect, and
  `ToolAgent` declares itself a `ts.Host`. The frozen option-A mirror
  (`scheduling/adapters/livekit.py`) is deleted per the spike's recorded
  plan, the tree's sigcheck ratchet burns to zero, and the
  sigcheck-vs-ruff F401 collision resolves itself — the mandated srv
  import is now load-bearing.
- `examples/python-app`'s `httpwire`/`cliwire` stop being homeless:
  request/response records become declared `ts.Request`/`ts.Response`
  shells, the `Endpoint`/`Command` Callable aliases become declared
  `__call__` ports (positional-only parameter — zero call sites
  changed), and the mechanism functions declare `@ts.function`. The
  ratchet rebases 173 → 176; the five remaining wire findings are named
  debt, one per open ruling (four exception classes on the `ts.Error`
  track, the type alias on the alias-declaration story — recorded as
  hard rule collisions, not conformance work).
- `ToolTurn.reply` is asserted on every turn, the srv/context shell
  distinctness is pinned, and the httpwire fidelity guards assert
  stored attributes again on the new substrate.

### Fixed

- sigcheck's `@ts.fake` rule accepts a fake that implements a wire
  port (previously a latent false positive on faking `Endpoint`,
  `Command`, or `ToolSurface`), the contradictory placement clause pair
  is reworded ("a host lives in srv and a wire kind in a wire module,
  never a context"), and `SRV_KINDS`/`WIRE_KINDS` are derived from the
  block table with the companion name/role maps guarded total — the
  sanctioned one-line kind extension previously crashed the analyzer
  instead of reporting.

## [0.0.17.0] - 2026-08-06

The LLM tool-call port spike: `examples/spike-llmport`, a `scheduling`
bounded context whose next workflow step is decided by an LLM tool call,
built in the `ts.*` shell idiom under the import-totality rulebook (the
`scheduling` context sigcheck-clean, the tree ratcheted at two accepted
findings), and shaped to answer three standing questions with running
code.

The design: the tool surface is data, not decorated host functions — and
the context's edge owns all of it. The service exposes one-Request-one-Response use
cases (`begin`/`provide_name`/`choose_slot`/`confirm`/`reoffer`/`status`);
the LLM wire — tool vocabulary, JSON schemas with the offered slots
embedded as a live enum, raw-argument parsing, tool-to-use-case dispatch,
and the conflict choreography (a taken slot re-offers fresh slots in the
error the model sees) — lives entirely in `adapters/handlers.py`. The
begin use case resumes an in-flight booking, so a session reconnect
continues the conversation instead of resetting it; the aggregate rejects
inconsistent reconstitution outright.

The host/handler question answered in code: the AgentSession wrapper is a
host. Once `instructions()` moved onto the handler, the LiveKit agent
became fully context-generic — `srv/voice/agent.py`'s `ToolAgent` imports
nothing from any context and speaks to `voicewire.ToolHandler`, a
state-generic protocol whose conformance is proven by a typed assertion
under mypy --strict. One voice host can mount any context's LLM handler,
exactly as the HTTP host mounts HTTP handlers. What blocks enacting the
verdict is carried as evidence: the tree's sigcheck ratchet holds exactly
one finding per open ruling (a class in srv — the host-vocabulary gap;
`voicewire.py` homeless — the root-module-homes gap), fail-closed in CI.

Hardened by a seven-reviewer pre-landing pass (four specialists, Claude
adversarial, two Codex passes): the recovery path can no longer bypass the
halt policy, tool dispatch is serialized per session, model-supplied
strings are bounded, an exhausted directory surfaces both the conflict and
the exhaustion, and the README records the five deliberate production
boundaries plus a newly surfaced rulebook collision (sigcheck mandates a
srv shell import that ruff's F401 forbids).

## [0.0.16.0] - 2026-08-06

The import-totality wave: sigcheck's rulebook grows from 41 to 57 rules
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
