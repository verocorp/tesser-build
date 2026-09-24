# Application-service types — orchestrators, actions, relays, activities, workflows, dispatchers

Status: **RULED, 2026-09-11 (Chris); the dependency shape re-ruled
2026-09-22; the adapter kinds re-ruled 2026-09-23.** The section immediately
below is the convention. Everything from "The three application kinds" onward is the
2026-08-29 record that produced it and is **historical**: it is kept because it
carries provenance that cannot be reconstructed — the fifteen codex challenge
findings and which were taken, the survey of seven orchestrators in
`~/workspace/flow`, the package names considered and rejected, and the two
options the job-context ruling chose between. Read it for *why*, never for
*what*. Where the two disagree, this section wins; `examples/voice/` and
`skills/tesser-build/python.md#orchestrators-actions-relays` are the spec,
and `examples/durable-execution/`, `examples/minimal/` and the generator's
templates follow it. The older kinds remain only as deprecated rules; see
**The deprecated kinds** below.

## The convention, 2026-09-23

There is no `ts.Job`, no `ts.JobContext`, no `adapters/jobs/` package, and no
job context threaded as the leading parameter of an action-port call (the
2026-09-11 ruling). Three application kinds and four adapter kinds replace all
of it, and no call site in Python addresses a handler by a written string.

| kind | base | lives in | built | depends on | reached through |
|---|---|---|---|---|---|
| relay | `ts.Relay` (`tesser.application.Relay`) | `application/relays/`, one per module, named for its far side, with the messages it speaks, a snapshot for each, and the names of the promises it awaits as constants | declared, not built — it is a protocol | nothing | a service or an orchestrator, through a dispatcher |
| activity | `ts.Activity` (`tesser.adapters.Activity`) | `adapters/activities/` | once, by the component, handed a `restate.Service` and an application client | the application client and the relays | the dispatcher that holds it, through its `.handler` |
| workflow | `ts.Workflow` (`tesser.adapters.Workflow`) | `adapters/workflows/`, beside the dispatchers it builds per invocation | once, by the component, handed a `restate.Workflow` and the activities | the orchestrators, the relays, and the activities | the dispatcher that holds it, through its `.handler` |
| signal | `ts.Signal` (`tesser.adapters.Signal`) | `adapters/dispatchers/` | once, by the component, handed the workflow's `restate.Workflow` | the relays | the dispatcher that holds it, through its `.handler` |
| dispatcher | `ts.Dispatcher` (`tesser.adapters.Dispatcher`) | `adapters/workflows/` (inside an invocation) or `adapters/dispatchers/` (over HTTP) | inside an invocation, per invocation by the workflow; over HTTP, once by the component | the relays, and the activity, workflow, or signal instances it calls | whoever holds the relay it implements |

**The call path, reduced to its essentials** (Chris, 2026-09-23). Every
durable path in the tree is some walk through these lines; relays,
dispatchers, application clients, and serdes are how each line is carried,
not extra steps.

```
tesser.Service.operation            -> restate.Client.operation
restate.Client.operation            ⇒  restate.Workflow.main | restate.Workflow.handler
restate.Workflow.main(wf_ctx)       -> tesser.Orchestrator(wf_ctx) -> tesser.Orchestrator.operation
tesser.Orchestrator.operation       -> wf_ctx.promise(name).value
restate.Workflow.handler(shared)    -> shared.promise(name).resolve
tesser.Orchestrator.operation       -> wf_ctx.operation
wf_ctx.operation                    ⇒  restate.Service.handler | restate.Workflow.main
restate.Service.handler(ctx)        -> tesser.Action.operation
tesser.Action.operation             -> tesser.Port.operation
```

`->` is a Python call, held by imports, protocols, and constructors, so the
type checker sees both ends. `⇒` crosses the engine, and so does the pair
`promise(name).value` / `promise(name).resolve`, which meet only in the
engine's journal. The engine addresses these three links by name; Python
gets each name from the object that registered it:

| link | addressed by | carried in the tree by |
|---|---|---|
| `restate.Client.operation ⇒ …` | service, key, handler | a dispatcher over HTTP: `restate.client.Client(httpx.AsyncClient(...)).workflow_call(self._restate_conduct_call.handler, key=..., arg=...)` |
| `wf_ctx.operation ⇒ …` | service, handler | a dispatcher inside the invocation: `wf_ctx.service_call(self._restate_record_call.handler, request)` |
| `.value` ↔ `.resolve` | promise name, within one workflow key | a relays constant (`PERSON_JOINED_PROMISE`), read by the dispatcher's `await_person_joined` and by the signal `person_joined` |

The SDK reads the service and handler name off the registered handler object
it is passed, and the component writes each container's name once, as a
literal. So a call names what it calls by holding the Python object that
registered it, and the type checker sees both ends of every line.

Separated this way, the dependencies form a straight chain with no loop.
Each row holds the row above it; a row never holds a row below.

| row | kind | package | constructed with | registers or calls |
|---|---|---|---|---|
| action handler | `ts.Activity` | `activities/` | `restate.Service`, application client | registers `record_call` on `CallActions`; calls the application client |
| workflow `main` | `ts.Workflow` | `workflows/` | `restate.Workflow`, the activities | registers `conduct_call` on `CallOrchestrator`; builds the orchestrator per invocation |
| invocation dispatcher | `ts.Dispatcher` | `workflows/` | `wf_ctx`, the activities it calls | `wf_ctx.service_call(activity.handler, ...)`, `wf_ctx.promise(CONSTANT).value()` |
| shared handler | `ts.Signal` | `dispatchers/` | the workflow's `restate.Workflow` | registers `person_joined` on `CallOrchestrator`; resolves `promise(CONSTANT)` |
| HTTP dispatcher | `ts.Dispatcher` | `dispatchers/` | `restate_url`, the workflow, the signals | `workflow_call(workflow.handler, ...)` or `workflow_call(signal.handler, ...)` |
| service | `ts.ApplicationService` | `application/` | the relay the HTTP dispatcher implements | `relay.run_conduct_call(...)` |

Notes on the lines, from the code and the Restate Python SDK (1.0.4):

- `wf_ctx` is `restate.WorkflowContext` and exists only in a workflow's `main`
  handler. A shared handler gets `restate.WorkflowSharedContext`, and a
  service handler gets a plain `restate.Context`, which the actions handlers do
  not use.
- The orchestrator is not handed `wf_ctx` itself: the workflow builds it over
  dispatchers that each hold `wf_ctx`. The line is written
  `tesser.Orchestrator(wf_ctx)` because that is the dependency once the
  dispatchers are taken out.
- `wf_ctx.operation ⇒ restate.Workflow.main` is one orchestrator starting
  another (`examples/durable-execution/`: `pay_for_order` reaching
  `OrderOrchestrator.confirm_order`).
- An action is reached only through the engine and never uses a relay; it
  uses one port.
- A durable promise can be resolved only from inside a handler of its own
  workflow: the SDK exposes `promise(...)` on `WorkflowContext` and
  `WorkflowSharedContext` only, and the HTTP client offers only calls and
  sends. That is why an outside event goes `restate.Client.operation ⇒
  restate.Workflow.handler -> .resolve` instead of resolving the promise
  directly, and why a signal registers on the container its workflow's `main`
  is registered on. A resolved promise cannot be resolved again.
- A dispatcher over HTTP opens an `httpx.AsyncClient` per call, as Restate's
  documentation does. One long-lived client crossed event loops in the LiveKit
  worker, and calls waiting on the workflow's `main` held every connection
  while the signals waited for one.

**One relay kind; lifetime is not a property of the protocol.** A relay
implemented over HTTP from outside the engine and one implemented inside an
invocation are the same `ts.Relay`, and the code holding one cannot tell which
it has. `examples/durable-execution/` shows it with two implementations of
`OrderOrchestratorRelay`: `RestateHttpOrderOrchestratorRelay`, built once by
the component, and `RestateInvocationOrderOrchestratorRelay`, built per
invocation of the purchase workflow to run the order workflow as a child.
Both hold the one `RestateConfirmOrder` instance and pass its `.handler`.

**A relay is named for its far side and carries any number of operations**
(Chris, 2026-09-22). A relay method is `<mode>_<operation>` and the mode is
the act, so the class name is free to say what sits on the other side of the
engine. The far side is what its dispatchers reach through a handler: an
activity's class of actions, a workflow's orchestrator, or a signal's
workflow. `CallOrchestratorRelay` carries `run_conduct_call`,
`run_person_joined`, and `run_person_turn_completed` because the first reaches
the workflow whose orchestrator is `CallOrchestrator` and the other two reach
signals on that same workflow; `CallActionsRelay` carries `run_record_call`
because that handler's activity calls `CallActions`. Every operation on one
relay must derive the same far side.

**There are three calling modes, and a signal relay is the one that awaits.**
`start_` sends and does not wait, `run_` sends and waits for the answer, and
`await_` sends nothing and waits for the far side's report — a durable promise
a signal resolves. `await_X` reads the promise whose name is the relays
constant equal to `"X"`, which the signal named `X` resolves, which `run_X`
invokes: one name, written once in `application/relays/`, read by both ends.
A relay that awaits is named `<FarSide>SignalRelay` and carries only `await_`
operations; no other relay carries one. Nothing outside an invocation can read
a durable promise, so a signal relay is implemented only inside an invocation,
and a Protocol cannot be partially implemented, so the two must not mix.
`examples/voice/` is the worked case: `CallOrchestratorSignalRelay` carries
`await_person_joined` and `await_person_turn_completed`, and
`RestateInvocationCallOrchestratorSignalRelay` is its only implementation.

**Lifetime is carried by placement instead.** A dispatcher inside an
invocation may hold that invocation's engine context; a gateway and a
repository never do. A port method takes exactly one `ts.Request`, with
nothing before it.

**A caller holds the callee's instance** (2026-09-23). An activity, a
workflow, and a signal each register their handler in `__init__` on the
container the component hands them and keep it as `self.handler`. A
dispatcher is constructed with the instances it calls and passes their
`.handler` to the SDK's typed call. The SDK serializes through the serdes
bound at registration, so a dispatcher names a snapshot only where it reads a
promise. Because the caller imports the callee's package, **imports go one
way: dispatchers → workflows → activities.** A dispatcher's name ends in the
relay it implements (`RestateInvocationCallActionsRelay`,
`RestateHttpCallOrchestratorRelay`), and its public methods are exactly the
relay's.

**The analyzer derives every name from those references** (TB085). (a) A
relay is named for the far side its dispatchers reach through
`self._x.handler`. (b) `run_X`/`start_X` passes the handler `def X`, with no
differing name, positional or `name=`. (c) `run_` waits (`*_call`) and `start_` does not
(`*_send`); an activity's handler is reached with `service_*`, a workflow's or
a signal's with `workflow_*`. (d) `await_X` and the signal named `X` use a relays constant equal
to `"X"`. (e) Each engine container is named for its far side, as a literal, positional or `name=`.
(f) Every activity, workflow, and signal is reached by a dispatcher, so the
engine holds no registration nobody calls. (g) An activity, workflow, or signal
registers exactly one handler, the one it keeps as `self.handler`: any function
in `__init__`, at any depth, decorated from or passed to `.handler(...)`/`.main(...)`
on an engine container parameter (typed as a `Service`, `Workflow`, or
`VirtualObject` of any package but tesser) or the attribute holding one. (h) A handler
name is unique in its engine container, because the SDK keeps one handler per
name. (i) A dispatcher never calls `generic_call`/`generic_send`. (j) A
`workflows/` module imports no HTTP client (`restate.client`, `httpx`,
`aiohttp`, `requests`, `urllib.request`, `urllib3`) and reads neither
`restate.create_client` nor `restate.RestateClient` (TB060): a call from inside
an invocation goes through its context, where the engine journals it, not over
HTTP, where it runs again on every replay. (k) An activity's handler calls its
application client's method named for the operation. (l) A signal's handler
calls `.promise(...).resolve(...)`. (m) A relays constant is assigned once,
because the analyzer reads one value and Python keeps the last. A signal relay's name is derived
today only through a `run_` operation that reaches its signal; an
`await_`-only relay is not derived yet (`TODOS.md`).

**The workflow builds the orchestrator.** Its `main` handler constructs the
orchestrator over that invocation's dispatchers and calls the operation:

```python
return await orchestrators.CallOrchestrator(
    RestateInvocationDialingActionsRelay(restate_workflow_context, restate_dial_person, restate_hang_up),
    RestateInvocationCallOrchestratorSignalRelay(restate_workflow_context),
    RestateInvocationSpeechActionsRelay(restate_workflow_context, restate_say_utterance),
    RestateInvocationCallActionsRelay(restate_workflow_context, restate_record_call),
).conduct_call(conduct_call_request)
```

Those dispatchers are declared in the workflow's module, since they exist
only for it and are tested through it. An orchestrator's public methods are
exactly those of the application client of its name in
`application/client/`, so its messages are relay messages. An activity
reaches a class of actions only through that class's application client,
which is the only way anything outside the application reaches it.

**No adapter translates a `DomainError`** into the engine's terminal error
today; one is retried under the registration's retry policy. A payload the
snapshot cannot parse is treated the same way: the engine-side serde turns
only an empty body into a terminal 400, and anything else the snapshot raises
is retried and then pauses the invocation under the retry policy.

**Open, 2026-09-23.** The workflow names the orchestrator implementation
directly (`orchestrators.CallOrchestrator(...)`); that is accepted for now and
not settled (Chris: "we still haven't uncovered the right architecture").
Nothing in voice holds the orchestrator's application client, which is
declared only because TB081 has the orchestrator mirror it. An `await_`
operation's request is read by nothing in its dispatcher. The workflows test
sits below the signals, so it cannot resolve the promises: it asserts the
journal up to the first promise wait, and the dispatchers test runs the whole
call.

**A relay message may carry a domain object, and that is not a widening of the
no-outward-representation line.** A relay is *inward*: it crosses the engine
inside one context and is never operated through the client. A `ts.Client`
faces outsiders and a `ts.Port` faces a foreign system, so those stay
primitives-only; a relay has us on both ends, so
`RecordCallRequest(call: domain.Call)` is legal and the call comes back whole.
A bare bool and a union are findings on a relay message too.

**Who may invoke a relay.** A service, through a dispatcher over HTTP, and an
orchestrator, through a dispatcher inside the invocation. Never an action — an
action has one port and one call on it, and a relay inside an action is the
engine calling the engine. Never a handler, never a component. An actions
class depends only on ports and the stores that yield them; a service and an
orchestrator may depend on ports, relays, and stores; nothing else may hold a
relay.

**A snapshot decides once, on shape.** A snapshot (`ts.Serde` from
`tesser.application`, in `application/relays/` beside its messages, or in
`application/snapshots/` when several relays share one) holds nothing and
declares exactly `serialize` and `deserialize`. `serialize` is one return of
`json.dumps` over a literal dict whose values are attribute reads or canonical
exits (`str(...)`, `int(...)`) of the message, or one return of another
snapshot's `serialize`. `deserialize` reads `json.loads`, carries at most one
guard — built only from `isinstance`, truthiness, and comparison to constants
over the loaded value — that raises `errors.invalid`, and ends in one
constructor call. The only calls a snapshot may name are `json.dumps`,
`json.loads`, `isinstance`, `str`, `int`, `errors.invalid`, `.encode`/`.decode`,
`.get` with one argument, the message and spec constructors, and another
snapshot's `serialize`/`deserialize`. A second branch, a loop that computes,
`.get` with a fallback, arithmetic, and any domain method are findings. The
engine-side serde (`tesser.adapters.Serde`, in the module of the activity,
workflow, or signal that binds it) keeps its narrower form: one guard on the
empty payload, then delegation to the snapshot.

**Reach.** An adapters module lives in `handlers/`, `gateways/`,
`repositories/`, `activities/`, `workflows/`, or `dispatchers/` and holds the
kinds its package names. `handlers/` → the context client. `gateways/`,
`repositories/` → `application.ports`. `activities/` → `application.client`,
`application.relays`. `workflows/` → `application.orchestrators`,
`application.relays`, `activities`. `dispatchers/` → `application.relays`,
`workflows`. Dispatchers → workflows → activities is the one order in which
adapters kind packages import each other; every other pair still may not.
**Only an activity imports the application client**, because an action is
reachable only through the engine, and **only a workflow imports the
orchestrators**, because it builds one per invocation. Each of the three
packages is one module in voice: a module imports no sibling module, and the
HTTP dispatcher names the signal classes beside it.

**What the component builds and publishes.** The component builds the
`restate.Service` and `restate.Workflow` containers, naming each once as a
literal, then builds activities → workflow → signals → dispatcher → services,
each handed what the one before it built. It publishes `client`, typed as its
`ts.Client`, and each attribute assigned from an engine registration
constructor (`restate.Service`, `restate.Workflow`, `restate.VirtualObject`)
that it hands to an activity, workflow, or signal constructor; `client` is
never such an attribute (TB081). The host binds the published containers
(`restate.app([...])`) and knows nothing else about the engine.

**What transfers from the service body rules to the adapter kinds.** Of the
four call-then-map rules (skill ruling 2026-08-30), exactly one costs nothing
on the trees as they stand, so exactly one ships: **a gateway, a repository,
and a dispatcher inline their logic** — no delegation to a private method or a
module function beside it. The other three were measured over all eleven app
trees and are not implemented: "name what you compute" would take 79 sites,
"decide nothing in the open body" 107 (40 of them in `layout/`'s single
`FilesystemRepoReader.read` and 35 in `tessercheck-py/`'s two filesystem
repositories), and "one call on the backend per method" 1. "An adapter raises
no domain kind" was rejected outright. The numbers are in `TODOS.md`.

**A second engine.** `examples/minimal/` runs every kind above on a small
synchronous in-process engine, `in_process/` at the tree's root, which
`.tesser-root` skips as it skips `memoryclient/`: a library the adapters
import, not a tesser kind. Its `Service` and `Workflow` register a `Handler`
object through `.handler()`/`.main()`, a caller passes that object to
`WorkflowContext.service_call` or to the module's `workflow_call`, and a
workflow keeps its promises per key, so the same TB085 rows hold. It does not
journal or suspend: a signal must resolve a promise before the workflow reads
it, and reading one nobody resolved raises.

**The deprecated kinds.** No tree uses them. Their rules still run until the
removal in `TODOS.md`: a runner (`ts.Runner`, `adapters/runners/`) implements a relay by calling its far side by literal
service and handler name (`generic_call`/`generic_send`, `promise("X")`), and a
workflow runner implements `ts.DeprecatedWorkflow` (the application-side
protocol formerly called `ts.Workflow`, declared beside an orchestrator's
application client and yielding it per invocation); a runtime (`ts.Runtime`,
`adapters/runtimes/`) registers the engine's handlers under literals and may
register only what a runner of its context reaches. TB085 checks those
literals against the relay.

---

*Everything below is the 2026-08-29 record. It speaks of jobs and job contexts,
which no longer exist; read it for the reasoning, not for the shape.*

## The three application kinds

| kind | base | public? | constructed | depends on | reached through |
|---|---|---|---|---|---|
| application service | `ts.ApplicationService` | yes, on `client.Client` | component, once | ports | a handler |
| orchestrator | `ts.Orchestrator` (new), in `application/orchestrators/` | no | a job, per invocation, with that invocation's `ts.JobContext` | exactly one `ts.JobContext` plus action ports — never a repository, never the workflow-start port, never a foreign client | the job that built it; nothing else holds one |
| action | `ts.Actions` (new) — a class of actions | no | component, once | exactly one `ts.Port` in `__init__`; each public method calls it exactly once (a class of actions shares one dependency; a second port is a second class) | a job, via an actions protocol |

All three keep the four-step body and the TB081/TB082 rules unchanged: one
`ts.Request` in, one `ts.Response` out, `match` only, no delegation chain.
What distinguishes them is scope, reach, and dependencies, not body shape.

Orchestrator extras: it may call several actions (sequencing them is its
job); it is async because the gateway awaits the engine. Everything it does
between journaled calls re-executes on replay, which is the mechanical
reason it holds actions and not repositories. Two rules that follow:

- Its `__init__` stores only its action ports; no other attribute is ever
  assigned, in `__init__` or in a method (codex #12 — "constructed per
  invocation" is not by itself a state rule; a `self._state` written between
  journaled calls diverges on replay). Same shape as the mapper's
  stores-nothing rule.
- Its stdlib allowlist is the application role's existing one,
  `{__future__, typing}` (`CORE_STDLIB["application"]`), unchanged. An
  earlier draft widened it to the domain's set minus `time`/`random`/
  `uuid`/`os`; that was wrong in direction — the domain set includes
  `datetime` — and unnecessary, because the application allowlist is already
  deterministic by construction (codex #8).

Orchestrators live in their own package, `application/orchestrators/`, one
per module, so the import row "only a job imports an orchestrator" names a
package rather than a class the analyzer would have to find by base (codex
#4).

The initial service stays an ordinary application service whose one port
happens to be the workflow-start port. It does the once-only,
non-deterministic work (mint the ID, validate at the door) and owns the
synchronous contract; the orchestrator owns the asynchronous one.

## Protocols — direction is carried by kind

A `ts.Port` is what the application declares so an adapter can implement it;
a `ts.Client` is what the application exposes so an adapter can call it.
Import rows and fakes both key on that, so one protocol object may not serve
both directions.

- Outbound (orchestrator → engine): a port. `application/ports/quoting.py`
  declares `Quoting(ts.Port)`, implemented by the engine gateway.
- Inbound (job → action): a client protocol, **`tesser.application.Client`**
  — a new class in the application package, not a reuse of
  `tesser.context.Client`. Same word, different package, the way
  `tesser.application.Request` and `tesser.context.Request` already coexist:
  an application module imports `tesser.application as ts` (TB050), so
  `ts.Client` there resolves to the application one and the totality check
  classifies by resolved base. It lives in a new package
  **`application/client/`**, the application-level mirror of the context's
  `client/` — one protocol per module, the module named for the actions it
  fronts. It cannot live on the context's `client.py`: anything there is
  reachable by a foreign context (TB061), and an action must be reachable
  only through the engine; `application/client/` is unreachable from outside
  by the existing row. The concrete `OrderActions(ts.Actions)` lives in
  `application/` beside the services.
  Naming follows the context-level client, not the repository: the protocol
  is `Client`, the impl is the plain noun, and there is no qualifier —
  a client fronts the one impl so outsiders depend on the protocol, not the
  impl, exactly as `client.Client` fronts `AlphaService`.

  ```
  application/client/order_actions.py    class Client(ts.Client, typing.Protocol)
  application/order_actions.py           class OrderActions(ts.Actions)
  ```

  A job reads `actions: order_actions.Client`, as a handler reads
  `client.Client`. The two modules share a basename; no module imports both
  (jobs import the protocol, the component imports the impl, and the
  component's actions attribute is private under the publishes-only rule
  below, so it needs no protocol annotation).
  An application client module is **not a leaf**: it imports exactly one
  ports module, for the DTOs it speaks, and nothing else from the tree. The
  rest of the ports-module discipline applies (one protocol per module,
  nothing runs at import, no decorators, no class-level statements). An
  earlier draft said "the ports-module discipline" without the carve-out,
  which contradicted the DTO rule below (codex #1).
- A single `application/client.py` module was considered and rejected: one
  protocol per module needs a package, and a bare module collides with the
  `import ordering.client.client as client` alias every handler uses.
- The orchestrator has no inbound protocol. Only the job calls it, and the
  job constructs it concretely.

## Messages — declared once, on the port

The engine is a relay, so the send side and the receive side of one message
are not independent boundaries; making them independent buys nothing and
lets them drift. Each message is a `ts.Request`/`ts.Response` declared once,
in the ports module, and both ends import it.

- The orchestrator takes the workflow port's own request
  (`order_workflow.StartRequest`); `client.RunRequest` goes away. Its
  response is its own (start is a fire-and-forget ack; the workflow result is
  a different message).
- The actions protocol speaks the port's `QuoteRequest`/`QuoteResponse`;
  `client.QuoteRequest` goes away. New line: an actions module speaks the
  DTOs of exactly one ports module.
- Because the action's request *is* the port's request type, TB082's
  "a value crossing into a port has passed through a domain type" must also
  catch the whole request object passed straight to the port, not only a
  field pulled off it (codex #2 found the hole). #138's action already passes
  through a domain type (`order.Sku(request.sku)`), so the rule is a check
  to add, not a change to the shape.
- No wire types. A custom `restate.serde.Serde` over `ts.Request`/`ts.Response`
  is bound at the handler decorators; the gateway reads it off the handler
  function, so it needs nothing. `protocol/durable.py` is deleted: it
  carried `sku`, `quantity`, `cents` — one context's vocabulary — and
  `protocol/` is context-generic (TB064). The serde class lives in
  `adapters/jobs/restate.py`, beside the decorators that bind it (the
  workflow gateway's sibling test decorates its throwaway handler over a
  serde stand-in defined inside the test, since a gateway test cannot reach
  `jobs/`). It carried the wave's one remaining `tesser:debt TB052` — every
  context class must declare a `ts.*` base, and `restate.serde.Serde` is an
  ABC — until the 2026-08-30 ruling named the kind: `tesser.adapters.Serde`,
  admitted in `adapters/jobs/`, declaring exactly `serialize` and
  `deserialize` over one type parameter, holding at most the target type, and
  branching on nothing but the empty payload. It is the one adapter class
  allowed a base from outside the tree, because the engine is the caller, so
  the class reads `class RecordSerde[T](ts.Serde, restate.serde.Serde[T])`
  and the marker is gone.
  What that serde has to be (codex #9): type-directed and recursive, not
  "JSON of `__init__` fields". Port DTO fields may be primitives, nested
  DTOs, tuples, and `enum.Enum` members (TB080); Optional and bool are
  already banned on port DTOs. Each of those needs an encoding and a
  decoding keyed on the annotation.
  What it does not yet have (codex #10, **deferred, named**): a payload
  versioning policy. A field added to a port DTO changes the bytes an
  in-flight journal already holds; replay then constructs the DTO from JSON
  that lacks the field. Whether the serde tolerates absent fields, the DTO
  carries a version, or a DTO change is a new message, is a durable-execution
  rule this wave does not make. Until it does, a port DTO on a durable leg
  is append-only in the example.
  On Temporal the serde is a data converter bound at client/worker creation,
  not at a decorator (codex #7). The kinds survive; the binding site moves.
- `client.py` shrinks back to one `Client` and its DTOs.

## Adapters — split by reach, not by transport

New adapter kind package `adapters/jobs/`, base `ts.Job`. The decision rule:
a handler calls the client; a job calls an action or constructs an
orchestrator. `RestateHandlers` (both `run` and `quote`) moves there.

The split exists because a role-level rule cannot tell an HTTP handler from
a Restate handler, and an HTTP handler that may import an action can call it
in-process — the bypass "not on the public Client" exists to close. Placement
is how the analyzer carries every other reach distinction — but only once
the adapters role stops importing itself freely. Today TB060 lets any role
import itself (`checks.py`, `pieces[1] == role`), so `handlers/http.py` may
import `adapters/jobs/*` and the package alone closes nothing (codex #3).
The `adapters` role therefore gets per-kind rows, below. The analyzer
already keys one row on whether a module holds a handler (`holds_handler`),
so per-kind rows extend an existing mechanism.

On Temporal the job is the worker registration: it holds the concrete
action the component built and registers a decorated closure over it as
the activity, the same shape `RestateHandlers` has (codex #6). No new
construction path is needed.

Gateways do not split: an engine gateway, a cross-context gateway, and a
vendor gateway all have the same row (→ ports).

LiveKit tool handlers (`examples/llmport`) stay in `handlers/`: they call the
client. LiveKit's own "job" (the server dispatching a room session to a
worker) is what the host accepts, not a `ts.Job`; one doc line so nobody
looks for `jobs/` in llmport.

Names considered: `workflows/` (collides with the workflow-start port, and
both engines use the word for only half the contents), `processes/`,
`invocations/`, `durable/`, `engines/`, `activities/`, `steps/`,
`orchestrations/`, `tasks/`, `work/`. `jobs/` chosen: plural noun,
engine-neutral, covers the workflow entry and the action handlers equally
(every invocation the server hands us is one job), and matches the
Rails/Celery reading where `jobs/` holds the code that runs when dequeued.

## The job context — how the invocation reaches the application

Something per invocation has to hold the engine's context (Restate's
`WorkflowContext`; on Temporal there is no object, the `workflow.*` API is
ambient). The question is which kind holds it. Surveyed `~/workspace/flow`
(2026-08-29): seven orchestrators in three regimes — ctx per method (bill,
delivery, settlement, order-plan), ctx stored in the constructor (order,
invoicegroup), ctx hidden behind an executor port (widgets only); the order
workflow mixes the first two inside one workflow, and its two phase ports
disagree (`BillingPhasePort.Run(ctx, ...)` vs `OpenPhasePort.OpenOrder(input)`
with the adapter storing the ctx). flow's `CLAUDE.md` names the widgets shape
as the intent; only the scaffold context obeys it.

**Ruled (option 2 of two):** one regime.

- `tesser.application.JobContext` is a protocol (re-exported unchanged as
  `tesser.adapters.JobContext` and `tesser.testing.JobContext`, so `ts.JobContext`
  is one class from every placement): what a step may do inside an
  invocation, engine-neutral. Today: `call[I, O](step: Callable[[Any, I],
  Awaitable[O]], request: I) -> O` — the SDK's `HandlerType` spelled in
  stdlib types, and Temporal's `execute_activity(fn, arg)` shape. `sleep`,
  `wait_for`, `send` are the next members when an orchestrator needs them.
- A job builds its context's implementation per invocation
  (`RestateJobContext(ctx)`, its own kind, in `adapters/jobs/`) and hands
  it to the orchestrator's constructor together with the action ports.
- The orchestrator stores exactly one job context and its action ports, and
  threads the job context as the **leading parameter of every action-port
  call**: `self._quotes.quote(self._job, request)`. An action port's method
  is `(ts.JobContext, one ts.Request) -> ts.Response` — the Go leading-`ctx`
  convention, and flow's `BillingPhasePort` one, applied everywhere.
- A gateway is built once by the component (holding the engine's handler
  function) and **never stores an invocation's context**; it receives the
  job context per call and does `job.call(self._quote, request)`. flow's
  `OpenPhaseAdapter` (stores the ctx) is the shape this forbids.
- Rejected: option 1, the gateway built per invocation by the job (needed a
  `jobs → gateways` row and, once an orchestrator needs a timer or a signal,
  two copies of one handle); and reading the SDK's ambient
  `restate.extensions.current_context()` — it exists and is set on every
  handler entry, but its module is documented as "internal extensions apis"
  and no documented handler code uses it.
- Cost paid: the workflow job needs the action handler *function* before it
  can build its gateway, so the Restate side is two job classes
  (`RestateActionJobs`, `RestateWorkflowJobs` — Restate's own Service /
  Workflow split) and a component publishes `jobs` as a tuple.

## Import rows that change

1. TB060 same-context matrix, with the `adapters` role split by kind
   package (codex #3):
   - `handlers` → `client`. Not `jobs`, not `application.client`, not
     `application.orchestrators`.
   - `jobs` → `application.client` + `application.orchestrators` (to
     construct) + `application.ports` (the message DTOs). Not the context's
     `client`. (A `jobs → adapters.gateways` row existed briefly, while the
     Restate gateway was built per invocation over the ctx; the job-context
     ruling below removed the need.)
   - `gateways`, `repositories` → `application.ports` (unchanged). Not
     `jobs`, not `handlers`.
   - a kind package may still import itself (a gateway may import a sibling
     gateway module); "a role imports itself" narrows to "a kind imports
     itself" inside `adapters`.
   Nothing outside `jobs` may import `application.client` or
   `application.orchestrators`.
2. TB063 host reach: handlers and jobs (the host mounts `definitions()`).
3. TB052 one-adapter-kind list: add `ts.Job`.
4. TB052/TB041: `application/client/` and `application/orchestrators/` are
   recognized application packages. `application/client/` has the
   ports-module discipline minus the leaf rule: one
   `tesser.application.Client` protocol per module, nothing runs at import,
   and it imports exactly one ports module.
   `orchestrators/` holds one `ts.Orchestrator` per module.
5. New body rules: an action has one port in `__init__` and one port call
   per public method; an orchestrator depends on action ports only, keeps
   the application stdlib allowlist, stores only its action ports, is
   constructed only in a job, and is held by nothing.
6. New component rule (codex #11 — a `ts.Client`-typed-attribute check is
   porous when the attribute can be untyped or `object`): a component
   publishes exactly `client`, typed as its `ts.Client`, and — when it has
   jobs — `jobs`, typed as its `ts.Job`; every other attribute is private.
   This closes the component-attribute gap the durable-execution memory
   carries as open.
7. TB070 test placement: add `jobs` to `TEST_TIER_HOME`, `TEST_TIER_REACH`
   (the `jobs` row from item 1), and `ADAPTER_TEST_TIERS`; add
   `orchestrators` and `actions` sibling tests with their packages' reach.
   These are literal tables in `checks.py`, so nothing follows
   automatically (codex #5).

## Deliberately out of scope for this wave

- Errors: the `DomainError ↔ TerminalError` mapping is duplicated in both
  handler bodies and the error rules are not right yet; leave as is.
- The llmport rework: `LlmToolHandler` carries too much logic; separate wave.
- The Temporal mirror: next; the kinds are expected to survive it unchanged
  (activities register `actions.quote` by reference; the workflow function
  builds the orchestrator).
- Multi-context host / one deployment per context: parked. Restate versions
  by deployment URI, so contexts likely want separate mounts.
- The engine-neutral runtime port (`run`/`sleep`/`wait_for`/`send`): not
  built; if it comes, it is the one non-action port an orchestrator may take.
- Retries, timeouts, heartbeats, idempotency keys, and activity options
  belong to the engine gateway — the durable route's concern — and never to
  the port DTO (codex #14/#15). Stated so they do not drift into the message.
- Payload versioning on a durable leg: deferred, named above under Messages.
- PR #138's host calls `app.close()` synchronously while the component's
  `close` is async: a bug to fix in the rework, not a rule.

## Not yet ruled

- ~~Whether TB081's one-request check accepts a `tesser.application.Request`
  on an action's public method where a service's takes a
  `tesser.context.Request` (codex #2, unverified against `checks.py`).~~
  **Ruled by the implementation, verified 2026-08-29:** it does.
  `_actions_violations` passes `param_block="port_request"`
  (`checks.py:7079-7090`), and `("tesser.application", "Request")` is that
  block (`checks.py:16`) — so an action's public method takes a
  `tesser.application.Request`, the same DTO its one port speaks.

## Codex findings not taken

- #13 (the handler/job rule is not a partition): a queue consumer that calls
  the client is a handler by the rule; the discomfort is naming, not reach.
- #14 beyond discovery-schema coupling: engine metadata lives on the gateway
  (see out of scope), so it does not force churn in the port DTO.
