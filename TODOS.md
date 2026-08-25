# TODOS

Deferred work with context. Each entry carries enough for a cold pickup.

## Sibling-reference rule: three open sub-rulings (2026-08-23, v0.0.76.0)

TB051's structural clause (a method may not reference a sibling method; direct
recursion and references to a directly recursive sibling exempt) bites three
shapes that were marked `# tesser:debt TB051` rather than restructured, each a
ruling Chris has not made yet:

- [ ] **`tesser-py/tesser/domain/entity.py:22,25`** — `Entity.__eq__`/`__hash__`
  read `self.identity`, the abstract property subclasses declare. This is the
  shipped runtime's template method: the identity contract *is* a sibling
  reference by design, and no field read can replace it because the subclass
  owns the property. Candidate carve-out: a dunder may read the contract its
  base defines. Or: the design is right and the debt marker is its honest cost.
- [ ] **`examples/python-app/protocol/http.py:95`** — `HttpResponse.problem`
  composes `cls.json`, the one path that sets Content-Type. Inlining duplicates
  that path; the marker preserves it. Candidate carve-out: classmethod builders
  composing builders. Or: inline and accept three duplicated lines.
- [ ] **`examples/python-app/srv/http/main.py:27,28`** — `run` passes
  `self.stop` to `signal.signal`. The outsider (the signal machinery) is the
  caller; `run` only hands the method over. The reference test cannot
  distinguish registration from invocation — that indistinguishability is why
  the rule fires on references at all (else `f = self._x; f()` dodges it).
  Candidate carve-out: none obvious that is mechanical; may just stay debt.

Also recorded, all accepted as residue for now (the rule is an experiment;
any of these appearing in a real tree is the evidence that would justify
tightening): the fake-recursion dodge (`if False: self._x(...)`), receiver
aliasing (`me = self; me.x()`, `type(self).x(self)`, `self.__class__.x(self)`,
`getattr(self, "x")()`), helpers relocated to a base/mixin class (member sets
are per-class, no MRO analysis), and assignment-defined members
(`x = staticmethod(...)`, `x = lambda self: ...`). Separately: debt markers sit
on the reported reference line, which for a wrapped call is a continuation
line — a reflow detaches the marker. The failure is loud (TB090 + the
resurfaced finding), not silent, so it is recorded rather than re-engineered.

## The skill still teaches the module-function idiom (2026-08-22, v0.0.74.0)

Removing `@ts.do_not_use_function` stripped three decorator lines from
`skills/tesser-build/python.md`, but the examples underneath them are stale in a
way the decorator was hiding: they teach module functions, which TB051 now bans.
(The `srv/http/main.py` example was one of the three; v0.0.75.0 rewrote it to
`ts.main` and the ruling that allowed it, so only the two below remain.)

- [x] **`python.md:529` shows `required_campaign` as a module function** — RESOLVED
  v0.0.83.0: the section now teaches the is-a mapper (`MapToCampaignSpec(ts.Mapper,
  campaign.CampaignSpec)`), which is what errorspy holds. Original entry: cited
  as "verified impl: examples/errorspy/". The verified impl no longer has it —
  `examples/errorspy/campaign/application/views.py` holds
  `MapToShortLinkSpec(ts.Mapper)` and `MapToCampaignSpec(ts.Mapper)` and no
  module function at all. So the skill teaches a shape the rule bans and the
  cited example abandoned. Rewriting the section to the `ts.Mapper` idiom was
  left out of the decorator-removal change deliberately — it is a content
  rewrite of shipped guidance, not a deletion, and it wants its own review.
- [ ] **`python.md:654` had the decorator on a `class`**, which was never valid
  — it decorated functions. Removed with the others; noted only because it means
  nothing in CI reads the skill's code blocks. A checker that parses fenced
  python in `skills/` and runs tessercheck over it would have caught this, and
  would catch the two above.

## scripts/verify portability (2026-08-22, v0.0.72.1)

`scripts/verify` and `scripts/install-dev` could not run on macOS until
v0.0.72.1: both used `mapfile`, a bash 4 builtin, and macOS ships bash 3.2.
Every CI job runs on `ubuntu-latest`, so CI was structurally incapable of
noticing. The builtins are gone; what is still open is anything stopping them
coming back.

- [ ] **No guard against a bash-4-ism returning.** The fix added a comment at
  each site saying why it is a `while` loop and not `mapfile`, which is the
  only thing standing between here and a well-meant "simplification" that CI
  would wave straight through. A real guard would be a static check — grep the
  four shell files (`scripts/verify`, `scripts/install-dev`,
  `scripts/verify-packaging`, `rationale/measure-ablation.sh`) for `mapfile`,
  `readarray`, `declare -A`, `${v,,}`/`${v^^}`, `;;&`, `coproc` — hung off the
  packaging job or its own. The alternative, a macOS runner, costs 10x and
  would be the only non-ubuntu job in the matrix. Deferred pending Chris's
  call on whether a bespoke grep-lint earns its place.
- [ ] **Retiring a Python example tree leaves dirt that breaks step 0.** When
  `examples/python` retired in v0.0.26.0 (#68) its sources left the repo but
  its `__pycache__`, `.pytest_cache`, and `.mypy_cache` directories stayed on
  disk. The layout app's `SKIP_DIRS` skips those as *entries*, but
  `examples/python` is itself an ordinary directory that happens to contain
  only skipped ones, so it enumerated as an `examples/*` tree and demanded a
  manifest row — failing step 0 with `examples/python has no manifest.json
  row`. Because the contents are gitignored, `git status` said nothing. Fixed
  on Chris's machine by deleting the directory; nothing in the repo changed,
  and nothing stops the next retirement doing it again. Teaching the layout
  app to ignore cache-only directories was considered and rejected: it would
  also hide a genuinely emptied example tree, which is the opposite of what
  the check is for. A retirement checklist item is the cheaper answer.

## Packaging gaps (2026-08-19 adversarial review of PR #113; rescued from PR #114 before it was closed)

These were found by the adversarial pass on #113 and recorded only in the
description of PR #114. #114 itself went obsolete — it asked to bump the
`tessercheck-py` wheel 0.2.0 → 0.2.1, and `main` reached 0.3.0 first — so it
was closed on 2026-08-21 and its findings moved here. Each was re-verified
against `main` at v0.0.71.0 rather than transcribed.

- [ ] **P1 — `tessercheck-py` depends on `tesser`, and that name belongs to
  someone else on PyPI.** `tessercheck-py/pyproject.toml` declares
  `dependencies = ["tesser"]`, meaning this repo's own runtime library, which
  `tesser-py/pyproject.toml` publishes as `name = "tesser"` at `0.1.0`.
  - **Verified 2026-08-21:** PyPI already has `tesser` — "Python SDK for Tesser
    Trading Engine", version `0.9.1`, uploaded 2025-11-27, pulling gRPC,
    pandas, and protobuf. Unrelated project, live, and ahead of us in version.
  - **Consequence, both directions:** the name cannot be claimed, so
    `tesser-py` has no publishable identity as written; and a published
    `tessercheck-py` would resolve `tesser` to that SDK and import
    `tesser.domain.ValueObject` out of a trading library.
  - **Latent, not live:** `tessercheck-py` is not on PyPI (404 as of
    2026-08-21), so nothing is broken for anyone today. It is a hard blocker on
    first publication, and it decides a public name, which is why it is P1
    despite hurting nobody yet.
  - **Start at:** this is a rename, not a pin — pick the distribution name for
    the runtime library, then update `tessercheck-py`'s dependency, the
    packaging gate, and every install instruction in the READMEs together.

- [ ] **P1 — `scripts/verify-packaging` cannot see the defect class it
  advertises.** Its header calls it "the gate on what `pip install` actually
  gets you", but it installs all three distributions from local paths in one
  invocation: `pip install "$VENV/tesser-py" "$VENV/tessercheck-py"
  "$VENV/tessercheck-cli"`. The local `tesser-py` satisfies the `tesser`
  requirement in that same resolution, so pip never queries an index. The gate
  is green and structurally blind to the entry above.
  - **Why it matters beyond this one bug:** every dependency-resolution defect
    is invisible to it, not just this one. A gate that names a guarantee it
    does not check is worse than no gate, because it is read as coverage.
  - **Start at:** decide what the gate is for. If it is "the wheel's contents
    are importable", say that and stop claiming the install path. If it is
    "what `pip install` gets you", it needs a resolution step that is allowed
    to reach an index (or a deliberate local index that proves the names
    resolve to what we think).

- [ ] **P2 — `tessercheck/adapters/handlers/cli.py` imports a package the wheel
  does not ship.** Line 8 is `from protocol.cli import CliRequest,
  CliResponse`, and `protocol` is a top-level package; the `[tool.setuptools]
  packages` list contains only `tessercheck.*` entries. From an install, that
  module raises `ModuleNotFoundError`. Same bug class as #113 (`ports` missing
  from the list), but the fix is not another list entry — `protocol`, `app`,
  and `srv` are the names `TB040` mandates for every tesser app, so shipping
  this one's `protocol` into site-packages would collide with the consumer's.
  Needs the design answer, not the mechanical one.

- [ ] **P2 — an explicit `packages` list has no totality check, and it already
  failed once.** `tessercheck-py` enumerates its eight packages by hand, so
  omitting one builds a valid wheel that silently lacks a module — exactly how
  #113 shipped without `tessercheck.application.ports`. Nothing fails in the
  under-listing direction. `tesser-py` already uses the discovering form
  (`[tool.setuptools.packages.find] include = ["tesser*"]`), so the repo holds
  both strategies and the hand-maintained one is the one with a defect history.

- [ ] **P3 — the rulebook reads a path the wheel excludes.**
  `tessercheck/adapters/repositories/rulebook_sources.py:15` reads
  `<tree>/tessercheck/tests/test_checks.py`, and `tessercheck.tests` is not in
  the packages list. The path is built from `request.tree`, so it resolves
  against the *analyzed* tree rather than the installed package — which makes
  the rulebook command a checkout-only path. That may well be intended, but it
  is undocumented, and it is inconsistent with the sibling `test_*.py` files
  that do ship. Decide which, then say so.

## Service-conformance wave follow-ups (2026-08-20, v0.0.71.0 ship review)

- [ ] **`ports.add` stores an item the name policy rejected — a policy bypass
  in the exemplar tree (P1, deferred by ruling 2026-08-20).**
  `CatalogService.add` saves unconditionally; only afterwards does
  `mapping.add_response` branch on the verdict and answer blank for
  `RESERVED`. The caller is told "refused" while the row is readable via
  `get`/`list`. Pre-existing (the v0.0.71.0 diff did not change the
  ordering). Every test asserts the response tuple only — none asserts
  nothing was saved (contrast python-app's
  `test_add_link_refuses_a_blocked_destination_and_saves_nothing`). The fix
  needs a contract ruling first: keep the blank-response style or raise like
  python-app — then reshape the service under the TB082 branch rules.
- [ ] **python-app `add_link` consults the policy gateway and the global slug
  index before checking the campaign exists (P2, deferred by ruling
  2026-08-20).** Order today: validate → `policy.check` → `slug_taken`
  (global) → `find`. Consequences: a well-formed id for a nonexistent
  campaign still drives the outbound policy gateway (cost/rate
  amplification), and `duplicate_slug` vs `campaign_missing` leaks whether a
  slug exists in *anyone's* campaign. Moving `find` first flips the error
  precedence two tests pin
  (`test_add_link_refuses_a_campaign_that_does_not_exist` reaches the policy
  today), so it needs its own ruling. Same window: `find` → mutate → `save`
  rewrites the whole record with no conditional write — concurrent
  `add_link`s are last-writer-wins, and `slug_taken` is a TOCTOU against it.
- [ ] **The new ID value objects check non-empty only — a floor, not a
  ceiling (deferred by ruling 2026-08-20).** `ItemID`, errorspy `CampaignID`,
  and `BookingID` validate shape-free because those trees' ids are
  client-chosen opaque strings. A consumer copying them where the id keys a
  filesystem path or datastore should add a format rule — python-app's
  `CampaignID` (16-hex `fullmatch`) is the model. Counter-caveat from the
  same review: python-app's regex encodes the identity *gateway's*
  `secrets.token_hex(8)` format, and only the read/mutate paths enforce it —
  swap the gateway (UUIDs, prefixed ids) and reads break for existing
  campaigns while `create_campaign`/`resolve`/`list_links` keep working.
  When the format question gets its ruling, decide where the format truth
  lives (domain vs gateway) at the same time.

- [ ] **`skills/tesser-build/python.md:403-419` teaches the shape TB082 now
  rejects.** The block tagged `verified impl: examples/errorspy/` shows the
  pre-v0.0.71.0 service bodies, including
  `self._repo.find(...FindCampaignRequest(campaign_id=req.campaign_id))` — a
  raw request field straight to a port, exactly what the provenance clause
  flags. Fix is a materializations pass, not a hot edit: update the snippet to
  the current bodies, walk the row in `rationale/coverage.md`, bump
  `skill-version` (rules in `docs/skill-authoring.md`). Found by the
  v0.0.71.0 doc sweep, 2026-08-20.

## Mapper wave follow-ups (2026-08-17, v0.0.61.0)

- [x] **12 provenance debt markers, and `ports` is the wrong tree to have them —
  RESOLVED v0.0.71.0.** All twelve burned by construction, none by debt marker:
  `ports` gained `ItemID` (and `add` passes the aggregate's own reading to the
  name policy), errorspy gained `CampaignID`, llmport gained `BookingID`,
  python-app's `deactivate_link` validates `values.CampaignID`, and
  `linkpolicy.check` passes through `policy.TargetURL`. A malformed lookup key
  is now a validation error at the constructor instead of a lookup miss — the same
  behaviour change `get_campaign` precedented. Every new ID value object
  validates shape only (non-empty); existence stays with the adapter.
- [ ] **`add_link` carries the body-length debt marker, now at 24 statements.**
  (v0.0.83.0: the is-a mapper took the method to 17 statements — every
  accessor-and-assemble block became one constructor call — and the cap itself
  went in v0.0.72.0, so this entry is history unless the cap returns.) It
  does six things — validate, check policy, check availability, load, mutate,
  save, respond — and the mapper style costs a statement per boundary crossing;
  the v0.0.71.0 caller-side collection assemblies added four more. Either the
  method splits, the read-back goes, or the threshold changes. Ruling (Chris,
  2026-08-19): body length may be excused here for now. `create_campaign` (11)
  and llmport's `confirm` (15) joined the body-length set in v0.0.71.0 —
  the only debt-marker kind left in any service.
- [ ] **`MapToShortLinkSpec` takes the raw request while its neighbours take
  value objects.** `MapToCheckTargetRequest` and `MapToSlugTakenRequest` take
  `values.TargetURL` / `values.Slug`; `MapToShortLinkSpec` takes
  `add_link_request` and reads `.slug` / `.target_url` off the wire. Harmless
  only because `canonical_str` is the identity function today — the moment it
  normalizes, the slug checked for availability and the slug stored diverge.
- [x] **`MapToCampaignSpecFromRecord` trips three mapper clauses — RESOLVED
  v0.0.71.0.** The mapper stopped constructing: it exposes `link_records` (the
  records it was given, passed through) and the *service* assembles the
  `ShortLinkSpec` elements, the `ShortLinksSpec`, and the `CampaignSpec`,
  naming each in a local. The `'active'` literal moved into the service
  comprehension (`link_record.status == "active"`), where originating is
  legal. Same treatment for the other two collection mappers:
  `MapToSaveCampaignRequest` hands the service a tuple of per-element
  `MapToLinkRecord` mappers, and `MapToCampaignView` exposes `link_rows`.
- [x] **`@ts.helper` builds a spec, and it should build any DTO-like object —
  RESOLVED v0.0.66.0.** TB073 now reads "a helper builds a spec or a DTO",
  checked against the new `DATA_BLOCKS`. A helper may not return a Protocol
  (that is `@ts.fake`) nor a domain object (ruling, Chris 2026-08-18: build the
  aggregate from a spec so the construction path runs). Two debt markers in `layout/`
  retired on their own, and the inlined fixtures went back behind helpers.
- [ ] **Only `create_campaign` reads through the query port.** `get_campaign`,
  `resolve`, and `list_links` still load records, rebuild an aggregate through
  `views.campaign_spec` / `required_campaign`, and project it — the over-fetch
  Vernon's use-case optimal query is aimed at, and the reason `list_links` loads
  every campaign to project links. Moving them is what makes the read port earn
  its second consumer, retires three more module
  functions, and drops `Campaign.links` to its last caller (the persistence
  mapper).
- [ ] **`ShortLinks` is declared `ts.Entity` and has no identity.** It is the
  only kind whose rules a collection can satisfy — TB080 requires an entity to
  construct from exactly one `ts.Spec`, which is what forced `ShortLinksSpec`
  into existence and is a good outcome. But a collection is not an entity: it
  has no identity of its own, it is not an aggregate root, and it cannot be a
  value object while it holds mutable entities and `deactivate` mutates in
  place. Declaring it an entity is a kind aliased for mechanical convenience —
  the same class of thing as the `Closeable -> "port"` row flagged in #86.
  Candidate: a `ts.Collection` kind in `tesser.domain`, with its own row in
  `KIND_NAME`/`KIND_ROLE` and its own shape rules (constructs from one spec,
  accessor returns a defensive copy, holds one backing sequence). Needs a ruling
  before more collections are written this way. `python.md:29` already speaks of
  a "collection value object `Labels`", so the vocabulary predates the kind.
- [x] **TB082 counts source lines, not statements — RESOLVED v0.0.62.0.** The
  counter is now `sum(1 for node in ast.walk(fn) if isinstance(node, ast.stmt)) - 1`
  and the clause reads "a service method body is at most 10 statements". The
  threshold stayed at 10: `create_campaign` is seven statements, so there is
  headroom, and tightening it is a separate call with its own evidence. The
  `# tesser:debt TB082` on `create_campaign` is deleted.
- [x] **Nothing forces the mapper shape — RESOLVED v0.0.63.0.** Six TB080
  clauses hold it: MapTo naming, whole-object parameters, no originated
  literals, properties only, `_mapper` on a nested accessor, and never
  constructing what it maps to. Two TB082 clauses hold the service side: a call
  in an argument position, and a declared kind assembled from more than one
  reader. Still no skill doc and no `rationale/coverage.md` row.
- [x] **27 debt markers to burn — the argument-position debt — RESOLVED v0.0.71.0.**
  Every computing-in-an-argument site was converted the way `create_campaign`
  was: the computed value gets a name, the port DTO gets a name, the method
  passes names and readers. The element-construction pair went two ways: the
  save path DID get the per-element mapper tuple (`MapToLinkRecord` — the shape
  this entry predicted would be worse reads fine in practice), and the two read
  paths avoided it by exposing the rows/records they were given for the service
  to assemble. No TB080 or argument-position TB082 debt marker remains anywhere;
  the only service debt markers left are the three body-length ones.
- [x] **Inbound is not symmetric with outbound, and the rules should say so** —
  RESOLVED v0.0.83.0 by dissolving the asymmetry: both directions are now a
  mapper constructor (`MapToCampaignSpec(request, issued, links)` inbound,
  `MapToSaveCampaignRequest(c)` outbound), so N sources is just N parameters
  and there is no assembly step left to be asymmetric about. Original entry:
  Outbound has exactly one source (the aggregate). Inbound has N (the request
  plus whatever the service obtained — identity now, a clock or a policy
  verdict later), so `MapToCampaignSpec` takes three arguments. A GoF builder
  was tried for the inbound half and reverted: `build()` returning `None` plus
  `| None` state cost five completeness guards and a temporal "build first"
  contract that mappers do not have. `ts.Builder` was added and removed in the
  same branch; do not re-add it without solving that.
- [ ] **The `"active"` literals survive — three, now back inside the mappers.**
  `campaign/adapters/handlers/cli.py:48` counts active links for its message
  (handler — ruled out of scope); since v0.0.83.0 the two inbound mappers
  (`views.MapToCampaignSpecFromSlugLookup`, `service.MapToCampaignSpecFromRecord`)
  convert `link_record.status == "active"` inside `super().__init__`, because
  the originated-literal clause went with the accessor mapper and the mapping
  is the one place the collapse belongs. Adversarial note (2026-08-20): the collapse is one-directional
  and *persisted* — any stored status that is not exactly `"active"` (an
  external writer, a case variant, a future third state) reads back as
  inactive, and the next `add_link`/`deactivate_link` full-record rewrite
  stores that collapse; meanwhile the view path passes the raw stored string
  through unvalidated, so the view and the aggregate can answer differently
  for the same record. All of it traces to `ShortLinkSpec.active: bool`. The second
  is the interesting one: `ShortLinkSpec.active` is a bool, so the domain's own
  construction spec is the last place link state is boolean, and that is what
  forced the literal into every translator. A `-> bool` predicate on the entity
  (`ShortLink.is_active()`) was tried and reverted — TB019 forbids it, and the
  ruling (Chris, 2026-08-17) is that TB019 stands and no bools cross the
  boundary.
- [ ] **`skills/tesser-build/testing.md:55` asserts `link.active is spec.active`
  on a `ShortLink`.** The entity exposes `status`, not `active` — the snippet
  was already wrong before this branch. One line, but editing a skill doc means
  bumping `skill-version` and walking the materializations matrix, so it waits
  for the docs pass.

## App/component follow-ups (2026-08-16, PRs #98-#101)

- [ ] **`srv` still holds module functions, and Chris ruled the design has
  none.** `main`, `run_until_signal`, `respond`, `dispatch`, `routes_for`,
  `make_server` — 24 across python-app, layout, and tessercheck-py. bootstrap
  and wiring were converted; srv was not in scope. **Needs a ruling:** is srv
  part of "this design"? If yes it is a host-class refactor.
- [ ] **`App.http` exists under protest.** HTTP config sits on the app only
  because TB052 says a srv module holds only a host class. Either srv gains a
  config kind or the app keeps knowing its transport — which contradicts the
  argument that an app should not presume its own server.
- [ ] **The partial-construction unwind has no test.** It is the one guarantee
  the design kept, and `App(cfg)` building its own components means a test
  cannot observe the components it closed on the way out. Verified by hand
  (patching `LinkPolicy.close`), which TB030 bans in a test.
- [ ] **Idempotent close is undecided.** Hosts call close in a `finally`; a CLI
  that also closes explicitly would double-close. Nothing currently guards it.
- [ ] **The component-close check does not see an inherited `close`.** It scans
  the class body only, so a component subclassing another component and
  inheriting its `close` is flagged despite having one. Narrow: it needs one
  component to extend another, which is itself questionable. The signature is
  already covered — `App.close()` calls `component.close()` with no arguments,
  so a wrong arity fails mypy before the analyzer sees it.
- [ ] **Bare `pytest` fails for python-app outside `scripts/verify`.** The
  config repository encapsulates the environment, so the runner supplies one.
  A developer running `pytest` directly gets a confusing failure in `srv` and
  `bootstrap/test_repository.py`. Options: accept, document, or add a
  pytest-level default (which is a default).

## T8 rename follow-ups (machine-local — meaningless outside Chris's machine)

- [ ] **Local directory rename** — `~/workspace/vero/go-ddd` → `~/workspace/vero/tesser-build`.
  - **Why:** the repo/module/tool renamed in T8 (PR #8); the local path is the
    last stale surface. Path-keyed Claude state (memory dir, session index,
    gstack slug) must move with it.
  - **How:** at a session boundary, run the `claude-project-migration` skill —
    it exists for exactly this. Do NOT rename mid-session.
  - **Then:** re-pin gbrain for the new path (`.gbrain-source` / re-register),
    and fix quanta's `.vscode/tasks.json` relative `../go-ddd` path (valid
    until the rename; re-sweep after).
  - **Risk of waiting:** path-keyed state keeps accumulating; the move gets
    costlier.

## Norm-module wave followups (2026-08-15, PRs #84-#86, Chris flag)

- [x] **Revisit the `("tesser.lifecycle", "Closeable") → "port"` kind-table
  entry** — RESOLVED 2026-08-16 by maintainer ruling: a port is for the
  application; Closeable is not a port, it is the lifecycle contract, its
  own kind. The runtime dropped the `ts.Port` base (Closeable is a plain
  Protocol), the kind table carries `"closeable"` as a distinct block, a
  fake may double it (TB072), and a production class declaring it as a base
  is a finding — production satisfies Closeable structurally. The runtime
  suite pins `Port not in Closeable.__mro__`; the kind-table meta test pins
  that closeable has no KIND_ROLE home. Original flag, kept for the record: (checks.py `TESSER_BASE_BLOCKS`, added in PR #86). Chris flagged it
  as a smell on two axes, to be revisited once the one-test-file workstream
  completes: (1) the design — hand-adding a runtime class to the analyzer's
  kind table is a second source of truth for what tesser-py exports mean, and
  it silently widens what counts as "a port" everywhere (any class extending
  `Closeable` classifies as a port); (2) the process — a rule-shaping change
  like this could be made and merged without an explicit ruling, which is the
  same class of gap the "every classification earned" test exists to close.
  Candidate directions when revisited: derive the kind table from tesser-py
  itself instead of a hand-list; or narrow the entry to the TB072 fake check
  rather than global classification; or require kind-table rows to carry a
  ruling reference the same way `.tesser-root` carries tree facts.

## TB083 spec-use follow-ups (2026-08-24, v0.0.80.0 ship red team)

- [ ] **An orphan spec — one no `__init__` takes — is reported nowhere useful.**
  Every read of it is a TB083 finding whose message asks for an owner that
  does not exist. A finding on the spec itself ("taken by no `__init__`; a
  spec constructs exactly one object") was built and pulled: 11 analyzer
  fixtures sketch throwaway specs, and the ruling was not asked for. Rule on
  it; the code is one block in `_spec_shared_violations`.
- [ ] **A subclass that takes its base's spec is reported as a second taker.**
  `class Sub(Base)` with both `__init__(self, spec: SSpec)` fires "a spec
  constructs exactly one object" — decide whether one lineage counts as one
  object.
- [ ] **Tuple-unpack from a maker returning `tuple[XSpec, XSpec]`, `[spec][0]`,
  and `{'k': spec}['k']` are untyped** — "bind it to something else first" is
  a general escape alongside the dict/`*args` items above.
- [x] **Container-typed spec parameters never enter the tracked set — RESOLVED
  v0.0.81.0.** `_spec_key` types `tuple`/`list`/`Sequence`/`Iterable` of a
  spec as a many-typed name; a `for` loop (plain or `enumerate`), a
  comprehension target, or a subscript over it binds the element, so
  `specs[0].value` and `for s in specs: s.value` are findings. Still open:
  `*args: XSpec` / `**kw: XSpec`, and `dict[str, XSpec]` values.
- [ ] **Tracking is flow-insensitive.** One rebinding anywhere in a function
  (`if flag: spec = 'plain'`) drops the name for the whole function, so a
  later genuine `spec.value` is missed — the deliberate price of the
  `for`/`with`/`except` false-positive fix; a per-branch model would close it.
- [ ] **A closure or lambda defined inside a domain `__init__` inherits the
  constructor's licence.** `def later(): return spec.value` stored on `self`
  keeps the spec alive past construction and is not reported; so does
  `lambda s=spec: s.value`.
- [ ] **A local name that collides with a module-level maker is read as the
  maker.** `build = lambda: 3; self._n = build()` fires a keep; `makes_spec`
  has no scope check against the function's own bindings.
- [ ] **Returning or yielding a spec from a method is neither a keep nor a
  read.** TB015 covers a spec returned by a domain object's public method
  only through its annotation; a bare `return spec` from an adapter method is
  covered by nothing — settle which rule owns the exit.
- [ ] **A non-maker call that takes the spec whole is silent by design**
  (`functools.partial(f, spec)`, `helper(spec)`) — that is what keeps
  `Tag(spec)` legal. `dataclasses.asdict`/`copy.copy` are read as `__dict__`
  by name; `.append`/`.extend`/`.insert`/`.setdefault` are keeps by name,
  while `.add`/`.update` are not, because `self._links.add(spec)` is how a
  domain collection consumes a spec (python-app `Campaign.add_short_link`) —
  a `set.add`/`dict.update` store is therefore silent; a wrapper allowlist is
  the open question.
- [ ] **Within one line, findings come out in reverse source order.** The
  sort key is the line only; `Violation` carries no column.
- [ ] **`SpecRef.one()`/`.many()` rebuild the `Symbol` from `str()`** (v0.0.82.0
  adversarial review). `Text.__str__` is `serialization.canonical_str`, a
  display hook; identity is rebuilt from display, which convention 3 forbids.
  Latent: `canonical_str` is the identity function today, so the round-trip
  holds and the whole-tree fuzz found no difference. Closing it collides with
  two rules — TB080 (a spec field is a primitive or a spec, never a built
  `Symbol`) and TB083 (a value object keeps no spec) — so it needs a ruling on
  how a compound value object re-enters its constructor with one component
  changed, not a one-line edit.
- [ ] **Two `__init__` definitions in one class taking different specs tie on
  the `_spec_shared` sort key** (`entry[:3]`, because `Symbol` is not
  orderable); the two findings at that line keep insertion order where the
  tuple sorted them by spec name. Degenerate input; nothing pins the order.
- [ ] **Twelve walk branches execute under the suite but no assertion pins
  them** (v0.0.82.0 coverage audit, mutation-tested; all pre-date the
  `SpecRef` change): maker-method name collision on the same spec and on a
  different spec (`checks.py` `returning`); a many-shaped `__init__`
  parameter must not register an owner; two second-takers in one module and
  their finding order; `tuple[tuple[XSpec, ...], ...]` yields no ref;
  `spec.kids.greeting` / `spec.kids.name` / `copy.copy(spec.kids)` must not
  resolve or read; `spec['k'].name` on a one-shaped owner; `spec.kids[1:]`
  keeps the many shape; a plain `for k in spec.kids: self._n = k.name`; a
  `for` over a one-shaped spec binds nothing; and the `taken.shape() ==
  SPEC_ONE` clause in the TB080 constructor rule, which a neutering mutant
  survived and looks redundant with the `Name`/`Attribute` clause after it.

## Mapper is-a wave follow-ups (2026-08-25, v0.0.83.0)

Ruling (Chris, 2026-08-25): a mapper is its target — `class MapToXSpec(ts.Mapper,
XSpec)`, one `super().__init__`, nothing stored, no other method — and the service
reads `Campaign(MapToCampaignSpec(...))`. The accessor mapper (v0.0.61.0–v0.0.71.0)
is gone. Recommendations 4–6 of that discussion were NOT taken in this wave and
wait for a ruling:

- [ ] **Decisions still live inside mappers.** `MapToShortLinkSpec` (python-app)
  matches on the policy verdict and the slug availability and raises `conflict`;
  `MapToCampaignSpecFromRecord`, `MapToCampaignSpecFromSlugLookup`,
  `MapToCampaignView` (python-app), `MapToCampaignSpec` (errorspy) and
  `MapToBookingSpec` (llmport) match on a lookup outcome and raise. A spec
  constructor raising a domain conflict hides the refusal inside a constructor
  call; a service that reads like a book would show "blocked destination →
  conflict" as its own statement. Recommendation: a mapper never raises; the
  outcome `match` moves back into the service as a statement. Blocked on the
  TB082 re-cut below, because a `match` on a port response field is not "a
  single call" today.
- [ ] **TB082's remaining clauses were written for the accessor mapper.** The
  one-mapper-assembly clause is gone with this wave. "Names a straight
  accessor", "computes in an argument", and "match subject is a single call"
  stay; the second is what makes `Campaign(MapToCampaignSpec(...))` legal (a
  mapper is a declared kind), the third is what keeps the outcome matches in
  the mappers. Re-cut with the decision above.
- [ ] **A domain method's parameters have no rule.** TB019 governs returns
  only; `Labels.get(key: str)` (python-app) takes a primitive and nothing
  reports it. Mirror clause: a domain object's public method takes a value
  object, an entity, or the spec it forwards whole.
- [ ] **"Stores nothing" reads `self.x = …`, `self.x: T = …`, `self.x += …` and
  any `.__setattr__(` call.** `setattr(self, …)`, `self.__dict__[…] = …`, and
  `vars(self)[…]` bypass it; a nested function assigning to `self` inside
  `__init__` is walked and caught, a lambda is not a statement and cannot.
- [ ] **A mapper's second base is checked by block, not by name.** Any class in
  `DATA_BLOCKS` qualifies, so `class MapToThing(ts.Mapper, SomeRequest)` in a
  *domain* module would classify; the role rule (a mapper's home is
  `application`) is what stops it, not the mapper clause.
- [ ] **The name clause is `target_name in cls.name`.** `MapToItemViewX` and
  `MapToXItemView` both pass; the intent is `MapTo` + target + optional
  `From…` suffix, and the substring check is looser than that.
- [ ] **A mapper still accepts a child spec parameter it never reads**, e.g.
  `MapToCampaignSpec(..., links: ShortLinksSpec)` forwards it whole. TB083
  covers the read; nothing says the parameter must be used at all.

## Module-only imports wave followups (2026-08-24, branch `worktree-imports-module-only`)

- [ ] **A parameter or local that shadows a module alias has no rule.** Six
  live handler sites bind a parameter `client` over `import <ctx>.client.client
  as client` (safe today: annotations are strings and bodies use the alias
  only in unshadowed methods); `service.py` dodges the same collision by hand
  with `import kernel.slug as kernel_slug`. TB033 covers builtins only, and
  `Module._resolve` maps `name.Attr` to the alias with no scope analysis. A
  shadowing rule over module aliases would make the convention enforced.
- [ ] **A package `__init__` re-export that shares a submodule's name shadows
  the submodule at `import a.b.c as c`** (`tesser.srv.main`,
  `tesser.testing.fake`/`helper` — the function is bound, not the module;
  `mypy --strict` accepts it). Zero live instances after the migration; the
  sibling tests import the package instead, which TB074 pairs by filename
  only. A rule that a re-exported name never equals a submodule name would
  close it.

## Import-totality wave followups (2026-08-06, branch `worktree-io-import-restrictions`)

- [x] **python-app conformance + remove the sigcheck CI ratchet** — RESOLVED
  2026-08-12 (zero-findings wave, merge-plan PR 4b). The ~104 member-form
  imports converted to aliased module imports, the srv/bootstrap functions
  declared with `@ts.function`, and the missing `tesser.*` imports added;
  the ratchet script and baseline are deleted and the CI step is a plain
  zero-findings gate. The ruling-blocked residue is now 20 site-level
  debt markers instead of baseline entries, each still tracked by its own
  open item below: 3 homeless modules (TB040 debt-file), 2 tests-package
  helper modules (TB041 debt-file, conftest-governance followup), 6
  host-machinery/bootstrap classes (TB051/TB052 — the `tesser.app`
  question), 2 type aliases with no conformant spelling (TB051, the alias
  hard collision), 2 `if __name__ == "__main__"` guards (TB051 — a
  module-level `if` has no conformant form), 15 pure-core imports (TB062 —
  the allowlist candidates), and 1 shape test importing `tesser.context`
  (TB050). Burning a debt marker = resolving its ruling; TB090 keeps the set
  honest.
  The hard-collision detail preserved from the ratchet era: an exception
  must subclass `Exception`, so a declares-its-block rule has no satisfiable
  form for wire exception classes (the `ts.Error` track), and the only
  analyzer-clean alias spelling (`JSONObject: Final = ...`) is rejected by
  `mypy --strict` [valid-type] — verified 2026-08-07. Those carry debt markers
  until their rule changes land.
- [ ] **Host-class vocabulary — PARTIALLY RESOLVED (srv-wire-vocabulary wave,
  2026-08-07).** `tesser.srv` now exists (Host, Port, Record, Request,
  Response — package-scoped kinds per the errors-ruling grammar; `Record`
  joined in the srv-matrix wave; `tesser.app` was deliberately left out as
  a real open question) and sigcheck admits declared host classes in srv
  modules plus wire kinds in `*wire.py` wire modules.
  Still open: host machinery that is not itself a host (`Route`, `Match` —
  and whether `HttpHost` just declares `ts.Host`), and the whole `tesser.app`
  half (`App`, `Config`, `HttpConfig`, `CleanupStack`).
- [x] **Homeless root modules — RESOLVED v0.0.29.0 (import-totality wave,
  2026-08-12).** The ruling: app-level shared modules stay at the root, the
  `tesser:debt-file TB040` is their declaration, and TB065 governs their imports —
  a root module is a leaf that imports nothing from its tree. The pure-core
  half (domain importing `errors`/`serialization` under TB062 debt markers) stays
  with the allowlist-candidates item below. (`cliwire`/`httpwire`/`voicewire`
  left this list in the srv-wire-vocabulary wave: a top-level `*wire.py` is a
  governed wire module — imports `tesser.srv` exactly once as ts, holds wire
  kinds, is context-generic, and never imports srv or bootstrap.)
- [x] **Pure-core allowlist candidates (from dogfood evidence only):**
  RESOLVED 2026-08-24 (module-only imports wave): `urllib.parse` and `copy`
  admitted to the default; their three `# tesser:debt TB062` markers are
  burned. The default is now a recommended default, widened per tree by
  `stdlib <module>` lines in `.tesser-root`. The `secrets` half is
  RESOLVED v0.0.61.0: it was injected through the `CampaignIdentity` port
  rather than admitted, and the service's `# tesser:debt TB062` is
  deleted — the outcome the entry predicted.
- [ ] **Named soundness holes in the import walker (from the ship adversarial
  reviews — evasion paths, none live on the current trees; relative-import
  resolution and top-level-only classification were fixed in-wave):**
  (1) RESOLVED v0.0.29.0 (import-totality wave): the `conftest` and
  `__main__` exemptions are gone — a conftest carries its location's row (a
  leaf at the tree root, a test tier's reach inside a tests location), and a
  context `__main__` composes from its own application, adapters, client,
  and wiring (TB063) — that classification was deleted in v0.0.33.0 (issue
  #75): a context `__main__` is a stray module (TB041), and an app is entered
  through a host in `srv/`. (2) RESOLVED 2026-08-11 (harness wave):
  `FilesystemSourceReader` prunes the standard skip set (`.venv`, `build`,
  `node_modules`, …), and an unparseable module, a non-UTF-8 file, or a
  module defined twice is a per-file TB043 finding instead of a crashed
  run. (3) MOOT 2026-08-12: the ratchet is deleted — the zero-findings wave
  replaced the baseline with site-level debt markers, which are reviewed in the
  diff like any code and self-report when stale (TB090). (4) quoted
  annotations (`money: 'domain.Money'`) bypass every classification-based
  rule — the exact bug class PR #44 / v0.0.13.1 fixed in tessercheck-py with
  one shared walk; sigcheck needs the same treatment. (5) `async def` is
  invisible to totality — it is neither a declarable function nor a class,
  reads as a loose statement, and evades the def-gated presence checks.
  (6) `TYPE_CHECKING` blocks and `try/except ImportError` optional imports
  have no conformant form (module-level `If`/`Try` are loose statements).
  (7) RESOLVED v0.0.30.0 (classifier-totality): the reader's `is_package`
  bit is a parameter of `_locate`, and the package/module split per location
  is pinned by the classification table in
  `tessercheck-py/tessercheck/tests/test_locate.py`. (8) `__import__`/
  importlib evade the pure-core allowlist (statically unpreventable at
  reasonable cost — accept and note). (9) a member import from a re-export
  `__init__` (`from rel.domain import Money`) does not classify — blocks
  propagate from defining modules only, so signature rules go quiet; either
  propagate through re-exports or rule that deep imports are canonical.
  (10) srv/bootstrap have no external-import allowlist, and a constants-only
  module can do import-time IO (`OUT: Final[bytes] = subprocess.check_output`)
  with zero findings — fold into the host-vocabulary ruling.
  (11) RESOLVED 2026-08-24: `TOOLING_MODULES` was deleted in v0.0.29.0, and
  the allowlist now has its per-consumer surface — `stdlib <module>` lines in
  `.tesser-root` widen `CORE_STDLIB["domain"]` for that tree (validated as a
  real stdlib module, not a repeat of the default, and used). The `ast`
  entry stays in the shipped default on the original evidence.
  (12) a top-level FILE sharing a context's name (context package without
  `__init__.py` + `<context>.py` beside it) falls through to
  `_context_init_violations` and is mislabeled "__init__ declares code" —
  the `len(parts) == 1` ⇒ package-init assumption predates wire modules
  and is no longer safe (adversarial 2026-08-07).
- [ ] **Graduate the srv/wire vocabulary into the skill docs** (opened
  2026-08-07, v0.0.18.0 doc sweep). `skills/tesser-build/python.md:600-619`
  and `:773-803` still teach `httpwire`/`cliwire` as frozen dataclasses with
  `Endpoint = Callable[...]` aliases — the pre-shell idiom — while
  `examples/python-app` now uses `ts.Request`/`ts.Response`/`ts.Port` +
  `@ts.function`. Deliberately not updated in-wave: skill docs encode only
  verified-implementation-backed rulings, and teaching `tesser.srv` needs
  the `rationale/coverage.md` walk + `skill-version` bump. The srv-matrix
  core landed in code 2026-08-07 (frozen ts.Record + behavior-carrying
  wire records + the tool binding table), so the taught shape is now
  live-verified in both example trees — graduation waits only on Chris
  confirming the enacted rulings (wire-vocabulary entry below) and on the
  wire-module governance items that could still move module-level shapes.
  The graduation pass must also re-verify every `verified impl:` file:symbol
  pointer in the skill docs, not just the code samples —
  `skills/tesser-build/srv.md:200` already dangles (`test_httpwire.py:
  content_length` was renamed to `buffered_length` in the srv-matrix wave).
  Scope re-measured 2026-08-08 (doc-release sweep): `python.md:598-794`,
  `handlers.md:47-98`, and `srv.md:138-219` present `json_response`/
  `problem`/`respond`/`decode_body`/`content_length`/`path_param` as free
  functions — roughly 30 lines of sample code the wave deleted, in a skill
  distributed copy-in to consumers. `testing.md:266` is a fourth site: its
  "rename in helper's clothing" anti-pattern is written as
  `def json_body(resp): return decode_body(resp.body)`, which now names a
  deleted function AND collides with the real `Response.json_body` reader
  (see item (c) of the wire-vocabulary entry below, which already rules the
  distinction) — rewrite the illustration, don't just rename the call.
  Root `README.md:106-121` and `CLAUDE.md:8` both under-describe tesser-py
  (each names only `tesser.domain.ValueObject`, while the package ships
  `adapters`, `application`, `context`, `domain`, `srv`, and `testing` —
  pre-existing narrowness, widened by every srv wave; fold in here).
- [x] **Make rules.py conformant — RESOLVED v0.0.29.0 (import-totality wave,
  2026-08-12).** `TOOLING_MODULES` is deleted; `rules.py` is a root module
  like any other — `tesser:debt-file TB040` declares it, TB065 governs its
  imports (stdlib only — passes), the universal checks run on it (its one
  docstring is removed), and it appears in RULES.md's homeless-module row.
- [x] **conftest governance — RESOLVED v0.0.29.0 (import-totality wave,
  2026-08-12).** A tree-root conftest is a TB065 leaf; a conftest inside a
  tests location carries that location's TB070 row. `tests.discovery` /
  `tests.support` keep their TB041 debt-file markers but now answer for their
  imports under the root-tests tier; `tests.test_shape`'s `tesser.context`
  import keeps its explicit TB050 pin.
- [ ] **Test-module annotation.** When tests declare themselves, flip
  "a test module imports tesser.testing at most once, as ts" to exactly-once.
- [ ] **Wire vocabulary — what the srv-matrix build wave left open**
  (re-cut 2026-08-07 after the srv-only build wave; Chris directive: build
  each option, let the code rule). Items (1)-(3) of the original smells
  entry are ENACTED IN CODE, each with its ruling recorded where it was
  made: (1) wire records carry behavior — `problem`/`json_response`/
  `redirect`/`respond` became Response classmethods, `decode_body`/
  `path_param`/`content_length` became HttpRequest readers (bag 9→2 public
  in httpwire, 4→0 in cliwire; the DTO-purity collision dissolved by the
  package-scoped kind grammar — context DTOs stay data-only); (2) the tool
  declaration became wire-side data — `ts.Record` is the new generic
  wire-record kind, `voicewire.Tool` its first instance, and the handler
  owns one binding table deriving dispatch + schemas (the three parallel
  string-keyed chains are gone); (3) immutability + value equality returned
  per-kind on `ts.Record` (VO-style frozen beat write-once — the
  losing arm and its smuggling hole are pinned in
  tesser-py/tesser/srv/test_record.py). STILL OPEN, needing Chris:
  (a) **the tool declaration as a context-side CLASS** (his original
  "declared tool object" shape) needs a new ADAPTERS kind — outside the
  srv-only scope; the sigcheck probe walls are recorded verbatim in
  examples/llmport/README.md. Rule whether the data-table shape
  stands or an adapters Tool kind is worth the vocabulary. Partly answered
  2026-08-08 by the routing move: with `dispatch` gone from the handler,
  what remains per tool is an endpoint method plus a schema declaration,
  so the "tool object" a class would have held is now split across the
  handler (invoke + schema) and the srv route table (name -> endpoint).
  (a2) **A wire record is a value object on the wire** (Chris framing
  2026-08-08). `Record` currently does two jobs: the shared frozen/equality
  mechanics base for Request/Response, and a declarable kind in its own
  right. Only the second is under-justified, and it is what creates (f).
  If the concept is "a value that appears on the wire but is not itself a
  message" — Tool, Route — then it wants that name and its own row, with
  the mechanics base staying undeclarable. Related: wire records are NOT
  context DTOs (context-generic, transport-shaped, different rate of
  change, and the handler exists to translate between them) and NOT domain
  VOs (an HttpRequest must be constructible from whatever arrived).
  (a3) **Wire-record construction should be one spec in, then instance
  methods** (Chris ruling 2026-08-08). `Response` currently has FOUR
  construction paths (`json`/`problem`/`redirect`/`respond`) where the
  repo's own rule — enforced for domain constructors as "takes exactly one
  ts.Spec" — is one. They passed only because wire kinds carry placement
  and import rules but no signature rules. Two of them are not even
  construction: `respond(run)` is an exception->Response policy mapper, and
  `json`/`problem` are "construct from a different input shape", which is a
  spec's job (the MoneyAmount("10.00") precedent parses in the
  spec-taking constructor). Extending the one-spec rule to wire kinds is a
  matrix rule change, so it was not folded into the srv-matrix wave.
  Narrowed 2026-08-08 (conformance sweep): `respond` is GONE from every
  response record — exception mapping is host policy now (srv/http/host.py,
  srv/cli/main.py, agent.py) — and constructor defaults are gone from all
  wire records. What remains of (a3) is the construction-path question alone:
  HttpResponse.json/problem/redirect and CliResponse.ok are
  construct-from-another-shape classmethods still awaiting the one-spec
  ruling; ToolTurn has none.
  (b) **`Endpoint`/`Command`/`ToolSurface` stay anonymous-`__call__`/named
  wire ports** — untouched this wave; if the position-naming convention
  needs more than the `Endpoint` precedent, that's a matrix row.
  (c) **`Response.json_body` knowingly resembles the deleted test-helper
  alias** (CHANGELOG once removed `tests/wire.py`'s `json_body` as a
  rename-in-helper's-clothing). Kept deliberately: it is the record's own
  reader mirroring `HttpRequest.json_body`, and its test-only callers are
  tests playing the HTTP-client role — not a test-local rename. Don't
  re-delete it without ruling the reader question.
  (d) **The one-shot construction guard forbids a multi-level record**
  (adversarial 2026-08-08): a child record cannot add its own fields via a
  second `Record.__init__` call, and a subclass that sets a derived field
  before `super().__init__()` gets "already constructed", which names the
  wrong problem. No in-tree record does either. Rule whether multi-level
  records are wanted before a consumer needs one. Related, same guard: the
  field check is one-directional (undeclared names are refused, declared
  ones are not required), so a subclass that conditionally omits a field
  still builds a partial record — it cannot be made strict without a
  declaration for the `object.__setattr__` derived-field idiom. And a
  record with NO fields is re-initializable (verified 2026-08-08, doc-release
  sweep): the guard reads a populated `__dict__`, which an empty record never
  has, so `r.__init__()` succeeds a second time. No in-tree record is
  field-less; same ruling covers it.
  (e) **The confirm_booking tool schema omits `required`** — restored to
  main's byte shape this wave (the refactor had silently added
  `"required": []`). OpenAI strict-mode function calling wants the key
  present even when empty, so if the spike ever runs against strict mode,
  rule which shape the provider gets.
  (f) **`ts.Record` admits direction-less wire declarations** (red team
  2026-08-08, verified): WIRE_KINDS is derived set arithmetic, so a wire
  module may declare every record as `ts.Record` — including Endpoint
  `__call__` parameter/return positions — and satisfy totality without
  ever committing to request vs response. Rule whether those positions
  require a directed kind, or record that the direction kinds are
  advisory and Record is the general case. Narrowed 2026-08-08: voicewire
  now declares its inbound message (`ToolCall(ts.Request)`, name + frozen
  arguments; endpoints are `(ToolCall) -> ToolTurn` like HTTP and CLI),
  so no in-tree wire module leaves a message direction-less anymore — the
  rule question is whether sigcheck should require that.
  (g) **A protocol module has no import allowlist** (survives from the
  2026-08-07 "least-governed home" adversarial item; the SUFFIX half was
  RESOLVED 2026-08-08 by the protocol-package ruling — membership in the
  top-level `protocol/` package is the declaration, so `firewire.py`/
  `tripwire.py`/`serdepy/wire.py` no longer opt into anything and
  `git mv shop/domain.py bizwire.py` lands homeless, not governed-lite).
  What remains: no CORE_STDLIB-style allowlist — a protocol module
  importing subprocess/boto3 gets zero findings, and bootstrap importing
  a protocol module is unconstrained. Evidence for the allowlist: after
  the conformance sweep all three protocol modules import only stdlib +
  tesser — errors.py left them with `respond` — so the allowlist would
  just record what the trees already do.
- [ ] **A role `__init__` re-export defeats the classifier** (found while
  splitting llmport's application.py into a package, 2026-08-08).
  RULES.md sanctions "a role __init__ only re-exports from its own role", but
  `resolve()` does not follow a base class through the re-export: with
  `scheduling/application/__init__.py` re-exporting `SlotDirectory` from
  `service.py`, every `@ts.fake` subclassing `application.SlotDirectory` drew
  "implements no application port, wire port, or client" — five false
  findings on a conforming tree. Worked around by emptying the `__init__`
  and importing submodules directly, which is what python-app already does
  (its `campaign/application/__init__.py` is empty) — so the sanctioned
  shape is one no tree in the repo can actually use. Either teach the
  classifier to follow re-exports or stop sanctioning them.
- [x] **sigcheck internal cleanups — RESOLVED 2026-08-11 (cleanup-batch wave)
  except item (7), which stays open below.** What landed, and the shapes the
  constraints forced: (1) one `_tesser_import_violations` covers all five
  exactly-once-as-ts sites (bootstrap/srv/protocol/role/test) — clause texts
  are passed as positional literals at each call site because the RULES.md
  generator binds call-site string constants into message holes, and the
  test row passes `absent_clause=None` to keep at-most-once semantics (the
  generator skips the never-imports row for a None binding); the
  statement-totality loop is one `_statement_violations`, with each caller
  keeping only its own ClassDef branch; (2) `ImportEdge` and `TesserImport`
  are `ts.ValueObject`s, NOT NamedTuples — a NamedTuple class declares no
  ts.* base and a type alias has no sigcheck-clean spelling (the documented
  alias hard collision), so the domain shape was the only conformant one;
  `alias: str | None` also has no conformant VO field form, so the slot is
  `as_ts: bool`, which is honest for from-edges (a from-import is never the
  module aliased as ts); (3) the `"tesser"` root comparisons are the
  `TESSER` constant; the package strings (`tesser.context` etc.) stay as
  call-site literals by design — the generator needs them literal to render
  rows; (4) legality sentinel → explicit `denied` list in
  `_import_violations`/`_app_import_violations`; (5) rules.py derives the
  conftest/`__main__` bullets from the `_module_violations` AST guards
  (`ungoverned_basenames`, cross-checked against `UNGOVERNED_PROSE`) —
  since deleted in v0.0.30.0, dead once v0.0.29.0 emptied the exemption
  list, so RULES.md's Named exemptions section is now static prose — and
  the TOOLING_MODULES not-found/wrong-shape errors are split; (6) `Module`
  freezes every accessor collection in `__init__`. One cosmetic RULES.md
  diff: the bootstrap module-contents row's two shapes swapped order.
- [ ] **sigcheck rule-coverage meta-test is clause-granular, not
  branch-granular** (item 7 of the cleanup batch, kept open) — branches
  sharing a clause collapse into one RULES.md row, so a fixture covering one
  branch reports the row covered (found 2026-08-07; all such branches were
  probed correct, so this is a guard-precision gap, not a bug). Unchanged by
  the extraction wave: clauses are parameterized per call site, so each
  caller still renders its own rows — the collapse is still branches WITHIN
  one row (again/from-names/no-alias share a clause), same as before.
- [x] **Two clauses claim more than the code enforces** — RESOLVED 2026-08-06,
  Chris ruling: "the code should enforce what I specified." The code moved,
  not the wording: (1) presence is unconditional — every role and
  srv/bootstrap module carries its `import tesser.* as ts`, constants-only
  and empty files included (the `__init__` files stay under their own total
  rules: context/tests/srv-bootstrap inits empty — the srv/bootstrap
  emptiness rule is new — and role inits re-export-only; test modules keep
  at-most-once per Chris's earlier blessing, pending test annotation).
  (2) `from . import client` now records as a member-form import and fires
  the aliased-module rule; the only conformant context-module form is
  `import <context>.<role> as <alias>`. Role-`__init__` dispatch now keys on
  the reader's `is_package` bit instead of the child-name prefix, closing
  soundness hole (7) below.

- [x] **Shared debt-marker namespace during the merge transition** —
  RESOLVED 2026-08-12 (ports wave): TB030 ported into sigcheck, its
  fixture-param finding lands on the def line python-app's four markers
  sit on, so the markers are load-bearing again and the four TB090
  baseline entries burned off (ratchet 152 → 148).
- [x] **Shells-substrate re-derivation ruling — RESOLVED by Chris ruling
  2026-08-12: "value objects only return other value objects", no tooling
  exemption.** Landed in the shell-norms wave: TB010–TB012 and TB015–TB019
  enforce on every ts.* tree; the analyzer's own Violation decomposed into
  Path/Line/Code/Text leaf VOs with canonical_str/canonical_int policy
  exits, the finding renderer moved from Violation.__str__ (a banned
  compound exit) to the application service composing from leaves, internal
  records (ImportEdge/TesserImport/Debt/Comment) wrapped their slots and
  dropped their public accessors (same-module attribute reads — the rules
  judge public surface, and nothing outside the domain touches them), and
  llmport's Booking exposes Step/CustomerName/Slot leaves with the
  ""-for-None mapping at the views boundary. Entity BARE field accessors
  (Module.name() -> str) remain unjudged — the reference analyzer had the
  same carve-out (bare returns route to TB010/TB011, which are VO/mutable
  scoped); if the ruling should reach those too, that is a new rule, not
  this port. TB031 still carries separately. One reference shape is NOT
  ported and is named debt: TB015's emit-a-sink half (a public `-> None`
  method streaming private fields into a sink parameter — the reference's
  `_emits_private_field`); the port covers the spec-return and
  conversion-dunder halves. Port it or rule it out of contract when the
  serialization norm gets its shells re-derivation pass.
- [ ] (superseded — kept for the original framing) **the remaining tessercheck
  ports** (opened 2026-08-12, ports wave — blocks merge-plan PR 3b).
  TB010–TB012, TB015–TB018, and TB019 were derived on the frozen-dataclass
  substrate, and their core terms do not transfer to the shell idiom
  without rulings: (a) TB010/TB019 ban primitive exposure and primitive
  returns, but every shell VO in the gated trees exposes its slots through
  accessor methods — sigcheck's own `ImportEdge.target() -> str`,
  `Violation.path()`, `Module.name()` would all be findings, so either the
  analyzer's domain wraps every slot in VOs, or accessors get a ruled
  exemption class, or the norm stays consumer-domain-only; (b) TB015's
  leaf/compound discrimination counts annotated fields, and a shell VO's
  private `_x` annotations make `Violation` a four-field compound whose
  `__str__` — the finding renderer itself — would be a banned conversion
  dunder; (c) TB018's canonical_* policy helpers do not exist in any shell
  tree. Decide the shell-substrate meanings first (what is a field, what
  is a leaf, which exits are licensed), then port; porting first would
  bury the decision under a pile of inline opt-outs. TB031's tree-scope
  contract (`testdata/tb031/`) carries over unchanged whenever its
  implementation lands.

- [x] **The final coupled wave — REMAINING HALF (serdepy/errorspy +
  legacy retirement).** Landed 2026-08-12 in two waves. First (docs wave):
  `python.md` rewritten
  onto the shells end to end (every code block mirrors
  `examples/python-app`; the srv/wire vocabulary graduation item is folded
  in), `examples/python` DELETED — its two unique derivations found shell
  homes (`Money` was already `python-app/campaign/domain/money.py`;
  `Labels` ported as `python-app/campaign/domain/labels.py` with a sibling
  test), every doc reference repointed (testing/serialization/comments/
  public-interface/coverage/CLAUDE/READMEs), the roadmap registry's
  py_example rows repointed and ROADMAP.md regenerated, the legacy
  analyzer's acceptance gate and tree-fixture classification test retired
  with the tree, and skill-version bumped to 30. Second (retirement wave,
  same date): `examples/serdepy` and `examples/errorspy` migrated to
  shells (serdepy as a `parcel` context; errorspy as a `campaign` context
  with every norm-proof assertion preserved), `tessercheck-py-legacy/`
  DELETED with its verify tree and CI job (the TB031 fixture pair moved
  to `tessercheck-py/testdata/` with a divergence guard),
  `roadmap/generate.py`'s py_check_codes repointed at the graduated
  analyzer's `rules.py` extraction with the registry claiming all 34
  codes, and the `rationale/coverage.md` Python column reworked onto the
  shell-declared analyzer.
- [x] ~~superseded framing~~ **tree migrations + legacy deletion + docs
  sweep as one unit** (scoped 2026-08-12 after the shell-norms wave; deferred
  together per Chris — "leave skill docs for later"). These cannot land
  separately: `skills/tesser-build/python.md` teaches from
  `examples/python` (9 path references), `serialization.md` from
  `examples/serdepy`, and migrating the trees to shells while their
  teaching docs still show the frozen-dataclass idiom breaks the
  docs↔example sync (and the roadmap living-surface link gate).
  Contents, in order: (1) migrate `examples/python`, `serdepy`,
  `errorspy` (and rule whether `examples/python`'s catalog/campaign
  frozen-dataclass example survives at all now that python-app is the
  canonical shell example — spike-shells is retired); (2) delete
  `tessercheck-py-legacy/` + its verify tree + CI job; (3) rework
  `roadmap/generate.py`'s py_checks registry import (it reads the legacy
  `CHECKS`; the new analyzer's registry is RULES.md); (4) the skill-docs
  sweep (python.md onto shells, srv/wire vocabulary graduation from the
  earlier TODOS item, coverage.md rows, comments.md/serialization.md/
  testing.md path retargets) with the `rationale/coverage.md` walk and
  the `skill-version` bump; (5) CLAUDE.md's convention section rewrite.

## Toolkit

- [x] **ValueObject-shape adoption decision + classifier support** —
  **DECIDED 2026-08-16 (Chris): `ts.ValueObject` supersedes the
  frozen-dataclass idiom, and the toolkit ships no dataclass at all.** The
  reason is measured, not stylistic: mutmut skips a decorated class
  wholesale, so the dataclass idiom and everything written inside it is
  invisible to mutation testing (`tesser-py/tests/ecosystem/mutmut/` asserts
  both halves). Both follow-ups were already satisfied when the decision
  landed — the classifier maps `("tesser.domain", "ValueObject")` to
  `valueobject` (`checks.py:21`), so `TB010`–`TB014` and the serialization
  norm see the shape; `skills/tesser-build/python.md` teaches `ts.ValueObject`
  with no dataclass mention; `rationale/coverage.md` already records the
  dissolved dataclass-era rows. Closed out by correcting the record:
  `README.md` (which still called the dataclass the taught convention),
  `docs/design-python-analyzer.md` (marked superseded on the substrate
  question), and `tesser.errors` (the last shipped dataclass, removed).

- [ ] **Move the rest of the repo off dataclasses** (the target Chris set
  2026-08-16 alongside the adoption decision). The distribution is clean;
  these remain, and each is a real question rather than a mechanical swap:
  - `examples/python-app/bootstrap/config.py` (2) and
    `tessercheck-py/bootstrap/config.py` (1) — app-level config aggregation.
    Each already carries `# tesser:debt TB051`, because a bootstrap
    module holds imports, declared functions, and Final constants — **no
    class at all**. So the fix is not a different base: either the app-level
    config moves out of bootstrap to a home where a class is legal, or
    TB051 grows a declared config kind. Going off dataclasses here *deletes*
    suppressions, which is the sign the direction is right.
  - `examples/python-app/srv/http/router.py` (1, `# tesser:debt
    TB052`) — a `Route` record in a srv module; same shape of question.
  - `roadmap/generate.py`, `examples/spike-totalreturn/probe.py` — a
    Go/Python hybrid tool and an ungated spike; lowest stakes.
  - **Deliberately keep:** `tesser-py/tests/ecosystem/mutmut/fixtures/dcvo/`
    (the negative control — it exists *because* it is a dataclass) and
    `tessercheck-py/testdata/tb031/` (analyzer fixtures under test).

- [x] **`examples/python-app`'s Money accepts non-finite amounts — RESOLVED
  2026-08-17 (v0.0.59.0).** `MoneyAmount` now requires `is_finite()`, so
  Infinity, -Infinity, NaN, and sNaN are all `invalid_budget_amount` rather
  than one accepted and one leaking `decimal.InvalidOperation` from the
  `parsed < 0` comparison. Kept for the record: the leak was not in the parse
  — `Decimal("NaN")` constructs happily and it is the comparison that signals,
  which is why a try around the parse alone never caught it.

- [ ] **Money's remaining numeric questions** (split out of the non-finite fix,
  2026-08-17). Two are open and both need a policy rather than a bug fix:
  (1) magnitude — `MoneyAmount("1e400")` is finite and therefore accepted;
  bounding it means choosing a maximum, which is a domain call, not a
  correctness one. (2) `add` may still round silently past 28 significant
  digits (decimal's default context). Then sweep the other VOs for the same
  class of gap. This is the behavioral ground the retired vobase Money port
  had covered.

- [ ] **TB031 construction-completeness checker** (contract landed 2026-07-20,
  v0.0.5.0)
  - **What:** the checker for `testing.md` rule 2. Its contract is already
    fixed and reviewed as the fixture pair
    `tessercheck-py/testdata/tb031/{good_tree,bad_tree}/`; only the
    implementation is missing. Rule: for each spec-constructed type, **at least
    one** test must construct it from a spec and assert **every** spec field.
    Report the type plus the fields no single test covers.
  - **How:** it is the first `scope: "tree"` check, so `run_paths` needs a
    whole-tree phase after its per-file loop (the harness already supports tree
    fixtures; no registered check has used it). Identify the completeness test
    **structurally** (a `def test_*` that constructs the type), NOT via the
    `is_test` flag — `test_meta.py`'s tree harness injects
    `is_test=lambda _: False`, so a flag-keyed check would behave differently
    in fixtures than in production. Register the `CheckMeta` in the same change;
    that retires the interim
    `test_tb031_fixture_pair_holds_its_contract_before_the_checker_ships` guard.
  - **Teeth, already located:** `examples/running/campaign/short_link_test.go:26`
    (`TestNewShortLink_Accepts` constructs from a valid spec and asserts only
    `Active()`, never `Slug` or `TargetURL`) is a real in-repo violation.

- [ ] **TB030's remaining evasion surface** (adversarial review 2026-07-20,
  Claude + Codex agreed; deliberately deferred from v0.0.5.0)
  - **What:** TB030 is syntactic and reports what one file's AST shows. Four
    shapes get through, all documented in `doubles_check.py`'s module docstring
    so they are declared rather than hidden:
    1. **aliased module import** — `import unittest as u` → `u.mock.patch`, and
       `import pytest as pt` → `pt.MonkeyPatch`. The attribute branches match the
       literal module name. This is the highest-value one and Codex rated it
       block-worthy.
    2. **dynamic import** — `importlib.import_module("unittest.mock")`,
       `__import__`, `getattr(unittest, "mock")`, `sys.modules[...]`.
    3. **use-site fixture access** — `request.getfixturevalue("monkeypatch")`
       takes no banned parameter, defeating the monkeypatch half of the rule.
    4. **a suppressed import whitelists the module** — the library branches fire on
       the import, not each use, so one marker clears every call site below.
  - **How:** (1) needs an alias table built in a first pass over `Import`
    nodes, then matching attribute roots against it — the natural next
    increment. (2) is cheap for the literal-string cases (flag
    `import_module`/`__import__` with a banned dotted-name argument). (3) and
    (4) need a use-site pass, which is a real design step.
  - **Why not now:** every one is a *self-service* bypass by an author who
    could equally write the marker. tessercheck is a local debt-paydown tool,
    not an enforcement gate, so the threat model is weak — but (1) is an
    ordinary import style someone could hit by accident, so it should land
    first.

- [ ] **Analyzer robustness — three systemic issues across all checkers**
  (adversarial review 2026-07-20; pre-existing, TB030 raised the stakes)
  - **What:** none of these are TB030's, but whole-tree test scanning made them
    matter more.
    1. **The suppression line table is built with `str.splitlines()`**, which
       splits on `\x0b \x0c \x1c \x1d \x1e \x85    ` — characters
       Python's tokenizer does NOT treat as line breaks. One such character in
       an earlier string literal shifts every subsequent line number, so a
       marker can silently fail to suppress (red build on conformant code) or
       silently suppress a violation on a different line. Shared by
       `comments_check.py` (TB020) and the TB015/TB016 suppressors. TB030 now
       tokenizes instead, so it is already immune — the others are not.
    2. **One non-UTF-8 source file kills the whole run.** `run.py` opens with
       `encoding="utf-8"` and catches only `OSError`; a legal PEP 263 latin-1
       file raises an uncaught `UnicodeDecodeError`, so no findings print at
       all and CI reads the traceback as an ordinary failure. Fix: catch
       `(OSError, UnicodeDecodeError)` into the error list, or read bytes and
       use `tokenize.detect_encoding`.
    3. **Reported columns are byte offsets, not character offsets**
       (`col_offset + 1`), so any non-ASCII earlier on the line shifts
       editor/CI annotations.
  - **Why not now:** all three span every checker; fixing them inside the
    testing-norm wave would hide a cross-cutting change in a feature diff.

- [ ] **Go mirror of the testing norm** (opened 2026-07-20 with TB030)
  - **What:** `testing.md` and `TB030` are Python-only. `rationale/coverage.md`
    names this gap in the TB030 row ("no Go analyzer — the Go testing mirror is
    a named gap"), so that pointer is live until this ships. Go's equivalent
    banned surface is `gomock`/`mockgen`-generated doubles and `testify/mock`.
  - **Why not now:** same deferral pattern as the queued Go `primitiveaccessor`
    mirror — Python is the pilot-consumer priority, and the norm should survive
    contact there first.

- [ ] **Give `bootstrap` an injectable builder so the wiring tests drop their
  suppressions** (opened 2026-07-20, ship review, confidence 9)
  - **What:** the three `# tesser:debt` markers in
    `examples/python-app/tests/test_cleanup.py` and `test_bootstrap_once.py`
    are the norm's flagship example opting out of the norm. What they patch
    (`monkeypatch.setattr(linkpolicy_wire, "build", fake_build)`) is an
    in-process module attribute, not a process seam — they qualify only because
    there is no injection point above the composition root.
  - **Why it matters:** a consumer reading `examples/` learns the escape hatch
    rather than the rule. `testing.md` says so explicitly and points here.
  - **How:** let `bootstrap.new` take its per-context builders, so the tests
    inject a hand-written double and the suppressions disappear.

- [ ] **Hoist the suppression primitive out of SIX checkers** (2026-07-20 ship
  review, confidence 9 — count corrected 2026-07-26)
  - **What:** `_SUPPRESS_MARKER` + a `suppressed(...)` helper is duplicated
    across `doubles_check.py`, `comments_check.py`, `typed_checks.py`,
    `checks.py`, and — since the test-helper wave — `helpers_check.py` and
    `shadowing_check.py`. **Six sites, not the four this entry used to claim.**
    The marker is load-bearing (it is also in the CLI's user-facing message), so
    changing or scoping it means editing all six.
  - ⚠ **A recorded count goes stale as quietly as anything else.** This one was
    wrong for five days because the wave that added two copies did not walk back
    to the TODO that counts them. Re-count before quoting it.
  - **How:** move the marker and a `suppressed_predicate(source)` into
    `astutil.py` (`typed_checks.py` already documents this predicate shape).
    Note TB030's variant scans a node's whole **line span** (so a wrapped import
    can be suppressed) while the others are single-line — unify deliberately,
    don't silently pick one.

- [ ] **Fold the standalone checkers into the existing `_Checker` NodeVisitor**
  (2026-07-20 ship review; **re-measured 2026-07-26, and my own correction to
  this entry was wrong too — see below**)
  - **Measured composition, not a checker count** (Python 3.12.5, HEAD `79c3a1a`,
    tree-equivalent traversals per file):
    | source | tree-equiv | note |
    |---|---|---|
    | `_Checker` NodeVisitor | 1.00x | the pass everything else could ride |
    | `comments_check` | 2.00x | two back-to-back `ast.walk` |
    | `doubles_check` | 1.00x | |
    | **`shadowing_check`** | **2.73x** | the largest single consumer |
    | `helpers_check` | **0.00x** | |
    | `typed_checks` | ~0 | iterates `tree.body`; walks only class bodies |
    | **total** | **~6.73x** | plus 4 tokenize passes on a test module |
  - ⚠ **Two things I asserted in this entry on 2026-07-26 were wrong**, and both
    were wrong in the direction of blaming the newest code:
    - `helpers_check` contributes **zero** walks. `_defines_a_test` was rewritten
      to iterate `tree.body` (pytest's collection rules), so the module contains
      no `ast.walk` at all. I wrote "the wave added two more walks" without
      re-reading the code I had just changed.
    - `classify_trees` per test file is **not** "a whole-tree classifier pass of
      its own" and does not need measuring separately — it iterates `tree.body`
      for top-level classes only. **Measured: 0.219 ms for all 50 test modules
      repo-wide, ~4 µs/file.** It is the cheapest thing in the checker.
  - **The biggest win is now TB033, not TB030** — which inverts what this entry
    used to say. See the `_bound_names` double-walk below.
  - **How:** fold the TB030 dispatch into the existing `_Checker` NodeVisitor as
    `visit_Import`/`visit_ImportFrom`/`visit_Attribute` + additions to the
    existing function visitors, which makes it near-free on a pass that already
    runs. Kept standalone for now to match `comments_check.py`'s established
    module shape. Related: `check_comments` itself does two back-to-back
    `ast.walk` passes that could be one — worth more than TB030 costs.

- [ ] **Go-side `primitiveaccessor` analyzer** (norm strengthened 2026-07-19)
  - **What:** the accessor half of the no-primitive-exposure norm is enforced
    in Python only (TB010 flags a VO `@property`/method whose body is a bare
    `return self._x` with a primitive type). Go has the norm in the design doc
    (`docs/design-python-domain-detection.md` "Grounded against Go", amended:
    the `Money.Currency()` single-rep carve-out is closed) but no analyzer —
    `rationale/coverage.md` row "#6a/6b no primitive accessors" is still demo
    pending. Concretely: `examples/catalog/money.go`'s `Currency() string`
    accessor is the exact shape the amendment closes and is now a
    non-conformant example with nothing to flag it until this ships.
  - **How:** a `go/analysis` pass over VO-candidate types flagging exported
    methods that return a builtin/`*big.Rat`/`decimal` field unchanged
    (mirror `_bare_self_field_returned`); add the coverage row + demo in the
    same change.
  - **Why not now:** the 2026-07-19 change set was the Python consumer
    feedback wave; the Go mirror deserves its own predeclared demo per the
    coverage-matrix discipline.

- [ ] **Generic consumer activation recipe** (eng review 2026-07-19, TODO 12A)
  - **What:** an activation section for `skills/tesser-build` documenting how a
    consumer wires the skill into its agent host — Claude Code (Skill system
    auto-loading) vs Codex CLI (an `AGENTS.md` routing line pointing at
    `SKILL.md`) — each with a one-step verification.
  - **Why:** recurring documented gap (`skill-artifact-plans-need-activation-design`
    learning): skill-artifact plans design distribution (copy-in) but omit
    activation, so doctrine ships without reaching the consuming agents.
  - **Depends on:** the first verified pilot-consumer-side activation (Wave 3R eng
    review 1A consumption contract) — evidence first, then the recipe; never
    document a host path that hasn't been exercised once.
  - **Start at:** the de-identified relayed form of the pilot consumer's working
    `AGENTS.md` line.

- [ ] **Time-type taxonomy** (opened 2026-07-20 with the serialization norm)
  - **What:** one canonical wire form is pinned (aware-UTC ISO-8601,
    microsecond precision — `serialization.md` rule 3), but real domains need
    *several* time types — instant vs calendar date vs local time, and
    per-precision variants — each deserving its own leaf-VO shape and its own
    canonical form. Decide the taxonomy and per-type canonical policies so
    consumers aren't pigeon-holed into one type.
  - **Trigger:** the first datetime-bearing VO a consumer relays (or PR-B if
    the verified impl grows one).
  - **Why not now:** the pinned single form unblocks the serialization wave;
    the taxonomy is a modeling decision that deserves its own evidence.

- [ ] **Leaf-vs-compound discriminator: collect the hard cases** (2026-07-20)
  - **What:** the discriminator ("does the concept have a *standardized*
    canonical primitive representation? → leaf") decides borderline types —
    URL, E.164 phone, postal address, email-with-display-name. A wrong call is
    expensive to reverse (re-classification breaks construction AND
    serialization), so hard cases should be collected and ruled once, in the
    doc, as they surface.
  - **How:** append each borderline type + its ruling to
    `value-objects.md#decisions-you-must-make`; when 3+ accumulate, sharpen
    the discriminator's wording from the pattern.
  - **Why not now:** no hard case has actually surfaced yet; ruling on
    hypotheticals invents doctrine.

- [ ] **Change-handling red team (ops/migrations, pulled closer)** (2026-07-20)
  - **What:** red-team what can *change* under the settled norms and how each
    change is handled: a canonical form (persisted bytes → migration), a
    parts field (total record vs old rows — the migration caveat in
    `serialization.md`), a leaf↔compound re-classification, spec evolution,
    wire-shape versioning. Operational concerns were deliberately deferred
    ("static code only" — SKILL.md), but serialization puts persisted bytes
    downstream of these norms, so part of the ops/migration story lands
    sooner than the rest.
  - **How:** enumerate change classes → for each, name the blast radius, the
    loud/silent profile, and the sanctioned procedure; fold results into
    `serialization.md` (per-edge migration decisions) and a future
    change-sequencing doc.
  - **Why not now:** wave (a/b/c) ships the static norms first; the red team
    needs those fixed as its subject.

- [ ] **Behavior-rebuild ergonomics (performance-triggered only)** (2026-07-20)
  - **What:** behavior methods rebuild new instances THROUGH the public
    constructor via canonical forms (`MoneyAmount(canonical_decimal(total))`) — ruled
    2026-07-20; the cost is parse overhead only, and cosmetic "ickiness" is
    not evidence. If a consumer measures a real hot-path cost, the recorded
    candidate designs are: a TB003-sanctioned same-class private rebuild
    (`object.__new__(EnclosingClass)` + setattr of declared fields inside the
    class's own methods — Go's package-private struct-literal idiom ported),
    or union-typed constructors (rejected once already: special cases for a
    perf-only benefit).
  - **Trigger:** a measured performance problem in a real consumer, not
    aesthetics.

- [ ] **python-app pre-existing error-path test gaps** (opened 2026-07-20,
  PR-B ship review; explicitly NOT that PR's debt)
  - **What:** two error surfaces in `examples/python-app` have never had
    tests, predating the parts restructure. (1) The HTTP handler's `_respond`
    translation matrix — all four branches (`BadRequest`→400,
    `DomainError`→`status_for(kind)`, `InfraError`→503, bare
    `Exception`→500) are the boundary that turns domain failure into wire
    status, and only the first two are now exercised (by the deactivate
    lifecycle tests). (2) `InMemoryCampaignRepository`'s `down=True`
    InfraError branch on all four methods — the flag exists solely to make
    that path testable and nothing calls it.
  - **Why it matters here:** the anatomy is what consumers adopt, and the
    error-translation boundary is one of the parts they copy most directly;
    an untested matrix teaches a matrix nobody checked.
  - **How:** a `tests/test_error_translation.py` driving each branch through
    `Handler` with a stub client that raises each error type, plus a
    `down=True` repo asserting 503 through the handler rather than the raw
    exception.
  - **Why not now:** the deactivate fix was scoped to the unreachable-state
    defect and the negative paths on code that PR introduced; sweeping
    pre-existing surfaces would have hidden that change inside a larger diff.

- [ ] **Repository read paths / projections — a named norm gap** (opened
  2026-07-20, PR-B outside review)
  - **What:** the serialization norm covers how domain data crosses an edge
    but says nothing about READ paths. The verified impl's
    `CampaignRepository.all()` reconstructs every aggregate (row → spec →
    constructor, invariants re-run) just to feed a flat read view
    (`list_links`) — correct and honest at template scale, but a bad clone
    at consumer scale: a list endpoint over 100k aggregates becomes full
    hydration, and one stale invalid row breaks an unrelated projection.
    The undecided question: does the anatomy teach a read-side
    query/projection port (a port returning parts-shaped projections
    straight from storage, no aggregate hydration) alongside the aggregate
    repository, and what keeps it honest (no invariant re-run on reads —
    is that acceptable, and where is it stated)?
  - **Trigger:** the first consumer with a list/report endpoint over a
    non-trivial aggregate count, or the reports-context restructure.
  - **Why not now:** it is a norm-level ruling (repositories.md +
    serialization.md scope), not a PR-B patch; inventing it inline would
    violate the evidence-first discipline.

- [ ] **Checker contracts as fixtures-first** (2026-07-20)
  - **What:** a check's *normative* contract artifact is its
    `good/bad` fixture pair set — authored and reviewed BEFORE the checker,
    with the doc prose describing and pointing at the fixtures, never the
    other way around. Prevents prose-derived checkers from encoding an
    imprecise sentence as analyzer semantics.
  - **How:** apply starting with the serialization-wave checks (PR-C): land
    fixture pairs as the reviewed contract, then the checker that satisfies
    them; the meta-test already enforces pair existence.
  - **Why not now:** it IS now — this entry records the discipline so it
    outlives the wave.

- [ ] **`date`/`time` have a ruled exit but no ruled canonical form**
  (2026-07-21, wave C2)
  - **What:** C1's temporal ruling put `date`/`datetime`/`time` in the
    wrappable set, and `_CANONICAL_EXIT` gives all three `__str__`. But only
    `datetime` has a *pinned form* (`canonical_datetime`). A `date`-backed leaf
    exits as "canonical text" with no policy saying which text, and `time` is
    worse (naive vs aware, precision). So `_CANONICAL_HELPER` is a proper
    subset of `_CANONICAL_EXIT` and TB018 leaves those leaves out of contract.
  - **Why it matters:** `examples/errorspy`'s `Day` is exactly this case — a
    gated example tree shipping a hand-rolled `.isoformat()` exit that the norm
    neither blesses nor flags. Every consumer with a date VO hits it.
  - **Depends on / blocked by:** the time-type taxonomy decision (instant vs
    date vs local time; per-precision types) already recorded above — `date`
    is probably a one-line ruling (`value.isoformat()`), `time` is not, and
    splitting them may be the answer.
  - **Start at:** `_CANONICAL_HELPER` in `tessercheck-py/tessercheck/typed_checks.py`
    (the gap is documented at the constant) and `serialization.md` rule 3.
    Ruling the form means adding the helper to each tree's `serialization.py`,
    routing `Day`, and the map grows to match `_CANONICAL_EXIT`'s keys.

- [ ] **The Go single-construction-path ANALYZER (TB017's analog)** (2026-07-21, wave C2
  review; the example half is done)
  - **What:** the one-constructor ruling is language-independent and every *rendering*
    now agrees — `go.md` states the rule, and `examples/catalog/labels.go` is
    down to one `NewLabels`. What is still missing is the machine: no Go
    analyzer flags a second exported constructor, so on the Go side this stays
    review-enforced while Python has TB017.
  - **Why it matters:** the asymmetry is now purely in enforcement, not in what
    the two languages teach. That is the honest state, and `go.md` says so —
    but a consumer's Go repo can still grow a `RequireX` and nothing catches it.
  - **Shape:** a `go/analysis` pass over exported funcs returning their own
    package type, mirroring TB017's "any second construction path, name-agnostic". The
    interesting Go-specific question is whether `NewX`/`MustNewX` counts as two
    construction paths — it does not (the `mustnew` convention is a sanctioned panic-wrapper
    over the same constructor), so the check must exempt the `Must*` twin explicitly.
  - **Start at:** `internal/analyzers/` alongside the existing passes; folds
    into the queued Go serialization umbrella.

- [ ] **TB018 trusts the helper's NAME, with no provenance check**
  (2026-07-21, wave C2 review)
  - **What:** the check matches `canonical_*` by name. A module-local
    `def canonical_str(v): return v.upper()`, or `from evil import shout as
    canonical_str`, satisfies TB018 while the exit runs arbitrary non-policy
    code — the exact second implementation the rule exists to prevent. Its
    "grep `canonical_` finds them all" claim holds for the name, not the
    behavior. Every swept fixture now defines a local no-op helper, so the
    fixtures demonstrate the shape.
  - **Why not now:** verifying provenance means resolving the binding to an
    import from the tree's sanctioned serialization module — a real design step
    (and AST alone cannot verify the target's contents). Deliberate limitation,
    stated rather than silently held.
  - **Start at:** `_check_canonical_routing` in `typed_checks.py`; collect
    module-level def/assign bindings and `import ... as` aliases for names in
    `_CANONICAL_HELPER` and flag a shadowed or aliased helper.

- [ ] **`bad.py` fixtures assert the code SET, never the count or lines**
  (2026-07-21, wave C2 review)
  - **What:** `test_bad_fixture_trips_only_its_own_code` asserts
    `{codes} == {code}`. `tb017/bad.py` carries 5 distinct violation shapes and
    `tb018/bad.py` 6; all fire today, but a refactor could detect only one and
    the fixture would still read as a passing multi-shape contract. Tree-scoped
    checks get an explicit teeth assertion; file-scoped ones do not.
  - **Start at:** `tests/test_checks.py:22` — assert a per-fixture finding count,
    or adopt want-markers on each violating line and assert the flagged line set.

- [ ] **`async def __str__` is invisible to TB015 and TB018** (2026-07-21)
  - **What:** `_defined_conversion_dunders` filters on `ast.FunctionDef` only.
    TB017 handles `AsyncFunctionDef` correctly, making this an inconsistency.
    Low practical impact (an async conversion dunder does not work at runtime),
    and it is pre-existing in TB015 rather than introduced here.
  - **Start at:** `_defined_conversion_dunders` in `typed_checks.py`.

- [ ] **Four byte-identical `serialization.py` copies, one of them untested**
  (2026-07-21, wave C2 review)
  - **What:** per-app ownership of the canonical-form policy is the norm's
    design, but `examples/errorspy`'s copy has no test over it and 5 of its 6
    functions are unused there — including `canonical_datetime`'s naive guard
    and its pinned UTC/microsecond form. If the pinned form changes, errorspy
    drifts silently. (`examples/python`'s copy is likewise untested in-tree.)
  - **Start at:** add the pinned-policy assertions to errorspy's tests, or a
    drift test asserting the copies agree.

- [ ] **The Literal/Annotated skip is keyed on the SPELLING, so an import
  alias restores the false positive it fixed** (adversarial review 2026-07-26,
  filed with a verified repro)
  - **What:** `astutil._annotation_refs` skips a `Literal[...]` slice and
    `Annotated`'s metadata by base name. `from typing import Literal as L` plus
    `L["Warehouse"]` defeats the skip and the full Literal-as-forward-ref false
    positive returns (TB012 + TB014 on a conformant discriminator field —
    reproduced). A *type alias* (`Kind = Literal["Warehouse"]`) is safe.
  - **Why not fixed now:** seeing through an import alias needs module-level
    import context threaded into a pure expression walk — the alias-disguise
    class this analyzer scopes out everywhere (classify's docstring: alias /
    NewType / cross-module are the optional mypy plugin's job). This entry
    exists because here the failure mode is the analyzer's own P1, not a
    missed detection.
  - **Start at:** decide whether checks get module import context as a general
    capability; a one-off for Literal would be the fourth diverged walk.

- [ ] **The wide walk credits names inside `type[X]` / `Callable[..., X]`, and
  no test pins whether that is intended** (coverage audit 2026-07-26)
  - **What:** with `returned_only=False`, `_contains_primitive` credits names
    inside those slots, so a VO field `kind: type[str]` or an accessor
    `-> Callable[[], str]` trips TB010 even though neither holds a `str`
    (verified with a non-primitive backing field). Pre-existing — the deleted
    flat `ast.walk` did the same — but `astutil._annotation_names`'s docstring
    now states the wide default as a deliberate promise.
  - **Start at:** decide whether "any name anywhere" should exclude
    not-the-value slots for the BAN checks too, then pin the answer with a
    test either way. The machinery (`returned_only`) already exists.

- [ ] **No example tree contains an `async def`, so async annotation handling
  is unproven end-to-end** (coverage audit 2026-07-26)
  - **What:** the metamorphic sweep's `visit_AsyncFunctionDef` branch and every
    checker's `AsyncFunctionDef` branch run only on synthetic unit fixtures —
    the four example trees have zero async code. The sweep looks like it
    covers async return annotations and does not.
  - **Start at:** this is a curriculum question first (should an example teach
    an async handler?), a coverage question second. If no example earns async
    on its own merits, add an async fixture pair under `testdata/` instead.

- [ ] **`ClassInfo.collection_element_names` is computed and never consumed**
  (2026-07-26, found while unifying the annotation-name walk)
  - **What:** `classify._collection_element_names` feeds a `ClassInfo` field with
    zero readers outside `classify.py` (verified by grep across `tessercheck/`
    and `tests/`). It also still misses a *fully*-quoted collection annotation
    (`links: "tuple[ShortLink, ...]"` is a `Constant`, not a `Subscript`, so the
    collection test fails before the elements are read) — inert only because
    nothing consumes the field.
  - **Start at:** decide whether a check will ever key on "collection of X"
    separately from `field_type_names`; if not, delete the field, and if so,
    unquote the annotation before the `Subscript` test in the same change.

- [ ] **Suppression is a substring scan on the OLD checkers — now with a
  verified repro** (2026-07-21; proven 2026-07-26)
  - **Confirmed by running it, both directions:**
    - `@dataclass(repr=("# tesser:debt"))` silences **TB001**
      (control fires TB001; spoofed returns nothing).
    - `x = "# tesser:debt"  # banned prose` silences **TB020**.
    - The two checkers this wave ADDED resist it — TB032's `_comment_lines` and
      TB033's `_suppressed_lines` both filter `token.type == tokenize.COMMENT`,
      and a marker appearing only inside a string does NOT suppress them.
  - **So the house pattern is already written, twice, in the new code.** What is
    left is `checks.py:_suppressed` (TB001–TB004) and `comments_check.suppressed`
    (TB020) still reading raw line text. Hoisting the tokenize-based reader into
    `astutil.py` fixes both and collapses the `_SUPPRESS_MARKER` duplication
    tracked above.
  - **Honest bound:** an author who can edit the file can equally write a real
    debt marker, so this is an inconsistency and an audit-grep blind spot,
    not a privilege boundary. That is why it is not a P1 — but it IS the kind of
    thing that makes a `grep -c 'tesser:debt'` audit lie.

- [ ] **`DIRECTIVE` matches the marker word as a bare prefix, so a near-miss
  marker is a free TB020 exemption** (resurfaced by the Codex adversarial pass
  during the v0.0.70.0 sentinel rename; **pre-existing — verified identical on
  the pre-rename tree**, so the rename preserved it rather than introducing it)
  - **Not new — this is comments norm v0's "prose may ride an exempt directive
    prefix", accepted by ruling on 2026-07-19 as a known-by-design limit.** What
    is new is the repro and the measurement below, which is what turns an
    accepted limit into a fixable item: at v0 the cost was unmeasured, and the
    answer to "how much does this leak today" turns out to be "nothing yet".
  - **What:** `DIRECTIVE` (`checks.py:209`) matches
    `^#\s*(...|tesser:debt|...)` with no boundary after the alternative, while
    `Module._debts_from` (`checks.py:843`) requires the next character to be a
    space or tab before it will register a debt. The two disagree on what counts
    as the marker, and every code path downstream of that disagreement leaks.
  - **Repro (run against both trees, same result):**
    - `import os  # tesser:debts TB040` → `TB040` only. No `TB020` (the comment
      was waved through as a directive) and no `TB090` (no debt was registered,
      so there is nothing to call stale).
    - `import os  # tesser:debtfile arbitrary banned prose` → same. Any prose
      after a near-miss marker word is exempt from the comments norm.
    - Control: `import os  # plain banned prose comment` → `TB020` + `TB040`.
    - On the pre-rename tree, `# tessercheck:ignored TB040` and
      `# tessercheck:ignorefile arbitrary banned prose` behave identically.
  - **Why it matters:** the comments norm has no other opt-out, so this is an
    *untracked* one — the one escape hatch the ledger cannot see. It also makes
    `README.md`'s "a typo in the marker word … makes the comment inert" false in
    one direction: the typo'd comment is inert as a suppressor of coded findings
    but very much live as a TB020 exemption.
  - **Start at:** decide whether `DIRECTIVE` should share the debt parser's
    classification outright rather than carry a second, looser spelling of the
    same grammar. Note the same unbounded-prefix property holds for `noqa`,
    `pragma`, and `type:` in that alternation, so a fix that tightens only
    `tesser:debt` buys consistency with the parser at the cost of consistency
    within the regex — that trade is the actual decision, not the regex edit.
    A tightened boundary will also newly fire TB020 on any near-miss marker
    already sitting in a gated tree, so grep before changing it — as of
    v0.0.70.0 that grep is clean (every `# tesser:debt` followed by a non-space
    is markdown prose, none is Python source), so the fix costs nothing today.

- [ ] **`@anything.fixture` exempts a function from TB032 with no declared fact**
  (found independently by two reviewers, 2026-07-26)
  - **What:** `_is_fixture` matches any decorator whose attribute is `fixture`,
    so a decorator that has nothing to do with pytest waves a function through
    the totality check — no marker, no record that anything was exempted.
    Verified: returns no findings.
  - **Why not fixed with the rest:** tightening to a pytest-rooted decorator
    risks a FALSE POSITIVE on legitimate re-exports (`from conftest import
    fixture`), and this wave already shipped one overcorrection that had to be
    walked back. A self-service bypass by an author who could equally write the
    marker is the cheaper failure.
  - **Start at:** `helpers_check._is_fixture`. Decide first whether the rule is
    "rooted at pytest" or "records the exemption somewhere", since those give
    different designs.

- [ ] **Suppression is a substring scan, and TB017/TB018 give it a natural
  surface** (2026-07-21, wave C2 review)
  - **What:** `# tesser:debt` is resolved by scanning the raw source
    line for the marker text, so a *string literal* containing it suppresses a
    real violation with no directive present. TB017 and TB018 suppress on the
    `def` line, where a string DEFAULT ARGUMENT carrying the marker is both
    mypy-clean and natural-looking:
    `def parse(cls, raw: str = "# tesser:debt") -> "Slug"` suppresses
    TB017 with no comment anywhere. Earlier codes suppressed on field or
    statement lines, where a marker-bearing literal looks out of place.
  - **Also:** the line table is built with `str.splitlines()`, which splits on
    `\x0b`/`\x0c`/` ` that Python's tokenizer does not — shifting every
    line number after such a character.
  - **Fix:** derive suppressed lines by tokenizing and keeping only real
    COMMENT tokens, failing closed on a tokenize error; cover TB017/TB018 in
    its regression tests. This is systemic — `comments_check.py` (TB020),
    `typed_checks.py` and `checks.py` all use the substring form.
  - **Note:** a parallel branch (the testing-norm wave) already derives
    suppression from COMMENT tokens in its own new check. Reconcile to ONE
    shared implementation when both land rather than leaving two.

- [ ] **Testing norm scope across the Python example trees** (2026-07-20,
  testing-norm eng review)
  - **What:** the testing norm (wave A) makes `examples/python` its sole
    canonical tree (R6). `examples/python-app` (13 test files), `examples/serdepy`,
    and `examples/errorspy` are all gated by tessercheck in CI but are NOT held to
    the testing norm, so their test suites will diverge from what `testing.md`
    teaches. Decide, per tree, whether each adopts the norm or is exempt-with-reason.
  - **Why it matters:** a norm that governs one example tree while three siblings
    gated in the same CI drift is exactly the inconsistency the toolkit argues
    against — and `python-app` is the anatomy consumers copy from most, so its
    tests teach by example whether or not they conform.
  - **Depends on / blocked by:** wave B of the testing norm — the norm is not
    complete until OQ2 (parametrize), OQ3 (layout), and OQ4 (AAA) are ruled; there
    is nothing stable to conform these trees to until then.
  - **Start at:** the design doc's R6 ruling and NOT-in-scope section
    (`~/.gstack/projects/verocorp-go-ddd/chris-main-design-20260720-152139.md`);
    mirror the shape of the "repository read paths" named-gap entry above.

- [ ] **Roadmap bindings at the artifact ("mechanism #2")** (2026-07-21, PR #27
  follow-up)
  - **What:** move the row BINDING out of `roadmap/registry.json` and onto the
    artifact that already knows it — a required `row` field on `CheckMeta`
    (`tessercheck-py/tessercheck/finding.py`), the same on the Go
    `analyzers.All` entries, and a `tb-row:` marker beside the existing
    `tb-status:` in each skill doc. The registry then declares only what no
    artifact can know: the row taxonomy itself, planned (`[]`) vs n/a (absent
    key), and rationale globs. `py_checks` / `go_analyzers` / `skill` come out
    of it and are computed by inversion.
  - **Why it matters:** PR #27's totality guard catches OMISSION, not
    MISASSIGNMENT — every check must be claimed by *some* row, but nothing
    checks it is the right one; TB030 could sit on `norm-comments` and CI stays
    green forever. Bindings at the artifact also collapse the two-place edit
    (checker + registry) that produced the original gap, and move the failure
    from CI-time to authoring-time: a `CheckMeta` without a row fails in the
    same file, in the same edit.
  - **How:** follows the repo's existing meta-test idiom in both languages —
    "a check cannot land without a fixture pair" (the `CHECKS` meta-test) and
    "an analyzer cannot land without tests" (`TestEveryAnalyzerIsTested`)
    become "a check cannot land without a row". The migration is mechanical: a
    few dozen strings move from JSON into `CheckMeta` entries and `tb-row:`
    markers.
  - **Also open, same area:** `examples/` is deliberately NOT a guarded
    universe — `examples/editor` and `examples/golangci` are genuinely not
    components, so it needs a marker scheme rather than an exemption list. And
    `tb-cell` judgment prose (e.g. "D3 won; D1 pending") is unverifiable by any
    mechanism; the only control is that markers live at the source they
    describe.
  - **Why not now:** #27 closed the failure that mattered — a whole shipped
    norm invisible in the matrix — and that guarantee does not decay if this
    never lands. This is a precision + ergonomics upgrade against 14 check
    codes, 8 analyzers and 21 skill docs: real, modest, and no worse to do
    later than now (ruled 2026-07-21, weighed against writing `errors.md`,
    which ranked higher).

## Bootstrap / host lifecycle (opened 2026-07-22, PR #31)

Left open when the host-lifecycle + one-loader work shipped
(`examples/python-app` + reconciled `srv.md`/`bootstrap.md`). None blocks that
change; each waits for a real need.

- [ ] **`APP_ENV` behavior-class validation — document or demonstrate?**
  - **What:** impl selection is coordinate-driven (a resource coordinate, never
    a magic env name — `bootstrap.md` rule 3). An `APP_ENV`, *if used at all*,
    may only be a behavior **class**, never a resource selector. Open question:
    does a behavior-class-only `APP_ENV` (an allowlist + a startup fingerprint
    validating the name *against* the actual resources) deserve a worked
    demonstration in `examples/python-app`, or only a paragraph of doctrine?
  - **Why:** `bootstrap.md` already bans `APP_ENV` as a resource selector; it
    says nothing about the legitimate behavior-class use. A reader has no
    example of the safe form.
  - **How:** if documented — a short "Decisions you must make" entry in
    `bootstrap.md`/`srv.md`; if demonstrated — a validated check at the host
    edge (inside `from_env`) that fails fast when the declared class disagrees
    with the resources it was handed.
  - **Why not now:** no consumer has hit it; premature to pick document-vs-build
    without the friction.

- [ ] **Secret-reference resolver (reference → DSN, at the edge)**
  - **What:** when credentials arrive as a secret *reference* (a Vault path, an
    AWS/GCP secret id) rather than an inline connection string, resolving the
    reference to the real coordinate is a launch-time job at the host edge —
    inside or just before `from_env` — never a lazy fetch below it. The example
    builds no resolver.
  - **Why:** the common production case injects a reference, not a raw secret;
    the one-loader + env-edge rules must survive it, and today the doctrine only
    names the case without showing the shape.
  - **How:** a pure resolver the host calls before/within `from_env`; document
    the shape in `srv.md`, optionally demonstrate with a fake resolver in
    `examples/python-app` (no live secret manager in CI).
  - **Depends on:** nothing hard; do it when a consumer needs reference-based
    secrets.

- [ ] **`Dsn` value object + a persisted context**
  - **What:** the coordinate-value-object demonstration — a `Dsn` parsed at the
    wiring constructor (scheme + host + database), validated, with a
    `redacted()` exit so credentials never reach a log — needs a context that
    actually persists to a real backend. Deferred: a SQL repository CI never
    connects to is CI-unrun code, the same reason `srv/wrk` is omitted.
  - **Why:** demonstrates coordinate VOs at the constructor and the
    end-to-end credential flow in running code; the example currently keeps its
    in-memory `storage` coordinate, so there is no DSN to wrap.
  - **How:** when a context gains a genuine persistence need, add the `Dsn` VO in
    that context's `repo_for`, and decide the CI story then (a real backend in
    CI vs keeping the SQL path exercised some other way — do not ship an
    unexercised repo).
  - **Depends on:** a context that needs to persist. Until then, the
    credential-flow story stays doctrine, not code.

## Testing norm — helper wave follow-ups (opened 2026-07-26, eng review)

- [ ] **TB033 walks each scope twice, for a measured 20% of its own cost**
  (performance review 2026-07-26, prototyped)
  - **What:** `_bound_names` materializes `_own_scope(node)` **twice** per scope —
    once for the `Global`/`Nonlocal`/`ExceptHandler` loop and again for the
    assignment-target loop. That is 1.71x tree of node touches where 0.85x would
    do, and it is why TB033 is now the most expensive checker in the analyzer
    (199.6 ms repo-wide vs TB020's 131.5 ms).
  - **The fix is a loop merge and it was prototyped:** 199.4 → 159.7 ms
    repo-wide, **byte-identical findings**. Beyond that, `_own_scope` re-derives
    per scope the same partition the scope-collecting `ast.walk` already visited;
    one traversal yielding each scope together with its own-scope nodes would take
    TB033 to roughly a single tree pass.
  - **Why not done on the way out:** it is a refactor of the exact function that
    produced three of this wave's defects, for a linter that runs in 0.3 s on the
    largest example tree. Three separate defects in this wave were introduced by
    fixes made under ship pressure. This one has no user-visible symptom, so it
    waits for a change window where it can be the only thing moving.

- [ ] **Every file is tokenized 3-4 times to build near-identical debt-marker sets**
  (performance review 2026-07-26, measured)
  - **What:** `comments_check`, `doubles_check`, `shadowing_check` and (on a test
    module) `helpers_check` each run their own `tokenize.generate_tokens` pass.
    **Measured: ~106 ms of a 584 ms repo run is redundant re-tokenization**; this
    wave added two of the four.
  - **One fix closes two entries:** tokenize once in `check_tree` and pass the
    suppressed-line set down. That collapses this cost AND the behavioral
    divergence in the six-checkers suppression entry above — the old checkers
    read raw line text, the new ones read COMMENT tokens, and a single shared
    reader makes them agree by construction.

- [ ] **TB033: three more binding forms Python treats as bindings**
  (adversarial review 2026-07-26, deferred deliberately)
  - **What:** TB033 counts parameters, assignment targets, `for` targets, walrus,
    `with ... as`, and `except ... as`. It does **not** count:
    - **`match` capture patterns** — `case len:` then `len(x)` calls the captured
      value. Confirmed by two independent reviewers.
    - **comprehension targets** — `[len(x) for len in fns]`. A comprehension has
      its own scope in Python 3, so this needs comprehension scopes added, not
      just another binding form.
    - **`import` bindings** — `from m import len` then `len(xs)`. Arguably NOT a
      bug: you deliberately imported something called `len` and calling it is
      what you meant. Rule the intent before building it.
  - **Why deferred:** every one is a false NEGATIVE, not a false positive, so
    nothing breaks in a consumer while they wait. They were found during a ship
    review and rushing them in behind a release is how the P1 in that same
    review got introduced.
  - **Start at:** `_bound_names` in `tessercheck-py/tessercheck/shadowing_check.py`,
    and the `scopes` list in `check_shadowing` for the comprehension case.

- [ ] **TB032 misses two more collectible-test shapes** (coverage review
  2026-07-26; both false NEGATIVES, neither locked into a test)
  - **A nested `Test*` class holding the tests.** `class TestOuter:` containing
    `class TestInner:` with the `test_*` methods — pytest collects
    `TestOuter::TestInner::test_it`, but `_defines_a_test` scans one level of
    `tree.body` for methods and never for a nested class. The module's helpers go
    unjudged.
  - **An indirect `unittest.TestCase` subclass.** `class Base(TestCase)` then
    `class CampaignCase(Base)` — pytest collects it; `_is_test_class` only matches
    a direct `TestCase` base. Decidable within one file, which makes it narrower
    than it sounds.
  - **Same shape as the bug the adversarial pass caught in TB033:** a walk got
    tightened to kill a false positive and took real detection with it. Both fail
    toward silence rather than noise, and there are no in-tree instances.
  - **Deliberately not locked into a test.** A test asserting current behavior
    here would ratchet the bug in place — which is exactly what happened once
    already this wave with the lambda blind spot.

- [ ] **TB032's structural blind spot is wider than first recorded**
  (adversarial review 2026-07-26)
  - **What:** a module defining no test pytest would collect is never judged. The
    known case was a helper-only module or `conftest.py`. Also uncollected, and
    therefore unjudged: tests generated by assignment
    (`test_x = make_case(...)`), and a project that redefines pytest's
    `python_functions` / `python_classes` in its own config.
  - **Why it matters:** `conftest.py` is where shared helpers actually go, so the
    totality check is blind in the file most likely to need it.
  - **Depends on:** deciding what makes a *non-test* module part of the test
    tree — a scoping question this check does not answer today. Wants a ruling
    before code.

- [ ] **Relocate the architecture detectors out of `tests/`**
  - **What:** the ~15 AST-analysis functions in
    `examples/python-app/tests/{test_enforcement.py,discovery.py,test_direction.py}`
    are real logic, not test scaffolding. Move them into a module outside the
    test tree and hold them to the toolkit's own conventions.
  - **Why:** `tests/` is an amnesty zone for **12 of the 14 shipped checks** —
    TB001/TB002/TB003 are gated at `checks.py:110,125,205` and all of
    TB010–TB018 at `checks.py:283 (if not is_test)`. Only TB020 and TB030
    survive. The detectors sit inside that amnesty and it shows:
    `_env_offenders(files: list[tuple[str, ast.Module]]) -> dict[str, list[int]]`,
    `_clients_reached(...) -> tuple[set[str], list[int]]`,
    `classify(root) -> tuple[list[str], list[str]]`. None would survive TB010
    anywhere else in the repo. Chris named it: *"domain logic coupled with
    testing interfaces"* — they should be built outside the example app and
    follow tesser-build guidelines and checks themselves.
  - **Same class as** the 10/10 learning `never-name-tessercheck-module-test-prefix`
    — that one reached the amnesty by filename, this one by directory.
  - **How:** ruff + import-linter adoption (Chris, parallel session) removes 4 of
    the 7 detector groups first. Redesign only what survives:
    `_import_time_side_effects`, `_clients_reached`, and `discovery.*` — the three
    that encode tesser-build's own doctrine and have no off-the-shelf equivalent.
  - **Cost warning:** outside the amnesty, TB001–TB018 apply, so the AST-analysis
    domain needs real value objects instead of primitive-collection tuples. Wave-sized.
  - **Depends on:** ~~the ruff/import-linter work landing~~ — landed as v0.0.12.0
    (PR #40). The surviving set is now known and is exactly the five functions
    named above. Wants `/office-hours` before a plan.
  - **State as of the TB032 wave:** all five carry `# tesser:debt` in
    `tests/test_enforcement.py`. That was chosen over a rushed redesign so the
    check could go live without a permanent exemption anywhere else — the debt is
    now named at the exact five lines rather than hidden behind a checker flag.
    **Deleting those five markers is the acceptance test for this TODO.**
  - **Related, unclosed:** `tests/discovery.py` defines no `test_*`, so TB032
    never judges it at all — it sits in the structural blind spot rather than
    under a marker. Relocating the detectors closes that too.

- [ ] **Test-argument pruning harness** (design refuted and repaired 2026-07-26)
  - **What:** find arguments a test passes to a helper that do not affect the
    outcome. Static tier: a kwarg whose literal equals the helper's declared
    default is provably redundant (AST-only, free). Dynamic tier: delete a kwarg,
    re-run that nodeid, still green means inert.
  - **Why:** the norm says a test passes only the one or two arguments that
    matter. Nothing checks it.
  - **⚠️ The dynamic tier is unsafe without a contrast pre-pass.** Verified on
    `examples/python`: pruning reduces `test_equality_is_identity_by_slug` to two
    IDENTICAL constructions and the suite stays green; a regression in `__eq__`
    then goes undetected where the unpruned test caught it (unpruned FAILED,
    pruned 4 passed). It does the same to a well-factored single-claim test, so
    this is **not** a test-quality problem — "the test still passes" is simply the
    wrong oracle. An argument can be inert for an assertion's truth value while
    being essential to its meaning.
  - **Mutation testing does NOT rescue it.** Measured with mutmut 3.6.0:
    byte-identical results before and after the damage (6 mutants, 3 killed,
    2 survived, 1 no-tests). mutmut generates exactly two mutants for that
    `__eq__` — `and`→`or` and `==`→`!=` — and both are killed by an assertion
    pruning never touches. Operators substitute; they cannot synthesize a missing
    input. **The "prune + mutate compose into a complete pair" hypothesis is dead;
    do not rebuild it.**
  - **The fix:** a contrast pre-pass. An argument that differs between two calls
    to the same helper within one test is that test's comparison axis and is never
    prunable. It must run BEFORE both tiers — in the verified repro the *static*
    tier struck first.
  - **Landscape (searched 2026-07-26):** nothing off the shelf. DSpot / AmPyfier /
    Small-Amp are the same machinery pointed the other way (amplify, not reduce);
    delta debugging / cause reduction is the right algorithm with no pytest
    implementation; pytest-deadfixtures is a different granularity.
  - **Depends on:** the helper norm landing — nothing to prune until helpers have
    defaults.

- [x] **TB033 — RULED AND SHIPPED 2026-07-26.** Neither framing won: the check
  targets the **collision, not the name** — a builtin bound in a scope that the
  same scope then *calls*.
  - **What settled it:** running both cases. A dataclass field named `id` costs
    nothing (the builtin stays callable in methods and `__post_init__`), while a
    parameter named `id` breaks — `id(object())` raises
    `TypeError: 'str' object is not callable`. So the field framing protects
    against nothing, and the name-based parameter framing taxes 12 sites to
    prevent a bug that occurred in none of them.
  - **The blast-radius figures recorded here were wrong** and are kept as a
    caution: "parameter target hits 1" counted only test helpers and predated
    the restyle. The real spread was 4 fields and **12** parameters, most of them
    production code — and two of the twelve
    (`BaseHTTPRequestHandler.log_message(self, format, *args)` overrides) cannot
    legally be renamed at all. Re-measure before weighing a stale count.
  - **Off the shelf was checked first** (the PR #40 precedent): ruff `A001`/`A002`
    already ships the name-based ban, flags those illegal-to-rename overrides
    here, and has no call-aware variant. That is what justified writing one.
  - **Shipped as a registered check, not fixtures-only** — under this ruling
    there is no rename cascade (zero findings repo-wide), and registration earns
    the standard meta-tests instead of a bespoke interim guard.

- [ ] **Revisit the inlined e2e HTTP client in `examples/python/tests/test_wiring.py`**
  - **What:** T4c of the helper wave inlines `_request(method, url, body=None)` at its 6
    call sites, per Chris's 2026-07-26 ruling. Revisit at the end of this gstack
    workstream, or later, once the marker mechanism has shipped.
  - **Why it was ruled that way:** `_request` fails the helper rule unambiguously — it has
    required params, a ternary, a `try/except`, and calls into `urllib.request` and `json`.
    That is logic, not defaults. Inlining is the reading of the rule that needs no new
    machinery, so it is the one that ships first.
  - **The cost that makes it worth revisiting:** ~54 lines of urllib boilerplate replace 6
    calls, inside `examples/python` — the canonical worked example consumers read. The rule
    is served and the example gets harder to read. That trade was made knowingly.
  - **The two alternatives, both still open and both cheaper *after* this wave than before:**
    1. Move it out of `tests/` as a small test-support HTTP client held to the toolkit's
       conventions — folds into the detector-relocation TODO above, which has the same shape
       (real logic living inside the `tests/` amnesty zone).
    2. Rule "hand-written client for an e2e test" a permitted category and annotate it with
       the `# tesser-category:` marker TB032 introduces. This is what the annotation
       mechanism exists for, but it needs a category name, and naming the vocabulary before
       the mechanism ships is backwards.
  - **Decide it with:** whether a second instance of this shape shows up. One e2e HTTP
    client is an anecdote; two is a category worth naming.
  - **Depends on:** T4c landing (the inline), and TB032's marker mechanism existing (for
    option 2).
