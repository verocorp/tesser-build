# Changelog

All notable changes to tesser-build are documented here.
Versions follow the 4-digit `MAJOR.MINOR.PATCH.MICRO` format. (This file
versions the toolkit repo as a whole; `tessercheck-py/pyproject.toml`
carries the analyzer package's own version — separate streams.)

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
