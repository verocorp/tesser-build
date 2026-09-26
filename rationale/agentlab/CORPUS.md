# Agent-improvement pilot scenario corpus

These are deterministic protocol workloads for an authorized agent-improvement
pilot. They test decisions and state transitions, not whether tesser-build
supports a particular broker, actor framework, streaming server, game engine,
vendor SDK, or LLM provider. All names and data are synthetic and public-safe.

The initial corpus has 12 distinct families, 81 base probes, and 24 independently
applied followups containing 60 more probes. There are 420 input/output pairs.
The first producer targets are `reserving-inventory` and `transferring-funds`.

The generated implementations run against the independent contracts in
`producer_test.go`. Known-fault controls must fail by giving wrong answers,
not merely by crashing. This exposed a missing sequence: rejecting a release
after a nonzero reservation must preserve that reservation. The added probe
strengthens the existing non-mutation requirement and needs no followup override.

## Protocol and disclosure boundary

Each JSON file has exactly `version`, `id`, `family`, `requirements`,
`vocabulary`, `probes`, and `followups`. A probe has `id`, `inputs`, and
`expected`. A followup has `id`, `requirements`, `probes`, and optionally
`base_expected`. Version is 1. `base_expected` is a nonempty object mapping
existing base-probe IDs to replacement arrays of expected JSON objects. Each
array must have exactly as many objects as that base probe has inputs. It may
not name a followup probe, add inputs, remove inputs, or remove a base probe.
Omit the field entirely when no base expectations change; null and an empty
object are invalid.
Requirements are authoritative; examples are executable claims about those
requirements, not a substitute specification.

Start a new candidate process for each probe. Send each input object as one
JSON line on stdin and require exactly one JSON object on stdout for that line.
Keep the process alive between lines of that probe only. Compare parsed JSON
objects structurally, ignoring object key order but preserving array order.
Missing or additional response keys are failures. Debugging output belongs on
stderr. A runner must reject missing, extra, malformed or non-object responses,
unexpected process failure, and hangs under a configured resource budget.
The time budget is runner policy, not domain logical time.

The protocol specifies well-formed JSON-object inputs. Malformed JSON bytes,
duplicate keys in requests, and non-object top-level requests are outside this
first workload contract; they need a separate transport-hardening suite.
Within an object, absent/extra fields, unsupported operations, wrong types,
null values, and invalid ranges have the defined `invalid_input` result.
Booleans are not integers. Validate complete shapes before state-dependent
rejections. Every rejection is non-mutating, including the atomic batch paths.
All domain time is caller-controlled logical time; all domain arithmetic is
integral. Fixture inputs may deliberately contain fractional numbers or other
invalid domain values to test `invalid_input`; a fixture decoder must not reject
those valid JSON numbers before the candidate sees them.

The base author receives base requirements and vocabulary, not the full corpus
file. An evaluator may choose to disclose base examples, but must record that
choice consistently across contenders. Keep base evaluation probes private if
the experiment claims unseen base evaluation. Followup requirements and probes
must not be included in the base prompt or made readable in the candidate's
workspace. The JSON files are public fixtures, so “withheld” means withheld by
the experiment's disclosure boundary, not intrinsically secret or immune to
training contamination.

For each followup, clone the same completed base candidate and disclose only
that followup's requirements plus the base requirements/vocabulary. Apply it
alone. Do not start from a candidate modified for a preceding followup. Run
**every original base probe with its original inputs**. For a probe whose ID is
in that followup's `base_expected`, use the entire predeclared replacement
expected array; otherwise use the original base expected array unchanged.
Then run all followup probes. Never skip an obsolete assertion or infer new
expected answers from a candidate's output. Each probe starts a fresh process,
including base probes rerun under a followup. Freeze the corpus revision and
overrides before producing followup implementations, and retain them in the
audit record with the candidate revision, disclosure, followup ID, and result.

## Base expectation override audit

All 24 followups were traced against all original base inputs. The 33 declared
whole-probe overrides below account for downstream state changes as well as
the directly changed result. Probe names in this table omit their scenario-ID
prefix; JSON keys contain the full base-probe IDs. An omitted map means all
base expected answers remain required, not that base evaluation is omitted.

| Scenario / followup | Overridden base probes | Requirement rationale |
| --- | --- | --- |
| Inventory / stock-ceiling | restock-and-reject | Restocking three units exceeds 12; stock stays 10 and the subsequent reserve of 13 also fails. |
| Inventory / minimum-available | reserve-boundary, release-cycle, restock-and-reject, ship-shares-availability | Allocation may not consume the final two available units; rejected operations leave later state unchanged. |
| Funds / flat-fee | round-trip, drain, reject-is-atomic, purchase-shares-funds | Successful debits include two extra units; transfers previously draining the source now fail, changing subsequent balances and affordability. |
| Funds / credit-failure | None | Base inputs omit fail_credit, whose default remains false. |
| Compensation / manual-cancel | None | Base probes never invoke the new cancellation operation. |
| Compensation / retry-charge | charge-fails, terminal-and-validation | A failed charge now retains the reservation instead of entering cancelled. |
| Approval / inclusive-deadline | exact-expiry | At exactly the deadline the request is still pending, so the following approval succeeds. |
| Approval / extend-once | None | Base probes do not extend a request. |
| Fanout / idempotent-results | duplicate, alternate-entrypath | Conflicting repeated task values now return conflicting_result, including a result after the zero-valued failure fallback. |
| Fanout / quorum-two | out-of-order, signed-results, alternate-entrypath | The second distinct completion closes the join; the third attempt is rejected and no longer contributes to total. |
| Queue / two-id-window | distinct-messages | Three accepted IDs leave a remembered count of two, while total is unchanged by eviction. |
| Queue / nonnegative-total | None | No base delivery or intermediate batch state would make total negative. |
| Projection / read-barrier | None | Base probes use no read barrier. |
| Projection / rebuild | None | Base probes never reset or rebuild the view. |
| Actors / value-ceiling | None | Every successful base mutation stays at or below 10; stale-version checks still precede the limit. |
| Actors / compare-replace | None | Base probes use no replacement command. |
| Stream / idempotent-cancel | cancel-exhausted | The repeated cancellation returns current status rather than already_cancelled. |
| Stream / byte-budget | pull-then-drain, cancel-both-paths, cancel-exhausted | Each read is capped at two bytes, changing cursor positions; the three-byte chunk is rejected without advancement. |
| Game / continuous-hazard | hazard-after-movement, dash-and-exhaustion, terminal | Odd-tick occupancy at cell 2 now damages health; reaching zero sooner makes subsequent valid commands game_over. |
| Game / fast-recharge | hazard-after-movement, bounds-and-recharge, terminal | Waiting restores two energy and caps at five; movement, timing, and health rules remain unchanged. |
| Vendors / euro-conversion | None | Base inputs contain no correctly cased EUR/eur currency. |
| Vendors / blocked-sku | None | No base input names the newly blocked recall SKU. |
| LLM / higher-confidence | accepted, batch | Scores of 70 and 80 no longer satisfy the new 90 threshold. |
| LLM / two-sources | accepted, confidence, batch | One source now fails the evidence check, including cases formerly rejected later for low confidence. |

`TestProducerContractSemanticTraces` independently computes inventory and funds
state transitions from input values and policy rules, then compares every base,
overridden-base, and followup response against the declared goldens. It does not
derive expected overrides from candidate output. The remaining ten families'
overrides were manually traced from their requirements; they still need the
independent reference-model/reviewer validation below before scored claims.

## What each family measures

| Scenario | Distinct decision and entrypaths | Required host integration before any runtime claim |
| --- | --- | --- |
| `reserving-inventory` | Allocation invariants shared by `reserve` and `ship`, plus release/restock. Reservation and shipment change different state. | Repository persistence and concurrent reservation isolation. |
| `transferring-funds` | Atomic debit/credit shared by general `transfer` and fixed-payee `purchase`; failure must not commit one side. | A real transaction boundary, rollback/crash tests, and concurrent account writes. |
| `compensating-booking` | `charge` and `deliver` can fail at different workflow stages and require different compensation depths. | A durable workflow engine, persisted progress, retries, and crash/recovery during compensation. |
| `expiring-approval` | Logical `advance` expires a request; `decide` must honor the terminal state. Expiry boundaries differ from business rejection. | Durable timers, callback delivery, replay, and decision/timeout races. |
| `joining-fanout` | `complete` and `fail` join named branches, with fallback results and duplicate/quorum decisions. | Concurrent dispatch, worker failure, out-of-order delivery, and durable joins. |
| `deduplicating-queue` | `deliver` and atomic `deliver_batch` separate message identity from payload and suppress redelivery. | A broker, acknowledgment timing, persistence, restart redelivery, and consumer concurrency. |
| `projecting-events` | `event` and atomic `events` enforce a contiguous sequence and distinguish replay, conflict, and gaps. | An event log, durable checkpoints, restart replay, and competing projector instances. |
| `serializing-actors` | `add` and `subtract` address isolated actor states and reject stale versions. | A real mailbox/scheduler, activation/deactivation, persistence, and simultaneous messages. |
| `cancelling-stream` | `pull` and `drain` share a cancellation fence while chunk consumption and exhaustion remain separate states. | A streaming transport, backpressure, disconnect propagation, and producer cleanup. |
| `advancing-game` | `step` and `dash` apply movement/energy, advance a tick, then resolve a position-dependent hazard. | A game loop, event input ordering, state replication if applicable, and replay tests. |
| `translating-vendors` | `quote` and `invoice` translate two vendor schemas and reject unsupported or unavailable data without partial results. | Actual vendor protocols/SDKs, transport failures, schema drift, and sandbox contract tests. |
| `constraining-llm-output` | `evaluate` and `evaluate_batch` validate untrusted structured output before evidence/confidence policy. | A provider adapter, real structured-output failures, prompt-injection evaluation, and model variability measurement. |

Followups vary policy rather than merely renaming fields: capacity/buffer rules,
fees/rollback, cancellation/retry, deadline/extension, idempotence/quorum,
retention/nonnegative application, read barriers/rebuild, value ceilings/CAS
replacement, cancellation idempotence/byte budgets, hazard/recharge,
currency conversion/blocked products, and confidence/source requirements.

No corpus requirement directs a candidate to violate the construction skill.
An experimental policy-distributed negative control is deliberately constructed
by the evaluator; it is not a recommended application architecture. Compare
variants on identical contracts and disclosure, and verify baseline behavioral
equivalence before measuring their change cost. Alternate entrypaths exist to
make an omitted policy update observable, not to reward duplicate logic.

## Oracle validation and negative controls

Authored expected answers are hypotheses. Passing the structural tests below
does **not** certify their semantics, the candidate, or an architectural claim.
Before using a family for scored conclusions:

1. Have a reviewer or independently developed reference model derive every
   expected response from the written requirements. Trace each multi-step probe
   from its fresh initial state. Resolve disagreements by reviewing the
   requirement, not by adjusting a candidate to match an unexplained golden.
2. Execute the base and each independent followup against the real candidate
   process protocol. Check every line, absence of extra output, process exit,
   and process isolation. Preserve the exact corpus revision and results.
3. Exercise negative controls: constant output, input echo, no state persistence,
   and shared state leaked across fresh probes must fail. Swap one expected
   response, delete one response, emit an extra response, and hang one probe;
   the evaluator must reject each rather than report a valid score.
4. Exercise policy-specific mutants below. Record which probe kills each mutant.
   A mutant that survives is an oracle or coverage gap, not evidence that the
   mutant is correct. Test both entrypaths when a policy is shared.
5. For change-cost comparisons, include a behaviorally equivalent variant with
   the same policy at more than one entrypath, change only one copy, and show
   that an alternate-entrypath followup probe fails. Count changed decision
   sites only after behavioral equivalence and the followup result are verified.

| Family | Example fault the oracle must detect |
| --- | --- |
| Inventory | Shipment ignores reservations, or release creates physical stock. |
| Funds | Debit commits on credit failure, or purchase avoids the new fee. |
| Compensation | Failed delivery releases stock but fails to refund the charge. |
| Approval | Expiry uses the wrong equality boundary, or a terminal decision is overwritten. |
| Fanout | A duplicate counts toward quorum, or a failed task remains pending. |
| Queue | Deduplication compares payload instead of identity, refreshes retention incorrectly, or a rejected batch partially commits. |
| Projection | A gap advances the checkpoint, a replay reapplies delta, or rebuild uses only the current view. |
| Actors | Version increments on rejection, stale subtraction succeeds, or actor keys share state. |
| Stream | Drain bypasses cancellation, an oversized chunk advances the cursor, or chunks are split. |
| Game | Hazard runs before movement/tick advancement, failed moves advance time, or dash bypasses energy. |
| Vendors | Translation silently accepts the other vendor's casing, rounding uses non-integral arithmetic, or an invoice skips item policy. |
| LLM policy | Model instructions override schema, evidence is not allowlisted, threshold comparison is wrong, or batch evaluation bypasses policy. |

The corpus alone cannot prove general runtime support, recovery guarantees,
security of an LLM application, broad construction-quality improvements, or an
unbiased effect size. Host integration and independently validated results are
separate evidence. Run budgets, scoring, reference implementations and runtime
adapters are not implemented by these corpus files.

## Structural gate

From the repository root:

```sh
go test ./rationale/agentlab -count=1
go vet ./rationale/agentlab
gofmt -l rationale/agentlab/scenarios_test.go
```

`scenarios_test.go` uses external package `agentlab_test` and only the standard
library. It checks all twelve family identities, filenames, schema version,
unknown fields, duplicate JSON keys, global IDs, nonempty requirements and
vocabulary, object-only inputs/outputs, exact
input/output cardinality, minimum probe/followup counts, duplicate input
sequences, and separation of base and followup requirements/probes. Overrides
must name existing base probes and preserve their input/output cardinality;
empty maps, nulls, non-object responses and unknown IDs are rejected. Negative
tests verify that malformed contracts are rejected, while valid fractional
invalid-input fixtures are accepted. The producer semantic trace tests cover
inventory and funds; structural checks alone remain data-quality checks, not
candidate execution or semantic validation of the other ten families.
