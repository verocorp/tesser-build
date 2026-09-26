# Pilot comparison: one policy or two copies

This is a prospective rule-value comparison, not a claim that Tesser is faster.
It asks whether consolidating a policy shared by two legitimate operations helps
a fresh agent change both correctly. Neither implementation is Tesser-conformant;
both must meet the same independent behavioral contract before admission.

## Frozen conditions

The baseline is `tesser-corpus --variant scattered --seed 1`. The candidate is
`--variant structured --seed 1`. The intervention consolidates allocation or
transfer policy in one state operation; the wire protocol, validation, initial
state, and externally observable behavior remain unchanged. Seeds do not count
as distinct workloads.

Inventory is the development family. Its undisclosed change requires both
reservation and shipping to leave two available units. Funds is the held-out
family. Its undisclosed change charges a fee of two on both transfer and
purchase, without crediting that fee to the recipient. No funds-specific repair
may be added to the intervention after inspecting its trial results.

Each of the four cells gets one fresh `codex/gpt-6-luna` agent at medium reasoning,
with no subagents, network dependencies, or architectural conversion requirement.
Prepare the workspace first, then record release when the selected followup is
delivered. The budget is 180 seconds from release through independent verification;
generation and provisioning are separate. The controller observes completion,
copies the submitted artifact, and verifies all original inputs plus the selected
followup before the deadline. Copying and observation delay count toward elapsed
time. A missing or late verified result is not a correct completion.

The initial agent may inspect the base implementation only after preparation is
complete and the change is released. It receives the base requirements, the one
selected change, and its implementation, never oracle inputs or answers. The
original oracle and its digest are frozen before release. Commands run in
disposable cloud machines. No assertion, conformance gate, or expected answer may
be changed to rescue a candidate.

## Interpretation

Report every cell, successful or not, with release, submission observation,
verification end, deadline, source and contract digests, final disposition,
controller interventions, and known resource consumption. Unknown provider usage
and cost remain unknown. Record the intervention's development separately from
agent trial effort. No user rescue is planned; controller clarifications, if any,
are assistance and remain visible.

The primary observation is correct completion within the same budget. Capped
completion time assigns the frozen 180 seconds to failures. With one trial per
cell, timing differences are descriptive only: they cannot establish a general
speed advantage or estimate repeated-trial uncertainty. Unknown cost prevents a
cost-efficiency claim. A pass in both arms is an inconclusive comparison, not a
win for the more structured implementation. An apparent improvement still needs
replication and actual Tesser-converted followup trials before changing a rule.

This comparison does not substitute for the separate construction/conversion
trials, conformant controls, runtime integration, or semantic naming assessment.
Those obligations retain their own results and limitations.

## First observed run — 2026-09-26 UTC

The four prepared source hashes matched the corresponding produced applications
before release. Release was recorded at `00:19:20.832Z`; the common deadline was
`00:22:20.832Z`. Each agent was sent only its base brief and the one change
above. The controller copied each submitted application to an independent
machine and ran `tesser-experiment verify --followup` against the frozen oracle.
This verified all original inputs with their predeclared revised expectations
and then the selected followup probes; the applications did not contain the
oracle. No human rescue was recorded. Provider usage and marginal cost are
unknown.

| Family | Arm | Independent result | Verified observation from release | Original source SHA-256 prefix | Oracle SHA-256 prefix |
| --- | --- | --- | ---: | --- | --- |
| Inventory | Scattered | Correct, 12 probe processes | 131.610 s | `e265356a` | `9dcee520` |
| Inventory | Structured | Correct, 12 probe processes | 131.878 s | `da0d6fc0` | `9dcee520` |
| Funds, held out | Scattered | Correct, 11 probe processes | 132.108 s | `0304d808` | `b08f7835` |
| Funds, held out | Structured | Correct, 11 probe processes | 132.360 s | `27b6a5d8` | `b08f7835` |

These are controller-observed, **not agent-active**, durations. The four agents
finished earlier; the common observation and sequential copying/verification
largely determine the nearly identical recorded times. The run therefore
supports only a 4/4 within-budget correctness observation and an
**inconclusive** policy comparison, not a speed ranking. One sample per cell,
only two families, unknown usage/cost, and no Tesser-conformant converted
snapshot preclude an architectural promotion. The exact verifier results,
initial and submitted Python sources, agent reports, and full SHA-256/timestamp
manifest are under [`evidence/2026-09-26/`](evidence/2026-09-26/manifest.json).
The manifest records how to reconstruct the complete generated candidate
trees; controller observation timestamps differ from agent-reported edit windows.
