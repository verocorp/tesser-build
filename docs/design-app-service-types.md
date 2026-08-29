# Application-service types — orchestrators, actions, jobs

Status: RULED and BUILT, 2026-08-29 — tesser-py kinds, tessercheck rules,
the `examples/minimal` exemplar, and the `examples/durable-execution` rework
(live-verified through a Restate server) all land in the same PR. Amended
after a codex challenge review (15 findings; the ones taken are marked
"codex #n" below) and once more by the rework (the jobs → gateways row).
Carved from the durable-execution example (PR #138,
`examples/durable-execution`) after the 2026-08-25 (flow/Temporal chain) and
2026-08-27/28 (Restate build) sessions. The example is to be reworked to
match; the rules follow the example.

## The three application kinds

| kind | base | public? | constructed | depends on | reached through |
|---|---|---|---|---|---|
| application service | `ts.ApplicationService` | yes, on `client.Client` | component, once | ports | a handler |
| orchestrator | `ts.Orchestrator` (new), in `application/orchestrators/` | no | a job, per invocation, over a gateway holding that invocation's engine ctx | action ports only — never a repository, never the workflow-start port, never a foreign client | the job that built it; nothing else holds one |
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
  `adapters/gateways/restate_workflow.py`, the send-side gateway (its own test and the job both reach
  it) and carries the wave's one remaining `tesser:debt TB052`: every context
  class must declare a `ts.*` base, `restate.serde.Serde` is an ABC, and no
  adapter serde kind exists yet — recorded in `TODOS.md`.
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

## Import rows that change

1. TB060 same-context matrix, with the `adapters` role split by kind
   package (codex #3):
   - `handlers` → `client`. Not `jobs`, not `application.client`, not
     `application.orchestrators`.
   - `jobs` → `application.client` + `application.orchestrators` (to
     construct) + `application.ports` (the message DTOs) + `adapters.gateways`
     (to construct the engine gateway per invocation — it needs the
     invocation's ctx, which only the job holds; `minimal` did not expose
     this because its component hands the job a ready gateway, the Restate
     tree did). Not the context's `client`.
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

- Whether TB081's one-request check accepts a `tesser.application.Request`
  on an action's public method where a service's takes a
  `tesser.context.Request` (codex #2, unverified against `checks.py`).

## Codex findings not taken

- #13 (the handler/job rule is not a partition): a queue consumer that calls
  the client is a handler by the rule; the discomfort is naming, not reach.
- #14 beyond discovery-schema coupling: engine metadata lives on the gateway
  (see out of scope), so it does not force churn in the port DTO.
