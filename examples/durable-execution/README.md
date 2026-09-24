# durable-execution — one FastAPI host: the API front door and the mounted Restate endpoint

The chain, top to bottom, with where each link lives:

| Step | Placement | Code |
|---|---|---|
| an HTTP host takes `POST /submissions` | `srv/http/main.py` | `HttpHost`'s `APIRouter` → `ordering/adapters/handlers/http.py` `Handler.submit_order` |
| the initial application service | `ordering/application/order_service.py` | `OrderService.submit_order` builds the `Order` aggregate |
| it starts the orchestrator through a relay | `ordering/application/relays/order_orchestrator_relay.py` | `OrderOrchestratorRelay.start_confirm_order(ConfirmOrderRequest) -> StartConfirmOrderResponse`; the request carries the `Order` aggregate itself |
| the HTTP dispatcher sends the workflow | `ordering/adapters/dispatchers/restate_http_order_orchestrator_relay.py` | `RestateHttpOrderOrchestratorRelay.start_confirm_order` → `restate.client.Client(...).workflow_send(self._restate_confirm_order.handler, key=order_id, arg=confirm_order_request)` |
| Restate's server calls back into the workflow | `ordering/adapters/workflows/restate_workflows.py` | `RestateConfirmOrder` (`ts.Workflow`) registered its `main` handler `confirm_order` on the `restate.Workflow("OrderOrchestrator")` the component handed it, and keeps it as `self.handler`; the host mounts that container at `/restate` |
| the orchestrator is built **inside the invocation** | `ordering/adapters/workflows/restate_workflows.py` | `confirm_order` builds `OrderOrchestrator(RestateInvocationOrderActionsRelay(restate_workflow_context, restate_price_product))` over *this* invocation's context and calls `confirm_order` on it |
| the orchestrator runs the action through its relay | `ordering/application/relays/order_actions_relay.py` | `OrderOrchestrator.confirm_order` reads the `Order` off the message, then `OrderActionsRelay.run_price_product(PriceProductRequest) -> PriceProductResponse` |
| the invocation dispatcher calls the action durably | `ordering/adapters/workflows/restate_workflows.py` | `RestateInvocationOrderActionsRelay.run_price_product` → `restate_workflow_context.service_call(self._restate_price_product.handler, price_product_request)` |
| Restate's server calls back into the activity | `ordering/adapters/activities/restate_activities.py` | `RestatePriceProduct` (`ts.Activity`) registered its handler `price_product` on the ingress-private `restate.Service("OrderActions")`, relaying to the application client |
| the action, a class of actions with one repository lookup | `ordering/application/order_actions.py` | `OrderActions.price_product` → `ProductCatalogRepository.get_product_price` → `adapters/repositories/memory_product_catalog_repository.py` |
| the price comes back up the same chain | | `PriceProductResponse.prices[0].cents` → `Order.total(PriceSpec)` → `ConfirmOrderResponse.confirmed_orders[0].total_cents` ends the workflow |

`POST /submissions` answers `202` with the order id as soon as the workflow is
accepted — the send is fire-and-forget, so the total is read back from
Restate, not from the response. Submitting an order is the asynchronous use
case: the order is accepted now and priced later. The verb is the domain's
word for what the caller gets back, not the engine's word for how it was
called; that one, `start_`, belongs to the relay and the dispatcher that implements it.

`POST /orders` is the other use case over the same orchestrator: placing an
order. `OrderService.place_order` builds the same `Order`, hands it to
`OrderOrchestratorRelay.run_confirm_order`, and waits; the Restate
dispatcher's `workflow_call` answers with the `ConfirmOrderResponse` the
workflow ended with, and the door answers `200 {"order_id", "total_cents"}`.
"Placed" is the state the caller gets back: priced, now. Both use cases run
`OrderOrchestrator/confirm_order` under the same key, so they are one business act done
to one order, and an order that was submitted cannot then be placed: the
engine has already run it.

That is the grid this tree is filling in. The verb on a relay method says
how the caller calls; the thing it names says what runs; either verb goes
with either thing.

| | a workflow (`OrderOrchestrator/confirm_order`) | an action (`OrderActions/price_product`) |
|---|---|---|
| `start_` — the engine accepts, the caller carries on | `start_confirm_order`, ingress `workflow_send`, behind `POST /submissions` | not yet |
| `run_` — the caller waits for the result | `run_confirm_order`, ingress `workflow_call`, behind `POST /orders` | `run_price_product`, `ctx.service_call`, inside the workflow |

`POST /purchases` is the third use case and the first scenario on top of the
grid: a **purchase** is an order paid for. `PurchaseService.make_order_payment` builds the
same `Order` and hands it to `PurchaseOrchestratorRelay.run_pay_for_order`;
the `PurchaseOrchestrator` workflow runs `OrderOrchestrator/confirm_order` as a **child
workflow** under the order's own key, waits for its total, and then runs the
`PurchaseActions/take_payment` action for that total. The door answers
`200 {"order_id", "total_cents", "payment_reference"}`. The walk-through is
[A workflow runs another](#a-workflow-runs-another-the-purchase).

The application never touches Restate. `OrderOrchestrator` depends on
`OrderActionsRelay` and nothing else; `PurchaseOrchestrator` depends on
`PurchaseActionsRelay` and `OrderOrchestratorRelay` and nothing else;
`OrderActions` (the class of actions) depends on the `ProductCatalogRepository`
port and nothing else, `PurchaseActions` on the `PaymentProcessor` port. All
are plain application code. What makes an orchestrator's calls durable is
which dispatcher implements the relay it was handed.

Restate *does* carry the domain, on the workflow leg only.
`ConfirmOrderRequest` is a **relay** message — a message whose far side
is this same context's own application code — so it holds the `Order`
aggregate, and `OrderSnapshot` writes it to the wire and rebuilds it on the
other side through the aggregate's own constructor.

## Two dispatchers cross the engine, because two lifetimes do

`application/relays/` holds both protocols, and each declares only what it is
for. The verb says how the caller calls: `start_` is an asynchronous send that
answers as soon as the engine accepts; `run_` is a synchronous call that
answers with the result. `OrderOrchestratorRelay` declares both verbs over one
message, because the two use cases differ only in whether the caller waits.

```python
# ordering/application/relays/order_orchestrator_relay.py
class OrderOrchestratorRelay(ts.Relay, typing.Protocol):

    async def start_confirm_order(
        self, confirm_order_request: ConfirmOrderRequest
    ) -> StartConfirmOrderResponse: ...

    async def run_confirm_order(
        self, confirm_order_request: ConfirmOrderRequest
    ) -> ConfirmOrderResponse: ...


# ordering/application/relays/order_actions_relay.py
class OrderActionsRelay(ts.Relay, typing.Protocol):

    async def run_price_product(
        self, price_product_request: PriceProductRequest
    ) -> PriceProductResponse: ...
```

`OrderOrchestratorRelay` is held by `OrderService`, lives as long as the
component, and its Restate implementation
`RestateHttpOrderOrchestratorRelay(ingress, restate_confirm_order)` is built
once at wiring. It holds the `RestateConfirmOrder` workflow the component
built and passes its `.handler` to the SDK's typed call, so the service and
handler names it sends to are read off the registered object, never written
at the call.

`OrderActionsRelay` is held by `OrderOrchestrator`, lives exactly as long as
one invocation, and its Restate implementation
`RestateInvocationOrderActionsRelay(restate_workflow_context, restate_price_product)`
is built by `RestateConfirmOrder`'s `main` handler over that handler's own
`restate.WorkflowContext`, in the same module as the workflow that builds it.
The context is required and is never `None` — there is no dispatcher for an
action outside an invocation.

`OrderOrchestratorRelay` has a second implementation with the second
lifetime: `RestateInvocationOrderOrchestratorRelay(restate_workflow_context,
restate_confirm_order)`, built by `RestatePayForOrder`'s `main` handler for
the *purchase* workflow, answers the same protocol with `ctx.workflow_call`
and `ctx.workflow_send` on the same `restate_confirm_order.handler` instead of
the ingress client. One relay, two dispatchers: the door holds the one that
lives with the component, a parent workflow holds the one that lives with its
invocation, and `OrderService` and `PurchaseOrchestrator` cannot tell which
they were handed. Both hold the one `RestateConfirmOrder` instance, so both
reach the child by the name that instance registered.

## A workflow runs another: the purchase

`ordering/application/orchestrators/purchase_orchestrator.py` is the parent:

```python
class PurchaseOrchestrator(ts.Orchestrator):

    def __init__(
        self,
        purchase_actions_relay: relays.PurchaseActionsRelay,
        order_orchestrator_relay: relays.OrderOrchestratorRelay,
    ) -> None: ...

    async def pay_for_order(self, pay_for_order_request):
        order = pay_for_order_request.order
        confirm_order_response = await self._order_orchestrator_relay.run_confirm_order(
            relays.ConfirmOrderRequest(order=order)
        )
        match confirm_order_response.outcome:
            case relays.ConfirmOrderOutcome.CONFIRMED:
                purchase = domain.Purchase(MapToPurchaseSpec(order, confirm_order_response))
            case (
                relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND
                | relays.ConfirmOrderOutcome.ALREADY_STARTED
            ):
                return MapToPayForOrderResponseFromConfirmOrderResponse(
                    order, confirm_order_response
                )
            case _ as never:
                typing.assert_never(never)
        take_payment_response = await self._purchase_actions_relay.run_take_payment(
            MapToTakePaymentRequest(purchase, pay_for_order_request.payment_method)
        )
        match take_payment_response.outcome:
            case relays.TakePaymentOutcome.TAKEN:
                payment = purchase.paid(MapToPaymentSpec(take_payment_response))
            case relays.TakePaymentOutcome.DECLINED:
                return MapToPayForOrderResponseFromTakePaymentResponse(
                    purchase, take_payment_response
                )
            case _ as never_taken:
                typing.assert_never(never_taken)
        return MapToPayForOrderResponseFromPayment(purchase, payment)
```

The parent's method is the operation, `pay_for_order`, never `run`: `run` says
nothing about what the act is, and it is already the caller's calling-mode
word on the relay. The two `match`es are the two relays it depends on, and
each names its own step in the parent's own words — a child that could not be
confirmed, for any reason the child had, is `ORDER_NOT_CONFIRMED` here, and
the child's reason rides along as data so the caller can still be told.

A `Purchase` is keyed by the order it pays for and holds the total the child
answered, and it carries three rules, each a `CONFLICT`: a pricing that names
another order cannot build the purchase (`priced_another_order`, so a child
that answered for a different key is refused before any payment); a payment
settles the purchase only if it names this order
(`payment_for_another_order`) and only if the amount charged equals the total
(`payment_mismatch`). The receipt names its order because the processor's
`ChargePaymentMethodResponse` does, and that id rides the relay as
`TakePaymentResponse.order_id` into `PaymentSpec`: without it the domain
could not tell one order's receipt from another's at the same amount. What
the purchase does not check is the total itself: the parent holds an `Order`
and no catalog, so the child's total is the child's word, and
`payment_mismatch` catches a processor that charged something other than
what it was asked, never a wrong price.
`PurchaseActions.take_payment` is the class of actions over the
`PaymentProcessor` port, and the port's operation is
`charge_payment_method`: a bare `charge` said what to do and never what to
do it to, and the request carried an order id and cents and nothing to
charge. A `PaymentMethod` value object now rides from the client's
`MakeOrderPaymentRequest` through the parent relay into
`ChargePaymentMethodRequest`, so the operation charges what its name says.
`adapters/gateways/memory_payment_processor.py` is
the stand-in, and it decides nothing the domain owns:
`charge_payment_method` answers the receipt it
already holds for the order, or takes the charge and holds the receipt it
made, in one `setdefault` with no branch, and the receipt is built by an
adapters mapper (`MapToReceipt`) so the method reads as store-then-map
the way every gateway in the tree reads as call-then-map. It does decide one
thing a real processor decides: a payment method of `"declined"` comes back
as `ChargePaymentMethodOutcome.DECLINED`, which is the stand-in's way of
being a vendor that refuses. The receipt wins over the refusal: an order
already charged answers its receipt whatever method asks again, so a
replay can never report a paid order as declined. The method is a plain
string the engine journals in clear, so a real integration puts an opaque
processor token there, never card data. A repeat for
another amount gets the original receipt too, and it is `Purchase.paid` that
refuses it as `payment_mismatch`, because whether a receipt settles a
purchase is the domain's rule and not the processor's. An earlier version of
this stand-in raised its own `CONFLICT` on that repeat, a decision made in
an adapter and a copy of a rule the aggregate already owned; the gateway is
where a payment is taken, never where it is judged. A processor behind an
action has to be idempotent on something the request carries, because an
action is the engine's retry unit: if the connection drops after the charge
but before Restate records the action's result, the action runs again, and a
processor that refused the repeat would turn a paid purchase into a failed
one. This stand-in keys on the order, which is enough only because the
shared key namespace already refuses a second purchase of one order; a real
processor takes an idempotency key on the request.

`Order` and `Purchase` are two aggregate roots, and they live in two domain
modules — `domain/order.py` and `domain/purchase.py` — because a domain module
declares at most one root, and a second root in one module is two consistency
boundaries sharing a file. Neither module imports the other: a purchase names
its order by `OrderId`. What both roots need lives in `domain/kernel/`, the
context kernel — `OrderId` in `order_id.py`, and `Quantity`, `PriceSpec` and
`Price` in `price.py`. A context kernel is an exporting package, so its
modules do not import each other either, which is why `Quantity` sits beside
`Price` rather than in a module of its own: `Price.times` takes a `Quantity`.
Both roots write `import ordering.domain.kernel as kernel` and name
`kernel.OrderId`.

Two value objects gained bounds in this change, because both were measured
as holes the purchase widens. `Quantity` is at most 1,000,000 units and
`Price` at most 10^12 cents, so their product stays far below Python's
4,300-digit integer-string limit; without the bound a 4 KB body with a
4,298-digit quantity passed every check until the workflow's output serde
raised on the way out, which the SDK does not wrap as terminal, so the engine
retried it forever while the caller's connection stayed open. And `OrderId`
refuses `.` and `..`: percent-encoding leaves a dot alone and httpx
normalizes dot segments on the way to the ingress, so an id of `..` would
have turned `POST /PurchaseOrchestrator/../pay_for_order` into `POST /pay_for_order`.

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
  `GET /restate/workflow/OrderOrchestrator/p1/output` answers the child's
  `ConfirmOrderResponse` — and so is the parent's, at
  `/restate/workflow/PurchaseOrchestrator/p1/output`.
- A child that could not price its product ends **successfully** now,
  answering `ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND` with the reason as
  data. The parent reads that outcome, summarises it as
  `PayForOrderOutcome.ORDER_NOT_CONFIRMED`, and ends successfully too; the
  service raises `client.OrderNotConfirmed` and the door answers `422`. No
  `PurchaseActions` row exists for it, because the parent returned before
  reaching the payment step — ordering, not compensation.
- `ctx.workflow_call` on a child whose key has already run does **not**
  attach to the stored result: it fails with a terminal `409 the workflow
  method was already invoked`. The child dispatcher recognises exactly that
  refusal — the 409 whose message is the server's already-invoked wording —
  and turns it into `ConfirmOrderOutcome.ALREADY_STARTED`; the parent reports
  its own step as `ORDER_NOT_CONFIRMED`. Any other 409, a cancelled
  invocation included, is a fault the dispatcher re-raises, because the SDK
  surfaces a cancellation in the same shape and only the message text tells
  them apart. So an order that was placed cannot then be paid for, and a
  payment cannot be repeated, for the same reason a placed order cannot be
  placed again.
- The same holds at the ingress (measured on `restate-server` 1.7.9): a
  repeat call on a completed key is `409 {"code":409,"message":"the
  workflow method was already invoked","source":"invocation"}`, and so is one
  on a key whose invocation is still running — the ingress never attaches a
  second caller. A cancel requested through the admin API while the endpoint
  is unreachable is accepted but stays undelivered (`backing-off`) until the
  handler next runs; a kill completes the invocation as `[409] killed` and the
  waiting creator receives `409 {"code":409,"message":"killed"}`, which the
  dispatcher re-raises. A repeat send is `202 PreviouslyAccepted`.

`RestateInvocationOrderOrchestratorRelay` reads one thing off the message,
`str(confirm_order_request.order.identity)`, for the child's key, and
passes it as it is: inside the engine the key is an argument to the SDK, not a
path segment, so there is nothing to percent-encode. A child's terminal error
reaches the parent as a `restate.TerminalError` carrying the child's status
(`server_context.py` raises `TerminalError(res.message, res.code)` on a failed
call future). The child dispatcher reads exactly one of them, the
already-invoked `409`, and answers `ALREADY_STARTED`; every other status is a
fault and is re-raised. The dispatchers for actions read none at all — an
action that ends terminally ends its workflow, and there is no member for it.

`ts.Relay` in tesser-py is a bare marker protocol, like `ts.Port`. There is
one relay kind and it says nothing about lifetime: a relay protocol names what
*this* context's actions or workflows are, by name, and an implementation may
live as long as the component or as long as one invocation.
`OrderOrchestratorRelay` has one of each, and the orchestrator holding it
cannot tell which it has.

`ProductCatalogRepository` (Postgres, or the in-memory stand-in) stays a
`ts.Port`, because a store is not us.

The distinction is what may cross. A `ts.Client` faces outsiders and a
`ts.Port` faces a foreign system, so both stay primitives-only. A relay is
inward — it has us on both ends, it crosses the engine inside one context, it
is never operated through the client, and Restate pins an invocation to one
deployment — so its messages may carry domain objects and they come back
whole. That is not a widening of the no-outward-representation line; it is the
line applied to a boundary that faces inward.

## Adapters, split by direction and by lifetime

| class | kind declared | direction | lifetime |
|---|---|---|---|
| `RestatePriceProduct`, `RestateTakePayment` (`adapters/activities/restate_activities.py`) | `ts.Activity` | Restate → us: each registers one action's handler (`price_product`, `take_payment`) on the ingress-private `restate.Service` it is handed, keeps it as `self.handler`, and calls the application client's method of that name | process |
| `RestateConfirmOrder`, `RestatePayForOrder` (`adapters/workflows/restate_workflows.py`) | `ts.Workflow` | Restate → us: each registers one workflow's `main` (`confirm_order`, `pay_for_order`) on the `restate.Workflow` it is handed, keeps it as `self.handler`, and builds its orchestrator over that invocation's dispatchers | process (each `main` call lasts one invocation) |
| `RestateInvocationOrderActionsRelay`, `RestateInvocationPurchaseActionsRelay` (`adapters/workflows/restate_workflows.py`, not exported) | `ts.Dispatcher` | us → Restate, from inside an invocation (`ctx.service_call(activity.handler, ...)`) | one invocation |
| `RestateInvocationOrderOrchestratorRelay` (`adapters/workflows/restate_workflows.py`, not exported) | `ts.Dispatcher` | us → Restate, from inside an invocation, to a child workflow (`ctx.workflow_call` to run, `ctx.workflow_send` to start, on `RestateConfirmOrder.handler`) | one invocation |
| `RestateHttpOrderOrchestratorRelay` (`adapters/dispatchers/`) | `ts.Dispatcher` | us → Restate, from outside any invocation (ingress HTTP: `workflow_send` to start, `workflow_call` to run, on `RestateConfirmOrder.handler`) | process |
| `RestateHttpPurchaseOrchestratorRelay` (`adapters/dispatchers/`) | `ts.Dispatcher` | us → Restate, from outside any invocation (ingress HTTP: `workflow_call` on `RestatePayForOrder.handler`) | process |

The activities and workflows are the inbound side, the same role the HTTP
handler plays for `POST /submissions`: the engine's server receives a request,
routes it to a handler, and the handler invokes application code. The
dispatchers are the outbound side, the same role an HTTP client gateway plays,
except that the far end is named by the Python object that registered it. A
dispatcher is constructed with the activity or workflow it calls and passes
that object's `.handler` to the SDK's typed call; the SDK reads the service
name and the handler name off the handler it is given, and serializes through
the serdes bound when the handler was registered. So each container's name is
written once, as a literal in the component (`restate.Service("OrderActions",
...)`), and each handler's name once, as the Python name of the function the
activity or workflow registers. No call site writes either, and the analyzer
checks what the objects carry (TB085): a relay is named for the far side its
dispatchers reach, `run_X`/`start_X` passes the handler `def X`, `run_` waits
and `start_` sends, an activity's handler is reached with `service_*` and a
workflow's with `workflow_*`, each container is named for its far side, and
every registration is reached by some dispatcher.

Both workflows live in one module, and the reason is the child call. The
purchase workflow's in-invocation dispatcher `RestateInvocationOrderOrchestratorRelay`
holds the order workflow's instance, so the module that declares it must name
`RestateConfirmOrder`, and a module may not import a module beside it (TB060).
The HTTP dispatchers each get a module of their own, because they share
nothing and each imports the `workflows` package, not a sibling. Imports go
one way — dispatchers → workflows → activities — because each caller holds
the callee's instance; only an activity imports the application client, and
only a workflow imports the orchestrators.

Each `restate.Service(...)` and `restate.Workflow(...)` also declares a
bounded `InvocationRetryPolicy` — `max_attempts=5`, `on_max_attempts="pause"`.
The engine is a host, and the SDK's policy for an exception that is
not a `TerminalError` is retry from the journal, which is right for a
transient fault and wrong forever for a permanent one. Five attempts then a
pause is an adapter's number with no input from the use case; it is recorded
here as a choice, not read as a design. **It raises the deployment's
discovery floor**: retry-policy fields exist only in discovery protocol v4,
so this endpoint needs `restate-server >= 1.5`, and `srv/http/test_main.py`
asks for `application/vnd.restate.endpointmanifest.v4+json`.

The two actions services are built with `ingress_private=True`. An action is
only ever called from inside a workflow, so nothing that reaches Restate's
ingress should be able to price a product or take a payment around the
services that decide when to. The two workflow containers stay public: the
HTTP dispatchers reach them through the ingress.

**An engine adapter never reads or names the payload.** The order's
fields — `sku`, `cents`, `quantity`, `total_cents` — cross only through the
snapshot, and no activities, workflows, or dispatchers module names one. Three
dispatchers do *construct* a relay response: when the ingress or the SDK
refuses with the engine's already-invoked 409, the dispatcher answers
`ConfirmOrderOutcome.ALREADY_STARTED` (or `PayForOrderOutcome.ALREADY_STARTED`)
directly. That is the adapter fulfilling its protocol, the same as
`MemoryProductCatalogRepository` naming the fields of
`GetProductPriceResponse`; two dispatchers writing the same construction are
two implementations of one relay, not duplicated logic.

The reason tuple is **empty** on that member. The server's refusal text
("the workflow method was already invoked") is the engine's word, not the
application's: the dispatcher keeps it as its recognition test and never
carries it inward. The member *is* the word, and the service and the parent
orchestrator each say it in their own language — "the order was already
started".

Every encoding is still a snapshot beside its message in `relays/`, and the
one payload read left is
`str(<request>.order.identity)` in the three dispatchers that reach a
workflow, for the workflow key Restate requires. Over HTTP the SDK splices
that key into the request path unencoded (`restate/client.py`,
`endpoint += f"/{key}"`), and the id comes from the public body, so the HTTP
dispatchers percent-encode it
(`urllib.parse.quote(key, safe="")`); an `order_id` of `../admin` reaches the
ingress as `/OrderOrchestrator/..%2Fadmin/confirm_order/send`, not as a different route.
`OrderId` refuses `.` and `..`, the two ids percent-encoding leaves alone.

The two workflow mains read the same identity once more, to refuse a body
whose order is not the workflow's key: `confirm_order` and `pay_for_order`
compare `str(<request>.order.identity)` with `restate_workflow_context.key()`
and raise a terminal `400` on a mismatch. Without it, a request sent to the
ingress under key A ran the workflow for another order under A's key.

An `OrderSnapshot` on the way in checks the shape of what it reads before
the constructor sees it: `order_id` and `sku` must be strings and `quantity`
an `int` that is not a `bool`, or the snapshot is refused as a validation
error. The value objects guard their invariants, not their types, so without
that check a list where a `sku` should be builds an `Order` that raises a
`TypeError` later, inside the orchestrator, where Restate would retry it.

## The application kinds, and where each lives

This tree is the worked example for `docs/design-app-service-types.md`:

- `OrderService(ts.ApplicationService)` and `PurchaseService` — the public
  use cases, built once by the component. Every method does the once-only
  work (validate at the door, build the `Order`); `submit_order` starts the
  order orchestrator through `OrderOrchestratorRelay.start_confirm_order`,
  `place_order` runs it through `run_confirm_order`, and `make_order_payment`
  runs the purchase orchestrator through
  `PurchaseOrchestratorRelay.run_pay_for_order`. Two services because
  two relays: a service holds the methods that share its dependencies, so the
  purchase, which holds a different relay, is a second service. What the
  context offers the world is still one `client.OrderingClient` protocol, and
  the component composes the two services behind it (below).
- `OrderOrchestrator(ts.Orchestrator)` and `PurchaseOrchestrator` in
  `application/orchestrators/` — not services. Built per invocation by the
  workflow's `main` handler over that invocation's dispatchers; store nothing
  but them; take the
  relay's own request — reading the `Order` straight off it — and return the
  relay's response. The purchase orchestrator holds two relays:
  `PurchaseActionsRelay` for the payment action, and `OrderOrchestratorRelay` for
  the child workflow.
- `OrderActions(ts.Actions)` and `PurchaseActions` beside the services —
  classes of actions over exactly one port each (`ProductCatalogRepository`,
  `PaymentProcessor`), each method making exactly one call on it. Not on the
  public client: each is reachable only through its own protocol in
  `application/client/` (`OrderingApplicationClient`,
  `PurchaseApplicationClient`) that only an activity imports.

## The component publishes the engine containers, the host mounts them

The component builds the four engine containers, naming each once, then the
activities, the workflows, and the two HTTP dispatchers, each handed what the
one before it built, and composes the two services behind the one client
protocol:

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

        async def make_order_payment(self, make_order_payment_request):
            return await self._purchase_service.make_order_payment(make_order_payment_request)

    def __init__(self, config: Config) -> None:
        ...
        self.order_actions_service: restate.Service = restate.Service(
            "OrderActions", ingress_private=True, invocation_retry_policy=_RETRY_POLICY
        )
        self.purchase_actions_service: restate.Service = restate.Service(
            "PurchaseActions", ingress_private=True, invocation_retry_policy=_RETRY_POLICY
        )
        self.order_orchestrator_workflow: restate.Workflow = restate.Workflow(
            "OrderOrchestrator", invocation_retry_policy=_RETRY_POLICY
        )
        self.purchase_orchestrator_workflow: restate.Workflow = restate.Workflow(
            "PurchaseOrchestrator", invocation_retry_policy=_RETRY_POLICY
        )
        restate_price_product = activities.RestatePriceProduct(
            self.order_actions_service,
            application.OrderActions(self._memory_product_catalog_repository),
        )
        restate_take_payment = activities.RestateTakePayment(
            self.purchase_actions_service,
            application.PurchaseActions(self._memory_payment_processor),
        )
        restate_confirm_order = workflows.RestateConfirmOrder(
            self.order_orchestrator_workflow, restate_price_product
        )
        restate_pay_for_order = workflows.RestatePayForOrder(
            self.purchase_orchestrator_workflow, restate_take_payment, restate_confirm_order
        )
        self.client: client.OrderingClient = Ordering.Client(
            application.OrderService(
                dispatchers.RestateHttpOrderOrchestratorRelay(config.ingress, restate_confirm_order)
            ),
            application.PurchaseService(
                dispatchers.RestateHttpPurchaseOrchestratorRelay(config.ingress, restate_pay_for_order)
            ),
        )
```

`restate_confirm_order` is handed to two places: the purchase workflow, whose
child dispatcher calls it from inside an invocation, and the HTTP dispatcher
behind `OrderService`. Both reach the same registration because they hold the
same object.

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
protocol) by the tail of the path. It takes exactly the four containers the
component publishes, so the host passes those and nothing collects or
flattens anything:

```python
api.mount(
    _RESTATE_DEPLOYMENT_PATH,
    restate.app(
        [
            durable_execution_app.ordering.order_actions_service,
            durable_execution_app.ordering.order_orchestrator_workflow,
            durable_execution_app.ordering.purchase_actions_service,
            durable_execution_app.ordering.purchase_orchestrator_workflow,
        ]
    ),
)
```

`_RESTATE_DEPLOYMENT_PATH` is the path component of the deployment URI the
Restate server registers, `http://<host>/restate`. `srv/http/test_main.py`
boots the real host, reads `/restate/discover`, and asserts the discovered
manifest against the published containers' registrations, so the manifest and the
code cannot drift apart silently.

**This diverges from `srv.md` rule 5 — the route table is the host's.** The
Restate names are declared in the context's component, not at the app edge.
The reason: here the context is its own caller, and the names are an
agreement between the activities and workflows that register handlers and
the dispatchers that call them, both ours.

## What this shape costs, in rules

**A serde is an application kind now.** `tesser/application/serde.py` is its
home, and `tesser.adapters` re-exports it the same direction `Relay` already
travels. That follows from where the encodings live: a snapshot belongs beside
the message it serves, and the messages belong to the relay.

**The analyzer carries the placement rows this shape needs, and not yet the
outcome rows.** `application/relays/` and `application/snapshots/` are
application packages, `ts.Relay` is a kind, a relay message may carry a domain
object, `ts.Serde` is an application kind and a snapshot's body is checked,
`adapters/activities/`, `adapters/workflows/` and `adapters/dispatchers/` are
adapter kind packages holding `ts.Activity`, `ts.Workflow` and `ts.Dispatcher`,
and a component publishes its client and the engine containers it hands an
activity or a workflow. What the outcome-on-response shape costs on top of
that is 71 `# tesser:debt` markers, every one written mechanically by
`tessercheck-mark`, and that list is the analyzer's work list:

- **`TB082`, 52.** Forty-three are in the four relay modules, and they are
  one ask: widen the snapshot's call allowlist. A response snapshot reads an
  outcome (`<Outcome>(snapshot.get("outcome"))`), checks each element of a
  collection (`all(...)` over a comprehension), and rebuilds the collections
  (`tuple(...)`, `list(...)`) — none of which the snapshot rule admits, and
  all of which are shape, not decision. Six are the `match` on a response's
  outcome field in a service or an orchestrator, which the analyzer reads as
  "not a call on a domain object" because a class named `*Outcome` activates
  nothing. Three are in `OrderSnapshot`, which raises and catches to refuse a
  body. The eight engine serdes carried one each for a `try` around the
  snapshot; they went with the old runtime module, because an engine serde now turns only
  the empty body into a terminal 400 and delegates everything else.
- **`TB085`, 4** — on `<Outcome>(snapshot.get("outcome"))`, a call the
  analyzer cannot read a class off.
- **`TB073`, 2.** A test helper that answers a canned wire body rather than a
  spec or a DTO. Moving the same data to a module-level constant trades them
  for `TB071`s, so there is no legal placement in a test module for data that
  is not construction data.
- **`TB023`, 3** — the routes `main` declares; `srv/` is still read.
  **`TB052`, 5** — a plain `enum.Enum` outcome in a relay module, which
  placement rejects today. **`TB062`, 4** — `import enum` in a relay module,
  outside its stdlib allowlist. **`TB081`, 1** —
  `OrderSnapshot.deserialize` answers a domain object.

The activities, workflows and dispatchers carry none: every name a
dispatcher reaches is read off a registered object, so there is nothing for
TB085 to check against a string, and the adapter tests drive the real engine
instead of a hand-written double of it.

Two families went away with `application/ports/engine.py`: six `TB060`, where
an adapter imported `ports` for its engine errors, and eleven `TB070`, where a
test module imported `ports` to name one. Nothing is hidden: the tree is at
zero findings because every finding is named, not because any is absent.

The remaining rule cost of putting an encoding in the application is `json`
and now `enum`: the application stdlib allowlist is `{__future__, typing}`,
`TB062` widens it by exactly `json` in `application/relays/` and
`application/snapshots/`, and the four `enum` imports are the four markers
above — the outcome lives on the response, and the response lives in the
relay.

## Messages are declared once, beside the protocol that speaks them

There are no wire types. Both ends are us, so the send side and the receive
side of one message are not independent boundaries.

- `order_orchestrator_relay.py` holds `ConfirmOrderRequest`,
  `StartConfirmOrderResponse`, and `ConfirmOrderResponse` — the
  orchestrator's input, the start ack, and the orchestrator's result.
  `run_confirm_order` answers with the result; after a start, the engine
  stores it and the ingress hands it back on request.
- `order_actions_relay.py` holds `PriceProductRequest` and
  `PriceProductResponse` — the action's two shapes.
  `application/client/order_actions.py` and `OrderActions` speak the same two.
- `purchase_orchestrator_relay.py` holds `PayForOrderRequest` (the `Order`
  again, now with the `PaymentMethod` the caller named — a purchase is asked
  for with an order and something to charge) and `PayForOrderResponse`, whose
  snapshot checks the outcome, the order id, the purchases and the reasons on
  the way in as the order's does.
- `purchase_actions_relay.py` holds `TakePaymentRequest` and
  `TakePaymentResponse`; `application/client/purchase_actions.py` and
  `PurchaseActions` speak the same two.
- `application/snapshots/order_snapshot.py` holds `OrderSnapshot`, the
  aggregate's canonical form, because two relay messages now carry an `Order`
  and a module in an exporting package may not import the module beside it:
  the encoding both relays share lives in a package both import, and it is
  written once.

**Every wire form is an explicit snapshot beside its message.** Nine in all:
`OrderSnapshot`, plus a request and a response snapshot in each of the four
relay modules. Each is a `ts.Serde` with exactly `serialize` and
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

`ConfirmOrderRequestSnapshot` is the whole of what a workflow start puts
on the wire — the order it carries, and nothing wrapped around it — so the
body `POST /OrderOrchestrator/o1/confirm_order/send` carries is:

```json
{"order_id": "o1", "sku": "widget", "quantity": 2}
```

**A snapshot decides once, and only about shape.** A field only some members
can fill is a tuple of zero or one — `prices`, `confirmed_orders`, `payments`,
`purchases` — and the snapshot checks the shape of the collection and of every
element in it, and stops there. It does **not** check that a `PRICED` response
carries exactly one price: whether the count agrees with the outcome is
consistency between two fields, not shape, and a snapshot that judged it would
be deciding twice. A payload where they disagree becomes an `IndexError` in
the consumer's happy arm, where it reads `xs[0]` — a fault, which is right,
because both ends of this wire are ours and a disagreement there is a bug in
us, not a caller's mistake.

The SDK cannot serialize a `ts.Request` on its own — `restate.serde.DefaultSerde`
handles msgspec Structs, Pydantic models, and dataclasses; anything else falls
through to `json.dumps(obj)` — so each activity or workflow module carries a
compatibility serde for every message its handler moves, eight in all, bound
when the handler is registered. A serde does two things and no more: answer
the SDK's `None`/empty convention, refusing an empty body as a
`restate.TerminalError`, and delegate to the relay's snapshot. A body that
does not exist is not a message: handing `None` to a handler declared over a
message raised an `AttributeError` there, which is not terminal, and Restate
retries a non-terminal failure until the retry policy pauses the invocation.
A body the snapshot cannot read raises from the snapshot. On a handler's
input the SDK wraps anything its input serde raises, the empty-body refusal
included, as a terminal error with status 500 (`invoke_handler` in
`restate/handler.py`), so an unreadable body is not retried. Because the
dispatchers pass the handler to the SDK's typed call, the same serdes encode
the request on the caller's side and decode the response.

```python
class RestatePriceProductRequestSerde(ts.Serde, restate.serde.Serde[relays.PriceProductRequest]):

    def serialize(self, price_product_request: relays.PriceProductRequest | None) -> bytes:
        if price_product_request is None:
            return b""
        return relays.PriceProductRequestSnapshot().serialize(price_product_request)

    def deserialize(self, buf: bytes) -> relays.PriceProductRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PriceProductRequestSnapshot().deserialize(buf)
```

None of them is generic and none of them knows a field. What crosses is decided
in one module — the relay's — and the engine adapter only carries it. A field
added to a message still changes the bytes an in-flight journal already holds;
payload versioning on a durable leg is a rule this tree does not yet make.

## Two failure classes, and nothing else

A **situation** is a business term the caller acts on; the client declares
them and raises them across itself. A **fault** is anything no expert has a
word for; it propagates untyped to the nearest host and is handled nowhere in
domain or application code. `client.Rejected`, `client.Missing`,
`client.Conflict` and `client.Unavailable` were neither — they were HTTP
statuses wearing class names, saying the same nothing at five hops — and they
are gone, with `application/ports/engine.py` and its four engine errors and
with `ports.ChargeDeclined`.

What a caller can be told is now five situations named for what happened:

```python
ERRORS = (OrderRejected, ProductPriceNotFound, OrderNotConfirmed,
          PaymentDeclined, OrderAlreadyStarted)
```

`OrderRejected` is the domain refusing a malformed order at the service door,
carrying the `DomainError`'s own code and message — it is a situation because
the caller can fix it, and it is named for what it is rather than for the 422
it happens to become. The other four are outcome members the service matched
and turned into words.

**An expected alternative from a dependency is an outcome member on the
response, never an exception.** A port or relay declares no errors at all.
Every hop passes its dependency's fact on under its own subject:

| act | outcomes |
|---|---|
| getting the product price | `GetProductPriceOutcome.FOUND / NOT_FOUND` |
| pricing the product | `PriceProductOutcome.PRICED / PRICE_NOT_FOUND` |
| confirming the order | `ConfirmOrderOutcome.CONFIRMED / PRODUCT_PRICE_NOT_FOUND / ALREADY_STARTED` |
| starting to confirm the order | `StartConfirmOrderOutcome.STARTED` |
| charging the payment method | `ChargePaymentMethodOutcome.CHARGED / DECLINED` |
| taking payment | `TakePaymentOutcome.TAKEN / DECLINED` |
| paying for the order | `PayForOrderOutcome.PAID / ORDER_NOT_CONFIRMED / PAYMENT_DECLINED / ALREADY_STARTED` |

Read each member as a sentence after the act. The catalog's `NOT_FOUND`
becomes `PRICE_NOT_FOUND` on the action's response and
`PRODUCT_PRICE_NOT_FOUND` on the child's — one fact keeping one word, gaining
a prefix as the carrier's subject changes — and then the parent summarises its
*own* step as `ORDER_NOT_CONFIRMED`, because the parent observed only that its
confirm step did not complete. A new reason inside `ConfirmOrderOutcome` does
not touch `PayForOrderOutcome`.

`ALREADY_STARTED` is the one kind of member the engine crossing adds. It
exists only on a relay response, only on the `run_` path, and it is produced
by the dispatcher translating the engine's refusal — never by an orchestrator. The
`start_` path has no second member, because a repeat send on an
existing key is accepted again (`202 "PreviouslyAccepted"`) and deduplicated
by the server, so the refusal is unobservable there (measured on
`restate-server` 1.7.2).

`StartConfirmOrderOutcome.STARTED` is a single-member enum for that reason. It
is a member rather than nothing at all so that the day a second way to start
exists, the response already has the field to carry it.

**Everything else is a fault.** A handler has no `except` arm; a dispatcher
has no status-code `match`. Concretely:

- A `TerminalError` from an action's `service_call` propagates. An action that
  ends terminally ends its workflow, and the dispatchers for actions read
  nothing off it.
- On a `run_` call, the child dispatcher and the two HTTP dispatchers recognise
  exactly one refusal: a `409` whose body says `the workflow method was
  already invoked`. That, and only that, is `ALREADY_STARTED`. Any other
  `409` — a cancelled invocation, which the SDK surfaces in the same shape
  and which only the message text tells apart — and every other status is
  re-raised.
- A `restate.HttpError` or an `httpx.TransportError` from the ingress
  propagates. A workflow the ingress cannot reach is not a business fact
  about an order, and calling it `Unavailable` said only that this tree once
  had a 503 to return.
- A success body the response snapshot cannot read is the SDK's decode
  raising, and it propagates too.

The host is where a fault stops. `srv/http/main.py` keeps `protocol.BadRequest
→ 400` and `except Exception → 500`, unchanged, and the ingress being down is
now a `500` where it used to be a `503` — the honest answer, since nothing in
the application claimed to know.

The engine is a host too, and it owns its own fault policy: the
bounded `InvocationRetryPolicy` on each `Service` and `Workflow` described
above. A permanent fault no longer replays forever; it is retried five times
and the invocation is paused.

**The handler's exhaustive match is the one place a situation becomes a
status.** `adapters/handlers/http.py` maps each of the five and closes on
`assert_never`, so adding a situation fails every host's match loudly:

| situation | status |
|---|---|
| `OrderRejected` | 422 |
| `ProductPriceNotFound` | 422 |
| `OrderNotConfirmed` | 422 |
| `PaymentDeclined` | 409 |
| `OrderAlreadyStarted` | 409 |

The word never implies the status. `ProductPriceNotFound` is 422 on
`POST /purchases`, where the body named an unknown product, and would be 404
on a `GET` for that product's price. The route decides, and a CLI host would
map the same five situations to exit codes.

**The synchronous run path is bounded.** `_RUN_TIMEOUT` was
`httpx.Timeout(5.0, read=None)`, which handed the caller's connection to the
engine's own policy with no end. It is now
`httpx.Timeout(5.0, read=30.0)` in both HTTP dispatchers. Thirty seconds is an
adapter's number with no input from the use case — recorded as a choice, not
read as a design. A workflow slower than that raises a
`httpx.ReadTimeout` at the door, which is a fault and a `500`; the real bound
belongs at the ingress or in the workflow, where a timed-out caller can still
attach to the result, and this tree still makes neither rule.

## Tests, and what the engine is asked to show

Every payload is pinned once, in the four `relays/test_*_relay.py` modules,
where the snapshots are defined — including the count check: a `PRICED`
response that carries no price and a `PRICE_NOT_FOUND` that carries one are
both refused. `ordering/component/test_component.py` and
`srv/http/test_main.py` assert the four containers, their names, their
handlers, that each declares the bounded retry policy, and that only the two
workflows face the ingress.

The activities, workflows, and dispatchers are tested against the real engine
(`testing.md` rule 10: an adapter's dependency is exercised, not doubled).
Each test builds the objects it tests over containers named with a fresh
`uuid4` suffix, serves them on a port of its own with hypercorn, registers
that endpoint with the Restate admin API at `DURABLE_CALLBACK_HOST`, calls
through the ingress with the objects' `.handler`s or the dispatcher under
test, reads what the engine recorded in `sys_invocation`, and removes the
deployment. The fresh names keep a test's rows apart from every earlier run on
a shared server, and they keep its registration apart from the app the arm
serves for the root-tier tests. The test-side containers are not
ingress-private, which is what lets the activities test call an action
through the ingress at all. What each test asks the engine to show is the one
thing the tests around it cannot see: that Restate is really in the path
doing the durable work. A workflow that called the application client
in-process would answer the same bytes and pass the acceptance test
unchanged. The fakes are of the application clients, the tree's own
protocols; nothing stands in for Restate.

- The activities test calls each action's handler through Restate and
  asserts that the request reached the application client and the answer came
  back through the serdes. Two more lock in what the engine refuses: a
  non-empty body the snapshot cannot read comes back as a terminal `500
  Unable to parse an input argument` (the SDK wraps the input serde's error),
  and a call through the ingress to an `ingress_private=True` actions service
  is refused with `400 the invoked service is not public`.
- The workflows test runs whole invocations. `confirm_order` records one
  `OrderActions…/price_product` row invoked by the order workflow;
  `pay_for_order` records the child `OrderOrchestrator…/<id>/confirm_order`
  keyed by the order's id exactly as it is (an id of `../admin?x=1#f-…`,
  because inside the engine the key is an argument, not a path segment) and
  then the `PurchaseActions…/take_payment` row. A not-found price and a
  declined charge end as outcomes; a purchase whose order was not confirmed,
  or whose order workflow already ran (the child-side already-invoked `409`,
  exercised for real), takes no payment.
- The dispatchers tests assert the row the engine keyed by the order's id,
  invoked by `ingress`, once the engine reports it completed — so forgetting
  the key, keying by the wrong field, or targeting the wrong workflow all
  show. The hostile id reaches the row as exactly that key, which is the
  percent-encoding proven from the engine's side. A repeat send leaves one
  row; a repeat run answers `ALREADY_STARTED`.

What the engine cannot be made to say from a sibling test is not asserted
there. A refusal that is not the already-invoked wording — a `409` saying
`killed` or `cancelled` — reaches only the caller that created the invocation
and only while its endpoint is unreachable, which the arm's own host cannot
arrange mid-suite; it was measured instead (below). And a body no Restate
server sends — a `409` that is not JSON, a `200` that is not the workflow's
result — is a conversation this adapter does not have, so no test provokes
one through a stand-in. The unreachable-ingress tests remain: a closed socket
is an absence, not a double.

## Async everywhere the SDK is

The SDK is async on both sides, so the request path is `async`: the four
relay protocols, `OrderService`, the three `OrderingClient` methods, the HTTP
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
the deployment and clients `POST :8080/OrderOrchestrator/o1/confirm_order` directly,
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
curl -X POST localhost:8000/purchases \
  --json '{"order_id":"p1","sku":"gadget","quantity":2,"payment_method":"card-4242"}'
                          # 200 {"order_id": "p1", "total_cents": 2000, "payment_reference": "pay-p1"}
curl localhost:18080/restate/workflow/OrderOrchestrator/p1/output
                                   # the child's ConfirmOrderResponse, by its own key
curl -X POST localhost:8000/orders --json '{"order_id":"p1","sku":"gadget","quantity":2}'
                                                    # 409 the child key is taken: p1 was paid for
curl -X POST localhost:8000/purchases \
  --json '{"order_id":"o2","sku":"gadget","quantity":3,"payment_method":"card-4242"}'
                                              # 422 o2 was placed above, so the child refuses
```

The failure arms answer at the front door, from the five situations the
client declares and the one category the host owns:

```
curl -X POST localhost:8000/orders --json '{"order_id":"o3"}'
   # 400 {"detail": "sku must be a string"}                        protocol.BadRequest
curl -X POST localhost:8000/orders --json '{"order_id":"o3","sku":"gadget","quantity":0}'
   # 422 {"detail": "an order is for at least one unit"}           client.OrderRejected
   #     with the ingress down, a well-formed order is 500: the engine being
   #     unreachable is a fault, and nothing in the application has a word for it
curl -X POST localhost:8000/orders --json '{"order_id":"o4","sku":"nope","quantity":1}'
   # 422 {"detail": "no price for sku 'nope'"}                     client.ProductPriceNotFound
curl -X POST localhost:8000/orders --json '{"order_id":"o2","sku":"gadget","quantity":3}'
   # 409 {"detail": "the workflow method was already invoked"}     client.OrderAlreadyStarted
curl -X POST localhost:8000/purchases \
  --json '{"order_id":"p2","sku":"gadget","quantity":1,"payment_method":"declined"}'
   # 409 {"detail": "the processor declined the charge for order 'p2'"}
   #                                                               client.PaymentDeclined
```

A product whose price the catalog does not hold no longer ends the workflow
terminally. `OrderActions.price_product` answers `PRICE_NOT_FOUND`, the child
answers `PRODUCT_PRICE_NOT_FOUND`, the workflow ends **successfully** with
that outcome, and the service turns it into `client.ProductPriceNotFound`. So
`/restate/workflow/OrderOrchestrator/o4/output` answers `200` with the
response the child wrote, and the reason is in it — a business fact, stored
and readable, rather than a `404` stashed in an error field.

**SIGTERM belongs to the SDK.** `restate.app` installs its own `SIGTERM`
handler on the first request, replacing hypercorn's: to Restate, SIGTERM
means drain the in-flight invocations. The host stops on SIGINT; the srv test
sends SIGINT.

## Production boundaries this example does not cross

- The catalog is an in-memory repository seeded with two SKUs; a second
  replica would not share it, which is fine only because the lookup is
  read-only. The payment processor is an in-memory ledger keyed by order,
  idempotent for an identical repeat; a real one is a vendor behind the same
  `PaymentProcessor` port, and that port is synchronous like the catalog's.
  A vendor call inside the action handler would block hypercorn's one event
  loop, which serves the public API and the `/restate` return leg of every
  in-flight invocation; a real processor makes the port async, which this
  tree has not done.
- A purchase has no compensation. If the payment is declined after the child
  order ran, the order stays confirmed and unpaid; the workflow ends
  `PAYMENT_DECLINED` and nothing undoes the child. The same holds when the
  payment *succeeded* and the domain then refused it (`payment_mismatch`,
  `payment_for_another_order`): the money is taken, and there is no outcome
  member for it — the domain's refusal is a fault, a `500` at the door and a
  paused invocation in the engine. Compensating only the steps that ran is the
  checkout scenario, and "checkout" as the parent act's name waits for it;
  until then the parent stays `pay_for_order`.
- The three doors share one key namespace. `POST /orders`,
  `POST /submissions`, and the purchase's child all run `OrderOrchestrator`
  under the caller-chosen order id, so an order placed or submitted first can
  never be purchased, and a purchased order can never be placed again, and
  any caller can take a key first. That is what "one business act done to one
  order" costs when ids are chosen by the caller with no authentication.
- A parent cannot attach to a child that already ran. `ctx.workflow_call` on
  a taken key is a terminal `409`, so a purchase of an order that was placed
  is refused rather than priced from the stored result; a parent that wanted
  the stored result would need the SDK's attach, which this tree does not
  use.
- `start_confirm_order` fires and forgets; `POST /submissions` never waits on
  the workflow. A submitted order's total is read back through Restate's
  ingress, because the API has no read route of its own; `POST /orders` is the
  route for a caller who wants the total in the response.
- `POST /orders` holds the caller's connection for up to the dispatcher's
  thirty-second read timeout, and has no deadline of its own and no cap on how
  many may wait at once; a burst of slow workflows holds that many connections
  open in this process, and a workflow that outruns the bound answers `500`
  while it keeps running. The real bound belongs at the ingress or in the
  workflow, where a caller who gave up can still attach to the result; this
  tree makes neither rule.
- A handler's registered name is part of the deployment, and this change
  renamed two of them: `OrderOrchestrator/run` became
  `OrderOrchestrator/confirm_order` and `PurchaseOrchestrator/run` became
  `PurchaseOrchestrator/pay_for_order`. To Restate that is a different
  service: re-register the deployment after upgrading, and an invocation
  journaled against the old name has no handler to replay against on the new
  one. Every relay message changed shape in the same breath — an outcome
  field, a tuple of records, a reasons tuple, a `payment_method` — so an
  in-flight journal written by the previous shape fails its count check on
  replay. A change to an outcome *set* is the same boundary, for the same
  reason. This tree has no deployments, so it renames freely; a real one
  keeps the old handler through a migration window or deploys the new version
  at its own endpoint and drains the old.
- The component can wire exactly one engine: the host mounts the four Restate
  containers it publishes. A second engine (an in-process one, or Temporal)
  would implement the same four relay protocols with dispatchers of its own
  over registrations of its own, and the component would have to publish
  those too.
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
