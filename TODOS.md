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
