# durable-execution — one FastAPI host: the API front door and the mounted Restate endpoint

The chain, top to bottom, with where each link lives:

| Step | Placement | Code |
|---|---|---|
| an HTTP host takes `POST /orders` | `srv/http/main.py` | `HttpHost`'s `APIRouter` → `ordering/adapters/handlers/http.py` `Handler.place` |
| the initial application service | `ordering/application/order_service.py` | `OrderService.place` builds the `Order` aggregate |
| it starts the workflow through the relay | `ordering/application/relays/order_relay.py` | `OrderRelay.start(StartRequest) -> StartResponse`, and `StartRequest` carries the `Order` aggregate itself |
| the Restate SDK sends the workflow | `ordering/adapters/jobs/restate.py` | `RestateOrderRelay.start` → `client.workflow_send(self._run, key=order_id, arg=request)` — the handler function itself, not a name, and the relay's own `StartRequest` as the body |
| Restate's server calls the workflow job | `ordering/adapters/jobs/restate.py` | `RestateWorkflowJobs`'s `@workflow.main()` `run`, mounted at `/restate` by the host |
| the orchestrator is built **inside the invocation** | `ordering/adapters/jobs/restate.py` | `run` builds `RestateOrderRelay(ingress, run, quote, ctx)` over *this* invocation's `ctx` and constructs `OrderOrchestrator(relay)` over it |
| the orchestrator runs the action through the same relay | `ordering/application/relays/order_relay.py` | `OrderOrchestrator.run` (`application/orchestrators/`) reads the `Order` off the message, then `OrderRelay.quote(QuoteRequest) -> QuoteResponse` — no context parameter; the invocation is inside the adapter |
| the Restate SDK calls the action durably | `ordering/adapters/jobs/restate.py` | `RestateOrderRelay.quote(request)` → `self._ctx.service_call(self._quote, request)` |
| Restate's server calls the action job | `ordering/adapters/jobs/restate.py` | `RestateActionJobs`: `@service.handler()` `quote`, relaying to the application client |
| the action, a class of actions with one repository lookup | `ordering/application/order_actions.py` | `OrderActions.quote` → `CatalogRepository.price` → `adapters/repositories/memory.py`, behind `application/client/order_actions.py` |
| the price comes back up the same chain | | `QuoteResponse.cents` → `Order.total(PriceSpec)` → `RunResponse.total_cents` ends the workflow |

`POST /orders` answers `202` with the order id as soon as the workflow is
accepted — `workflow_send` is fire-and-forget, so the total is read back from
Restate, not from the response.

The application never touches Restate. `OrderOrchestrator` depends on
`OrderRelay` and nothing else; `OrderActions` (the class of actions) depends
on the `CatalogRepository` port and nothing else. Both are plain application
code. What makes the orchestrator's call to its actions durable is which
implementation of the relay it was handed.

Restate *does* carry the domain, on the workflow leg only. `StartRequest` is
a **relay** message — a message whose far side is this same context's own
application code — so it holds the `Order` aggregate, and `OrderSnapshot`
writes it to the wire and rebuilds it on the other side through the
aggregate's own constructor.

## The relay — `OrderRelay`, one protocol, specific methods

A **`ts.Relay`** (`application/relays/`) is a port whose far side is this
context's own application code, reached through an engine instead of by a
synchronous call. There is exactly one here, `OrderRelay`, and it declares
the two things this context asks the engine to do, by name:

```python
class OrderRelay(ts.Relay, typing.Protocol):

    async def start(self, request: StartRequest) -> StartResponse: ...

    async def quote(self, request: QuoteRequest) -> QuoteResponse: ...
```

`CatalogRepository` (Postgres, or the in-memory stand-in) stays a `ts.Port`,
because a store is not us.

The distinction is what may cross. A `ts.Client` faces outsiders and a
`ts.Port` faces a foreign system, so both stay primitives-only. A relay has
us on both ends, and Restate pins an invocation to one deployment, so a relay
message may carry domain objects and they come back whole. Only the engine's
own adapter package — `adapters/jobs/` — may import a relays module.

**There is no job context any more.** The earlier shape threaded a generic
`ts.JobContext` with one generic `call[I, O](step, request)` from the job
through the orchestrator to the gateway, so that the orchestrator could hand
the invocation back to the adapter that needed it. `OrderRelay.quote` says
what the call *is*, so the invocation never has to travel through the
application at all: it stays inside `RestateOrderRelay`, which the workflow
job builds per invocation over that invocation's `ctx`. `ts.JobContext` still
exists in tesser-py; this example no longer uses it.

**One relay class, two instances, because the two legs have different
lifetimes.** `quote` needs the per-invocation `restate.Context`; `start`
needs the ingress URL and outlives any invocation. `RestateOrderRelay` takes
both plus the two handler functions, and `ctx` is `None` on the instance the
component builds once for `OrderService`. Two classes were the alternative
and were worse: each would still have to declare both protocol methods, so
each would still have a method that cannot run — the `None` at least says
which leg an instance is for, at the one place that builds it.

A job hands a relay message on whole and reads nothing off it: both
`RestateActionJobs.quote` and `RestateWorkflowJobs.run` pass `request` straight
through. Stronger, and greppable: **no field name of any message or domain
object appears anywhere in `adapters/jobs/restate.py`** — not `sku`, not
`cents`, not `quantity`, not `order_id`, not `total_cents`. Every encoding is a
snapshot in `order_relay.py`, and the module's one remaining read is
`str(request.order.identity)` in `RestateOrderRelay.start`, for the workflow key
Restate's ingress requires.

## The three application kinds, and where each lives

This tree is the worked example for `docs/design-app-service-types.md`:

- `OrderService(ts.ApplicationService)` — the public use case, on
  `client.Client`, built once by the component. It does the once-only work
  (validates at the door) and starts the workflow through `OrderRelay.start`.
- `OrderOrchestrator(ts.Orchestrator)` in `application/orchestrators/` —
  not a service. Built per invocation by the job with that invocation's
  `OrderRelay`; stores nothing but it; takes the relay's own `StartRequest`
  — reading the `Order` straight off it — and returns the relay's `RunResponse`.
  It has no job context and no generic call.
- `OrderActions(ts.Actions)` beside the services — a class of actions over
  exactly one port (`CatalogRepository`), each method making exactly one call
  on it. Not on the public client: it is reachable only through
  `application/client/order_actions.py`, a `tesser.application.Client`
  protocol that only a job may import.

And the adapter kind that ties them to the engine, all in one module,
`adapters/jobs/restate.py`: `RestateActionJobs(ts.Job)` declaring the
`OrderingActions` service over the application client,
`RestateWorkflowJobs(ts.Job)` declaring the `Ordering` workflow and building
`RestateOrderRelay` per invocation, and four compatibility shims that know
nothing but `None` and which relay snapshot to call. A handler calls the context
client; a job calls an application client or constructs an orchestrator.

## What the engine is, in this anatomy

- **Inbound, it is a host.** Restate's server calls the endpoint mounted at
  `/restate`, which routes to the two jobs: one `Workflow` and one
  `Service`, each with one typed handler taking and returning the relay's own
  request and response — no wire types.
- **Outbound, it is one gateway over the relay.** `RestateOrderRelay`
  implements both legs — `start` through the ingress, `quote` through the
  invocation — and lives in `adapters/jobs/`, the one adapter package
  allowed to import a relays module.

**Everything Restate is addressed by a function, not a name.** The gateways
take the handler *function* and hand it to the SDK — `client.workflow_send(self._run, ...)`
and `ctx.service_call(self._quote, ...)` — and the SDK reads the service name,
the handler name, and both serdes off the decorated object
(`handler_from_callable`). A rename is a rename; there is no string to keep in
step, and no address DTO any more. `"Ordering"` and `"OrderingActions"` appear
exactly once each, in the `restate.Workflow(...)` / `restate.Service(...)`
constructor calls, one in each job's `__init__`.

**The invocation's context never leaves the adapter.** A Restate handler is
handed a `WorkflowContext`, and only calls made through it are journaled.
`run` builds `RestateOrderRelay(ingress, run, quote, ctx)` over *this* ctx
and constructs `OrderOrchestrator(relay)` over that, per invocation. The
orchestrator calls `self._relay.quote(request)` and never sees the context at
all. (The SDK does keep the invocation in a `ContextVar`,
`restate.extensions.current_context()`, but its module docstring says
"internal extensions apis" and no documented handler code reads it; a
convention example does not build on an internal name.) The cost is that the
relay's gateway is built per invocation and holds the ctx — the shape the
earlier `ts.JobContext` design existed to avoid; on Temporal the same
`OrderRelay` is implemented over `workflow.execute_activity`, and the
orchestrator is unchanged either way.

## The context declares its Restate service, the host only mounts it

`RestateActionJobs` and `RestateWorkflowJobs` are the Restate service
modules the Restate docs would have you write, except they are classes so
their dependencies arrive by constructor instead of by module global. They
are two classes rather than one because the workflow job needs the action
handler *function* before it can build a relay: the component builds
`RestateActionJobs(actions)`, then
`RestateWorkflowJobs(cfg.ingress, action_jobs.quote)` — Restate's own Service
/ Workflow split, in dependency order — and finally
`RestateOrderRelay(cfg.ingress, workflow_jobs.run, action_jobs.quote, None)`
for `OrderService`. The component publishes both jobs as `jobs` — the only thing
a component publishes besides `client`; the host does
`api.mount("/restate", restate.app([d for job in app.ordering.jobs for d in job.definitions()]))`
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

The serde kind itself costs nothing at the engine. The 2026-08-30 ruling named
it: `tesser.adapters.Serde`, admitted in `adapters/jobs/`, declaring exactly
`serialize` and `deserialize`, holding at most the target type, and branching
on nothing but the empty payload — and it is the one adapter class allowed a
base from outside the tree, because the engine is the caller. The four Restate
shims read `class RestateXSerde(ts.Serde, restate.serde.Serde[X])`.

What does cost is that **`OrderSnapshot` is not at the engine.** It belongs to
the relay, so it lives in `application/relays/order_relay.py`, and an
application module can neither name `ts.Serde` (it is an adapters kind) nor
import `json` (the application stdlib allowlist is `{__future__, typing}`).

**The relay does cost, and this tree is currently red because of it.** The
analyzer has no notion of a relay yet, so `application/relays/`, `ts.Relay`, a
domain import inside a relays module, a domain object on a `ts.Request` field,
a serde in an application module, and a gateway living in `adapters/jobs/` all
draw findings. They are recorded rather than suppressed: this branch is a spike
for the relay rules, not a shape the current rulebook admits.

## Messages are declared once, on the relay

There are no wire types. Both ends of a relay are us, so the send side and the
receive side of one message are not independent boundaries: `RunRequest` *is*
`order_relay.StartRequest`, and the action's `QuoteRequest` / `QuoteResponse`
are the relay's own. The gateway sends the relay's DTO, the job receives it,
and `application/client/order_actions.py` speaks the same two shapes to the
job. The workflow's result, `RunResponse`, is a relay message too — the engine
stores it and the ingress hands it back — so it lives there with the rest. All
five exist exactly once, in `application/relays/order_relay.py`.

**Every wire form is an explicit snapshot beside its message, and they all
belong to the relay.** `order_relay.py` carries five: `OrderSnapshot` for the
aggregate, and `StartRequestSnapshot`, `QuoteRequestSnapshot`,
`QuoteResponseSnapshot`, `RunResponseSnapshot` for the messages that cross.
Each is a `ts.Serde` with exactly `serialize` and `deserialize`, written out
longhand rather than derived:

```python
class OrderSnapshot(ts.Serde):

    def serialize(self, running: domain.Order) -> bytes:
        return json.dumps(
            {
                "order_id": str(running.identity),
                "sku": str(running.sku),
                "quantity": int(running.quantity),
            }
        ).encode()

    def deserialize(self, buf: bytes) -> domain.Order:
        snapshot = json.loads(buf)
        return domain.Order(
            domain.OrderSpec(
                order_id=snapshot["order_id"],
                sku=snapshot["sku"],
                quantity=snapshot["quantity"],
            )
        )
```

So the wire carries the aggregate's **public** vocabulary — `order_id`, `sku`,
`quantity`, each through its canonical exit (`str`/`int`) — and never a private
attribute name. Reconstruction goes through `OrderSpec` and the aggregate's own
constructor, the serialization norm's one inbound path, so every invariant
re-runs on the way in and a journal holding an order of zero units is refused on
replay rather than hydrated. Renaming `_sku` is now an ordinary rename.

`StartRequestSnapshot` is the whole of what a workflow start puts on the wire —
the order it carries, and nothing wrapped around it:

```python
class StartRequestSnapshot(ts.Serde):

    def serialize(self, request: StartRequest) -> bytes:
        return OrderSnapshot().serialize(request.order)

    def deserialize(self, buf: bytes) -> StartRequest:
        return StartRequest(order=OrderSnapshot().deserialize(buf))
```

so the body `POST /Ordering/o1/run/send` carries is:

```json
{"order_id": "o1", "sku": "widget", "quantity": 2}
```

**No field name of any message or domain object appears in
`adapters/jobs/restate.py`.** The SDK cannot serialize a `ts.Request` on its own
— `restate.serde.DefaultSerde` handles msgspec Structs, Pydantic models, and
dataclasses; anything else falls through to `json.dumps(obj)` — so that module
carries four compatibility shims, one per message the SDK moves. A shim does two
things and no more: answer the SDK's `None`/empty convention, and delegate to
the relay's snapshot.

```python
class RestateStartRequestSerde(ts.Serde, restate.serde.Serde[order_relay.StartRequest]):

    def serialize(self, obj: order_relay.StartRequest | None) -> bytes:
        if obj is None:
            return b""
        return order_relay.StartRequestSnapshot().serialize(obj)

    def deserialize(self, buf: bytes) -> order_relay.StartRequest | None:
        if not buf:
            return None
        return order_relay.StartRequestSnapshot().deserialize(buf)
```

They are bound at the decorators in the jobs:

```python
@self.workflow.main(
    input_serde=RestateStartRequestSerde(),
    output_serde=RestateRunResponseSerde(),
)
```

None of them is generic and none of them knows a field. What crosses is decided
in one module — the relay's — and the engine adapter only carries it. A field
added to a message still changes the bytes an in-flight journal already holds;
payload versioning on a durable leg is a rule this tree does not yet make.

The one thing `restate.py` still reads off a message is the **workflow key**:
`RestateOrderRelay.start` does `str(request.order.identity)`, because Restate's
ingress addresses a workflow by key and the aggregate's identity is the key. That
is the aggregate's public identity, not an internal, but it is still the engine
module reaching into a message.

Binding it on the handler is enough for both directions: the ingress client
reads `handler_from_callable(tpe).handler_io` for its serde and its
content-type, so the gateway sets no headers of its own. Nothing hand-parses a
body any more — no `BytesSerde`, no `text()`/`integer()` accessors — and a
malformed body never reaches a handler.

Discovery reports `contentType: "application/json"` for both handlers. It does
**not** carry a real JSON schema; the SDK generates one only for msgspec and
Pydantic types.

## Errors across the engine

A `DomainError` in a job becomes a `restate.TerminalError` with the kind's
status — no retry. When the action job raises it, the workflow's gateway
receives it as a `TerminalError` from `service_call` and raises it again as a
`DomainError`, so the orchestrator and the workflow job see a domain error,
not an SDK one, and the workflow ends terminally with the action's message.
Anything else propagates as-is and Restate retries the invocation.

## The gateway holds the SDK's client, and nothing sits between

`RestateOrderRelay` takes the ingress URL and the `run` handler function
itself, and `start` opens its own client per send:
`async with httpx.AsyncClient(base_url=self._ingress)` around
`restate.client.Client(http).workflow_send(...)`, which is all
`restate.create_client` does under its context manager. **Nothing async
outlives a request**, so nothing has to be closed on the loop that opened it —
`Ordering.close` and `App.close` are plain sync methods, and every caller is
`app = loader.load()` … `finally: app.close()`, with no `asyncio.run` in
sight. The cost is honest and stated: no connection pooling across sends.
The sibling test builds the same real client over a real socket listening on
`127.0.0.1:0`, hands the relay the real `run` handler off a real
`RestateWorkflowJobs`, and checks the request line the SDK forms from it
(`POST /Ordering/o1/run/send`). It asserts the route and the key, not the body
— every payload is pinned once, in `relays/test_order_relay.py`, where the
snapshots are defined; the Restate tests assert routing, delegation, and the
SDK's `None`/empty convention, and never a literal body. A transport cannot be
injected through a base URL any
more, and inventing a constructor parameter only tests would pass is worse than
talking to a real socket — so the test talks to a real socket, and the
unreachable case just points at a closed port.

`RestateOrderRelay.quote` is the one thing whose real call path the suite
cannot reach: it needs a live `restate.Context`, the SDK's context class is an
ABC that no `@ts.fake` may implement (a fake must implement a port, a client,
or a config repository), and the SDK's own `create_test_harness` wants Docker
and `testcontainers`. Its sibling test covers the no-invocation arm; the
journaled call and the `TerminalError` → `DomainError` mapping are covered by
the live run below.

## Async everywhere the SDK is

The SDK is async on both sides, so the request path is `async`:
`OrderRelay`, `OrderService`, `Client.place`, the HTTP handler,
`OrderOrchestrator`, and both Restate jobs. The
class of actions and its repository are sync — plain application code that
runs inside the action job. There is no `asyncio.run` on the request path at
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
- `RestateOrderRelay.start` fires and forgets; `POST /orders` never waits on
  the workflow. The result is read back through Restate's ingress, so the API
  has no `GET /orders/{id}` of its own.
- The Temporal mirror is the next increment: the same context, the same
  `OrderRelay`, and a `TemporalOrderRelay` whose `start` is `ExecuteWorkflow`
  and whose `quote` is `ExecuteActivity`, plus a worker host that registers the
  workflow and the activity.
