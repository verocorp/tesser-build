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
