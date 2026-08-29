# Application-service types — orchestrators, actions, jobs

Status: DRAFT rulings, 2026-08-29. Carved from the durable-execution example
(PR #138, `examples/durable-execution`) after the 2026-08-25 (flow/Temporal
chain) and 2026-08-27/28 (Restate build) sessions. The example is to be
reworked to match; the rules follow the example.

## The three application kinds

| kind | base | public? | constructed | depends on | reached through |
|---|---|---|---|---|---|
| application service | `ts.ApplicationService` | yes, on `client.Client` | component, once | ports | a handler |
| orchestrator | `ts.Orchestrator` (new) | no | a job, per invocation, over a gateway holding that invocation's engine ctx | action ports only — never a repository, never the workflow-start port, never a foreign client | the job that built it; nothing else holds one |
| action | `ts.Action` (new) | no | component, once | exactly one `ts.Port` in `__init__`; each public method calls it exactly once (a class of actions shares one dependency; a second port is a second class) | a job, via an actions protocol |

All three keep the four-step body and the TB081/TB082 rules unchanged: one
`ts.Request` in, one `ts.Response` out, `match` only, no delegation chain.
What distinguishes them is scope, reach, and dependencies, not body shape.

Orchestrator extras: deterministic between journaled calls, so its stdlib
allowlist is the domain's minus `time`/`random`/`uuid`/`os`; it may call
several actions (sequencing them is its job); it is async because the
gateway awaits the engine. Everything it does between journaled calls
re-executes on replay, which is the mechanical reason it holds actions and
not repositories.

The initial service stays an ordinary application service whose one port
happens to be the workflow-start port. It does the once-only,
non-deterministic work (mint the ID, validate at the door) and owns the
synchronous contract; the orchestrator owns the asynchronous one.

## Protocols — direction is carried by kind

A `ts.Port` is what the application declares so an adapter can implement it;
a `ts.Client` is what the application exposes so an adapter can call it.
Import rows and fakes both key on that, so one protocol object may not serve
both directions.

- Outbound (orchestrator → engine): a port. `application/ports/order_actions.py`
  declares `OrderActions(ts.Port)`, implemented by the engine gateway.
- Inbound (job → action): a new client-kind protocol, `ts.Actions`, in a new
  package `application/actions/` — one protocol per module, the inbound twin
  of `ports/`. It cannot live on `client.py`: anything there is reachable by a
  foreign context (TB061), and an action must be reachable only through the
  engine. The concrete `OrderActions(ts.Action)` lives in `application/`
  beside the services and implements it.
- `application/client.py` was considered and rejected: it collides with the
  `client` role name, with the `import ordering.client.client as client`
  alias every handler already uses, and with the reach the word names.
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
- No wire types. A custom `restate.serde.Serde` over `ts.Request`/`ts.Response`
  (JSON of `__init__` fields) is bound at the handler decorators; the gateway
  reads it off the handler function, so it needs nothing. `protocol/durable.py`
  is deleted: it carried `sku`, `quantity`, `cents` — one context's
  vocabulary — and `protocol/` is context-generic (TB064). The serde class
  lives in the jobs module.
- `client.py` shrinks back to one `Client` and its DTOs.

## Adapters — split by reach, not by transport

New adapter kind package `adapters/jobs/`, base `ts.Job`. The decision rule:
a handler calls the client; a job calls an action or constructs an
orchestrator. `RestateHandlers` (both `run` and `quote`) moves there.

The split exists because a role-level rule cannot tell an HTTP handler from
a Restate handler, and an HTTP handler that may import an action can call it
in-process — the bypass "not on the public Client" exists to close. Placement
is how the analyzer carries every other reach distinction.

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

1. TB060 same-context matrix: `jobs` → `application.actions` + the
   orchestrator module (to construct it) + `application.ports` (the message
   DTOs). `handlers` stays → `client`. Nothing else may import `actions/` or
   an orchestrator module.
2. TB063 host reach: handlers and jobs (the host mounts `definitions()`).
3. TB052 one-adapter-kind list: add `ts.Job`.
4. TB052/TB041: `application/actions/` is a recognized application package
   with the ports-module discipline (one protocol per module, leaf-ish,
   nothing runs at import).
5. New: an action has one port in `__init__` and one port call per public
   method; an orchestrator depends on action ports only, has the restricted
   stdlib, is constructed only in a job, and is held by nothing; nothing
   assigned to a `ts.Client`-typed attribute is an `Action` or an
   `Orchestrator`.
6. TB070 test placement follows the packages automatically.

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
- PR #138's host calls `app.close()` synchronously while the component's
  `close` is async: a bug to fix in the rework, not a rule.

## Not yet ruled

- Placement of the orchestrator module: beside the services in
  `application/`, or `application/orchestrators/`. The import row is easier
  to state as a package.
- Whether the actions protocol and the concrete action share a name
  (`OrderActions` in two modules) or the protocol gets its own.
