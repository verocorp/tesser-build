# Agent improvement experiments: acceptance and evidence

This contract precedes the first trial. The experiment asks whether a toolkit
intervention helps agents make correct changes and subsequent changes. Passing
the current checker alone is not evidence that an architectural rule helps.

## Two questions, two tracks

The current-toolkit track requires the selected Tesser version's conformance,
behavioral, type, and runtime gates. The rule-value track lets the alternative
violate the rule being tested while retaining the same behavioral and runtime
requirements. Otherwise the rule wins by definition.

Each comparison identifies its intervention, applicable gates, starting snapshot,
scenario version, agent/model configuration, resource limits, and evaluation
population before execution. Changing a contract starts a new comparison; it
does not retroactively repair a losing result.

## Workload population

The target corpus spans twelve distinct scenario families. Controlled
nonconformant implementations and independent raw agent implementations are
separate sources, with conformant implementations as controls. Different names
or random seeds of one application are not different architectural families.

Protocol-level scenarios do not establish support for real actor, broker,
streaming, game-engine, or model runtimes. Such claims require the corresponding
runtime integration and workload measurements. A prototype must report which
families, producers, integrations, and follow-up trials actually ran.

Historical failure cases are regression seeds, not a representative sample.
Training and evaluation splits hold out entire scenario families or defect
combinations, not only seeds. Preserve failed generation attempts. Separate
pre-existing behavioral bugs from conversion failures; a controlled structural
mutation is admitted only after its behavior matches the independent contract.

## Scenario boundary

A scenario declares requirements and vocabulary before its implementations.
Deterministic probes exercise an implementation-neutral JSON-lines process
boundary. Every probe starts a fresh process, supplies a sequence of JSON
objects, and expects exactly one JSON object per input. State persists within
that sequence, never implicitly between probes. Logical time, integer
quantities, and explicit inputs avoid unrecorded nondeterminism.

A scenario also declares independent follow-up requirements before the first
implementation is built. The initial builder/converter receives neither those
requirements nor their expected outputs. A follow-up trial receives only the
chosen requirement. Its verifier runs the base behavior and that follow-up's
probes. Explicitly incompatible migrations need a separately versioned contract,
not silently removed base checks.

Expected outputs are hypotheses until checked. Validate the oracle through
independent reasoning, reference models or differential execution as appropriate,
and known faults that it must reject. A second agent author is not an oracle by
itself. A historical behavior comparison may preserve a bug, so it does not
substitute for requirements-based checks.

## Correct completion

A trial is correct only if an independent verifier accepts all applicable gates
against the submitted snapshot before the trial deadline. Missing verification,
removed behavior, weakened protected assertions, unauthorized suppressions or
skips, and disabled gates cannot produce success. The agent's completion message
has no scoring authority.

The oracle resides outside the implementation workspace. The implementation
must not alter its verifier, expected answers, or scoring contract. Verify a
stable copy and detect changes while probing or running gates. Same-user process
execution is not a hostile-code security boundary; this harness is intended for
disposable isolated machines. Do not run generated subjects on a personal device
or claim that filesystem separation alone contains malicious code.

Known-bad controls include incorrect state identity despite a correct result
type, partial writes on failed transactions, duplicate side effects, omitted
responses, extra output, timeout, a failed gate followed by a successful one,
and subject mutation during verification. Checker loopholes such as repacking
two primitive fields into one tuple must not receive architectural credit merely
because findings disappear.

## Instrumentation and accounting

The trial runner records task release, agent activity, tool execution,
interventions, verification, and final disposition. Elapsed time runs from task
release in a prepared workspace through independent verification. Report queue,
agent/tool, verification, and human-wait spans separately; do not infer active
human labor from message gaps.

A verifier invoked on an already completed tree measures verification time,
not agent completion time. Its timeout is a verification budget, not a task
deadline. Do not manufacture end-to-end speed evidence from verifier timings.

Correct completion rate is verified completions divided by all eligible started
trials. Retain failed and timed-out attempts. An infrastructure-invalid trial
needs an explicit reason and the same retry policy in every arm. Capped task
completion time uses actual end-to-end elapsed time for success and the frozen
task deadline for failure. Never drop failures from the denominator to make a
candidate appear faster.

Execution cost includes implementers, subagents, retries, judges, machines,
verification, and external services. Record actual marginal charges separately
from model/resource consumption; subscriptions do not make computation free.
Unknown usage is unknown, never zero. Development cost of an intervention is
separate and visible. Cost per correct completion includes unsuccessful trials.

Human rescues are explicit events with reason and supplied information. Report
assisted and autonomous completion separately. Final approval is distinct from
rework requested at review. Active human minutes require actual recording.

## Follow-up effort and alternatives

Fresh agents perform the same withheld change on original, baseline-converted,
and candidate-converted snapshots. Measure correct completion, elapsed time,
resource cost, and intervention again. Forced edits and affected modules explain
mechanisms; fewer lines or files do not establish lower effort.

Report change families separately as well as overall. A required-family
regression cannot disappear inside an average. Preserve the same invariants,
workload, hardware allocation, runtime limits, and failure conditions. Broader
timeouts or smaller workloads are contract changes, not improvements.

A credible simpler contender is executable, satisfies the same behavioral and
runtime contract, and receives comparable construction/repair effort. It may
violate the architectural rule under examination. Inventory concepts, public
interfaces, wiring, dependencies, and generated artifacts separately; no arbitrary
complexity score converts these into one objective number.

## Decisions

Scripts record executable results and compute matched summaries. Agent judges
diagnose causes, test semantic interpretation against established meanings, and
propose alternatives with evidence. They cannot override failed acceptance tests.
Unresolved domain meanings or rubric disagreements remain unresolved rather than
becoming success by majority vote.

A candidate may increase verified completion at fixed limits, or reduce capped
completion time without reducing completion on the evaluated cases. Increased
cost or human rescue makes that a tradeoff, not an unqualified improvement.
Follow-up regressions or weakened requirements block an unqualified promotion.
Report repeated-trial uncertainty; a noisy difference remains inconclusive.

The four possible decisions are win, loss, tradeoff, and inconclusive. A simpler
contender matching the claimed benefit with no greater change effort weakens the
case for making the rule mandatory in that class of work. A conditional benefit
narrows the claim. Finite trials do not prove that an intervention is never worse.

## Bounded pilot exit

The pilot must demonstrate renewable workload production, an independently
validated verifier, actual construction/conversion and withheld-change trials,
truthful resource/intervention evidence, and at least one complete intervention
comparison. It must run under bounded orchestration without human task
management. A negative result can complete the experiment but cannot establish
that Tesser improved. Infrastructure alone is an intermediate deliverable, not
the pilot's completion.
