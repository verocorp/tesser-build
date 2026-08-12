# tesser-build — agent guide

This repo is an **application-construction toolkit** (DDD + hex/onion/clean as
inspiration, chosen for changeability, enforced where mechanically decidable;
the build-side member of the tesser family): the `go/analysis` analyzers in
`cmd/tessercheck` (composed from `internal/analyzers.All`), a golangci-lint module
plugin (`gclplugin/`), the Python analyzer (`tessercheck-py/` — the `TB0*`
checks), a Python runtime library (`tesser-py/` — `tesser.domain.ValueObject`,
the repo's first shipped runtime dependency rather than a build-time checker;
candidate mutation-testable VO base, see `examples/vobase/`), an executable
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
analyzer also carries the identity taxonomy (`TB010`–`TB014`), the
serialization norm (`TB015`–`TB018`), the comments norm (`TB020`, mirrored by
the Go `comments` analyzer), and the testing norm (`TB030` — a test double is a
hand-written fake, never a mocking library; `TB032` — a test helper builds a
spec or DTO and nothing else, and is the analyzer's first *totality* check:
every module-level function in a test module must classify or declare itself
with `# tesser-category:`; `skills/tesser-build/testing.md`).
The full check list with per-code rules is `tessercheck-py/README.md`; which
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
scripts/verify                           # all nine Python trees
scripts/verify python-app spike-shells   # or just the ones you touched
```

Two things to know:

- **`scripts/verify` covers more than the tree you are editing.** The
  analyzer gates run over every `ts.*` tree, and the parked legacy analyzer's
  CLI gates still run over `examples/python-app`, `examples/serdepy`, and
  `examples/errorspy`, so a layout change in an example can break an analyzer
  without touching a file under either analyzer tree. That is not
  hypothetical — it is how PR #56 failed.
- **`roadmap` is not in it.** `generate.py --check` and 2 of its 32 tests shell
  out to `go run ./cmd/analyzers-json`, so it is a Go/Python hybrid, not a
  Python tree. It stays a workflow job:

```
python3 roadmap/generate.py --check      # ROADMAP.md is generated — never hand-edit it
(cd roadmap && pytest tests -q)          # the generator's own suite (needs Go)
```

Every tessercheck gate is a plain zero-findings check — there is no ratchet
and no code-family off switch. A finding is either fixed or carries a
site-level `# tessercheck:ignore [TB0xx]` at the line it excuses (an ignore
that suppresses nothing is itself a finding).

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
