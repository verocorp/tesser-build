# tesser-build

An agent-first application-construction toolkit for **Go** and **Python**. It
takes DDD, hexagonal/onion/clean architecture, and related principles as
*inspiration* — not doctrine — and settles them into one consistent set of
construction conventions, chosen for **changeability**: the next change should
be cheap, and a wrong change should fail loudly at compile/CI time instead of
silently at runtime. The conventions are **enforced where mechanically
decidable** (analyzers), taught where they aren't (the agent skill), and
justified by executable proof (the rationale layer).

What ships: the `tessercheck` analyzers (`go/analysis` multichecker + a
golangci-lint plugin for Go; a zero-dependency stdlib-`ast` analyzer for
Python), an executable rationale layer, an agent skill
([`skills/tesser-build/`](skills/tesser-build/)) that teaches coding agents the
conventions, worked examples kept conformant by CI, and human docs
([start here](docs/start-here.md), [FAQ](docs/faq.md)).

tesser-build is the build-side member of the [tesser](https://github.com/verocorp/tesser)
family: tesser covers adopting *other people's* software (discover, assess);
tesser-build covers constructing *your own* — including the gateway/handler
seams that make later integration and instrumentation cheap.

## Why: the rationale layer

Enforcement without a demonstrated reason gets ignored. [`rationale/`](rationale/)
is the executable case: a neutral fixture (spaceflight navigation, anchored on
the Mars Climate Orbiter unit-confusion loss) whose tests **assert** the wins:
a `Feet`-where-`Meters` call that won't compile, `0°C == 273.15K` under value
equality, a sub-absolute-zero temperature rejected at construction. Benchmarks
show the honest cost (collection value objects pay a defensive-copy
allocation a raw map doesn't). [`rationale/coverage.md`](rationale/coverage.md)
maps each rule to its demo and its checker, with a meta-test that forbids silent
gaps. [`docs/case-study.md`](docs/case-study.md) carries the magnitude measured on
a real ~1,100-commit codebase.

The component-level coverage view — which convention has a Python example, a Go
example, a skill doc, a checker, and executable rationale — is
[`roadmap/ROADMAP.md`](roadmap/ROADMAP.md), **generated** by
[`roadmap/generate.py`](roadmap/generate.py) from the repo itself (CI fails on
drift); the row taxonomy lives in [`roadmap/registry.json`](roadmap/registry.json).

The fixture runs **three contenders** over the same domain: bare primitives
([`rationale/primitive/`](rationale/primitive/)), a realistic *mixture* of
primitives and inconsistently-built value objects
([`rationale/inconsistent/`](rationale/inconsistent/)), and consistent value
objects ([`rationale/valueobject/`](rationale/valueobject/)). The arm-2 tests
prove the point that justifies the checkers: a value object adopted
*inconsistently* reopens the same silent sites a bare primitive does. The
dividend is bought by the **standard**, not by the pattern. See
[`docs/design-three-contender-changeability.md`](docs/design-three-contender-changeability.md).

## What's here

### `cmd/tessercheck`: the Go analyzers

`tessercheck` is a [`go/analysis`](https://pkg.go.dev/golang.org/x/tools/go/analysis)
multichecker. Run it standalone (`tessercheck ./...`) or as a `go vet` tool
(`go vet -vettool=$(command -v tessercheck) ./...`). For editor diagnostics see
[Editor integration](#editor-integration) below; gopls does *not* surface these
analyzers. The analyzers (each independently adoptable, a menu not
all-or-nothing):

| Analyzer | What it enforces |
|---|---|
| `mustnew` | Every value-object constructor `NewX(...) (X, error)` has a paired `MustNewX(...) X` that panics on error. |
| `vofields` | A value object has no exported fields (representation stays encapsulated). |
| `voconstructor` | A value object has a validating constructor `NewX(...) (X, error)` as the single construction path. |
| `stringequality` | A test never compares two value objects by their `.String()` form (`a.String() == b.String()`, or `assert.Equal(a.String(), b.String())`). Compare by value, not by string. |
| `stringer` | A value object has a `String() string` display form. |
| `primitiveaccessor` | A value object exposes no primitive accessors (`ToString` / `To<builtin>`). |
| `comparability` | A value object defines `Equal` when `==` is unavailable (slice/map/func field) or unsafe (pointer/interface field). |

Configuration is a single `.tesser-build.yaml` `exclude:` list at the consumer
repo root, read by every analyzer: the aggregate/entity types that match the
value-object heuristic but aren't value objects. Generate a starter with
`tessercheck -gen-excludes ./...`, then review and curate it. The list is
per-consumer config. Every repo has its own aggregates.

### `tessercheck-py`: the Python analyzer

The Python analog ([`tessercheck-py/`](tessercheck-py/)): a zero-dependency,
stdlib-`ast` conformance analyzer for the frozen-dataclass conventions in
[`skills/tesser-build/python.md`](skills/tesser-build/python.md). Syntactic
checks (`TB001`–`TB004`) plus classification-aware checks (`TB010`–`TB014`)
that distinguish value objects from identity objects. Run
`python -m tessercheck path/to/domain`; flake8-style output; suppress a single
line with a trailing `# tessercheck:ignore`.

### Using it in CI: the `go tool` directive

tesser-build ships a tool, not a CI pipeline. You pin `tessercheck` in your own
module and run it in your own workflow, the same way you'd consume staticcheck
or NilAway. There is no tesser-build-owned GitHub Action; CI wiring stays
yours, so you keep control of your Go version, package scoping, and caching.

**1. Pin the tool** (records a `tool` directive in your `go.mod`; Renovate/
Dependabot bump it like any dependency):

```sh
go get -tool github.com/verocorp/tesser-build/cmd/tessercheck@latest
```

**2. Run it** as a step in your existing workflow:

```sh
go tool tessercheck ./...        # exits non-zero on any violation
```

In GitHub Actions that's one line in *your* `test.yml`, not an owned action:

```yaml
- run: go tool tessercheck ./...
```

**Config:** a single `.tesser-build.yaml` `exclude:` list at your repo root
(generate a starter with `go tool tessercheck -gen-excludes ./...`, then
curate). The standalone run reads it fresh every time, so an exclude edit
always takes effect.

**Large repos (secondary):** `tessercheck` is also a `go vet` tool:
`go vet -vettool=<path-to-tessercheck> ./...`. That path is the more scalable
one on large modules (per-package, file-based intermediates, fact caching).

**Know before you adopt:**
- **Your packages must compile.** The analyzers are type-aware; an unrelated build
  error also reds the check. (For a real module that already builds in CI, a
  non-event.)
- **Go version:** this module is `go 1.25`, and the `tool` directive itself needs
  Go ≥ 1.24. Consumers on an older toolchain can't use the directive.
- **`go.mod` footprint:** the directive pulls `golang.org/x/tools` + `gopkg.in/
  yaml.v3` (and their transitive deps) into your `go.mod`/`go.sum`.
- **A malformed `.tesser-build.yaml` fails the run loud** (a missing one is
  fine). It never silently falls back to "no excludes". That would silently
  change enforcement.

### Editor integration

gopls only runs the analyzers compiled into it, so it cannot surface a custom
`go/analysis` analyzer; there is no setting that points it at `tessercheck`.
Two ways to get the diagnostics into the editor, both **on save** (gopls is the
only on-keystroke path, and it's unavailable to us):

**Native, via golangci-lint (recommended).** `tessercheck` ships as a
golangci-lint
[module plugin](https://golangci-lint.run/docs/plugins/module-plugins/)
([`gclplugin/`](gclplugin/)), so the editor's standard `go.lintOnSave` pipeline
renders the findings as squiggles, no extra extension. One-time setup:

1. Copy [`examples/golangci/.custom-gcl.yml`](examples/golangci/.custom-gcl.yml)
   and build the bundled binary: `golangci-lint custom` (needs golangci-lint v2).
   Put the resulting `custom-gcl` on your PATH (e.g. `~/go/bin`).
2. Enable the linter: copy
   [`examples/golangci/.golangci.yml`](examples/golangci/.golangci.yml) (adds the
   `tessercheck` linter; `.tesser-build.yaml` stays the exclude source).
3. Point the editor at the custom binary, in `.vscode/settings.json`:
   ```json
   "go.lintTool": "golangci-lint-v2",
   "go.lintOnSave": "package",
   "go.alternateTools": { "golangci-lint-v2": "/abs/path/to/custom-gcl" }
   ```
   Same `custom-gcl` runs in CI (`custom-gcl run ./...`) and folds `tessercheck`
   into one lint pass alongside your other linters.

**No-build fallback, via a task.** If you don't use golangci-lint, copy
[`examples/editor/tasks.json`](examples/editor/tasks.json) (runs
`go tool tessercheck`, output parsed by a `problemMatcher`): *Tasks: Run Task →
tessercheck* on demand, or add
[Trigger Task on Save](https://marketplace.visualstudio.com/items?itemName=Gruntfuggly.triggertaskonsave)
for on-save. Same on-save timing, no custom binary, but a third-party extension
instead of the native pipeline. (Background on the trade: `docs/design-ddd-vet-migration.md`
Decisions 14–15.)

### `skills/tesser-build`: the agent skill

The skills rung of the adoption ladder (docs → skills → CI): a copy-in skill
directory that teaches coding agents to classify and build domain objects —
value objects, entities, aggregates — **and to place behavior correctly around
them** (application services, repositories, a domain-service stub), before CI
ever sees the code. [`SKILL.md`](skills/tesser-build/SKILL.md) is a small router
(progressive disclosure: agents read only the concept/language file a task
routes to); construction mechanics ship for **Go** and **Python**. Humans: read
[`docs/start-here.md`](docs/start-here.md) and [`docs/faq.md`](docs/faq.md)
instead.

**Install (copy-in — distribution AND activation, both required):**

- **Claude Code:** copy the directory and add one routing line to your
  repo's `CLAUDE.md`:

  ```bash
  cp -r skills/tesser-build /path/to/your-repo/.claude/skills/tesser-build
  ```

  ```markdown
  <!-- CLAUDE.md -->
  Creating or modifying domain types (new type, field, constructor, validation),
  OR writing a handler/endpoint, a use-case / application or domain service, or
  persistence / repository code → load the tesser-build skill first.
  ```

- **Codex:** Codex has no skill auto-loading, so the routing line does the
  work. Copy the directory anywhere in the repo (e.g. `skills/tesser-build/`) and add
  to `AGENTS.md`:

  ```markdown
  <!-- AGENTS.md -->
  Creating or modifying domain types (new type, field, constructor, validation),
  OR writing a handler/endpoint, a use-case / application or domain service, or
  persistence / repository code → read skills/tesser-build/SKILL.md and follow its routing.
  ```

Without the routing line the skill is just files on disk — agents won't
reliably load it. Hosts covered: Claude Code and Codex; anything else is
untested. `SKILL.md` carries a `skill-version` line; when conventions are
revised the version bumps and release notes name the changed sections —
re-copy to pick them up.

## The conventions, briefly

The machine-enforced core is three rules about value objects (the skill teaches
the broader construction conventions — entities, aggregates, services,
repositories, composition roots — that the analyzers don't yet cover):

1. **Value objects get `MustNew*` helpers.** Value objects are cheap to construct; tests should be able to write `MustNewCustomerID("cust-1")` inline without error-handling noise. Aggregates and entities are not value objects; they carry real construction risk and don't get `Must*` constructors.

2. **Every VO has explicit equality test coverage.** Equality is a load-bearing property of value objects; behavior changes (adding a field, changing comparability) should be caught by a `Test*_Equality` test that exists specifically to lock that behavior.

3. **`.String()` is for display, not for equality.** If you find yourself comparing `a.String() == b.String()` (or `assert.Equal(a.String(), b.String())`), you're doing value-object equality the wrong way; it silently mis-equates value objects that have more than one valid representation. The `stringequality` analyzer flags exactly that comparison; a lone `.String()` (display, a discarded call, a compare against a string literal) is left alone. Exercising stringification belongs in a `Test*_String` test.

## Consumers

- [verocorp/certus](https://github.com/verocorp/certus): reference implementation
- [verocorp/metron](https://github.com/verocorp/metron)
- [verocorp/quanta](https://github.com/verocorp/quanta)

## Status

The checkers originated in certus's `ci/` directory and now run on the `go/analysis` framework: `tessercheck` works as a standalone multichecker, a `go vet` tool, and a golangci-lint plugin. The three consumers above are the proving ground. (This repo was previously named `go-ddd` and the tool `ddd-vet`; renamed 2026-07 — the old name was wrong on both axes, since the toolkit is neither Go-only nor DDD-doctrine.)

Two conventions are documented but not yet machine-enforced: every value object should also carry an explicit `Test*_Equality` and a `Test*_String`. The `equalitytest` checker that would enforce the first is parked; `comparability` ships in its place (it flags a value object that needs `Equal` because `==` is unavailable or unsafe). See [`docs/design-ddd-vet-migration.md`](docs/design-ddd-vet-migration.md).
