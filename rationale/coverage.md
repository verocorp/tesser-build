# Coverage matrix — rule ↔ demonstrated win ↔ enforcement

This is the single source of truth linking each value-object rule to (a) the
executable demo in this `rationale/` package that shows the bug it prevents, and
(b) the `ddd-vet` analyzer that enforces it (if one exists). `coverage_test.go`
fails on a **silent gap** — a shipping analyzer (`internal/analyzers.All`) with no
row here, or a row naming a test that doesn't exist. It tolerates the honest ❌/⚠️
rows by design: the rationale makes the case for the whole discipline, and some
analyzers enforce a rubric rule that has no demo *yet* — both directions are
tracked openly, neither is allowed to be silent.

> Enforcement moved from the standalone `cmd/check*` directory-walkers to the
> `go/analysis` analyzers in `ddd-vet` (see
> [`docs/design-ddd-vet-migration.md`](../docs/design-ddd-vet-migration.md)). The
> rows below name the analyzers; the guard keys off the `analyzers.All` registry
> so it stays live after the old walkers are deleted.

| Value-object rule | Demonstrated win (test in this package) | Real-world anchor | Enforced by | Status |
|---|---|---|---|---|
| Distinct types instead of bare primitives | `TestTypeConfusion_ValueObjectRejectsWrongUnit` — `Feet` where `Meters` expected won't compile | Mars Climate Orbiter (1999, $327M) | — | ❌ no analyzer yet |
| Value equality, not representation equality | `TestEquality_ValueObjectIsRight` — `0°C` == `273.15K` | scale/representation collision | — (`equalitytest` parked; `comparability` guards the structural `==` hazard — separate row — but no analyzer locks the equality *test*) | ⚠️ enforcer dropped |
| Constructors validate invariants | `TestValidation_ValueObjectRejectsBadInput` — sub-absolute-zero rejected | physically impossible state | `voconstructor` (enforces the validating constructor *exists* as the single path; that the body validates stays the test's job) | ⚠️ structural, not semantic |
| VO constructors get `MustNew*` helpers | `TestMustReimplementation_HandRolledHelpersDiverge` (consistency demo, table below) | without it, authors reinvent divergent must-helpers | `mustnew` | ✅ consistency demo |
| `.String()` is for display, not equality | `TestEqualityByString_InconsistentIsWrong` — display-string equality mis-equates `0°C` and `273.15K` | `a.String() == b.String()` mis-equates multi-rep VOs | `stringequality` | ✅ 1:1 |

**Reading the gaps:** the ❌ row (distinct types) is a win go-ddd does not yet
enforce. The two ⚠️ rows are honest partials worth naming: **value equality** lost
its enforcer when `equalitytest` (the `Test*_Equality` existence tripwire) was
parked — `comparability` now guards the structural `==` hazard (pointer/interface
fields, see the rubric table) but nothing locks the equality *test* itself, the
parked equality-correctness gap in the design doc; **constructor validation** is
enforced only structurally (`voconstructor` checks the constructor exists as the
single path, not that its body validates). Nothing here is a *silent* gap.

## VO-construction rubric — enforced, demo pending

These analyzers ship in `ddd-vet` and enforce value-object rubric rules, but the
`rationale/` package does not yet carry an executable demo of the leak each
prevents. They are the inverse of the ❌ rows above (a demonstrated win with no
checker): here the checker leads its demo. Tracked openly so the gap is not
silent; the demos are backlog, not a blocker.

| Rubric rule | Analyzer | Demo (test in this package) | Status |
|---|---|---|---|
| #1 no exported fields (encapsulate representation) | `vofields` | — | ❌ demo pending |
| #6 a value object has a `String() string` display form | `stringer` | — | ❌ demo pending |
| #6a/6b no primitive accessors (`ToString` / `To<builtin>`) | `primitiveaccessor` | — | ❌ demo pending |
| #7 `Equal` exists when `==` is unavailable or unsafe (slice/map/func, or pointer/interface field) | `comparability` | — | ❌ demo pending |

## Consistency dimension — the case for the *standard*, not just the pattern

The matrix above is arm 1 (primitive) vs arm 3 (consistent value object). But a
value object adopted *inconsistently* buys nothing on the change-speed axis: if
every author holds a different idea of what a VO is, the result leaks
representation and construction the same way a bare primitive does. **Inconsistent
VOs ≈ no VOs.** `rationale/inconsistent/` is arm 2 — a realistic mixture of bare
primitives and non-conforming value objects — and each row below proves it
reopens a silent site the consistent VO closes. This is the rationale for the
*analyzers* (and the coming skills): they enforce the one canonical form that
actually delivers the dividend.

| Non-conformance (arm 2) | Silent site it reopens | Demo (test in this package) | Real-world anchor | Analyzer that plugs it | Status |
|---|---|---|---|---|---|
| **Partial adoption** — some concepts left primitive while others get wrapped | type confusion / wrong unit | `TestPartialAdoption_InconsistentAdmitsWrongUnit` | a slot left a bare string across 43 call sites while its VO existed | — | ❌ no analyzer yet |
| **Scattered validation** — no single constructor; the invariant copied across builders | bad value admitted at the site that forgot; rule change is an N-site edit | `TestScatteredValidation_InconsistentAdmitsBadValue`, `TestScatteredValidation_RuleLivesInManyPlaces` | pricing primitive-obsession postmortem (parent-validates-child) | `voconstructor` (forces a single constructor path; does not check the body validates) | ⚠️ structural |
| **Equality via `.String()`** — comparing the display form | scale/representation collision | `TestEqualityByString_InconsistentIsWrong` | `.String()`-as-equality residue (test-VO audit) | `stringequality` | ✅ |
| **Must-helper reimplementation** — no canonical `MustNew`, so authors hand-roll divergent ones | construction behavior diverges (panic vs admit vs clamp) on the same bad input | `TestMustReimplementation_HandRolledHelpersDiverge` | 9 ad-hoc `must*` helpers across 5 files (`e7a470c`) | `mustnew` | ✅ |
| **Naming drift** — same value category, inconsistent naming convention | a format/meaning change silently misses the drifted literal | `TestNamingDrift_InconsistentMixesConventions`, `TestNamingDrift_FormatChangeMissesTheOutlier` | `revert_earn` underscore vs hyphen siblings (realized-harm) | — | ❌ no analyzer yet |

The ❌ rows are the analyzer backlog, now each grounded in a demonstrated leak:
**partial adoption** maps to the distinct-types checker (type-confusion /
primitive-should-be-VO) still unbuilt. **Naming drift** is a *new* candidate the
demo surfaced: a separator/format-convention checker. The ✅ rows show `mustnew`
and `stringequality` each plug a real consistency leak, and the ⚠️ row shows
`voconstructor` plugs scattered validation structurally (single path) without
yet checking the validation body.

A further dimension the metric measures but no analyzer yet gates: the **leak rate
past docs + skills** (how many inconsistencies CI catches when agents write *with*
the skills that say exactly how to build a VO). That is the deepest analyzer
rationale; it is gated on the skills landing in this repo. See
[`docs/design-three-contender-changeability.md`](../docs/design-three-contender-changeability.md).

## Skill materializations — rule ↔ renderings (manual v1)

The conventions are materialized in prose several times over: a concept file,
two language mechanics files, an FAQ entry, and a resolver route in
[`skills/ddd/`](../skills/ddd/) plus [`docs/faq.md`](../docs/faq.md). Separately
authored renderings drift; this matrix is the map of which renderings carry
each rule, so a rule change is a walk across its row in one commit (and a
`skill-version` bump in `SKILL.md`). The rows are maintained by hand, but the
**structural** check is machine-enforced: [`coverage_test.go`](coverage_test.go)
(`TestSkillMaterializationAnchors`) asserts every heading anchor named in this
matrix exists in its file, so a renamed heading or a routeless concept file
fails CI. It does **not** check semantic agreement between renderings — that
stays human review, and the row tells the reviewer which pairs to diff. `—` is
an honest gap, not an oversight: not every rule earns every rendering.

The **strategic-design** rows below carry `—` in the `go.md`/`python.md`/FAQ
columns on purpose: subdomains, bounded contexts, and ubiquitous language are
problem-and-solution-space *reasoning*, not a type you construct, so they have a
concept-file rendering and a resolver route but no language mechanics to
materialize. That is the honest-gap `—`, not an omission.

| Rule | Concept file | go.md | python.md | FAQ | Resolver route (SKILL.md) |
|---|---|---|---|---|---|
| One validating constructor, single construction path | `value-objects.md#rules` | `go.md#value-objects` | `python.md#value-objects` | #5 | "writing or changing a constructor" |
| VO immutability (no setters; behavior returns new values) | `value-objects.md#rules` | `go.md#value-objects` | `python.md#value-objects` | #3 | — |
| Equality by value; never by string form | `value-objects.md#rules` | `go.md#value-objects` (equality paths) | `python.md#value-objects` (equality paths) | #8 | "comparing two domain objects in a test" |
| `MustNew*` for VOs only (never entities/aggregates) | `value-objects.md#tests-you-must-write` | `go.md#value-objects` + `go.md#entities` (no-Must rule) | `python.md#value-objects` (no-twin note) | #9 | — |
| Primitive fields: check-then-wrap (no VO theater) | `value-objects.md#is-this-what-im-building` | — | — | #4 | "adding a primitive-typed field" |
| Entity identity explicit; equality is identity | `entities.md#rules` | `go.md#entities` | `python.md#entities` | #1 | "modeling a brand-new concept" |
| Mutability is a domain decision (fact vs lifecycle) | `entities.md#decisions-you-must-make` | `go.md#entities` + `go.md#aggregates` | `python.md#entities` + `python.md#aggregates` | #3 | "needing mutation / a state transition" |
| Aggregate = consistency boundary; invariant in the root's constructor | `aggregates.md#rules` | `go.md#aggregates` | `python.md#aggregates` | #2, #10 | "adding a rule that spans two or more owned objects" |
| Defensive copies on collection accessors | `aggregates.md#rules` | `go.md#aggregates` | `python.md#aggregates` | — | "adding a collection field" |
| Aggregates are never value-compared (non-comparability) | `aggregates.md#rules` | `go.md#aggregates` | `python.md#aggregates` | — | — |
| Spec leaves are primitives; constructor is the boundary | `value-objects.md#decisions-you-must-make` | `go.md#the-spec-pattern` | `python.md#the-spec-pattern` | #6 | "writing or changing a constructor" |
| Spec nesting mirrors composition (composition-frequency coupling) | — (mechanics-owned) | `go.md#the-spec-pattern` | `python.md#the-spec-pattern` | #7 | "writing or changing a constructor" |
| Validation belongs to the value, not parents | `value-objects.md#rules` | `go.md#entities` (wrap, don't re-check) | `python.md#entities` | #5 | — |
| Application service = coordination, no business logic (4-step: convert→delegate→persist→respond) | `application-services.md#rules` | `go.md#application-services` | `python.md#application-services` | #13 | "writing a use-case / orchestration / a service method" |
| Response is a DTO, not a domain object (no service-boundary leak) | `application-services.md#rules` | `go.md#application-services` | `python.md#application-services` | — | "writing a use-case / orchestration / a service method" |
| Domain-logic leakage checks (canonical signal list) | `application-services.md#domain-logic-leakage-checks` | `go.md#application-services` | `python.md#application-services` | #14 | "business logic that wants to live in a service or handler" |
| Handler is thin: parse/auth → call app service; no domain math/repo | `application-services.md#is-this-what-im-building` | — | — | #15 | "writing a handler / endpoint / controller" |
| Repository = whole aggregate in, reconstructed out, no business logic | `repositories.md#rules` | `go.md#repositories` | `python.md#repositories` | #16 | "loading or saving an aggregate, or writing a repository" |
| Repo draws persistence-vs-query line; query object ≠ spec | `repositories.md#rules` | `go.md#repositories` | `python.md#repositories` | — | "loading or saving an aggregate, or writing a repository" |
| Domain service = rare no-single-owner case (stub; check for a missing type first) | `domain-services.md#is-this-what-im-building` | — (mechanics deferred) | — (mechanics deferred) | — | "domain logic that fits no single object" |
| Public interface = decoupling boundary; `Client` speaks DTOs, satisfied by embedding the service | `composition-root.md#the-public-interface` | `go.md#the-composition-root` | `python.md#the-composition-root` | #17 | "exposing a component/service behind a public interface" |
| Composition root = single wiring site; returns/injects interfaces never domain objects, chooses the impl, injects the handler | `composition-root.md#the-composition-root` | `go.md#the-composition-root` | `python.md#the-composition-root` | #18 | "wiring the app / writing an entry point / a composition root" |
| Subdomain = problem-space area classified Core/Supporting/Generic; the tier sets modeling investment | `strategic-design.md#subdomains` | — | — | — | "classifying a subdomain" |
| Bounded context = one model + one language boundary; contexts talk through the `Client`+DTOs, never each other's internals | `strategic-design.md#bounded-contexts` | — | — | — | "deciding where a context boundary goes" |
| Ubiquitous language = one term one meaning per context; the code speaks the domain's words | `strategic-design.md#ubiquitous-language` | — | — | — | "naming the domain language" |

The heading anchors above are load-bearing: renaming a heading in a skill file
is a breaking change to this matrix (and to the resolver's routes). Authoring
rules for the skill files live in
[`docs/skill-authoring.md`](../docs/skill-authoring.md).

## Changeability arms — executable proof per decision

A separate dimension from the VO win tables above: each **skill decision** is put
under an executable contender-arm benchmark that proves it earns its place on the
**changeability** axis (how the cost of a representative change scales with the
number of dependents N), or surfaces what to change. The arms are scored by a
predeclared contract, `changeability/SCORING.md`, committed before any arm; an
outside model (Codex) authors the coupled + red-team arms, committed with their
provenance. This matrix row is the anti-silent-gap net for that dimension:
`coverage_test.go` also globs `changeability/anchor/*_test.go` and
`changeability/nooutward/*_test.go`, so a named arm test that is renamed or deleted
fails the guard.

| Decision (skills/ddd) | Change(s) | Arms | Result | Committed tests |
|---|---|---|---|---|
| **Public interface** (`composition-root.md`) | C1 backend migration (`-tags swap`); C2 substitution (`-tags subst`) | decoupled (depends on `Client`); coupled fan-out + 3 realistic patterns; Codex red-team `portless` (facade); a fake for substitution | **C1 is TIED** by the lower-ceremony facade (a facade decouples from a backend too) — decoupled 0 vs coupled N at N=8/16. **C2 the interface WINS** — it substitutes a fake at 0 edits; the facade cannot (no seam). | `anchor/`: `TestDecoupledArm_SurvivesBackendSwap`, `TestContrast_C1_DecoupledFlat_CoupledTracksN`, `TestInterfaceDependent_SubstitutesForFree`, `TestFacadeDependent_CannotSubstituteWithoutEdit` |
| **No outward representation** (`application-services.md` Respond) | D3 outward-representation migration (`-tags repv2`: response DTO field reshaped) | decoupled (operate on `domain.Maneuver` value objects); coupled fan-out + 2 realistic patterns (`webhookpayload`, `burnsort`); Codex red-team `burnquery` (query facade) | **Decision 3 WINS** — a domain that emits its own DTO fans a wire reshape out to N; the decoupled arm is 0, coupled N at N=8/16. The red-team facade is the *sanctioned* mapper (0 edits) — it does not justify a domain emitting a DTO; it only ties on read-ceremony. **No compile guard** (a dumb DTO imports nothing → no cycle); the fan-out is the proof. | `nooutward/`: `TestDecoupledArm_SurvivesRepMigration`, `TestContrast_DecoupledFlat_CoupledTracksN` |

**Findings folded to doctrine.** (1) C1 alone under-justifies the interface, so
`composition-root.md` teaches the interface earns its place via *substitutability*,
not backend-swap-survival ("Why an interface and not just a facade?"). (2) For
decision 3, `application-services.md` folds the alternatives the *anatomy-of-a-
perfect-technical-answer* way: the domain never emits its DTO, and for reads a
query/projection facade beats exposing the domain VO graph — with the axis each
wins/loses. Provenance: `changeability/{anchor,nooutward}/adversary_provenance.md`.
Real-code corroboration for the interface: `changeability/anchor/CORROBORATION.md`.

Decisions 1 (app-service SRP) and 4 (repo speaks domain objects) are pending — each
needs its **discriminating** change (the facade/DTO lesson: not every change
discriminates the rule you defend).

## Run

```
go test ./rationale/...                 # the wins + the matrix meta-test
go test -bench=. -benchmem ./rationale/ # the adversarial cost (collection-VO defensive-copy tax)
./rationale/measure-ablation.sh ...     # measure changeability on your own repo
```

## Python enforcement (ddd-vet-py)

The Go analyzers above are `go/analysis`; they do not run on Python. The Python
analog is [`ddd-vet-py`](../ddd-vet-py/) — a zero-dependency stdlib-`ast` tool
that enforces the *syntactically decidable* subset on the frozen-dataclass
substrate `skills/ddd/python.md` teaches. Roughly half the Go ruleset dissolves
(`mustnew` — Python constructors raise) and the rest reframe to the dataclass
grain. `primitiveaccessor`, first dropped as theater, is **reinstated** as
`DDD010`: it is the load-bearing spec/VO discriminator, keyed on the
**identity-taxonomy classifier** (`ddd_vet/classify.py`) — a whole-tree two-pass
pass that classifies each class as value_object / spec / identity_object / other.
Its own meta-test (`ddd-vet-py/tests/test_meta.py`) is the Python analog of this
matrix's silent-gap guard: it fails if a registered check has no good/bad
fixture, if an unregistered code is emitted, or if the analyzer is not clean on
the canonical `examples/python` tree. Full rationale:
[`docs/design-python-analyzer.md`](../docs/design-python-analyzer.md) and the
classifier design
[`docs/design-python-domain-detection.md`](../docs/design-python-domain-detection.md).

| Go analyzer | Python check | python.md rule | Fixture (`ddd-vet-py/testdata/`) |
|---|---|---|---|
| `vofields` | `DDD001` frozen-dataclass | "`frozen=True` always" | `ddd001/{good,bad}.py` |
| `comparability` | `DDD002` hashable-fields | collection VO backs itself with a sorted tuple (classification-aware: fires only on a `VALUE_OBJECT`, so a spec / persistence row is exempt) | `ddd002/{good,bad}.py` |
| `voconstructor` | `DDD003` no-setattr-bypass | "no setters, no mutation" (canonicalize only in `__post_init__`) | `ddd003/{good,bad}.py` |
| `stringequality` | `DDD004` no-string-equality | "Never `str(a) == str(b)`" | `ddd004/{good,bad}.py` |
| `primitiveaccessor` | `DDD010` no-primitive-exposure | a value object hides its primitive (the spec/VO discriminator), keyed on the identity-taxonomy classifier | `ddd010/{good,bad}.py` |
| — no Go analyzer (defensive-copy check is Python-only today) | `DDD011` no-collection-leak | an aggregate/entity accessor returns a defensive copy, never the backing mutable collection, keyed on the classifier | `ddd011/{good,bad}.py` |
| — no Go analyzer (reference-boundary check is Python-only today) | `DDD012` reference-roots-by-id | an aggregate references another root by its ID value object, never by holding the root object; keyed on the whole-tree registry (a root is a reference-identity entity that embeds ≥1 entity — `is_aggregate_root`) | `ddd012/{good,bad}.py` |
| (construction) | `DDD013` construct-through-spec | a structured domain object (entity/aggregate) constructs through `__init__(self, spec)`; no separate `from_spec` factory (the value-taking-ctor half is a deferred extension) | `ddd013/{good,bad}.py` |
| `comparability` / `equalitytest` | `DDD014` equality-by-type | equality matches the stereotype: VO compares by value (never blocks); entity defines `__eq__`+`__hash__` together (by ID); aggregate root blocks equality (`__eq__ = None`/`__hash__ = None`) — keyed on the classifier | `ddd014/{good,bad}.py` |
| `mustnew` | — dissolved | "No `Must*` twin is needed" | — |
| (type-aware residual) | — deferred (P1) | primitive-obsession field resolution; identity-`__eq__` field | — |
