# Acceptance-gate record — skills/ddd v2, the seam layer (2026-07-11)

The gate for v2 (design `chris-main-design-20260711-134559.md`, Success Criteria
as hardened by the eng review): a fresh agent that did not author the skill
models a domain from the skill alone, and its output places behavior correctly —
the seam doctrine, not just the noun taxonomy. Verified independently of the
authoring session.

## Setup — Go gate, Claude Code host (fresh Sonnet agent) — PASS

**Fresh subagent**, no author context, given only (a) the broadened v2 routing
line (as it would appear in a consumer's CLAUDE.md — "creating/modifying domain
types, OR writing a handler/endpoint, use-case/service, or persistence/repository
code → read skills/ddd/SKILL.md") and (b) a neutral task: a **book-lending
domain** (member borrows books, ≤3 at once, return, late fees, overdue listing,
persistence). No mention of value object / entity / aggregate / service /
repository / DTO, no file list, and — critically — the task's requirements
*naturally embed the four wrong-placement temptations* the gate exists to test,
never named as such. Output: a new package `examples/lending/`.

**Activation (observed):** followed the routing line to `SKILL.md` first,
unprompted, then routed onward. ✅

**Progressive disclosure (observed):** read `SKILL.md` → `value-objects.md` →
`entities.md` → `aggregates.md` → `application-services.md` → `repositories.md`
→ `go.md`. Did **not** read `python.md` (Go task) or `domain-services.md`
(nothing needed a no-single-owner service). ✅ — the router disclosed only what
the task required.

## Objective criteria (verified independently — I read the code, not the report)

| Criterion | Result |
|---|---|
| `go test ./examples/lending/` green (67 test funcs, ~70 subtests) | ✅ |
| `gofmt -l` and `go vet` clean | ✅ |
| Application service = 4-step convert→delegate→persist→respond, zero business logic | ✅ (`service.go`, all four methods) |
| **Modify-existing** case = load→guarded-transition→save (not construct-only) | ✅ (`CheckOutBook`, `ReturnBook` both load + call `member.CheckOut`/`member.Return` + save) |
| Service returns a **DTO**, never a domain object | ✅ (every method returns a `*Response` struct) |
| Invariant (≤3 active loans) lives in the **aggregate**, not handler/service | ✅ (`NewMember` + `CheckOut` guarded transition in `member.go`) |
| Cross-loan sum (`TotalLateFees`) on the **aggregate**, not a service loop | ✅ (`member.TotalLateFees`; service delegates; comment cites `application-services.md#domain-logic-leakage-checks`) |
| Repository: whole aggregate in, repo decomposes, reconstructed via constructor | ✅ (`Save`/`decomposeMember`/`Load`→`NewMember`) |
| Read query computes **no domain rule** in the repo | ✅ (`FindOverdueLoans` asks each `loan.IsOverdueAsOf`, doesn't decide the rule) |
| Query result is a projection, **not a Spec, not an aggregate** | ✅ (`OverdueLoan` documented as such) |
| Zero vero-private references | ✅ (fresh neutral domain) |

**The four placement temptations — all redirected:**
- (a) the ≤3 invariant → placed in the aggregate, not the service. ✅
- (b) total-late-fees sum → a method on the aggregate, not a service `for`-loop. ✅
- (c) overdue listing → a repo read-projection that asks the domain, no fee/rule
  logic in the repo. ✅
- (d) responses → DTOs, no domain object leaks out of the service. ✅

The service's only `for`-loop maps domain results → DTO rows (the exempted
Respond step), and the agent commented it as such.

## Sound judgment calls the agent made from the skill alone

- Left `time.Time` fields unwrapped on `Loan` (defensible per the
  primitive-obsession "don't wrap the incidental" check) and added `Loan.Equal`
  for identity — which also sidesteps `time.Time`'s monotonic-clock `==` hazard.
- Minted the loan ID inside the aggregate via a direct value-object literal
  (correct: no `Must*` on runtime data; domain behavior builds its own results).
- Treated the cross-member overdue **read** as a legitimate repository
  projection, explicitly distinct from the skill's cross-aggregate **write**
  punt — the exact persistence-vs-query line v2 added (H3).

## Finding for the CI fast-follow (premise 2, made concrete)

`go run ./cmd/ddd-vet ./examples/lending/` flags the entity `Loan`, the
aggregate `Member`, **and the seam types** `LendingService` /
`InMemoryMemberRepository` — the VO analyzers assume any `New*→X` is a
value-object constructor and have no model for application services or
repositories. `-gen-excludes` auto-classifies only `Loan` and `Member` (the
`ID()` signal); the seam types would need **manual** exclusion. This is premise 2
in the flesh — and slightly worse than "no net": it is a *false-positive* net on
the seam layer. Candidate fast-follow: teach the analyzers the
service/repository shapes (a service has an injected dependency and returns
DTOs; a repository maps aggregates) so they stop treating them as malformed value
objects — or accept that consumers exclude seam types by hand. Not wired into CI
here for that reason: silently excluding services/repos would hide the decision.

## Verdict

**PASS.** Stronger than the v1 gate: it exercised exactly the gaps the eng
review added — the modify-existing load-transition-save shape, DTO responses,
the leakage-check redirect, and the repository read-line — and a fresh Sonnet
agent produced all of them correctly from the skill alone, citing the
leakage-check anchor in its own comments. `examples/lending/` is the v2 gate
output (the agent's work, not author-seeded). rhema discovery loop still pending
(gated on access); the analyzer-misclassifies-seams finding is the harvested
fast-follow input.
