# durable-execution — one FastAPI host: the API front door and the mounted Restate endpoint

The chain, top to bottom, with where each link lives:

| Step | Placement | Code |
|---|---|---|
| an HTTP host takes `POST /orders` | `srv/http/main.py` | `HttpHost`'s `APIRouter` → `ordering/adapters/handlers/http.py` `Handler.place` |
| the initial application service | `ordering/application/order_service.py` | `OrderService.place` builds the `Order` aggregate |
| it starts the workflow through a port | `ordering/application/ports/order_workflow.py` | `OrderWorkflow.start(StartRequest) -> StartResponse` |
| the Restate SDK sends the workflow | `ordering/adapters/gateways/restate_workflow.py` | `RestateOrderWorkflow.start` → `client.generic_send(service, handler, body, key=order_id)` on the `RestateClient` and the two names the component handed it |
| Restate's server calls the workflow handler | `srv/http/main.py` | the endpoint mounted at `/restate`: `@workflow.main()` → `ordering/adapters/handlers/restate.py` `WorkflowHandler.run` |
| the orchestrator, an internal application service | `ordering/application/order_orchestrator.py` | `OrderOrchestrator.run` builds the `Order`, asks its actions for a quote |
| it runs the action through a port | `ordering/application/ports/order_actions.py` | `OrderActions.quote(QuoteRequest) -> QuoteResponse` |
| the Restate SDK calls the action durably | `ordering/adapters/gateways/restate_actions.py` | `RestateOrderActions.quote` → `ctx.generic_call(service, handler, body)` on `restate.extensions.current_context()` |
| Restate's server calls the action handler | `srv/http/main.py` | the same mounted endpoint: `@actions.handler()` → `ActionHandler.quote` |
| the action, an internal application service with a repository lookup | `ordering/application/order_actions.py` | `OrderActions.quote` → `CatalogRepository.price` → `adapters/repositories/memory.py` |
| the price comes back up the same chain | | `QuoteResponse.cents` → `Order.total(PriceSpec)` → `RunResponse.total_cents` ends the workflow |

`POST /orders` answers `202` with the order id as soon as the workflow is
accepted — `generic_send` is fire-and-forget, so the total is read back from
Restate, not from the response.

Restate never touches the domain, and the application never touches
Restate. `OrderOrchestrator` depends on the `OrderActions` port and nothing
else; `OrderActions` (the application service) depends on the
`CatalogRepository` port and nothing else. Both are plain application code.
What makes the orchestrator's call to its actions durable is which
implementation of the port it was handed — a gateway that goes through the
engine.

## What the engine is, in this anatomy

- **Inbound, it is a host.** Restate's server calls the endpoint mounted at
  `/restate`, which routes to handlers like any other host: one `Workflow`
  and one `Service`, each with one named handler. `BytesSerde` on both sides
  keeps the body opaque bytes so the handler owns content.
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
`restate_sdk>=1.0` and the srv test reads the host's `/restate/discover`
manifest, which is where an SDK change would surface.) The gateway's sibling test can
only cover the outside-an-invocation path — the SDK's context class is an
ABC no `@ts.fake` may implement — so the call path is covered by the live
run below.

## The context owns its Restate address

The four names Restate is addressed by are declared once, in the component:
`RestateAddress(workflow, run, actions, quote)` is a client DTO that
`Ordering.__init__` constructs and publishes as `Ordering.address`. Both
readers take it from there — the gateways are handed the two names each one
calls (outbound), and `srv/http/main.py` registers
`restate.Workflow(built.ordering.address.workflow)` and
`@workflow.main(name=built.ordering.address.run, ...)` (inbound). Nothing else
in the tree spells them. `srv/http/test_main.py` boots the real host, reads
`/restate/discover`, and asserts the discovered manifest against the address
the component published.

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
handler names the component addressed it with, and calls `generic_send` on
it. The component builds the real one —
`restate.client.Client(httpx.AsyncClient(base_url=cfg.ingress))`, which is
all `restate.create_client` does under its context manager — and closes it.
Because an httpx client's connections belong to the loop that opened them,
the app's lifecycle is async end to end: `Ordering.close` and `App.close`
are `async`, and the host awaits them in the `finally` of the same loop it
serves on. The sibling test builds the same real client over
`httpx.MockTransport` and checks the URL the SDK forms
(`/Ordering/o1/run/send`), the content-type, and the body.

## Async everywhere the SDK is

The SDK is async on both sides, so the request path is `async`:
`OrderWorkflow`, `OrderService`, `Client.place`, the HTTP handler,
`OrderActions` (the port), `Orchestrator`, `WorkflowHandler`. The action
service and its repository are sync — plain application code that runs
inside the action handler. There is no `asyncio.run` on the request path at
all: the one loop is hypercorn's, opened once by `HttpHost.run`.

## One process of ours, two mechanisms in it

`srv/http/main.py` is the whole `srv/` directory. It builds one FastAPI app
and serves it under one hypercorn:

- an `APIRouter` carrying `POST /orders`, the API this app offers the world;
- `app.mount("/restate", restate.app([workflow, actions]))`, the endpoint
  Restate's server calls back into.

**Restate's own recommendation is that the ingress IS the API** — you register
the deployment and clients `POST :8080/Ordering/o1/run` directly, with no
service of yours in front. A front door of our own exists here for exactly one
reason: to own the public contract. `POST /orders` is a URL, a body shape, and
a status code this app is free to keep stable while the workflow behind it is
renamed, split, or moved off Restate entirely. Nothing else is bought — the
route adds a hop and cannot make the send durable, which is why it answers
`202` and not the total.

**This diverges from `srv.md` rule 6 — one long-running thing per process.**
Two delivery mechanisms are normally two processes. Here they are one, on
purpose: the mounted endpoint is not a second delivery mechanism serving
someone else's traffic, it is the return leg of the workflow this same process
started. Splitting it out would mean two processes, two copies of the graph,
and a deployment URL pointing at the half that has no API. The rule's carve-out
already admits a listener a platform requires; this is the same argument one
step further, and it is a deliberate departure rather than an oversight.

Mounting under a prefix works because the SDK parses the tail: `parse_path`
(`restate/server.py`) reads `$mountpoint/discover` and
`$mountpoint/invoke/:service/:handler` off the end of `scope["path"]`, so it
does not care what is in front. Starlette 1.6 keeps the full path and sets
`root_path` to the mount prefix; an older Starlette strips the prefix instead.
Either way the tail is the same, and `srv/http/test_main.py` asserts it against
a real running host.

## Running it

```
pip install -r requirements-dev.txt
docker run -d --name restate -p 18080:8080 -p 19070:9070 \
  --add-host=host.docker.internal:host-gateway docker.io/restatedev/restate:latest
PYTHONPATH=.:../../tesser-py RESTATE_INGRESS=http://localhost:18080 \
  python -m srv.http.main 0.0.0.0:8000 &            # the API and the Restate endpoint
curl -X POST localhost:19070/deployments --json '{"uri":"http://host.docker.internal:8000/restate"}'
curl -X POST localhost:8000/orders --json '{"order_id":"o1","sku":"gadget","quantity":2}'
                                                    # 202 {"order_id": "o1"}
curl localhost:18080/restate/workflow/Ordering/o1/output
                                                    # {"order_id": "o1", "total_cents": 2000}
```

The failure arms answer at the front door, mapped from the three exception
kinds the handler and the application can raise:

```
curl -X POST localhost:8000/orders --json '{"order_id":"o1"}'
   # 400 {"detail": "sku must be a string"}
curl -X POST localhost:8000/orders --json '{"order_id":"o2","sku":"gadget","quantity":0}'
   # 422 {"detail": "an order is for at least one unit"}          errors.status_for(VALIDATION)
   #     with the ingress down, a well-formed order is 503 {"detail": "unavailable"}
```

A domain error raised *inside* the workflow ends it terminally instead, and is
read back off the ingress — an unknown SKU leaves
`/restate/workflow/Ordering/o4/output` answering `404 {"code":404,"message":"no
price for sku 'nope'"}`.

**SIGTERM belongs to the SDK.** `restate.app` installs its own `SIGTERM`
handler on the first request, replacing hypercorn's: to Restate, SIGTERM
means drain the in-flight invocations, and the deployment is expected to
SIGKILL afterwards. The host stops on SIGINT; the srv test sends SIGINT.

## Production boundaries this example does not cross

- The catalog is an in-memory repository seeded with two SKUs. One process now
  means one copy of it, but it is still in-memory: a second replica would not
  share it, which is fine only because the lookup is read-only.
- `RestateOrderWorkflow.start` fires and forgets; `POST /orders` never waits on
  the workflow. The result is read back through Restate's ingress, so the API
  has no `GET /orders/{id}` of its own.
- The Temporal mirror is the next increment: the same context and ports, a
  `TemporalOrderActions` gateway whose `quote` is `ExecuteActivity`, a
  `TemporalOrderWorkflow` gateway over `ExecuteWorkflow`, and a worker host
  that registers the workflow and the activity.
