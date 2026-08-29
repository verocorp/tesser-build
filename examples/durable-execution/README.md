# durable-execution — one FastAPI host: the API front door and the mounted Restate endpoint

The chain, top to bottom, with where each link lives:

| Step | Placement | Code |
|---|---|---|
| an HTTP host takes `POST /orders` | `srv/http/main.py` | `HttpHost`'s `APIRouter` → `ordering/adapters/handlers/http.py` `Handler.place` |
| the initial application service | `ordering/application/order_service.py` | `OrderService.place` builds the `Order` aggregate |
| it starts the workflow through a port | `ordering/application/ports/order_workflow.py` | `OrderWorkflow.start(StartRequest) -> StartResponse` |
| the Restate SDK sends the workflow | `ordering/adapters/gateways/restate_workflow.py` | `RestateOrderWorkflow.start` → `client.workflow_send(self._run, key=order_id, arg=RunRequest(...))` — the handler function itself, not a name |
| Restate's server calls the workflow handler | `ordering/adapters/handlers/restate.py` | `RestateHandlers`'s `@workflow.main()` `run`, mounted at `/restate` by the host |
| the orchestrator is built **inside the invocation** | `ordering/adapters/handlers/restate.py` | `run` constructs `RestateOrderActions(ctx, quote)` and `OrderOrchestrator(...)` per invocation, over this `ctx` |
| the orchestrator runs the action through a port | `ordering/application/ports/order_actions.py` | `OrderOrchestrator.run` builds the `Order`, then `OrderActions.quote(QuoteRequest) -> QuoteResponse` |
| the Restate SDK calls the action durably | `ordering/adapters/gateways/restate_actions.py` | `RestateOrderActions.quote` → `ctx.service_call(self._quote, QuoteRequest(sku))` on the ctx it was built with |
| Restate's server calls the action handler | `ordering/adapters/handlers/restate.py` | the same `RestateHandlers`: `@service.handler()` `quote` |
| the action, an internal application service with a repository lookup | `ordering/application/order_actions.py` | `OrderActions.quote` → `CatalogRepository.price` → `adapters/repositories/memory.py` |
| the price comes back up the same chain | | `QuoteResponse.cents` → `Order.total(PriceSpec)` → `RunResponse.total_cents` ends the workflow |

`POST /orders` answers `202` with the order id as soon as the workflow is
accepted — `workflow_send` is fire-and-forget, so the total is read back from
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
  `/restate`, which routes to `RestateHandlers`: one `Workflow` and one
  `Service`, each with one typed handler taking and returning a frozen
  dataclass the SDK serializes.
- **Outbound, it is a gateway over a port.** Starting the workflow is
  `RestateOrderWorkflow` over `OrderWorkflow`; running an action is
  `RestateOrderActions` over `OrderActions`.

**Everything Restate is addressed by a function, not a name.** The gateways
take the handler *function* and hand it to the SDK — `client.workflow_send(self._run, ...)`
and `ctx.service_call(self._quote, ...)` — and the SDK reads the service name,
the handler name, and both serdes off the decorated object
(`handler_from_callable`). A rename is a rename; there is no string to keep in
step, and no address DTO any more. `"Ordering"` and `"OrderingActions"` appear
exactly once each, in the `restate.Workflow(...)` / `restate.Service(...)`
constructor calls inside `RestateHandlers.__init__`.

**The orchestrator is built inside the invocation.** A Restate handler is
handed a `WorkflowContext`, and only calls made through it are journaled. So
`run` constructs its own `RestateOrderActions(ctx, quote)` over *this* ctx and
its own `OrderOrchestrator` over that gateway, per invocation. Neither is a
component attribute: the component wires what outlives a request, and an
invocation-scoped object does not. Nothing reads an ambient context, and
nothing binds or stores one.

## The context declares its Restate service, the host only mounts it

`RestateHandlers` is the Restate service module the Restate docs would have you
write, except it is a class so its dependencies arrive by constructor instead
of by module global. It builds the `Workflow` and the `Service`, decorates the
two handlers as closures over the injected `client.Actions`, and hands the
whole thing back through `definitions()`. The component builds it once; the
host does `api.mount("/restate", restate.app(built.ordering.handlers.definitions()))`
and knows nothing else about Restate.

`srv/http/test_main.py` boots the real host, reads `/restate/discover`, and
asserts the discovered manifest against what `definitions()` declares — so the
manifest and the code cannot drift apart silently.

**This still diverges from `srv.md` rule 5 — the route table is the host's.**
The Restate names are declared in a context adapter, not at the app edge. The
reason is the same as before: here the context is its own caller, and the names
are an agreement between this context's gateway and this context's handler. On
the typed path they are barely an agreement at all — the gateway holds the
function, so the only reader of the string is the SDK.

### What this shape costs, in rules

Four tessercheck findings stand, deliberately, awaiting a ruling:

- `ordering/adapters/handlers/restate.py` imports
  `ordering.application.order_orchestrator` (**TB060**). An adapter may reach
  `application.ports`, not an application service. But the orchestrator is
  invocation-scoped, and the invocation only exists inside the handler, so the
  handler is the only place that can construct it.
- both gateways — and their sibling tests — import `protocol.durable`
  (**TB066**, **TB070**). Only a handler may reach the app shell's `protocol`
  package. But on the typed path the gateway and the handler must speak the
  *same* Python types, and those types are the wire shapes.

And the wire shapes themselves are plain `@dataclasses.dataclass(frozen=True)`
records with no `ts.*` base (**TB050**, **TB052** ×4), because that is what the
SDK can serialize. See below.

## What the SDK needs from the wire types

The typed path serializes the handler's declared argument and return types, so
`protocol/durable.py` holds four frozen dataclasses and nothing else — no
`BytesSerde`, no `json.dumps`, no hand-written `text()`/`integer()` accessors,
no `BadInvocation`. The SDK parses the body, and a malformed one never reaches
the handler.

Two SDK facts this cost real time to find, both worth knowing before the
Temporal mirror:

- **Dataclass support is an optional extra.** `DefaultSerde` routes dataclasses
  through `dacite`, which ships only with `restate_sdk[serde]`. Without it the
  call raises `RuntimeError: Trying to deserialize into a @dataclass. Please
  add the optional dependencies needed.` The requirement is pinned as
  `restate_sdk[serde]>=1.0`.
- **A handler's `DefaultSerde` is never told its type.**
  `update_handler_io_with_input_type_hints` (`restate/handler.py`) swaps in a
  dedicated serde for msgspec Structs and Pydantic models, but for a dataclass
  it records the type hint and leaves `DefaultSerde()` with `type_hint = None`
  — which falls through to `json.dumps(obj)` and raises `TypeError: Object of
  type RunRequest is not JSON serializable`. The fix is to bind the serde
  explicitly at the decorator:
  `@self.service.handler(input_serde=restate.serde.DefaultSerde(durable.QuoteRequest), ...)`.
  The client side needs no separate fix — `do_call` reads
  `handler_from_callable(tpe).handler_io`, so binding it once on the handler
  serves both directions, and that is also why the gateway sets no
  content-type header any more.

Discovery reports `contentType: "application/json"` for both handlers, up from
`*/*` under `BytesSerde`. It does **not** carry a real JSON schema: the
manifest's `jsonSchema: true` reads the same as it did before, and the SDK
generates an actual schema only for msgspec and Pydantic types.

## Errors across the engine

A `DomainError` in a handler becomes a `restate.TerminalError` with the kind's
status — no retry. When the action handler raises it, the workflow's gateway
receives it as a `TerminalError` from `service_call` and raises it again as a
`DomainError`, so the orchestrator and the workflow handler see a domain error,
not an SDK one, and the workflow ends terminally with the action's message.
Anything else propagates as-is and Restate retries the invocation.

## The gateway holds the SDK's client, and nothing sits between

`RestateOrderWorkflow` takes the ingress URL and the `run` handler function
itself, and opens its own client per send:
`async with httpx.AsyncClient(base_url=self._ingress)` around
`restate.client.Client(http).workflow_send(...)`, which is all
`restate.create_client` does under its context manager. **Nothing async
outlives a request**, so nothing has to be closed on the loop that opened it —
`Ordering.close` and `App.close` are plain sync methods, and every caller is
`app = loader.load()` … `finally: app.close()`, with no `asyncio.run` in
sight. The cost is honest and stated: no connection pooling across sends.
The sibling test builds the same real client over
a real socket listening on `127.0.0.1:0`, hands the gateway a real handler
function decorated on a throwaway `restate.Workflow`, and checks the request
line the SDK forms from it (`POST /Ordering/o1/run/send`) and the JSON body.
A transport cannot be injected through a base URL any more, and inventing a
constructor parameter only tests would pass is worse than talking to a real
socket — so the test talks to a real socket, and the unreachable case just
points at a closed port.

`RestateOrderActions` is the one thing whose real call path the suite cannot
reach: it needs a live `restate.Context`, the SDK's context class is an ABC
that no `@ts.fake` may implement (a fake must implement a port, a client, or a
config repository), and the SDK's own `create_test_harness` wants Docker and
`testcontainers`. Its sibling test covers both branches — the answer path and
the `TerminalError` → `DomainError` mapping — over a stand-in defined inside
each test, and the real journaled call is covered by the live run below.

## Async everywhere the SDK is

The SDK is async on both sides, so the request path is `async`:
`OrderWorkflow`, `OrderService`, `Client.place`, the HTTP handler,
`OrderActions` (the port), `OrderOrchestrator`, and both Restate handlers. The
action service and its repository are sync — plain application code that runs
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
