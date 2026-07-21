# Changelog

All notable changes to tesser-build are documented here.
Versions follow the 4-digit `MAJOR.MINOR.PATCH.MICRO` format. (This file
versions the toolkit repo as a whole; `tessercheck-py/pyproject.toml`
carries the analyzer package's own version — separate streams.)

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
