# durable-execution — one FastAPI host: the API front door and the mounted Restate endpoint

The chain, top to bottom, with where each link lives:

| Step | Placement | Code |
|---|---|---|
| an HTTP host takes `POST /submissions` | `srv/http/main.py` | `HttpHost`'s `APIRouter` → `ordering/adapters/handlers/http.py` `Handler.submit_order` |
| the initial application service | `ordering/application/order_service.py` | `OrderService.submit_order` builds the `Order` aggregate |
| it starts the orchestrator through a runner | `ordering/application/relays/order_orchestrator_runner.py` | `OrderOrchestratorRunner.start_order_orchestrator(OrderOrchestratorRequest) -> StartOrderOrchestratorResponse`; the request carries the `Order` aggregate itself |
| the Restate runner sends the workflow | `ordering/adapters/runners/restate_order_orchestrator_runner.py` | `RestateOrderOrchestratorRunner.start_order_orchestrator` → `workflow_send(runtime.order_orchestrator_handler, key=order_id, arg=request)` |
| Restate's server calls back into the runtime | `ordering/adapters/runtimes/restate_order_runtime.py` | `RestateOrderRuntime`'s `@order_orchestrator_workflow.main()` handler `run`, registered as `OrderOrchestrator/run`, mounted at `/restate` by the host |
| the orchestrator is built **inside the invocation** | `ordering/adapters/runtimes/restate_order_runtime.py` | `run` builds `RestateOrderActionsRunner(restate_workflow_context, self)` over *this* invocation's context and constructs `OrderOrchestrator` over it |
| the orchestrator runs the action through its runner | `ordering/application/relays/order_actions_runner.py` | `OrderOrchestrator.run` reads the `Order` off the message, then `OrderActionsRunner.run_price_product(PriceProductRequest) -> PriceProductResponse` |
| the Restate runner calls the action durably | `ordering/adapters/runners/restate_order_actions_runner.py` | `RestateOrderActionsRunner.run_price_product` → `restate_workflow_context.service_call(runtime.price_product_handler, request)` |
| Restate's server calls back into the runtime | `ordering/adapters/runtimes/restate_order_runtime.py` | `RestateOrderRuntime`'s `@order_actions_service.handler()` handler `price_product`, registered as `OrderActions/price_product`, relaying to the application client |
| the action, a class of actions with one repository lookup | `ordering/application/order_actions.py` | `OrderActions.price_product` → `ProductCatalogRepository.get_product_price` → `adapters/repositories/memory_product_catalog_repository.py` |
| the price comes back up the same chain | | `PriceProductResponse.cents` → `Order.total(PriceSpec)` → `OrderOrchestratorResponse.total_cents` ends the workflow |

`POST /submissions` answers `202` with the order id as soon as the workflow is
accepted — `workflow_send` is fire-and-forget, so the total is read back from
Restate, not from the response. Submitting an order is the asynchronous use
case: the order is accepted now and priced later. The verb is the domain's
word for what the caller gets back, not the engine's word for how it was
called; that one, `start_`, belongs to the runner.

`POST /orders` is the other use case over the same orchestrator: placing an
order. `OrderService.place_order` builds the same `Order`, hands it to
`OrderOrchestratorRunner.run_order_orchestrator`, and waits; the Restate
runner's `workflow_call` answers with the `OrderOrchestratorResponse` the
workflow ended with, and the door answers `200 {"order_id", "total_cents"}`.
"Placed" is the state the caller gets back: priced, now. Both use cases run
`OrderOrchestrator/run` under the same key, so they are one business act done
to one order, and an order that was submitted cannot then be placed: the
engine has already run it.

That is the grid this tree is filling in. The verb on a runner method says
how the caller calls; the thing it names says what runs; either verb goes
with either thing.

| | a workflow (`OrderOrchestrator/run`) | an action (`OrderActions/price_product`) |
|---|---|---|
| `start_` — the engine accepts, the caller carries on | `start_order_orchestrator`, ingress `workflow_send`, behind `POST /submissions` | not yet |
| `run_` — the caller waits for the result | `run_order_orchestrator`, ingress `workflow_call`, behind `POST /orders` | `run_price_product`, `ctx.service_call`, inside the workflow |

`POST /purchases` is the third use case and the first scenario on top of the
grid: a **purchase** is an order paid for. `PurchaseService.purchase` builds the
same `Order` and hands it to `PurchaseOrchestratorRunner.run_purchase_orchestrator`;
the `PurchaseOrchestrator` workflow runs `OrderOrchestrator/run` as a **child
workflow** under the order's own key, waits for its total, and then runs the
`PurchaseActions/take_payment` action for that total. The door answers
`200 {"order_id", "total_cents", "payment_reference"}`. The walk-through is
[A workflow runs another](#a-workflow-runs-another-the-purchase).

The application never touches Restate. `OrderOrchestrator` depends on
`OrderActionsRunner` and nothing else; `PurchaseOrchestrator` depends on
`PurchaseActionsRunner` and `OrderOrchestratorRunner` and nothing else;
`OrderActions` (the class of actions) depends on the `ProductCatalogRepository`
port and nothing else, `PurchaseActions` on the `PaymentProcessor` port. All
are plain application code. What makes an orchestrator's calls durable is
which implementation of the runner it was handed.

Restate *does* carry the domain, on the workflow leg only.
`OrderOrchestratorRequest` is a **relay** message — a message whose far side
is this same context's own application code — so it holds the `Order`
aggregate, and `OrderSnapshot` writes it to the wire and rebuilds it on the
other side through the aggregate's own constructor.

## Two runners cross the engine, because two lifetimes do

`application/relays/` holds both protocols, and each declares only what it is
for. The verb says how the caller calls: `start_` is an asynchronous send that
answers as soon as the engine accepts; `run_` is a synchronous call that
answers with the result. The orchestrator runner declares both verbs over one
message, because the two use cases differ only in whether the caller waits.

```python
# ordering/application/relays/order_orchestrator_runner.py
class OrderOrchestratorRunner(ts.Relay, typing.Protocol):

    async def start_order_orchestrator(
        self, order_orchestrator_request: OrderOrchestratorRequest
    ) -> StartOrderOrchestratorResponse: ...

    async def run_order_orchestrator(
        self, order_orchestrator_request: OrderOrchestratorRequest
    ) -> OrderOrchestratorResponse: ...


# ordering/application/relays/order_actions_runner.py
class OrderActionsRunner(ts.JobContext, typing.Protocol):

    async def run_price_product(
        self, price_product_request: PriceProductRequest
    ) -> PriceProductResponse: ...
```

`OrderOrchestratorRunner` is held by `OrderService`, lives as long as the
component, and its Restate implementation
`RestateOrderOrchestratorRunner(ingress, restate_order_runtime)` is built once
at wiring.

`OrderActionsRunner` is held by `OrderOrchestrator`, lives exactly as long as
one invocation, and its Restate implementation
`RestateOrderActionsRunner(restate_workflow_context, restate_order_runtime)`
is built inside the workflow handler over that handler's own
`restate.WorkflowContext`. The context is required and is never `None` —
there is no such thing as an actions runner outside an invocation.

`OrderOrchestratorRunner` has a second implementation with the second
lifetime: `RestateOrderOrchestratorChildRunner(restate_workflow_context,
restate_order_runtime)`, built inside the *purchase* workflow's handler,
answers the same protocol with `ctx.workflow_call` and `ctx.workflow_send`
instead of the ingress client. One relay, two runners: the door holds the one
that lives with the component, a parent workflow holds the one that lives with
its invocation, and `OrderService` and `PurchaseOrchestrator` cannot tell
which they were handed.

## A workflow runs another: the purchase

`ordering/application/orchestrators/purchase_orchestrator.py` is the parent:

```python
class PurchaseOrchestrator(ts.Orchestrator):

    def __init__(
        self,
        purchase_actions_runner: relays.PurchaseActionsRunner,
        order_orchestrator_runner: relays.OrderOrchestratorRunner,
    ) -> None: ...

    async def run(self, purchase_orchestrator_request):
        order = purchase_orchestrator_request.order
        order_orchestrator_response = await self._order_orchestrator_runner.run_order_orchestrator(
            relays.OrderOrchestratorRequest(order=order)
        )
        purchase = domain.Purchase(MapToPurchaseSpec(order, order_orchestrator_response))
        take_payment_response = await self._purchase_actions_runner.run_take_payment(
            MapToTakePaymentRequest(purchase)
        )
        payment = purchase.paid(MapToPaymentSpec(take_payment_response))
        return MapToPurchaseOrchestratorResponse(purchase, payment)
```

A `Purchase` is keyed by the order it pays for and holds the total the child
answered; `paid` is its one rule — the payment settles the purchase only if
the amount charged equals that total, else `CONFLICT payment_mismatch`.
`PurchaseActions.take_payment` is the class of actions over the
`PaymentProcessor` port (`adapters/gateways/memory_payment_processor.py` is
the stand-in, which charges an order once and refuses a second charge as
`CONFLICT payment_already_taken`).

The child is run, not inlined, because it is already a workflow of its own:
`OrderOrchestrator/<order_id>` is what `POST /orders` runs directly, it has
its own key, its own journal, and its own stored result. Measured on
`restate-server` 1.7.2 through `POST /purchases {"order_id": "p1", ...}`:

- `sys_invocation` holds four rows for `p1`: `PurchaseOrchestrator` keyed
  `p1`, `OrderOrchestrator` keyed `p1`, one `OrderActions` call, one
  `PurchaseActions` call. Parent and child share the key because they are one
  business act done to one order; they do not collide because they are two
  services.
- The child's result is readable by its own key afterwards —
  `GET /restate/workflow/OrderOrchestrator/p1/output` answers
  `{"order_id": "p1", "total_cents": 2000}` — and so is the parent's, at
  `/restate/workflow/PurchaseOrchestrator/p1/output`.
- A child that ends terminally ends the parent with the same status: a
  purchase for an unknown sku is `404` at the door, and no `PurchaseActions`
  row exists for it. The payment step never ran because the parent raised
  before reaching it, which is ordering, not compensation.
- `ctx.workflow_call` on a child whose key has already run does **not**
  attach to the stored result: it fails with a terminal `409 the workflow
  method was already invoked`, the parent ends `409`, and the door says so.
  So an order that was placed cannot then be purchased, and a purchase cannot
  be repeated, for the same reason a placed order cannot be placed again.

`RestateOrderOrchestratorChildRunner` reads one thing off the message,
`str(order_orchestrator_request.order.identity)`, for the child's key, and
passes it as it is: inside the engine the key is an argument to the SDK, not a
path segment, so there is nothing to percent-encode. A child's terminal error
reaches the parent as a `restate.TerminalError` carrying the child's status
(`server_context.py` raises `TerminalError(res.message, res.code)` on a failed
call future), and the child runner maps it exactly as the actions runner maps
an action's: `422`/`404`/`409` to the kind, as
`DomainError(kind, "order_rejected")` with the child's message, anything else
re-raised terminal.

`ts.JobContext` in tesser-py is a bare marker protocol, like `ts.Port` and
`ts.Relay`. The generic `call[I, O](step, request)` it used to declare is gone:
a runner says what *this* context's actions are, by name, on the subclass.

`ProductCatalogRepository` (Postgres, or the in-memory stand-in) stays a
`ts.Port`, because a store is not us.

The distinction is what may cross. A `ts.Client` faces outsiders and a
`ts.Port` faces a foreign system, so both stay primitives-only. A relay and a
job context both have us on both ends, and Restate pins an invocation to one
deployment, so their messages may carry domain objects and they come back
whole.

## Six adapters, split by direction and by lifetime

| class | kind declared | direction | lifetime |
|---|---|---|---|
| `RestateOrderRuntime` (`adapters/runtimes/`) | `ts.Job` | Restate → us: registers `OrderActions/price_product`, `OrderOrchestrator/run`, `PurchaseActions/take_payment`, and `PurchaseOrchestrator/run` | process |
| `RestateOrderOrchestratorRunner` (`adapters/runners/`) | `ts.Gateway` | us → Restate, from outside any invocation (ingress HTTP: `workflow_send` to start, `workflow_call` to run) | process |
| `RestatePurchaseOrchestratorRunner` (`adapters/runners/`) | `ts.Gateway` | us → Restate, from outside any invocation (ingress HTTP: `workflow_call`) | process |
| `RestateOrderActionsRunner` (`adapters/runners/`) | `ts.JobContext` | us → Restate, from inside an invocation (`service_call`) | one invocation |
| `RestatePurchaseActionsRunner` (`adapters/runners/`) | `ts.JobContext` | us → Restate, from inside an invocation (`service_call`) | one invocation |
| `RestateOrderOrchestratorChildRunner` (`adapters/runners/`) | `ts.JobContext` | us → Restate, from inside an invocation, to a child workflow (`workflow_call` to run, `workflow_send` to start) | one invocation |

The runtime is the inbound side, the same role the HTTP handler plays for
`POST /submissions`: the engine's server receives a request, routes it to a
handler, and the handler invokes application code. The two runners are the
outbound side, the same role an HTTP client gateway plays, except that they
address the far end by the handler object the runtime registered rather than
by a URL. That is what the Restate SDK's typed calls take: `service_call`,
`workflow_send` and `workflow_call` all read the service name, the handler
name, and both serdes off the decorated function (`handler_from_callable`),
so a rename is a rename
and there is no string to keep in step. `"OrderActions"`,
`"OrderOrchestrator"`, `"PurchaseActions"` and `"PurchaseOrchestrator"` appear
exactly once each, in the `restate.Service(...)` and `restate.Workflow(...)`
constructor calls in `RestateOrderRuntime.__init__`; the handler names are the
Python function names (`price_product`, `take_payment`, `run`), except that
the purchase workflow's main is declared `main(name="run")` so both workflows
answer to `run` while the two Python functions keep different names.

The runners hold the runtime to reach those handlers. The actions runner
cannot own the handler it invokes: it is built per invocation, and
registration has to be finished before the first invocation exists — the
host mounts the runtime's `Service` and `Workflow` at startup, when no
workflow context exists yet. So the runtime owns every handler, and each
runner reaches its own through the runtime.

**A runner and the runtime hand a message on whole and read nothing off it.**
Stronger, and greppable: no field name of any message or domain object appears
anywhere under `adapters/runtimes/` or `adapters/runners/` — not `sku`, not
`cents`, not `quantity`, not `order_id`, not `total_cents`. Every encoding is
a snapshot beside its message in `relays/`, and the one read left is
`str(<request>.order.identity)` in the three workflow runners, for the
workflow key Restate requires. The SDK splices that key into the request
path unencoded (`restate/client.py`, `endpoint += f"/{key}"`), and the id
comes from the public body, so the runner percent-encodes it
(`urllib.parse.quote(key, safe="")`); an `order_id` of `../admin` reaches the
ingress as `/OrderOrchestrator/..%2Fadmin/run/send`, not as a different route.

An `OrderSnapshot` on the way in checks the shape of what it reads before
the constructor sees it: `order_id` and `sku` must be strings and `quantity`
an `int` that is not a `bool`, or the snapshot is refused as a validation
error. The value objects guard their invariants, not their types, so without
that check a list where a `sku` should be builds an `Order` that raises a
`TypeError` later, inside the orchestrator, where Restate would retry it.

## The three application kinds, and where each lives

This tree is the worked example for `docs/design-app-service-types.md`:

- `OrderService(ts.ApplicationService)` and `PurchaseService` — the public
  use cases, built once by the component. Every method does the once-only
  work (validate at the door, build the `Order`); `submit_order` starts the
  order orchestrator through `OrderOrchestratorRunner.start_order_orchestrator`,
  `place_order` runs it through `run_order_orchestrator`, and `purchase` runs
  the purchase orchestrator through
  `PurchaseOrchestratorRunner.run_purchase_orchestrator`. Two services because
  two runners: a service holds the methods that share its dependencies, so the
  purchase, which holds a different runner, is a second service. What the
  context offers the world is still one `client.OrderingClient` protocol, and
  the component composes the two services behind it (below).
- `OrderOrchestrator(ts.Orchestrator)` and `PurchaseOrchestrator` in
  `application/orchestrators/` — not services. Built per invocation by the
  runtime with that invocation's runners; store nothing but them; take the
  relay's own request — reading the `Order` straight off it — and return the
  relay's response. The purchase orchestrator holds two runners: its job
  context for the payment action, and the order orchestrator's relay for the
  child workflow.
- `OrderActions(ts.Actions)` and `PurchaseActions` beside the services —
  classes of actions over exactly one port each (`ProductCatalogRepository`,
  `PaymentProcessor`), each method making exactly one call on it. Not on the
  public client: each is reachable only through its own protocol in
  `application/client/` (`OrderingApplicationClient`,
  `PurchaseApplicationClient`) that only the runtime imports.

## The component publishes the runtime, the host mounts it

The component builds the runtime once and uses it three times — as the
thing the host mounts, and as what each of the two ingress runners sends
through — and composes the two services behind the one client protocol:

```python
class Ordering(ts.Component):

    class Client:

        def __init__(self, order_service: application.OrderService, purchase_service: application.PurchaseService) -> None:
            self._order_service = order_service
            self._purchase_service = purchase_service

        async def submit_order(self, submit_order_request):
            return await self._order_service.submit_order(submit_order_request)

        async def place_order(self, place_order_request):
            return await self._order_service.place_order(place_order_request)

        async def purchase(self, purchase_request):
            return await self._purchase_service.purchase(purchase_request)

    def __init__(self, config: Config) -> None:
        ...
        self.restate_order_runtime = runtimes.RestateOrderRuntime(
            self._order_actions, self._purchase_actions
        )
        self.client: client.OrderingClient = Ordering.Client(
            application.OrderService(
                runners.RestateOrderOrchestratorRunner(config.ingress, self.restate_order_runtime)
            ),
            application.PurchaseService(
                runners.RestatePurchaseOrchestratorRunner(config.ingress, self.restate_order_runtime)
            ),
        )
```

`Ordering.Client` is the one object that satisfies `client.OrderingClient`;
the module alias tells the two apart the way `Spec` and `Config` are told
apart from `ts.Spec` and `ts.Config`. It holds the services and forwards each
protocol method to the one that owns it, three lines of forwarding, which is
what composing two services costs in Python; it is where a reshaped contract
would go if the public surface ever differed from a service's signature. It
subclasses nothing: a protocol is satisfied structurally, and the annotation
on `self.client` is where that is checked. The analyzer has no row for a
class nested in a component and reports nothing on it — whether that is the
rule or a hole is an open ruling in `TODOS.md`.

`restate.app(services)` is two things glued together: an `Endpoint`, a dict
of `Service` and `Workflow` objects by name, and an ASGI app that routes
`.../discover` (the manifest the Restate server reads once, at deployment
registration) and `.../invoke/<Service>/<handler>` (the per-invocation
protocol) by the tail of the path. It takes exactly the four objects the
runtime holds as attributes, so the host passes those and nothing collects or
flattens anything:

```python
api.mount(
    _RESTATE_DEPLOYMENT_PATH,
    restate.app(
        [
            durable_execution_app.ordering.restate_order_runtime.order_actions_service,
            durable_execution_app.ordering.restate_order_runtime.order_orchestrator_workflow,
            durable_execution_app.ordering.restate_order_runtime.purchase_actions_service,
            durable_execution_app.ordering.restate_order_runtime.purchase_orchestrator_workflow,
        ]
    ),
)
```

`_RESTATE_DEPLOYMENT_PATH` is the path component of the deployment URI the
Restate server registers, `http://<host>/restate`. `srv/http/test_main.py`
boots the real host, reads `/restate/discover`, and asserts the discovered
manifest against the runtime's four registrations, so the manifest and the
code cannot drift apart silently.

**This diverges from `srv.md` rule 5 — the route table is the host's.** The
Restate names are declared in a context adapter, not at the app edge. The
reason: here the context is its own caller, and the names are an agreement
between the runtime's handlers and the runners that send to them, both ours.

## What this shape costs, in rules

**A serde is an application kind now.** `tesser/application/serde.py` is its
home, and `tesser.adapters` re-exports it the same direction `JobContext` and
`Relay` already travel. That follows from where the encodings live: a snapshot
belongs beside the message it serves, and the messages belong to the relay.

**The analyzer has no rows for this shape yet.** `application/relays/`,
`ts.Relay`, a domain object on a `ts.Request` field, a serde in an application
module, `adapters/runtimes/` and `adapters/runners/` as kind packages, a job
context protocol outside `adapters/`, and a component publishing something
besides `client` and `jobs` all draw findings. Every one carries a
`# tesser:debt TB0xx` marker at its line — 103 of them, plus twenty-four
`TB023` markers on nested functions: the four handlers the SDK registers, the
three route functions `main` declares, and the seventeen fake-ingress
functions the two orchestrator runners' tests bind to a socket — and that
marker list is the registration this tree asks of the analyzer. The purchase
roughly doubled it, because a second workflow is a second relay, a second
class of actions, a second application client, and three more runners, each
of the shape the analyzer has no row for; the list grows by the shape, not by
the scenario. Nothing is hidden: the
tree is at zero findings because every finding is named, not because any is
absent.

The remaining rule cost of putting an encoding in the application is `json`:
the application stdlib allowlist is `{__future__, typing}`, and the four
relays modules and `snapshots/order_snapshot.py` import it (five of the 103).

## Messages are declared once, beside the protocol that speaks them

There are no wire types. Both ends are us, so the send side and the receive
side of one message are not independent boundaries.

- `order_orchestrator_runner.py` holds `OrderOrchestratorRequest`,
  `StartOrderOrchestratorResponse`, and `OrderOrchestratorResponse` — the
  orchestrator's input, the start ack, and the orchestrator's result.
  `run_order_orchestrator` answers with the result; after a start, the engine
  stores it and the ingress hands it back on request.
- `order_actions_runner.py` holds `PriceProductRequest` and
  `PriceProductResponse` — the action's two shapes.
  `application/client/order_actions.py` and `OrderActions` speak the same two.
- `purchase_orchestrator_runner.py` holds `PurchaseOrchestratorRequest` (the
  `Order` again — a purchase is asked for with an order) and
  `PurchaseOrchestratorResponse`, whose snapshot checks `order_id`,
  `total_cents`, and `payment_reference` on the way in as the order's does.
- `purchase_actions_runner.py` holds `TakePaymentRequest` and
  `TakePaymentResponse`; `application/client/purchase_actions.py` and
  `PurchaseActions` speak the same two.
- `application/snapshots/order_snapshot.py` holds `OrderSnapshot`, the
  aggregate's canonical form, because two relay messages now carry an `Order`
  and a module in an exporting package may not import the module beside it:
  the encoding both relays share lives in a package both import, and it is
  written once.

**Every wire form is an explicit snapshot beside its message.** Five in all:
`OrderSnapshot`, `OrderOrchestratorRequestSnapshot` and
`OrderOrchestratorResponseSnapshot` in `order_orchestrator_runner.py`;
`PriceProductRequestSnapshot` and `PriceProductResponseSnapshot` in
`order_actions_runner.py`. Each is a `ts.Serde` with exactly `serialize` and
`deserialize`, written out longhand rather than derived:

```python
class OrderSnapshot(ts.Serde):

    def serialize(self, order: domain.Order) -> bytes:
        return json.dumps(
            {
                "order_id": str(order.identity),
                "sku": str(order.sku),
                "quantity": int(order.quantity),
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
re-runs on the way in and a journal holding an order of zero units is refused
on replay rather than hydrated. Renaming `_sku` is an ordinary rename.

`OrderOrchestratorRequestSnapshot` is the whole of what a workflow start puts
on the wire — the order it carries, and nothing wrapped around it — so the
body `POST /OrderOrchestrator/o1/run/send` carries is:

```json
{"order_id": "o1", "sku": "widget", "quantity": 2}
```

The SDK cannot serialize a `ts.Request` on its own — `restate.serde.DefaultSerde`
handles msgspec Structs, Pydantic models, and dataclasses; anything else falls
through to `json.dumps(obj)` — so the runtime module carries four compatibility
shims, one per message the SDK moves. A shim does two things and no more:
answer the SDK's `None`/empty convention on the way out, refuse an empty body
on the way in, and delegate to the relay's snapshot. A body that does not
exist is not a message: handing `None` to a handler declared over a message
raised an `AttributeError` there, which is not terminal, and Restate retries a
non-terminal failure without bound.

```python
class RestatePriceProductRequestSerde(ts.Serde, restate.serde.Serde[relays.PriceProductRequest]):

    def serialize(self, price_product_request: relays.PriceProductRequest | None) -> bytes:
        if price_product_request is None:
            return b""
        return relays.PriceProductRequestSnapshot().serialize(price_product_request)

    def deserialize(self, buf: bytes) -> relays.PriceProductRequest | None:
        if not buf:
            return None
        return relays.PriceProductRequestSnapshot().deserialize(buf)
```

None of them is generic and none of them knows a field. What crosses is decided
in one module — the relay's — and the engine adapter only carries it. A field
added to a message still changes the bytes an in-flight journal already holds;
payload versioning on a durable leg is a rule this tree does not yet make.

## Errors across the engine

A `DomainError` in a handler becomes a `restate.TerminalError` with the kind's
status — no retry. When the action handler raises it, the actions runner
receives it as a `TerminalError` from `service_call` and maps the status back
to its kind (`422` → `VALIDATION`, `404` → `NOT_FOUND`, `409` → `CONFLICT`),
raising a `DomainError` with the action's message, so the orchestrator and the
workflow handler see a domain error, not an SDK one, and the workflow ends
terminally with the action's status. A `TerminalError` carrying any other
status is not the domain's (the SDK's own 500, a cancellation) and is
re-raised as it is, still terminal. Anything that is not a `TerminalError`
propagates as-is and Restate retries the invocation.

On the way out, the two calling modes answer a repeat differently, and the
runner maps what each one measured on `restate-server` 1.7.2:

- A repeat `workflow_send` on an existing key is accepted again — `202` with
  `"status": "PreviouslyAccepted"` — and deduplicated by the engine. So a
  second `POST /submissions` for the same order is a `202`, the same as the
  first. The runner still maps an ingress `409` on the send path to
  `DomainError(CONFLICT, "order_already_started")`, for a server that refuses
  rather than deduplicates.
- A repeat `workflow_call` on an existing key is `409` with a body of
  `{"code": 409, "message": "the workflow method was already invoked"}`: the
  runner raises `DomainError(CONFLICT, "order_rejected")` carrying that
  message and `POST /orders` answers `409`. The runner does not claim the
  order was placed: a workflow's own terminal conflict arrives in the same
  shape, and only the message tells the two apart.
- A workflow that ended terminally answers `workflow_call` with the
  `TerminalError`'s own status and a body carrying `code` and `message`, so
  an unknown sku is `404 {"code": 404, "message": "no price for sku 'nope'"}`.
  The runner takes a body as the workflow's own only when its `code` equals
  the HTTP status, which is how the server shapes a `TerminalError`; it then
  maps `422`/`404`/`409` back to the domain's kind, as
  `DomainError(kind, "order_rejected")` with the action's message, and
  `POST /orders` answers with that status.
- A success body is the response snapshot's to check, the way
  `OrderSnapshot` checks an order on the way in: `order_id` a string,
  `total_cents` an `int` that is not a `bool` and not negative, or the
  snapshot refuses it. The runner turns that refusal, a body that is not
  JSON, and a body nested past the decoder's depth into an `InfraError`,
  because none of them is the caller's fault and a `422` would say it was.
- The run path waits as long as the workflow takes. Its `httpx` client keeps
  the five-second connect, write and pool timeouts and lifts the read
  timeout (`_RUN_TIMEOUT`), because a caller who asked for the total has
  asked to wait for it; under the default read timeout a workflow slower
  than five seconds would answer `503` while it kept running, and the retry
  would meet the `409` above. How long an order may take to price is a rule
  this tree does not make; a real one puts the bound in the workflow or at
  the ingress, where a timed-out caller can still attach to the result.
- A refusal whose body has no `code` is the ingress's, not the workflow's —
  an unregistered service or handler is `404 {"message": "service ... not
  found"}` — and is an `InfraError`, reported as `503`. So is any status the
  domain does not own (the SDK's own `500`), and every transport failure.

## Tests, and the one thing they fake

Every payload is pinned once, in `relays/test_order_orchestrator_runner.py`
and `relays/test_order_actions_runner.py`, where the snapshots are defined.
The runtime's test asserts the two registrations and that the action handler
hands its request to the application client; the shims are asserted to write
what their snapshots write. The orchestrator runner's test builds the real
SDK client over a real socket listening on `127.0.0.1:0` and checks the
request line the SDK forms from the registered handler
(`POST /OrderOrchestrator/o1/run/send` to start, `POST /OrderOrchestrator/o1/run`
to run), the route and the key. On the run path the fake ingress answers the
response snapshot's bytes, or a refusal shaped as the server shapes it, so the
test pins the mapping above: `409` with a `code` is a conflict, `404` with a
`code` is the domain's not-found, `404` without one is infrastructure.

The actions runners' tests double the one thing the SDK gives no other way to
reach: a `FakeRestateWorkflowContext` whose `service_call` records the handler
it was handed, so the test asserts the runner journals a call to the runtime's
own `price_product_handler` (or `take_payment_handler`), and that a
`TerminalError` from the call comes back as a `DomainError`. The child
runner's test gives the same fake `workflow_call` and `workflow_send`, and
asserts the run journals a call to `order_orchestrator_handler` under the
order's id as it is, the start journals a send, and the child's terminal
statuses map to the kind. Those fakes double an SDK class rather than a port,
which the testing norm does not admit; each carries its own debt marker.

## Async everywhere the SDK is

The SDK is async on both sides, so the request path is `async`: the four
runner protocols, `OrderService`, the three `OrderingClient` methods, the HTTP
handler, both orchestrators, and the four Restate handlers. The class of actions and its
repository are sync — plain application code that runs inside the action
handler. There is no `asyncio.run` on the request path at all: the one loop is
hypercorn's, opened once by `HttpHost.run`.

## One process of ours, two mechanisms in it

`srv/http/main.py` is the whole `srv/` directory. It builds one FastAPI app
and serves it under one hypercorn: an `APIRouter` carrying `POST /submissions`,
`POST /orders` and `POST /purchases`, the API this app offers the world, and
the Restate endpoint mounted at `/restate`, the one Restate's server calls
back into.

**Restate's own recommendation is that the ingress IS the API** — you register
the deployment and clients `POST :8080/OrderOrchestrator/o1/run` directly,
with no service of yours in front. A front door of our own exists here for
exactly one reason: to own the public contract. `POST /submissions`,
`POST /orders` and `POST /purchases` are a URL, a body shape, and a status
code this app is free to keep stable while the workflow behind them is
renamed, split, or moved off Restate entirely.

**This diverges from `srv.md` rule 6 — one long-running thing per process.**
The mounted endpoint is not a second delivery mechanism serving someone else's
traffic, it is the return leg of the workflow this same process started.

Mounting under a prefix works because the SDK parses the tail: `parse_path`
(`restate/server.py`) reads `$mountpoint/discover` and
`$mountpoint/invoke/:service/:handler` off the end of `scope["path"]`.

## Running it

```
pip install -r requirements-dev.txt
docker run -d --name restate -p 18080:8080 -p 19070:9070 \
  --add-host=host.docker.internal:host-gateway docker.io/restatedev/restate:latest
PYTHONPATH=.:../../tesser-py RESTATE_INGRESS=http://localhost:18080 \
  python -m srv.http.main 0.0.0.0:8000 &            # the API and the Restate endpoint
curl -X POST localhost:19070/deployments --json '{"uri":"http://host.docker.internal:8000/restate"}'
curl -X POST localhost:8000/submissions --json '{"order_id":"o1","sku":"gadget","quantity":2}'
                                                    # 202 {"order_id": "o1"}
curl localhost:18080/restate/workflow/OrderOrchestrator/o1/output
                                                    # {"order_id": "o1", "total_cents": 2000}
curl -X POST localhost:8000/orders --json '{"order_id":"o2","sku":"gadget","quantity":3}'
                                                    # 200 {"order_id": "o2", "total_cents": 3000}
curl -X POST localhost:8000/purchases --json '{"order_id":"p1","sku":"gadget","quantity":2}'
                          # 200 {"order_id": "p1", "total_cents": 2000, "payment_reference": "pay-p1"}
curl localhost:18080/restate/workflow/OrderOrchestrator/p1/output
                                                    # {"order_id": "p1", "total_cents": 2000}  the child, by its own key
curl -X POST localhost:8000/orders --json '{"order_id":"p1","sku":"gadget","quantity":2}'
                                                    # 409 the child key is taken: p1 was purchased
curl -X POST localhost:8000/purchases --json '{"order_id":"o2","sku":"gadget","quantity":3}'
                                                    # 409 o2 was placed above, so the child call refuses
```

The failure arms answer at the front door, mapped from the three exception
kinds the handler and the application can raise, the same on both routes:

```
curl -X POST localhost:8000/orders --json '{"order_id":"o3"}'
   # 400 {"detail": "sku must be a string"}
curl -X POST localhost:8000/orders --json '{"order_id":"o3","sku":"gadget","quantity":0}'
   # 422 {"detail": "an order is for at least one unit"}          errors.status_for(VALIDATION)
   #     with the ingress down, a well-formed order is 503 {"detail": "unavailable"}
curl -X POST localhost:8000/orders --json '{"order_id":"o2","sku":"gadget","quantity":3}'
   # 409 {"detail": "the workflow method was already invoked"}    o2 was placed above
```

A domain error raised *inside* the workflow ends it terminally. On
`POST /orders` the caller is waiting, so it comes back through the door with
the domain's status — an unknown sku is `404 {"detail": "no price for sku
'nope'"}`. After `POST /submissions` nobody is waiting, so it is read back off
the ingress: `/restate/workflow/OrderOrchestrator/o4/output` answers
`404 {"code":404,"message":"no price for sku 'nope'"}`.

**SIGTERM belongs to the SDK.** `restate.app` installs its own `SIGTERM`
handler on the first request, replacing hypercorn's: to Restate, SIGTERM
means drain the in-flight invocations. The host stops on SIGINT; the srv test
sends SIGINT.

## Production boundaries this example does not cross

- The catalog is an in-memory repository seeded with two SKUs; a second
  replica would not share it, which is fine only because the lookup is
  read-only. The payment processor is an in-memory gateway that charges each
  order once; a real one is a vendor behind the same `PaymentProcessor` port.
- A purchase has no compensation. If `take_payment` ended terminally after
  the child order ran, the order would stay placed and unpaid; the purchase
  workflow would end with the payment's status and nothing would undo the
  child. Compensating only the steps that ran is the checkout scenario, not
  this one.
- A parent cannot attach to a child that already ran. `ctx.workflow_call` on
  a taken key is a terminal `409`, so a purchase of an order that was placed
  is refused rather than priced from the stored result; a parent that wanted
  the stored result would need the SDK's attach, which this tree does not
  use.
- `RestateOrderRuntime` now hosts the purchase's service and workflow too;
  it is ordering's one Restate runtime and the name has not followed. A
  rename is a redeploy of nothing here (the handler names are unchanged) and
  is left for its own change.
- `start_order_orchestrator` fires and forgets; `POST /submissions` never waits on
  the workflow. A submitted order's total is read back through Restate's
  ingress, because the API has no read route of its own; `POST /orders` is the
  route for a caller who wants the total in the response.
- `POST /orders` holds the caller's connection for as long as the workflow
  takes, with no read timeout, no deadline of its own, and no cap on how many
  may wait at once; a burst of slow or stuck workflows holds that many
  connections open in this process. The bound belongs at the ingress or in
  the workflow, where a caller who gave up can still attach to the result;
  this tree makes neither rule.
- A handler's registered name is part of the deployment. Renaming one (this
  tree's `prepare_quote` became `price_product`) makes the service a different
  one to Restate: re-register the deployment after upgrading, and an
  invocation journaled against the old name has no handler to replay against
  on the new one. This tree has no deployments, so it renames freely; a real
  one keeps the old handler through a migration window or deploys the new
  version at its own endpoint and drains the old.
- The component can wire exactly one engine: the host mounts this runtime's
  two Restate objects by name. A second engine (an in-process one for tests,
  or Temporal) would implement the same two runner protocols over its own
  runtime, and the component would have to publish that too.
- The deployment endpoint at `/restate` is mounted on the same public bind as
  `POST /submissions`, with no `identity_keys`. Anyone who can reach port 8000 can
  `POST /restate/invoke/OrderActions/price_product` with a body of their own
  and bypass the service. A deployment passes Restate's request-identity keys
  to `restate.app(...)` or serves the endpoint on a bind only the Restate
  server reaches.
- An invalid snapshot that reaches the deployment endpoint directly (a
  `quantity` of `0` posted to the ingress rather than to `POST /submissions`) is
  refused inside the SDK's input deserialization, which wraps every exception
  as a `TerminalError` with status 500 (`restate/handler.py`); the same body
  at `POST /submissions` is a 422. Restate does not retry it, but the status is
  the SDK's, not the domain's. Validating inside the handler instead would
  make the wire shape something other than the aggregate.
