# durable-execution — one context whose workflow runs on Restate

The chain, top to bottom, with where each link lives:

| Step | Placement | Code |
|---|---|---|
| a CLI host places an order | `srv/cli/main.py` | `CliHost` → `ordering/adapters/handlers/cli.py` |
| the initial application service | `ordering/application/order_service.py` | `OrderService.place` builds the `Order` aggregate |
| it starts the workflow through a port | `ordering/application/ports/order_workflow.py` | `OrderWorkflow.start(StartRequest) -> StartResponse` |
| the Restate SDK sends the workflow | `ordering/adapters/gateways/restate_workflow.py` | `RestateOrderWorkflow.start` → `client.generic_send(service, handler, body, key=order_id)` on the `RestateClient` and the two names the component handed it |
| Restate's server calls the workflow handler | `srv/restate/main.py` | `RestateHost` mounts `@workflow.main()` → `ordering/adapters/handlers/restate.py` `WorkflowHandler.run` |
| the orchestrator, an internal application service | `ordering/application/order_orchestrator.py` | `OrderOrchestrator.run` builds the `Order`, asks its actions for a quote |
| it runs the action through a port | `ordering/application/ports/order_actions.py` | `OrderActions.quote(QuoteRequest) -> QuoteResponse` |
| the Restate SDK calls the action durably | `ordering/adapters/gateways/restate_actions.py` | `RestateOrderActions.quote` → `ctx.generic_call(service, handler, body)` on `restate.extensions.current_context()` |
| Restate's server calls the action handler | `srv/restate/main.py` | `@actions.handler()` → `ActionHandler.quote` |
| the action, an internal application service with a repository lookup | `ordering/application/order_actions.py` | `OrderActions.quote` → `CatalogRepository.price` → `adapters/repositories/memory.py` |
| the price comes back up the same chain | | `QuoteResponse.cents` → `Order.total(PriceSpec)` → `RunResponse.total_cents` ends the workflow |

Restate never touches the domain, and the application never touches
Restate. `OrderOrchestrator` depends on the `OrderActions` port and nothing
else; `OrderActions` (the application service) depends on the
`CatalogRepository` port and nothing else. Both are plain application code.
What makes the orchestrator's call to its actions durable is which
implementation of the port it was handed — a gateway that goes through the
engine.

## What the engine is, in this anatomy

- **Inbound, it is a host.** Restate's server calls `RestateHost`, which
  routes to handlers like any other host: one `Workflow` and one `Service`,
  each with one named handler. `BytesSerde` on both sides keeps the body
  opaque bytes so the handler owns content.
- **Outbound, it is a gateway over a port.** Starting the workflow is
  `RestateOrderWorkflow` over `OrderWorkflow`; running an action is
  `RestateOrderActions` over `OrderActions`. Each is built once, at wiring
  time, like any gateway.

**The invocation context is the SDK's to provide.** A Restate handler is
handed a `WorkflowContext`, and only calls made through it are journaled.
The SDK sets that context into its own `ContextVar` when it enters a handler
and exposes it as `restate.extensions.current_context()`, so a gateway that
was wired once reads the current invocation's context at call time. Nothing
in this tree binds, stores, or hands the context around: the host routes,
the handler transforms, the gateway reads the ambient context. (The SDK's
module docstring calls `extensions` internal; this example pins
`restate_sdk>=1.0` and the srv test reads the host's `/discover` manifest,
which is where an SDK change would surface.) The gateway's sibling test can
only cover the outside-an-invocation path — the SDK's context class is an
ABC no `@ts.fake` may implement — so the call path is covered by the live
run below.

## The context owns its Restate address

The four names Restate is addressed by are declared once, in the component:
`RestateAddress(workflow, run, actions, quote)` is a client DTO that
`Ordering.__init__` constructs and publishes as `Ordering.address`. Both
readers take it from there — the gateways are handed the two names each one
calls (outbound), and `srv/restate/main.py` registers
`restate.Workflow(built.ordering.address.workflow)` and
`@workflow.main(name=built.ordering.address.run, ...)` (inbound). Nothing else
in the tree spells them. `srv/restate/test_main.py` boots the real host, reads
`/discover`, and asserts the discovered manifest against the address the
component published.

**This diverges from `srv.md` rule 5 — the route table is the host's — and does
so on purpose.** A route table is an app-level decision because the callers are
outside the app. Here the context is its own caller: the address is an
agreement between this context's gateway and this context's handler, and the
host only speaks it to the SDK at registration. Mounting this context beside
others would still leave the host owning the transport, but not this name.

Two placement facts shape the DTO. It is a `ts.Response` on the client module,
not a `ts.Record`: `ts.Record` is a protocol kind from `tesser.srv`, while a
client module imports only `tesser.context` (TB050/TB062) and holds only
requests, responses, and clients (TB052). And the gateways take the two names
as parameters rather than the whole DTO, because only a handler imports its own
context's client (TB060) — the same rule that keeps the SDK's typed path (which
derives the names from the decorated handler object) out of a gateway's reach.
Nothing in tessercheck yet says what a component may publish beside `client`
and `close`; `address` sits in that gap, as `orchestrator` and `actions`
already do.

## Errors across the engine

A `DomainError` or a `BadInvocation` in a handler becomes a
`restate.TerminalError` with the kind's status — no retry. When the action
handler raises it, the workflow's gateway receives it as a `TerminalError`
from `generic_call` and raises it again as a `DomainError`, so the
orchestrator and the workflow handler see a domain error, not an SDK one,
and the workflow ends terminally with the action's message. Anything else
propagates as-is and Restate retries the invocation.

## The gateway holds the SDK's client, and nothing sits between

`RestateOrderWorkflow` takes a `restate.RestateClient`, plus the service and
handler names the component addressed it with, and calls `generic_send` on it. The component builds the real one —
`restate.client.Client(httpx.AsyncClient(base_url=cfg.ingress))`, which is
all `restate.create_client` does under its context manager — and closes it.
Because an httpx client's connections belong to the loop that opened them,
the app's lifecycle is async end to end: `Ordering.close` and `App.close`
are `async`, and each host awaits them inside its own loop. The sibling
test builds the same real client over `httpx.MockTransport` and checks the
URL the SDK forms (`/Ordering/o1/run/send`), the content-type, and the body.

## Async everywhere the SDK is, sync only at the process edge

The SDK is async on both sides, so the request path is `async`:
`OrderWorkflow`, `OrderService`, `Client.place`, the CLI handler,
`OrderActions` (the port), `Orchestrator`, `WorkflowHandler`. The action
service and its repository are sync — plain application code that runs
inside the action handler. The only `asyncio.run` on the request path is
in `CliHost`, where a loop begins; the Restate host's loop is hypercorn's.

## Running it

```
pip install -r requirements-dev.txt
docker run -d --name restate -p 18080:8080 -p 19070:9070 docker.io/restatedev/restate:latest
PYTHONPATH=.:../../tesser-py RESTATE_INGRESS=http://localhost:18080 \
  python -m srv.restate.main 0.0.0.0:9080 &                     # the workflow + action host
curl -X POST localhost:19070/deployments --json '{"uri":"http://host.docker.internal:9080"}'
PYTHONPATH=.:../../tesser-py RESTATE_INGRESS=http://localhost:18080 \
  python -m srv.cli.main o1 gadget 2                            # places the order, starts the workflow
curl localhost:18080/restate/workflow/Ordering/o1/output       # {"order_id": "o1", "total_cents": 2000}
```

**SIGTERM belongs to the SDK.** `restate.app` installs its own `SIGTERM`
handler on the first request, replacing hypercorn's: to Restate, SIGTERM
means drain the in-flight invocations, and the deployment is expected to
SIGKILL afterwards. The host stops on SIGINT; the srv test sends SIGINT.

## Production boundaries this example does not cross

- The catalog is an in-memory repository seeded with two SKUs; the CLI host
  and the Restate host each hold their own copy, which is fine only because
  the lookup is read-only.
- `RestateOrderWorkflow.start` fires and forgets; the CLI never waits on the
  workflow. The result is read back through Restate's ingress.
- The Temporal mirror is the next increment: the same context and ports, a
  `TemporalOrderActions` gateway whose `quote` is `ExecuteActivity`, a
  `TemporalOrderWorkflow` gateway over `ExecuteWorkflow`, and a worker host
  that registers the workflow and the activity.
