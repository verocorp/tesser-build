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

## Import-totality wave followups (2026-08-06, branch `worktree-io-import-restrictions`)

- [ ] **python-app conformance + remove the sigcheck CI ratchet.** The wave's
  rules (tesser exactly-once-as-ts, whole-tree totality, pure-core allowlist,
  module-only aliased context imports) fire 173 findings on the freshly
  migrated tree, so the zero-findings CI step became a ratchet
  (`examples/python-app/sigcheck-ratchet` — the accepted-debt baseline as a
  normalized finding set, not a scalar count: any finding outside the baseline
  fails even at an equal total, and an analyzer crash fails closed).
  - **Mechanical (~145):** 123 import-form conversions (`from x.client import Y`
    → `import x.client as client`), 13 `@ts.function` declarations + 7
    `import tesser.context as ts` in srv/bootstrap, 2 Final constants.
  - **Blocked on the rulings below:** 9 srv/bootstrap classes, 5 homeless
    modules, several pure-core hits.
  - **Then:** regenerate the baseline per fix (the sed|sort pipeline in
    test.yml); at zero findings delete `sigcheck-ratchet` and restore the plain
    zero-findings step.
- [ ] **Host-class vocabulary.** A class in srv/bootstrap always flags — no
  shell exists for `Route`, `Match`, `HttpHost`, `CleanupStack`, `App`,
  `HttpConfig`, `Config`. Decide: `tesser.srv` (Host/Request/Response) +
  `tesser.app` (App/Config) shells per the 2026-08-02 package map, or relocate
  the classes.
- [ ] **Homeless root modules.** `errors`, `serialization`, `lifecycle`,
  `cliwire`, `httpwire` belong to no governed package; ruling needed on where
  app-level shared modules live. Same ruling resolves the pure-core hits where
  domain imports `errors`/`serialization`.
- [ ] **Pure-core allowlist candidates (from dogfood evidence only):**
  `urllib.parse` in `campaign.domain.values` / `linkpolicy.domain.policy`
  (pure parsing — likely admit; the matcher accepts exact dotted entries, so
  `urllib.parse` can be admitted without opening `urllib.request`), `copy` in
  `campaign.domain.short_link` (pure — likely admit), `secrets` in
  `campaign.application.service` (ambient entropy — likely inject through a
  port instead of admitting).
- [ ] **Named soundness holes in the import walker (from the ship adversarial
  reviews — evasion paths, none live on the current trees; relative-import
  resolution and top-level-only classification were fixed in-wave):**
  (1) the `conftest` and `__main__` exemptions are basename-anywhere — a
  production `campaign/domain/conftest.py` escapes all rules (fold into the
  conftest-governance followup). (2) `FilesystemSourceReader` sweeps every
  `*.py` under the root with no exclusions (`.venv`, `build`, generated
  code), one unparseable or non-UTF-8 file crashes the whole run, and a role
  FILE colliding with a role PACKAGE (`domain.py` + `domain/__init__.py`)
  aborts on duplicate names — per-file isolation and an exclusion surface are
  consumer-facing needs when sigcheck graduates. (3) the ratchet baseline is
  branch-controlled — a PR can regenerate `sigcheck-ratchet` upward and pass;
  accepted while the ratchet is temporary because the file's diff is itself
  reviewed, but a shrink-only comparison against the base branch is the
  durable fix if the ratchet outlives the conformance wave. (4) quoted
  annotations (`money: 'domain.Money'`) bypass every classification-based
  rule — the exact bug class PR #44 / v0.0.13.1 fixed in tessercheck-py with
  one shared walk; sigcheck needs the same treatment. (5) `async def` is
  invisible to totality — it is neither a declarable function nor a class,
  reads as a loose statement, and evades the def-gated presence checks.
  (6) `TYPE_CHECKING` blocks and `try/except ImportError` optional imports
  have no conformant form (module-level `If`/`Try` are loose statements).
  (7) a submodule appearing under a role FILE silently flips it to the
  role-`__init__` ruleset (detection is name-prefix, not is_package — thread
  the reader's `is_package` bit into the dispatch). (8) `__import__`/
  importlib evade the pure-core allowlist (statically unpreventable at
  reasonable cost — accept and note). (9) a member import from a re-export
  `__init__` (`from rel.domain import Money`) does not classify — blocks
  propagate from defining modules only, so signature rules go quiet; either
  propagate through re-exports or rule that deep imports are canonical.
  (10) srv/bootstrap have no external-import allowlist, and a constants-only
  module can do import-time IO (`OUT: Final[bytes] = subprocess.check_output`)
  with zero findings — fold into the host-vocabulary ruling.
  (11) `TOOLING_MODULES` and CORE_STDLIB's `ast` entry are name-keyed and
  global — any consumer with a top-level `rules.py` inherits the bypass, and
  the allowlist has no per-consumer config surface yet.
- [ ] **Make rules.py conformant** (Chris 2026-08-06). The generator is
  currently exempt via `TOOLING_MODULES` in the whole-tree totality rule;
  make it conform (or rule where tooling lives) and shrink the exemption.
- [ ] **conftest governance** (Chris 2026-08-06). The exemption is now named in
  RULES.md; discuss governing conftest alongside the test-organization work.
  Related: `tests.discovery` / `tests.support` fire the tests-package rule in
  python-app, and `tests.test_shape` imports `tesser.context` — the same
  test-organization pass should settle all three.
- [ ] **Test-module annotation.** When tests declare themselves, flip
  "a test module imports tesser.testing at most once, as ts" to exactly-once.
- [ ] **sigcheck internal cleanups (pre-landing review, deferred as a batch).**
  From the ship review of the import-totality wave: (1) the
  exactly-once-as-ts walk is triplicated (`_app_module_violations`,
  `_import_violations`, `_test_module_violations`) and the statement-totality
  loop is duplicated (`_app_module_violations` vs `_role_module_violations`)
  — extract helpers without breaking the generator's literal-clause guard;
  (2) `import_edges()`/`tesser_imports()` return positionally-decoded
  4-tuples with different slot meanings — make both NamedTuples, and make
  `has_alias` honest (or unrepresentable) for from-edges; (3) hardcoded
  `"tesser.context"`/`"tesser.testing"`/`"tesser"` comparison literals →
  Final constants; (4) the `len(found) == before` legality sentinel → an
  explicit `denied` list; (5) rules.py: derive the conftest/`__main__`
  exemption bullets from the AST guards (like TOOLING_MODULES) so governing
  conftest forces the RULES.md diff, and split the TOOLING_MODULES
  not-found vs wrong-shape errors.
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

## Toolkit

- [ ] **ValueObject-shape adoption decision + classifier support** (shipped as
  experiment 2026-08-01, `tesser-py/` + `examples/vobase/`)
  - **What:** decide whether `tesser.domain.ValueObject` (the mutmut-visible
    VO base) supersedes the frozen-dataclass idiom. If adopted:
    (1) teach `tessercheck-py`'s classifier to recognize `ts.ValueObject`
    subclasses as value objects — today TB003/TB010–TB014 are blind to the
    shape (red-team verified: a raw-primitive accessor that TB010 catches on a
    frozen dataclass passes silently on a ValueObject subclass);
    (2) add the `python -m tessercheck examples/vobase` CI gate — the
    `vobase-example` job in `.github/workflows/test.yml` deliberately omits
    tessercheck until then; TB032 also
    misfires on `tests/test_money.py`'s `_spec` helper under the new shape;
    (3) walk the affected rows in `rationale/coverage.md` and re-render
    `skills/tesser-build/python.md`, bumping skill-version.
  - **Also found in that review, independent of the decision:**
    `examples/python/catalog/money.py` shares the bugs the vobase port fixed —
    `MoneyAmount("NaN")` raises `decimal.InvalidOperation` (not ValueError,
    from `parsed < 0` outside the try), `"Infinity"` is accepted, and `add`
    silently rounds past 28 significant digits. Fix the catalog original (and
    check `examples/python-app`'s VOs for the same class of gap).
  - **Context:** decision frame = (a)+cosmic-ray vs (e)+mutmut, measured
    2026-07-29; five-way prototype data in the session memory
    `go-ddd-mutmut-vo-stance` and `~/.tesser/digests/github.com/boxed/mutmut@*`.

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
  - **What:** the metamorphic sweep's `visit_AsyncFunctionDef` arm and every
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
    - `@dataclass(repr=("# tessercheck:ignore"))` silences **TB001**
      (control fires TB001; spoofed returns nothing).
    - `x = "# tessercheck:ignore"  # banned prose` silences **TB020**.
    - The two checkers this wave ADDED resist it — TB032's `_comment_lines` and
      TB033's `_suppressed_lines` both filter `token.type == tokenize.COMMENT`,
      and a marker appearing only inside a string does NOT suppress them.
  - **So the house pattern is already written, twice, in the new code.** What is
    left is `checks.py:_suppressed` (TB001–TB004) and `comments_check.suppressed`
    (TB020) still reading raw line text. Hoisting the tokenize-based reader into
    `astutil.py` fixes both and collapses the `_SUPPRESS_MARKER` duplication
    tracked above.
  - **Honest bound:** an author who can edit the file can equally write a real
    ignore comment, so this is an inconsistency and an audit-grep blind spot,
    not a privilege boundary. That is why it is not a P1 — but it IS the kind of
    thing that makes a `grep -c 'tessercheck:ignore'` audit lie.

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

- [ ] **Every file is tokenized 3-4 times to build near-identical ignore sets**
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
  - **State as of the TB032 wave:** all five carry `# tessercheck:ignore` in
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
