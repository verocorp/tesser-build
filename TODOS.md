# TODOS

Deferred work with context. Each entry carries enough for a cold pickup.

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

## Toolkit

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
       `import pytest as pt` → `pt.MonkeyPatch`. The attribute arms match the
       literal module name. This is the highest-value one and Codex rated it
       block-worthy.
    2. **dynamic import** — `importlib.import_module("unittest.mock")`,
       `__import__`, `getattr(unittest, "mock")`, `sys.modules[...]`.
    3. **use-site fixture access** — `request.getfixturevalue("monkeypatch")`
       takes no banned parameter, defeating the monkeypatch half of the rule.
    4. **a suppressed import whitelists the module** — the library arms fire on
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
  - **What:** the three `# tessercheck:ignore` markers in
    `examples/python-app/tests/test_cleanup.py` and `test_bootstrap_once.py`
    are the norm's flagship example opting out of the norm. What they patch
    (`monkeypatch.setattr(linkpolicy_wire, "build", fake_build)`) is an
    in-process module attribute, not a process seam — they qualify only because
    there is no injection point above the composition root.
  - **Why it matters:** a consumer reading `examples/` learns the escape hatch
    rather than the rule. `testing.md` says so explicitly and points here.
  - **How:** let `bootstrap.new` take its per-context builders, so the tests
    inject a hand-written double and the suppressions disappear.

- [ ] **Hoist the suppression primitive out of four checkers** (2026-07-20 ship
  review, confidence 9)
  - **What:** `_SUPPRESS_MARKER` + a `suppressed(...)` helper is now duplicated
    across `doubles_check.py`, `comments_check.py`, `typed_checks.py`, and
    `checks.py`. The marker is load-bearing (it is also in `comments_check.py`'s
    `_DIRECTIVE` regex and in the CLI's user-facing message), so changing or
    scoping it means editing four sites.
  - **How:** move the marker and a `suppressed_predicate(source)` into
    `astutil.py` (`typed_checks.py` already documents this predicate shape).
    Note TB030's variant scans a node's whole **line span** (so a wrapped import
    can be suppressed) while the others are single-line — unify deliberately,
    don't silently pick one.

- [ ] **TB030 adds a 4th full-tree AST walk per file** (2026-07-20 ship review,
  measured)
  - **What:** measured on this repo's own corpus (146 files): 142.5 ms → 176.7 ms,
    **+24%** wall clock for one check, ~0.23 ms/file. Real but small; a linter,
    not a hot path.
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
    or union-typed doors (rejected once already: special cases for a
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

- [ ] **The Go single-door ANALYZER (TB017's analog)** (2026-07-21, wave C2
  review; the example half is done)
  - **What:** the one-door ruling is language-independent and every *rendering*
    now agrees — `go.md` states the rule, and `examples/catalog/labels.go` is
    down to one `NewLabels`. What is still missing is the machine: no Go
    analyzer flags a second exported constructor, so on the Go side this stays
    review-enforced while Python has TB017.
  - **Why it matters:** the asymmetry is now purely in enforcement, not in what
    the two languages teach. That is the honest state, and `go.md` says so —
    but a consumer's Go repo can still grow a `RequireX` and nothing catches it.
  - **Shape:** a `go/analysis` pass over exported funcs returning their own
    package type, mirroring TB017's "any second door, name-agnostic". The
    interesting Go-specific question is whether `NewX`/`MustNewX` counts as two
    doors — it does not (the `mustnew` convention is a sanctioned panic-wrapper
    over the same door), so the check must exempt the `Must*` twin explicitly.
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

- [ ] **`_annotation_names` duplicates `classify._all_names`** (2026-07-21)
  - **What:** near-identical bodies; the new one additionally resolves string
    forward references. `astutil.py` exists for exactly this sharing. The
    divergence is silent — the classifier still cannot see through a quoted
    annotation.
  - **Start at:** move the forward-ref-resolving version into `astutil.py` and
    route both call sites through it.

- [ ] **Suppression is a substring scan, and TB017/TB018 give it a natural
  surface** (2026-07-21, wave C2 review)
  - **What:** `# tessercheck:ignore` is resolved by scanning the raw source
    line for the marker text, so a *string literal* containing it suppresses a
    real violation with no directive present. TB017 and TB018 suppress on the
    `def` line, where a string DEFAULT ARGUMENT carrying the marker is both
    mypy-clean and natural-looking:
    `def parse(cls, raw: str = "# tessercheck:ignore") -> "Slug"` suppresses
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
    wiring construction door (scheme + host + database), validated, with a
    `redacted()` exit so credentials never reach a log — needs a context that
    actually persists to a real backend. Deferred: a SQL repository CI never
    connects to is CI-unrun code, the same reason `srv/wrk` is omitted.
  - **Why:** demonstrates coordinate VOs at the construction door and the
    end-to-end credential flow in running code; the example currently keeps its
    in-memory `storage` coordinate, so there is no DSN to wrap.
  - **How:** when a context gains a genuine persistence need, add the `Dsn` VO in
    that context's `repo_for`, and decide the CI story then (a real backend in
    CI vs keeping the SQL path exercised some other way — do not ship an
    unexercised repo).
  - **Depends on:** a context that needs to persist. Until then, the
    credential-flow story stays doctrine, not code.
