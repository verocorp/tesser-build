# Voice conversation behavior: Given/When/Then test draft

Status: requirements draft, not implemented tests or a settled architecture.
Saved 2026-09-21 for the voice refactor in [PR #208](https://github.com/verocorp/tesser-build/pull/208).

The original A1–A21 and O1–O13 cases are preserved below so review references
remain meaningful. The challenge-review refinements afterward identify proposed
rewrites, additions, and unresolved decisions. Original wording such as “the
aggregate requests” does not settle the aggregate/orchestrator control flow.

## Requirements and scope

- Completed user input can arrive at any point during a call, including while
  processing or agent speech is underway. There may be zero, one, or many user
  completions for one agent utterance.
- Start processing completed input promptly. Further input can revise processing,
  interrupt speech, or produce a follow-up, depending on application policy and
  how far the response has progressed.
- An acknowledgement can play while substantive processing proceeds. It need not
  request another user response or introduce a response timeout.
- Delayed and reordered events retain their original observation context. An
  observed speech index is a causal bound, not an exact reply-to relationship or
  proof that the person heard a particular utterance.
- Response deadlines are independent events. “No speech started” and “no completed
  input arrived” are different policies; the earlier eight-second silence request
  does not resolve which deadline every application should use.
- Different applications can select different response policies. Tests should
  name concrete policy fixtures rather than bake one choice into the architecture.
- The aggregate owns domain rules. Orchestrator unit tests use the real aggregate
  and controllable fake relays. These tests do not establish SDK delivery or
  durable-engine recovery guarantees by themselves.

Working terms such as contribution, attempt, utterance, and expectation do not
commit us to final class names, a command-emitting aggregate, or a `progress()`
loop. Implementation is outside this draft's scope.

## Original draft

I’d separate the aggregate’s decisions from the orchestrator carrying them out. Where behavior depends on application policy, that policy belongs explicitly in the Given.
“Contribution,” “processing attempt,” and “utterance” below are working terms, not final type names.

## Aggregate cases (original draft)

| Case | Given | When | Then |
|---|---|---|---|
| A1 First contribution | The agent has asked a question; no user contribution has arrived | A completed contribution arrives | Record it and request processing immediately |
| A2 Input during processing | Processing is underway; policy is to revise using additional input | Another contribution arrives | Record it and request processing that considers both contributions, without waiting for the earlier attempt to finish |
| A3 Three or more contributions | Several contributions have already arrived | Another arrives | Preserve all distinct contributions and apply the same revision policy; there is no one-contribution-per-utterance limit |
| A4 Input during speech | Agent speech is playing | A contribution arrives | Record it and evaluate the configured response policy immediately |
| A5 Delayed contribution | The agent is on utterance 9 | A contribution arrives carrying observation context from utterance 7 | Preserve that context and consider its relevance to current work; do not relabel it as a response to utterance 9 or discard it merely because it is late |
| A6 Reordered delivery | Contribution B has arrived, with a source sequence later than A | A arrives | Preserve source ordering and reconsider work that proceeded without A |
| A7 Duplicate delivery | A contribution has already been accepted | The same contribution ID arrives again | Do not append it or trigger its effects again |
| A8 Superseded result | A processing attempt has been superseded | Its result arrives | Do not allow that result to authorize obsolete speech or actions |
| A9 Result still applicable | Additional input arrived, but policy determines an earlier result remains useful | That result arrives | Incorporate it according to policy; lateness alone does not make it unusable |
| A10 Pending speech replaced | Speech has been prepared but has not started; policy permits replacement | New input makes it obsolete | Withdraw the pending speech and request a revised response |
| A11 Interrupt and revise | Speech is playing; policy is to interrupt for additional input | Another contribution arrives | Request interruption and revised processing using the additional input |
| A12 Finish and follow up | Speech is playing; policy is to finish before following up | Another contribution arrives | Preserve the current speech, begin processing the new input, and arrange the follow-up |
| A13 Acknowledge while processing | Additional input needs substantial processing; policy permits an acknowledgement | That input arrives | Request an acknowledgement and substantive processing without making the substantive work wait for a user response |
| A14 Speech already delivered | An earlier response has finished playing | New input changes the answer | Preserve the delivered speech in history and request an appropriate correction or follow-up |
| A15 Interrupted speech | Only part of an utterance played | Interruption is confirmed with available playback information | Record the delivered portion separately from the unspoken remainder |
| A16 No contribution | A response is expected and its configured deadline expires | The timer event arrives | Request the configured timeout behavior |
| A17 Speech started, completion pending | The deadline measures failure to start speaking | User speech starts before expiry | Satisfy that expectation; do not treat a long answer as silence |
| A18 Completion deadline | A separate deadline measures failure to receive completed input | That deadline expires while speech is underway | Apply that deadline’s policy, independently of the no-speech-started policy |
| A19 Obsolete timer | An expectation has been satisfied or superseded | Its timer event arrives late | Produce no timeout response for that obsolete expectation |
| A20 Non-question utterance | An acknowledgement does not request a response | Its playback finishes | Do not automatically create a response expectation or delay pending substantive work |
| A21 End with pending input | A contribution is accepted before call closure is finalized | The call would otherwise finish | Apply an explicit disposition to that contribution; do not silently leave it unhandled |

For A21, allowed dispositions remain to be chosen, e.g. process before closing or explicitly decline because closure has begun. The test should name the chosen policy.

## Orchestrator cases (original draft, using the real aggregate)

Fake relays let the test hold an operation pending, inject an event, and release results in any chosen order.

| Case | Given | When | Then |
|---|---|---|---|
| O1 Immediate processing | A live call with no processing underway | A completed contribution is delivered | Invoke the processing relay without waiting for another contribution or a timer |
| O2 Continuous input consumption | A processing relay call is held pending | Another contribution arrives | Deliver it to the aggregate and execute its resulting decisions before the pending call completes |
| O3 Continuous input during playback | A speech operation is held pending | A contribution arrives | Deliver it to the aggregate without waiting for speech completion |
| O4 Revised processing | The aggregate requests replacement processing | The earlier operation cannot be cancelled immediately | Start the replacement without waiting for cancellation to finish |
| O5 Late result | Replacement processing is underway | The older result completes | Deliver the result with its original attempt identity; execute only the aggregate’s resulting decisions |
| O6 Reordered input | B reaches the orchestrator before A | A subsequently arrives | Preserve both events’ original IDs, sequence, and speech context when delivering them to the aggregate |
| O7 Speech identity established first | The aggregate requests an utterance | The orchestrator dispatches it | The utterance is already identifiable in call state, so callbacks can reference it even before the dispatch operation returns |
| O8 Obsolete queued speech | An utterance has been superseded before playback | Its generation finishes or its delayed start command reaches the output executor | The obsolete utterance is prevented from starting |
| O9 Acknowledgement and processing | The aggregate requests both | The acknowledgement is still playing | Substantive processing is already underway; no intervening user response is required |
| O10 Interruption result | The aggregate requests interruption | The output executor confirms what stopped | Deliver that playback result to the aggregate before treating the speech as stopped |
| O11 Deadline anchored to playback | A question requires a deadline after playback | Speech generation starts, then playback later finishes | Schedule the deadline from the specified playback milestone, not from generation or dispatch |
| O12 Timer cancellation race | Cancellation has been requested | The timer event nevertheless arrives | Deliver its original expectation identity; the aggregate recognizes it as obsolete |
| O13 Clean completion | The aggregate authorizes call closure | The orchestrator finishes | All accepted contributions and outstanding operations have the disposition required by the closure policy |

Important test shape: a controlled interleaving. Example: Given processing A is pending. When contribution B arrives, processing B starts, and then A finishes. Then B was handled promptly, A’s result retains its original identity, and obsolete speech is not dispatched.

These tests establish application behavior. Separate SDK integration tests must establish completed-input delivery in relevant playback states and trustworthy observation metadata.

## Challenge-review refinements

The gstack `/codex` challenge reviewed this draft on 2026-09-21. These are proposed
refinements, not assertions that the original tests are already executable or that
all policy choices have been agreed.

### Make the existing cases falsifiable

- **A1–A4, O1–O4:** replace “immediately” with a controlled interleaving: hold the
  earlier operation pending, deliver input, and observe processing of the new input
  before releasing the earlier operation. Do not require a separate concurrent
  attempt if an existing operation can accept incremental input.
- **A5–A6, O6:** preserve identity, original observation metadata, and arrival order.
  Only assert source order where comparable source metadata establishes it. Use a
  concrete policy to say how late input changes current work.
- **A7:** define identity scope and the response to the same identity carrying
  different content. Identical text with different identities is not necessarily
  duplicate input.
- **A8–A12, O5, O8, O10:** distinguish authorization, the final controllable playback
  boundary, actual playback, and interruption acknowledgement. A stop request is
  not evidence that speech stopped. For A9, name exactly which part of an earlier
  result remains applicable and why.
- **A14–A15:** preserve reported playback extent and its uncertainty. Do not claim
  that local playback proves remote hearing or that exact spoken text is known
  when only a coarse playback signal is available.
- **A16–A19, O11–O12:** identify the expectation, deadline anchor, clock, and tie
  policy. Include already-fired timers whose response is being prepared or queued.
- **A21, O13:** define input acceptance and terminal handling explicitly. “Queued”
  or “processing” is not a terminal disposition.
- **All orchestrator cases:** assert observable relay calls, their correlation,
  and scheduling, rather than requiring an aggregate-produced command protocol.
  Keep domain authorization assertions in the aggregate tests.

### Proposed additional or replacement scenarios

Every policy named here is an example fixture. A different supported policy needs
its own concrete Then; the policy choice is not a universal invariant.

| Case / layer | Given | When | Then |
|---|---|---|---|
| R1 Orchestrator: processing does not strand input | A finite set of contributions has been accepted; the fixture requires an answer incorporating all of them; services eventually succeed | Further input stops and outstanding work completes | A response covering every accepted contribution is produced; no contribution remains indefinitely pending |
| R2 Aggregate + orchestrator: processing failure | One accepted contribution is awaiting processing; the fixture allows one retry, then an explicit failure outcome | The first attempt fails, then its retry fails | Exactly one retry is started, followed by the fixture's terminal failure outcome; the contribution is not left marked as processing |
| R3 Orchestrator + output integration: stale start race | Prepared speech is held before the final controllable playback boundary; the fixture replaces pending speech on new input | New input invalidates that speech before the boundary is crossed | The invalidated speech does not start, even if its preparation result or delayed start arrives afterward |
| R4 Aggregate + orchestrator: interruption is delayed | Playback has begun; the fixture requests interruption and prepares a revised answer concurrently | The stop request remains pending | Revised processing starts, but playback remains recorded as active until a confirming observation; replacement playback does not overlap under this fixture |
| R5 Orchestrator: unknown ordering | A contribution arrives without comparable source-order metadata | Processing can begin | Processing starts without waiting for a hypothetical predecessor; no unsupported source order is asserted |
| R6 Aggregate + orchestrator: queued timeout response | A timeout has fired and its response is queued; the fixture suppresses that response if input satisfies the expectation before playback | Qualifying input arrives before the response crosses the final controllable playback boundary | The timeout response does not start; processing of the input proceeds |
| R7 Aggregate + orchestrator: expectation isolation | Expectation E1 has been replaced by E2 | An E1 timer or playback callback arrives | Its identity remains E1; it does not satisfy, cancel, or reschedule E2, and cannot revive E1's obsolete timeout response |
| R8 Aggregate + orchestrator: closure races with input | The fixture finishes accepted input before closing and rejects input after the acceptance boundary closes | A contribution races with closure | Input accepted before that boundary reaches a terminal outcome before final closure; input after it is explicitly rejected under the fixture, not accepted and abandoned |
| R9 Input integration: delivery during playback | User speech can complete during interruptible playback, uninterruptible playback, or a pending prior callback | The selected input source observes completion | The application receives the contribution without waiting for playback or the earlier application callback to finish |
| R10 Observation integration: context capture races | Context N becomes established at the agreed observation point while input completion occurs | The input observation is captured and its delivery is delayed until later speech | The contribution retains the context captured at observation; later delivery does not replace it with the then-current context, and the context alone does not prove hearing or satisfy a response expectation |

For R9, the current LiveKit `on_user_turn_completed` path must be checked against
this requirement: prior source inspection found that it is a pre-reply hook that
can serialize behind earlier hooks or be skipped in some playback/scheduling
states. A fake that always emits completion cannot prove this requirement. If the
selected SDK path cannot satisfy it, the design still has a delivery gap.

For R10, establishing speech context at the observation source does not inherently
require publishing it to LiveKit Cloud. Choose the actual session/room mechanism
and milestone before making this scenario executable. Neither callback-time
sampling nor an assumed minimum human reaction time proves exact attribution.

### Durable-runtime coverage

These complement unit tests and need a real durable execution boundary. Recovery
must not be inferred merely from in-memory aggregate behavior.

| Case | Given | When | Then |
|---|---|---|---|
| D1 Accepted input survives recovery | A contribution has crossed the durable acceptance boundary but has not been processed | The workflow restarts | The contribution remains available for handling with its original identity and observation metadata |
| D2 Replayed results | An identified processing result has already been durably applied | Recovery replays delivery of that result | It is not applied as a new result or used to authorize an additional response solely because of replay |
| D3 Ambiguous speech dispatch | A speech request may have reached output, but its acknowledgement was not durably recorded | Execution recovers | The request retains its original identity and follows the chosen reconciliation policy; recovery does not silently label it unspoken or completed |

D3 deliberately leaves an open decision: whether output can reconcile by identity,
prevent duplicate playback, or expose an unknown outcome that a policy handles.
Do not claim exactly-once audible speech from workflow durability alone.

### Consolidation

- Parameterize A3 with multiple distinct contributions instead of treating “three”
  as a different rule.
- Fold A4 into concrete interruption and finish/follow-up scenarios.
- Keep A10/O8 and A19/O12 as paired domain-rule and orchestration-interleaving
  cases, with distinct assertions rather than duplicated tests.
- Cover A20's absent response expectation within A13/O9's acknowledgement scenario.

## Decisions before executable tests

1. **Observation and identity:** what marks an utterance's context as established;
   where completion captures that context; which delivery path covers required
   playback states; contribution identity scope, conflicting duplicates, and
   available source-order metadata.
2. **Policy fixtures and terminal handling:** concrete revision, interruption,
   follow-up, acknowledgement, earlier-result reuse, processing failure, and
   closure policies. Define acceptance and terminal outcomes. Preserve the option
   of explicit workflow coordination with domain authorization.
3. **Timing and recovery:** speech-start silence versus missing completion;
   playback anchor, clock, and deadline ties; treatment of stale timeout output;
   durable acceptance and reconciliation of ambiguous external effects.

## Validation status

This file records proposed behavior and review follow-ups. None of these scenarios
is claimed to pass because it appears here. The existing acceptance test and its
run instructions are documented in
[the voice test guide](../examples/voice/tests/README.md).
