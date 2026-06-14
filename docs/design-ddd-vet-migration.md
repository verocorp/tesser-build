# Design: migrate the checkers to go/analysis + add the rubric checkers

**Status:** Add phase BUILT and green (7 analyzers + generator + meta-test, all
tests/vet/gofmt clean). Migrate + Remove not started — paused for eng review (see
Build notes). Supersedes the standalone `cmd/check*` directory-walkers. Builds on
the spike (`ebca404`) that proved the port.
**Date:** 2026-06-13
**Origin:** 2026-06-13 go-ddd session, after the spike validated one ported and
one new analyzer on `go/analysis`.

---

## Goal

Move every checker onto the `go/analysis` framework, behind one binary
(`cmd/ddd-vet`), and add the value-object rubric checks go-ddd doesn't yet
enforce. One framework buys `go vet` composition, editor diagnostics via gopls,
caching, and type-aware checks the AST-only walkers couldn't do. Each checker is
independently adoptable (a menu, not an all-or-nothing).

The standalone `cmd/checkmustnew|checkequality|checkstring` programs go away once
the analyzers and the Action replace them, with their test cases ported first so
no coverage is lost.

---

## The analyzer set

```
  analyzer            rubric  kind     status     identifies VO via   needs type info
  ─────────────────────────────────────────────────────────────────────────────────
  mustnew             #4      port     BUILT ✓    NewX(X,error)       no  (AST)
  stringequality      #6use   port     BUILT ✓    n/a (usage scan)    no  (AST)
  vofields            #1      new      BUILT ✓    NewX(X,error)       yes (struct fields)
  voconstructor       #2      new      BUILT ✓    type decls          yes (find missing ctor)
  stringer            #6      new      BUILT ✓    NewX(X,error)       yes (Implements)
  primitiveaccessor   #6a/6b  new      BUILT ✓    NewX(X,error)       yes (method returns)
  comparability       #7      new      BUILT ✓    NewX(X,error)       yes (Comparable + ptr/iface + Equal)
  ─────────────────────────────────────────────────────────────────────────────────
  (equalitytest       #8)     PARKED   — built (c571e38) then dropped; see Parked below
  (nosetters          #5)     DEFERRED — debatable rule, no clean default-off in multichecker
```

7 analyzers ship. `comparability` (#7) was widened past the original "non-comparable
→ needs Equal" rule to also flag a value object with a **pointer or interface
field** anywhere in its field tree, because there `==` compiles but is
identity-based (pointer) or can panic (interface) rather than a value comparison.
That structural hazard is the highest-likelihood equality footgun, and it
subsumes the reason `equalitytest` existed.

All composed in `cmd/ddd-vet` via `multichecker`, enrolled through the single
`internal/analyzers.All` registry. Shared value-object identification + signal
helpers live in `internal/voscan` and `internal/genexclude` (module-root
`internal/`, not `passes/internal/` — see Build notes #2).

Per-analyzer notes:
- **voconstructor (#2):** every value object has a `NewX(...) (X, error)`. The
  structural rule is "the error-returning constructor exists"; whether the body
  *validates* is semantic and stays the test's job. Identifies candidate VOs by a
  different signal than the others (it's checking for the *absence* of the
  constructor), so it leans on the exclude config + type decls, not the
  constructor itself.
- **stringer (#6):** the value object's method set includes `String() string`
  (`types.Implements` against `fmt.Stringer`). Trivial with type info.
- **primitiveaccessor (#6a/6b):** no method named `ToString`, and no `To*` method
  whose return type is a Go builtin primitive. A `To*` returning another value
  object (e.g. `Feet.ToMeters()`) is fine and must NOT be flagged.
- **comparability (#7):** a value object needs `Equal(X) bool` whenever `==` is
  unavailable or unsafe. Two structural triggers: (a) not Go-comparable
  (slice/map/func field, or a `[0]func()` blocker — `types.Comparable` catches
  these), so `==` is a compile error; (b) **comparable but unsafe** — a pointer
  field (`==` compares identity, not value) or an interface field (`==` compares
  the dynamic value and can panic), found by a recursive walk of the field tree.
  Flag such VOs that lack `Equal`. A value object with only comparable scalar /
  value-struct fields has a correct `==` and is left alone (requiring `Equal`
  there is taste, not a structural hazard). The widened pointer/interface trigger
  is what replaced `equalitytest` — see Parked.

---

## The exclude list — generated, then curated

The value-object heuristic (`NewX(X,error)`) also matches aggregates and
entities, so consumers must exempt those. Rather than hand-maintain that list, a
generator produces it.

**Signals (entity/aggregate → exclude):**
- **Identity** (the strongest signal): an `ID()` method, or a field named
  `id`/`ID`/`<Type>ID`. Value objects have no identity.
- **Mutability:** a pointer-receiver method that assigns to a field (setter /
  state transition).
- **Child collections:** a slice/map field of other domain types (aggregate root).

**Tool:** `ddd-vet -gen-excludes ./...` scans every constructor-bearing type,
classifies it, and writes a starter config with a one-line reason per entry:

```yaml
# Generated by `ddd-vet -gen-excludes` on <date>. Review and edit — each entry is
# a type the checkers SKIP (treated as an entity/aggregate, not a value object).
exclude:
  - Ledger       # has ID() method            (entity)
  - Transaction  # field: id TransactionID    (entity)
  - Transfer     # mutated by (*Transfer).Apply()  (aggregate)
```

**Why generate-and-review, not pure runtime auto-classification:** a wrong "this
is an entity" guess makes the checkers *silently skip a real value object* — the
exact silent gap this toolkit exists to prevent. A generated, version-controlled,
human-ratified list keeps every exclusion explicit and auditable. The generator
removes the blank-page toil; the human keeps the domain call.

**Config:** `.go-ddd.yaml` at the consumer repo root, one `exclude:` list every
analyzer reads (resolves the "shared vs per-analyzer flags" question toward
shared). The generator's identity/mutability detection is shared with the
`comparability` checker, so it isn't pure overhead.

---

## Migration sequence (Add → Migrate → Remove)

```
  Add ─────────────────────────────────────────────────────────────────────── DONE
   1. Port stringequality; build voconstructor, stringer, primitiveaccessor,
      comparability (widened to pointer/interface). Each with analysistest
      coverage that matches or exceeds the original's cases (see Test parity
      below). equalitytest was built then parked (see Parked).
   2. Build the exclude generator (ddd-vet -gen-excludes) + the .go-ddd.yaml
      reader in voscan; wire all analyzers to read it.
   3. Register every analyzer in cmd/ddd-vet (multichecker).

  Migrate ───────────────────────────────────────────────────────────────────
   4. actions/run-ddd-checks: build ddd-vet from go-ddd, then run it inside the
      consumer repo as a go vet tool:
        go build -o $RUNNER/ddd-vet <action_path>/../../cmd/ddd-vet
        cd $GITHUB_WORKSPACE && go vet -vettool=$RUNNER/ddd-vet ./...
      Preserve the Action's input interface (mustnew-exclude / equality-exclude)
      by mapping them onto the config/flags, OR move consumers to .go-ddd.yaml
      and keep the inputs as overrides. Consumers (certus/metron/quanta) keep
      working.

  Remove ────────────────────────────────────────────────────────────────────
   5. Delete cmd/checkmustnew | checkequality | checkstring and their *_test.go
      ONLY after their cases are ported and the Action is green on ddd-vet.
   6. Update README + rationale/coverage.md to point at ddd-vet and the analyzers.
```

**Consequence to accept:** the type-aware analyzers require the target package to
**compile** (go vet builds it). The old walkers were build-free (`parser.ParseDir`,
no type-checking). Consumer repos are real modules that build in CI, so this is
fine, but it is a real behavior change: the Action now runs `go vet` inside a
module that must resolve its dependencies.

---

## Test parity standard (non-negotiable)

Every analyzer gets `analysistest` coverage (`// want` comments on testdata) that
matches or exceeds the standalone checker it replaces. The originals carry
469–503 lines of table tests each; their cases must be reproduced, not
approximated. Parity checklist to port:

- **mustnew:** VO with counterpart (pass); VO missing it (flag); excluded type
  (skip). The shared VO-matcher parity — factory `NewCollect -> Operation` (not
  matched, suffix != return type); generics `Foo[T]` and `Foo[T, U]`; non-`New`
  funcs ignored; methods with receivers ignored; pointer/qualified/slice/map/
  func/chan/interface return shapes — lives once in `internal/voscan` table
  tests (`voscan_test.go`), shared by every analyzer.
- **stringequality:** `.String()` inside `Test*_String` (allowed); `.String()`
  elsewhere in a test file (flag); package-level call; nested call; non-test files
  not scanned.
- **voconstructor / stringer / primitiveaccessor / comparability:** positive +
  negative per rule; the `To*`-returns-VO exemption for primitiveaccessor; a
  non-comparable VO with and without `Equal` for comparability; exclude honored by
  every analyzer.
- **generator:** entity classified by ID() method; by id field; aggregate by
  pointer-receiver mutator; a true VO NOT excluded; the emitted YAML parses back.

A meta-test (`internal/analyzers`, sibling-in-spirit of
`rationale/coverage_test.go`) enforces this two ways: every registered analyzer
must have a `passes/<name>/` with a `_test.go` and a `testdata/` dir (no checker
lands untested), and every `passes/<dir>` that defines an `Analyzer` must be in
`analyzers.All` (no built-but-forgotten checker sits out of `ddd-vet`). All 7
shipping analyzers use `analysistest`; the test checks for test coverage
generally rather than `analysistest` specifically, which is what let the parked
`equalitytest` use a `go vet`-faithful harness without tripping it.

---

## Decisions (this session)

1. **Framework:** `go/analysis`, one `cmd/ddd-vet` multichecker. Go 1.25 bump
   (from `golang.org/x/tools`) accepted; consumers move to 1.25.
2. **Old checkers:** removed after migrate; test cases ported first.
3. **Exclude:** generated shared `.go-ddd.yaml`, human-curated, read by all
   analyzers. Not per-analyzer flags, not pure runtime auto-classification.
4. **no-setters (#5):** deferred (debatable rule; no clean default-off).
5. **Dropped earlier:** spec pattern (#3, an entity/aggregate concern, not a VO
   rule) and domain-methods-enforce-consistency (#9, a conformance property for
   tests, not a structural linter).
6. **equalitytest (#8) dropped, comparability (#7) widened (eng review).** The
   existence tripwire was traded for a structural check of the actual `==` hazard
   (pointer/interface fields). 7 analyzers ship. See Parked + Risks.
7. **Action goes `.go-ddd.yaml`-only (eng review).** At Migrate, drop the
   `mustnew-exclude` / `equality-exclude` Action inputs entirely (no back-compat
   shims). Consumers (certus/metron/quanta) move their lists into the file; it is
   accepted that they break until migrated. One way to say a thing, not two.
8. **Compile-required is accepted (eng review).** `go vet` needs the consumer
   package to build; an unrelated compile error now also reds the DDD check.
   Accepted on purpose; document it in the Action README at Migrate.
9. **Config cache: force a clean run for now (eng review).** At Migrate the Action
   forces a fresh vet (e.g. `go clean -cache` or a scratch `GOCACHE`) so a
   `.go-ddd.yaml` edit always takes effect, since `go/analysis` doesn't track the
   file as an action input. The principled fix is parked (see Parked).

## Risks

- **comparability (#7)** is the highest-complexity analyzer (recursive field-tree
  walk for pointer/interface hazards). It checks that `Equal` *exists*, not that
  its logic is correct — equality-correctness is the parked gap (see Parked).
- **Generator misclassification** is mitigated by review, but a noisy generator
  erodes trust — tune signals against certus's real aggregates before shipping.
- **Build-required targets:** if a consumer repo doesn't compile in CI, `go vet`
  fails for the wrong reason. Acceptable for real modules; document it.

## Build notes & open questions for eng review (Add phase complete)

The Add phase is built and green (`go test ./...`, `go vet ./...`, `gofmt -l .`).
All 7 analyzers compose in `ddd-vet`; an end-to-end `go vet -vettool` run flags
incomplete VOs and skips `.go-ddd.yaml`-excluded entities. Findings that surfaced
during the build — the spike's two analyzers were intra-file and never hit these:

1. **equalitytest — RESOLVED by dropping it (eng review).** The finding was: it
   is a source↔test correlation, which `go/analysis` splits by package variant.
   Empirically (verified with a real `go vet` run): cmd/go vets the
   *test-augmented* variant (production + **in-package** `_test.go`) in one pass,
   so an in-package `Test*_Equality` correlates correctly, but an **external**
   `package foo_test` is vetted without the constructors, so an externally-tested
   VO false-positives. The eng review concluded the deeper problem is that
   `equalitytest` only checks a *name exists* — a hollow `Test*_Equality{}` passes
   it — so its value was mainly as an agent tripwire, while the real equality
   hazard (a comparable struct whose `==` is identity/panic via a pointer or
   interface field) went unguarded. Decision: **widen `comparability` to that
   hazard and drop `equalitytest`**, which also makes the in-package/external
   variant question moot. See Parked. (`stringequality` had no such problem — its
   violations live in the test files themselves — and ships.)

2. **Shared helpers are in module-root `internal/`, not `passes/internal/`** (as
   the table above originally said). The Go internal-package rule makes
   `passes/internal/*` importable only under `passes/`, and `cmd/ddd-vet` is not;
   the generator forced the move. Functionally identical, still non-public.

3. **voconstructor's heuristic** (exported struct, ≥1 field, all-unexported, no
   `NewX(X,error)`) has a real false-positive surface: deliberate zero-value
   types that share the shape. They go on the exclude list. Tune against certus's
   real types before relying on it in CI.

4. **`-gen-excludes` never clobbers an existing `.go-ddd.yaml`** (it is
   human-curated; overwriting could drop a hand-added exclusion). First run
   writes it; thereafter it prints to stdout to diff in.

5. **Config caching caveat.** Analyzers read `.go-ddd.yaml` from disk, which
   `go/analysis` does not track as an action input. A config edit may not
   invalidate the build cache; a `go clean -cache` or vettool rebuild forces it.
   Relevant to how the Action invokes `ddd-vet` (Migrate phase).

6. **stringer / primitiveaccessor / comparability check the VALUE method set**
   deliberately — a value object is used by value, so a pointer-receiver
   `String`/`Equal` does not satisfy the rule (and is flagged). Confirm this
   strictness is what we want.

## Parked — equalitytest (#8) and the equality-correctness gap

`equalitytest` was built (commit **c571e38**, full `go vet`-faithful harness +
parity tests) and then removed from the set. It only verifies a function named
`Test<Type>_Equality` *exists* — a hollow `func TestX_Equality(t *testing.T){}`
passes it — so it is an agent/author tripwire ("did you think about equality?"),
not a guarantee. Recover from git if we want it back.

**Revisit if:** we want the agent-nudge value back AND have resolved the
in-package/external variant question (codify in-package, or keep it as the
`cmd/checkequality` directory-walker which has no variant problem).

What the shipped set does and does NOT cover on equality, so the gap is explicit:

```
covered now:  comparability (#7) — Equal exists when == is impossible (slice/map/
                func) or unsafe (pointer/interface)
              stringequality (#6use) — no .String()-based equality in tests
              vofields / primitiveaccessor / stringer — encapsulation preconditions
NOT covered:  is the Test*_Equality / Equal logic actually CORRECT (hollow test,
                skips a field, not symmetric) — needs a shared equality-laws
                assert helper or mutation testing, not a linter
              callers using == where Equal is required, and VO-with-Equal used as
                a map key — would be a future `equaluse` usage-scan analyzer
              float/NaN fields — left to the type's own test
              VOs not identified (non-error constructor, factory-named, primitive
                VOs) — escape VO identification entirely
```

These are follow-up scope, not blockers for Add→Migrate→Remove.

**Parked: cache-correct config.** The Migrate-time "force a clean vet run"
(Decision 9) is a blunt fix that throws away `go vet`'s caching whenever excludes
might have changed. The principled version: have the **Action** read
`.go-ddd.yaml` and pass the resolved excludes as per-analyzer `-exclude` flags,
instead of each analyzer reading the file from disk. Analyzer flags ARE part of
`go vet`'s action cache key, so a changed exclude set would invalidate the cache
correctly and a clean run would no longer be needed. Revisit when the clean-run
cost (cold cache every CI run) actually bites.

**Parked: voconstructor adoption scoping (decision deferred).** Direction agreed:
require a constructor for all VOs (it is the consistency/changeability principle,
and "requires a constructor" means the construction path exists, NOT that it
validates — a trivial `NewX(...) (X, error)` returning nil error is fine; the
always-error signature is itself the consistency-for-changeability choice so
adding validation later is zero call-site churn). The zero-value-useful idiom is
not in tension here: it applies to mutable utility types, which are voconstructor
false positives to exclude, not real VOs. What is NOT decided: how a large
existing codebase opts in/out. When tackled, the recommendation is to resist a
four-axis (package/dir/module/object) config matrix — it is accidental complexity
and a silent-misconfig surface — and instead: (1) add a **default-off opt-in
mode** (strangler-fig rollout; default-on floods a big codebase day one), (2) lean
on per-package/dir scoping that is mostly free already (`go vet` package patterns
+ `FindConfig` walk-up), (3) keep the per-object `.go-ddd.yaml` exclude, (4) add
an inline `//ddd:ignore` directive only if the file proves too coarse. Note the
one-time migration cost on existing code is paid by humans+agents regardless;
agents lower steady-state cost, not migration cost.

## Out of scope

no-setters (#5), the leaking-representation rationale demo (still catalogued in
the changeability design doc), and the primitive-hunter port (separate, larger:
it *finds* primitives that should be VOs rather than checking the shape of VOs
that exist).
