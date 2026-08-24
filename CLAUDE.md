# tesser-build — agent guide

This repo is an **application-construction toolkit** (DDD + hex/onion/clean as
inspiration, chosen for changeability, enforced where mechanically decidable;
the build-side member of the tesser family): the `go/analysis` analyzers in
`cmd/tessercheck` (composed from `internal/analyzers.All`), a golangci-lint module
plugin (`gclplugin/`), the Python analyzer (`tessercheck-py/` — the `TB0*`
checks) and its packaged console entry point (`tessercheck-cli/` — the
`tessercheck-check` command, so a consumer repo can run the analyzer from an
install instead of a checkout), a Python runtime library (`tesser-py/` — `tesser.domain.ValueObject`,
the repo's first shipped runtime dependency rather than a build-time checker;
candidate mutation-testable VO base — the mutmut-visibility claim is asserted
by the ecosystem test in `tesser-py/tests/ecosystem/mutmut/`), an executable
rationale layer (`rationale/`), an agent
skill (`skills/tesser-build/` — Go + Python construction guidance, copy-in distributed
to consumers), and human docs (`docs/start-here.md`, `docs/faq.md`). If you are
writing or changing domain objects here — or in a consumer repo (certus, metron,
quanta, and a pilot consumer) — follow the conventions below, because this repo is what
enforces them in CI.

**Creating or modifying domain types (new type, field, constructor, validation),
OR writing a handler/endpoint, a use-case / application or domain service, or
persistence / repository code → read `skills/tesser-build/SKILL.md` and follow its
routing.** This repo
dogfoods its own skill; `examples/ddd/` is the acceptance-gate output and the
canonical worked example (kept conformant by CI). When you change a convention,
walk its row in `rationale/coverage.md`'s skill-materializations matrix and
update every rendering in the same change (rules in `docs/skill-authoring.md`);
bump `skill-version` in `skills/tesser-build/SKILL.md`.

## The conventions (what the analyzers enforce)

1. **Value objects get `MustNew*` helpers.** Every `NewX(...) (X, error)` VO
   constructor has a paired `MustNewX(...) X` that panics on error; tests use
   `MustNewX` for inline construction. (`mustnew` analyzer.) Aggregates and
   entities are *not* VOs — they carry real construction risk and get no `Must*`.
2. **Every VO has explicit equality test coverage** — a `Test*_Equality` that
   locks equality semantics, so a later field/comparability change is caught.
   This convention stands, but is *not* machine-enforced: the `Test*_Equality`
   existence check (`equalitytest`) was parked. What ships instead is
   `comparability`, which flags a VO that needs `Equal` because `==` is
   unavailable (slice/map/func) or unsafe (pointer/interface field). See
   `docs/design-ddd-vet-migration.md` "Parked".
3. **`.String()` is for display, not equality.** The `stringequality` analyzer
   flags a test that compares two value objects by their string form —
   `a.String() == b.String()` or `assert.Equal(a.String(), b.String())` — because
   that silently mis-equates multi-representation VOs; compare by value
   (`==`/`Equal`). It fires only on a comparison whose *both* sides are `.String()`
   calls: a lone display call, a discarded `_ = x.String()`, a literal compare
   (`x.String() == "USD 100"`), and a stdlib `.String()` are all left alone.
   Testing stringification inside a `Test*_String` test stays the convention, but
   (like rule 2) is not itself machine-enforced.

These three are the value-object core, not the whole enforced set. The Python
analyzer also carries the identity taxonomy (`TB010`–`TB012`), the
serialization norm (`TB015`–`TB018`), the comments norm (`TB020`, mirrored by
the Go `comments` analyzer), the import norm (`TB050`–`TB066` — every module in
the tree carries an import row keyed on where it sits; there are no exempt
modules, so a root module and a `conftest` are leaves that import nothing from
the tree), and the testing norm (`TB030` — a test double is a hand-written
fake, never a mocking library; `TB070` — placement carries the tier, so where a
test lives fixes what it may import; `TB074` — every implementation module
carries exactly one sibling test file named for it, and every sibling test
file names the module beside it; `TB071`/`TB072`/`TB073` — the totality check over
test modules: every module-level function is a test, a declared `@ts.helper`,
or a declared `@ts.fake` (`TB071`), a class is a `Test`-prefixed test class
holding only test methods or a declared `@ts.fake` (`TB072`), and what does
not classify is a finding;
`skills/tesser-build/testing.md`).
The full check list with per-code rules is `tessercheck-py/RULES.md`; which
convention has a doc, an example, and a checker is `roadmap/ROADMAP.md`.

Build a VO the canonical way: private fields, a single validating constructor as
the only construction path, value equality (not representation equality), and no
representation leak. **Consistency is the point** — a value object built a
different way each time buys nothing on the change-speed axis (see below).

## Where the "why" lives — read before changing the analyzers or conventions

- [`rationale/`](rationale/) — the executable case. Three contenders over one
  neutral domain (Mars Climate Orbiter navigation): `primitive/`,
  `inconsistent/` (a mixture of primitives and non-conforming VOs), and
  `valueobject/`. The tests **assert** the wins; don't narrate them.
- [`rationale/coverage.md`](rationale/coverage.md) — the rule ↔ demo ↔ checker
  matrix. `coverage_test.go` fails on a **silent gap** (a checker with no row, or
  a row naming a test that doesn't exist). When you add a checker or a demo,
  update this matrix in the same change.
- [`docs/design-three-contender-changeability.md`](docs/design-three-contender-changeability.md)
  — the changeability metric (silent-site count) and the docs→skills→CI adoption
  ladder.
- [`docs/case-study.md`](docs/case-study.md) — the magnitudes measured on a real
  ~1,100-commit codebase (anonymized).

Deeper rationale and provenance live in the brain at `~/workspace/brain`
(`originals/changeability-silent-site-cost.md`,
`originals/obligations-conformance-changeability.md`). Use `gbrain search` for
semantic lookups across it.

## Verify

```
go test ./...                          # checkers + the rationale wins + the meta-test
go test -bench=. -benchmem ./rationale/ # the honest cost (collection-VO copy tax)
go vet ./... && gofmt -l .             # both must be clean
```

The Python half is not covered by `go test`. **`scripts/verify` runs every
Python gate CI runs** — the same commands, from the same definitions, because
the CI jobs call this script rather than inlining their own copies. If it is
green, that half of CI is green.

```
python3 -m venv .venv && source .venv/bin/activate
scripts/install-dev                      # every tree's requirements-dev.txt
scripts/verify                           # every Python tree, from manifest.json
scripts/verify python-app serdepy        # or just the ones you touched
```

**Every directory says what it is** (`docs/design-repo-layout.md`).
`manifest.json` has a row for every top-level directory and every `examples/*`
directory — two kinds only, `app` and `ungated`, because everything is an app.
Each tree that tessercheck runs on carries a `.tesser-root` file (first line
`app`, then only `skip <dir>`, `export <dir>`, `import <package>`, and
`stdlib <module>` lines —
anything specific to one repo goes in this file, never in the analyzer's
code; at most one `export` line, because a tree has one exported kernel). A missing, unreadable, wrong, or
nested `.tesser-root` is a `TB044` finding; a symlinked directory inside a
declared tree is `TB045`; when either fires, it is the only finding reported —
the analyzer says what the directory is before saying anything about its
contents. The layout check is itself an app (`layout/` — domain rules, a
filesystem reader, a client, and `srv/cli` entry points, gated at the same
bar as every other tree). Run by `scripts/verify` as step 0 and by its own CI
job, it fails when the directories on disk, the manifest, the `.tesser-root`
files, and the CI jobs disagree in any direction, including a
`requirements-dev.txt` at any depth outside an `app` row. **Do not create a new top-level directory (or
`examples/` subdirectory) without adding its manifest row**; the check exists
precisely to make that impossible to do silently. `scripts/verify` reads its
tree list from the manifest, so a new `app` row must come with a `run_*` arm
in the script and a CI job.

Three things to know:

- **`scripts/verify` covers more than the tree you are editing.** The
  shipped analyzer runs a zero-findings gate over every example tree
  (`llmport`, `python-app`, `ports`, `serdepy`, `errorspy`), so a
  layout change in an example can break the analyzer without touching a file
  under `tessercheck-py/`. That is not hypothetical — it is how PR #56
  failed.
- **`scripts/verify tesser-py` shells out to the real mutmut CLI.** The
  ecosystem gate (`tesser-py/tests/ecosystem/mutmut/`) runs `mutmut` — pinned
  exact at `==3.7.0` in `tesser-py/requirements-dev.txt` — over two fixture
  projects, so that arm is slower than the others and it can go red because
  the ecosystem moved, not because this repo changed. That is the gate doing
  its job: read the failure before re-pinning around it.
- **`roadmap` is not in it.** `generate.py --check` and 2 of its 32 tests shell
  out to `go run ./cmd/analyzers-json`, so it is a Go/Python hybrid, not a
  Python tree. It stays a workflow job:

```
python3 roadmap/generate.py --check      # ROADMAP.md is generated — never hand-edit it
(cd roadmap && pytest tests -q)          # the generator's own suite (needs Go)
```

Every tessercheck gate is a plain zero-findings check — there is no ratchet
and no code-family off switch. A finding is either fixed or carries a
site-level `# tesser:debt TB0xx` at the line it excuses. Bare codes, no
brackets: a debt marker whose payload does not parse as codes suppresses
nothing, and a debt marker that suppresses nothing is itself a finding. The one
exception: `TB044` (the tree's `.tesser-root` file) and `TB045` (a symlinked
directory) report on files that cannot carry a Python comment and run before
the suppression filter — they are fixed, never suppressed.

## Git & shipping

**Never commit directly to `main`** (Chris ruling 2026-07-19, superseding the
earlier trunk-based convention). For every change set: work on a **worktree
branch** (`.claude/worktrees/<name>`), commit there, and open a **PR**; merge
after CI is green. Ship via **/gstack-ship** — it owns the version → PR →
release tracking arc. After a set of file changes, commit (on the branch)
before returning control. Write a descriptive message. Don't ask permission
to commit. Stage files individually — never `git add -A`/`.`.

## GBrain Search Guidance (configured by /sync-gbrain)
<!-- gstack-gbrain-search-guidance:start -->

GBrain is set up and synced on this machine. The agent should prefer gbrain
over Grep when the question is semantic or when you don't know the exact
identifier yet.

**This worktree is pinned to a worktree-scoped code source** via the
`.gbrain-source` file in the repo root (kubectl-style context).
`gbrain code-def`, `code-refs`, `code-callers`, `code-callees`, `search`, and
`query` from anywhere under this worktree route to that source by default —
no `--source` flag needed (gbrain >= 0.41.38.0; on older gbrain the call-graph
commands need `--source "$(cat .gbrain-source)"`). Conductor sibling worktrees
of the same repo each have their own pin and their own indexed pages, so
semantic results match the code on disk here.

Call-graph queries (`code-callers`/`code-callees`) also need the graph to be
built first — run `/sync-gbrain --dream` (or `--full`) if they return
`count: 0`. This only works if this source's gbrain schema pack extracts code
symbols; on a non-code-aware pack `--dream` completes but the graph stays empty
and reports a WARN. `code-def`/`code-refs` need the same extraction.

Two indexed corpora available via the `gbrain` CLI:
- This worktree's code (auto-pinned via `.gbrain-source`).
- `~/.gstack/` curated memory (registered as `gstack-brain-<user>` source via
  the existing federation pipeline).

Prefer gbrain when:
- "Where is X handled?" / semantic intent, no exact string yet:
    `gbrain search "<terms>"` or `gbrain query "<question>"`
- "Where is symbol Y defined?" / symbol-based code questions:
    `gbrain code-def <symbol>` or `gbrain code-refs <symbol>`
- "What calls Y?" / "What does Y depend on?":
    `gbrain code-callers <symbol>` / `gbrain code-callees <symbol>`
- "What did we decide last time?" / past plans, retros, learnings:
    `gbrain search "<terms>" --source gstack-brain-<user>`

Grep is still right for known exact strings, regex, multiline patterns, and
file globs. Run `/sync-gbrain` after meaningful code changes; for ongoing
auto-sync across all worktrees, run `gbrain autopilot --install` once per
machine — gbrain's daemon handles incremental refresh on a schedule.

Safety: don't run `/sync-gbrain` while `gbrain autopilot` is active — the
orchestrator refuses destructive source ops when it detects a running autopilot
to avoid racing it (#1734). Prefer registering user repos with `gbrain sources
add --path <dir>` (no `--url`): URL-managed sources can auto-reclone, and the
sync code walk for them requires an explicit `--allow-reclone` opt-in.

<!-- gstack-gbrain-search-guidance:end -->
