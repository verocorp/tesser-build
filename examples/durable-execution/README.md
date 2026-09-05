# durable-execution — one FastAPI host: the API front door and the mounted Restate endpoint

The chain, top to bottom, with where each link lives:

| Step | Placement | Code |
|---|---|---|
| an HTTP host takes `POST /orders` | `srv/http/main.py` | `HttpHost`'s `APIRouter` → `ordering/adapters/handlers/http.py` `Handler.place` |
| the initial application service | `ordering/application/order_service.py` | `OrderService.place` builds the `Order` aggregate |
| it starts the workflow through a port | `ordering/application/ports/order_workflow.py` | `OrderWorkflow.start(StartRequest) -> StartResponse` |
| the Restate SDK sends the workflow | `ordering/adapters/gateways/restate_workflow.py` | `RestateOrderWorkflow.start` → `client.workflow_send(self._run, key=order_id, arg=request)` — the handler function itself, not a name, and the port's own `StartRequest` as the body |
| Restate's server calls the workflow job | `ordering/adapters/jobs/restate.py` | `RestateWorkflowJobs`'s `@workflow.main()` `run`, mounted at `/restate` by the host |
| the orchestrator is built **inside the invocation** | `ordering/adapters/jobs/restate.py` | `run` wraps this invocation's `ctx` as `RestateJobContext(ctx)` (`jobs/restate_context.py`) and constructs `OrderOrchestrator(job, quotes)` over it |
| the orchestrator runs the action through a port | `ordering/application/ports/quoting.py` | `OrderOrchestrator.run` (`application/orchestrators/`) builds the `Order`, then `Quoting.quote(job, QuoteRequest) -> QuoteResponse` — the job context threaded as the leading argument |
| the Restate SDK calls the action durably | `ordering/adapters/gateways/restate_quoting.py` | `RestateQuoting.quote(job, request)` → `job.call(self._quote, request)` → `ctx.service_call`; the gateway was built once by the component and holds only the handler function |
| Restate's server calls the action job | `ordering/adapters/jobs/restate.py` | `RestateActionJobs`: `@service.handler()` `quote`, relaying to the application client |
| the action, a class of actions with one repository lookup | `ordering/application/order_actions.py` | `OrderActions.quote` → `CatalogRepository.price` → `adapters/repositories/memory.py`, behind `application/client/order_actions.py` |
| the price comes back up the same chain | | `QuoteResponse.cents` → `Order.total(PriceSpec)` → `RunResponse.total_cents` ends the workflow |

`POST /orders` answers `202` with the order id as soon as the workflow is
accepted — `workflow_send` is fire-and-forget, so the total is read back from
Restate, not from the response.

Restate never touches the domain, and the application never touches
Restate. `OrderOrchestrator` depends on the `Quoting` port and nothing
else; `OrderActions` (the class of actions) depends on the
`CatalogRepository` port and nothing else. Both are plain application code.
What makes the orchestrator's call to its actions durable is which
implementation of the port it was handed — a gateway that goes through the
engine.

## The three application kinds, and where each lives

This tree is the worked example for `docs/design-app-service-types.md`:

- `OrderService(ts.ApplicationService)` — the public use case, on
  `client.Client`, built once by the component. It does the once-only work
  (validates at the door) and starts the workflow through the
  `OrderWorkflow` port.
- `OrderOrchestrator(ts.Orchestrator)` in `application/orchestrators/` —
  not a service. Built per invocation by the job with that invocation's
  **job context** (`ts.JobContext`, the engine-neutral protocol for what a
  step may do inside an invocation) and its action ports (`Quoting`: a port
  an application client speaks); stores nothing but those; threads the job
  context as the leading argument of every action-port call; takes the
  workflow port's own `StartRequest` and returns its own `RunResponse`.
- `OrderActions(ts.Actions)` beside the services — a class of actions over
  exactly one port (`CatalogRepository`), each method making exactly one call
  on it. Not on the public client: it is reachable only through
  `application/client/order_actions.py`, a `tesser.application.Client`
  protocol that only a job may import.

And the adapter kind that ties them to the engine: the two jobs in
`adapters/jobs/restate.py` — `RestateActionJobs(ts.Job)` declaring the
`OrderingActions` service over the application client, and
`RestateWorkflowJobs(ts.Job)` declaring the `Ordering` workflow over the
`Quoting` port — plus `RestateJobContext(ts.JobContext)` in
`jobs/restate_context.py`, the one per-invocation object the workflow job
builds. A handler calls the context client; a job calls an application
client or constructs an orchestrator. Every gateway is built once by the
component; none holds an invocation's context.

## What the engine is, in this anatomy

- **Inbound, it is a host.** Restate's server calls the endpoint mounted at
  `/restate`, which routes to the two jobs: one `Workflow` and one
  `Service`, each with one typed handler taking and returning the port's own
  request and response — no wire types.
- **Outbound, it is a gateway over a port.** Starting the workflow is
  `RestateOrderWorkflow` over `OrderWorkflow`; running an action is
  `RestateQuoting` over `Quoting`.

**Everything Restate is addressed by a function, not a name.** The gateways
take the handler *function* and hand it to the SDK — `client.workflow_send(self._run, ...)`
and `ctx.service_call(self._quote, ...)` — and the SDK reads the service name,
the handler name, and both serdes off the decorated object
(`handler_from_callable`). A rename is a rename; there is no string to keep in
step, and no address DTO any more. `"Ordering"` and `"OrderingActions"` appear
exactly once each, in the `restate.Workflow(...)` / `restate.Service(...)`
constructor calls, one in each job's `__init__`.

**The invocation's context enters the application as a job context.** A
Restate handler is handed a `WorkflowContext`, and only calls made through it
are journaled. `run` wraps *this* ctx as `RestateJobContext(ctx)` — the
Restate implementation of `ts.JobContext`, whose one method today is
`call(step, request)` → `ctx.service_call(step, request)` — and constructs
its own `OrderOrchestrator(job, quotes)` over it, per invocation. The
orchestrator threads the job context as the leading argument of every
action-port call, and the gateway on the other side of that call
(`RestateQuoting`, built once by the component, holding only the `quote`
handler function) does `job.call(self._quote, request)`. So the ctx travels
by parameter, the way Restate's own examples thread it and the way Go
threads `ctx` — never stored by a gateway, never read from an ambient
variable. (The SDK does keep the invocation in a `ContextVar`,
`restate.extensions.current_context()`, but its module docstring says
"internal extensions apis" and no documented handler code reads it; a
convention example does not build on an internal name.) On Temporal the same
`JobContext` is implemented over `workflow.execute_activity`, and the
orchestrator is unchanged.

## The context declares its Restate service, the host only mounts it

`RestateActionJobs` and `RestateWorkflowJobs` are the Restate service
modules the Restate docs would have you write, except they are classes so
their dependencies arrive by constructor instead of by module global. They
are two classes rather than one because the workflow's gateway needs the
action handler *function* before the workflow job can exist: the component
builds `RestateActionJobs(actions)`, then `RestateQuoting(action_jobs.quote)`,
then `RestateWorkflowJobs(quoting)` — Restate's own Service / Workflow split,
in dependency order. The component publishes both as `jobs` — the only thing
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

Nothing, since the serde kind landed. `RecordSerde` in
`ordering/adapters/jobs/restate.py` used to carry a `tesser:debt TB052`,
because every context class declares a `ts.*` base and the engine's serde is
an ABC that cannot be duck-typed away. The 2026-08-30 ruling named the kind:
`tesser.adapters.Serde`, admitted in `adapters/jobs/`, declaring exactly
`serialize` and `deserialize` over one type parameter, holding at most the
target type, and branching on nothing but the empty payload — and it is the
one adapter class allowed a base from outside the tree, because the engine is
the caller. So the class reads
`class RecordSerde[T](ts.Serde, restate.serde.Serde[T])`, and this tree now
runs the analyzer with no markers at all.

## Messages are declared once, on the port

There are no wire types. The engine is a relay, so the send side and the
receive side of one message are not independent boundaries: `RunRequest`
*is* `order_workflow.StartRequest`, and the action's `QuoteRequest` /
`QuoteResponse` are the `Quoting` port's own. The gateway sends the
port's DTO, the job receives it, and `application/client/order_actions.py`
speaks the same two shapes to the job. Each message exists exactly once, as a
`ts.Request` / `ts.Response` in a ports module; the one exception is the
workflow's result, `RunResponse`, which no port speaks and which the
orchestrators module therefore declares itself.

The SDK cannot serialize a `ts.Request` on its own —
`restate.serde.DefaultSerde` handles msgspec Structs, Pydantic models, and
dataclasses; anything else falls through to `json.dumps(obj)` — so the tree
brings its own serde. `RecordSerde[T](restate.serde.Serde[T])` is twelve
lines over `vars(obj)` and `self._kind(**json.loads(buf))`, bound at each
decorator in the job, where it lives:

```python
@self.workflow.main(
    input_serde=restate_workflow.RecordSerde(order_workflow.StartRequest),
    output_serde=restate_workflow.RecordSerde(order_orchestrator.RunResponse),
)
```

It is flat: port DTO fields are primitives here. A nested DTO, a tuple, or an
enum field would need type-directed decoding this serde does not do, and a
field added to a port DTO changes the bytes an in-flight journal already
holds — payload versioning on a durable leg is a rule this tree does not yet
make, so its port DTOs are append-only.

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

`RestateQuoting` is the one thing whose real call path the suite cannot
reach: it needs a live `restate.Context`, the SDK's context class is an ABC
that no `@ts.fake` may implement (a fake must implement a port, a client, or a
config repository), and the SDK's own `create_test_harness` wants Docker and
`testcontainers`. Its sibling test covers both branches — the answer path and
the `TerminalError` → `DomainError` mapping — over a stand-in defined inside
each test, and the real journaled call is covered by the live run below.

## Async everywhere the SDK is

The SDK is async on both sides, so the request path is `async`:
`OrderWorkflow`, `OrderService`, `Client.place`, the HTTP handler,
`OrderActions` (the port), `OrderOrchestrator`, and both Restate jobs. The
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
curl -X POST localhost:8000/orders --json '{"order_id":"o1","sku":"gadget","quantity":2,"note":"gift"}'
                                                    # 202 {"order_id": "o1"}
curl localhost:18080/restate/workflow/Ordering/o1/output
                                                    # {"order_id": "o1", "total_cents": 2000}
```

The failure arms answer at the front door, mapped from the three exception
kinds the handler and the application can raise:

```
curl -X POST localhost:8000/orders --json '{"order_id":"o1"}'
   # 400 {"detail": "sku must be a string"}
curl -X POST localhost:8000/orders --json '{"order_id":"o2","sku":"gadget","quantity":0,"note":"gift"}'
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
