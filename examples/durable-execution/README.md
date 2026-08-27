# durable-execution — one context whose workflow runs on Restate

The chain, top to bottom, with where each link lives:

| Step | Placement | Code |
|---|---|---|
| a CLI host places an order | `srv/cli/main.py` | `CliHost` → `ordering/adapters/handlers/cli.py` |
| the initial application service | `ordering/application/order_service.py` | `OrderService.place` builds the `Order` aggregate |
| it starts the workflow through a port | `ordering/application/ports/order_workflow.py` | `OrderWorkflow.start(StartRequest) -> StartResponse` |
| the Restate SDK sends the workflow | `ordering/adapters/gateways/restate_workflow.py` | `RestateOrderWorkflow.start` → `RestateIngress.send` → `client.generic_send(WORKFLOW, RUN, body, key=order_id)` |
| Restate's server calls the workflow handler | `srv/restate/main.py` | `RestateHost` mounts `@workflow.main()` → `ordering/adapters/handlers/restate.py` `WorkflowHandler.run` |
| the orchestrator | `ordering/application/order_orchestrator.py` | `OrderOrchestrator.run` builds the `Order`, asks for a quote |
| it runs the action through a port | `ordering/application/ports/quotes.py` | `Quotes.quote(QuoteRequest) -> QuoteResponse` (async) |
| the Restate SDK calls the action | `ordering/adapters/gateways/restate_quotes.py` | `RestateQuotes.quote` → `ctx.generic_call(ACTIONS, QUOTE, body)` |
| Restate's server calls the action handler | `srv/restate/main.py` | `@actions.handler()` → `ActionHandler.quote` |
| the action, an application service with a repository lookup | `ordering/application/order_actions.py` | `OrderActions.quote` → `CatalogRepository.price` → `adapters/repositories/memory.py` |
| the price comes back up the same chain | | `QuoteResponse.cents` → `Order.total(PriceSpec)` → `RunResponse.total_cents` ends the workflow |

Restate never touches the domain. Every value that crosses into the engine
is a port DTO turned into JSON bytes by a gateway, and every value that
comes out of it is JSON bytes turned into a protocol record by the host and
into a client DTO by a handler (`protocol/durable.py`). The domain
(`ordering/domain/order.py`) imports nothing but `tesser.domain`.

## The two things Restate needs that the rules had to place

**The durable context is bound per invocation, not wired once.** A Restate
handler is handed a `WorkflowContext`, and only calls made through it are
journaled. The orchestrator's port is wired once, at composition time, so
the gateway that implements it (`RestateQuotes`) holds a `contextvars.ContextVar`
and the host binds `ctx.generic_call` into it at the top of each invocation
(`built.ordering.quotes.bind(ctx.generic_call)`). The component exposes the
gateway as `Ordering.quotes` for exactly that reason; the host reaches it at
runtime the way it reaches `Ordering.client`, without importing an adapter.
The gateway takes the call as a plain `Callable[[str, str, bytes], Awaitable[bytes]]`
rather than the SDK's context class, so its sibling test binds a nested
coroutine and never needs a double of a foreign ABC.

**The action is a second Restate service, not `ctx.run`.** `ctx.run_typed`
would journal an in-process closure — the simplest durable step. This
example calls the action through `ctx.generic_call` to a separate service
(`OrderingActions/quote`) because that is the shape a Temporal activity has
(registered separately, dispatched by the engine, reached by name), and the
example exists to show the same context mounted on either engine. The
Temporal mirror is the next increment.

## Names cross the tree twice, on purpose

`WORKFLOW`/`RUN` and `ACTIONS`/`QUOTE` are declared in the gateway that
addresses them (outbound) and in `srv/restate/main.py` (the route table). A
gateway cannot import `srv` or `protocol` (TB063/TB066), and the host cannot
import a gateway, so the names are the same kind of shared knowledge as a URL
an HTTP gateway posts to. `srv/restate/test_main.py` boots the real host and
reads its `/discover` manifest, which is where a drift would surface.

## Async where the engine owns the loop, sync where it does not

The workflow side (`Quotes`, `Orchestrator`, `RestateQuotes`, `WorkflowHandler`)
is `async` because Restate runs the handler on its event loop and every
journaled call is awaited. The ingress side (`OrderWorkflow`, `OrderService`)
is sync: the CLI process has no loop, so `RestateOrderWorkflow.start` runs
the SDK's async ingress client under `asyncio.run`.

## Running it

```
pip install -r requirements-dev.txt
restate-server &                                      # https://restate.dev
PYTHONPATH=.:../../tesser-py RESTATE_INGRESS=http://localhost:8080 \
  python -m srv.restate.main 127.0.0.1:9080 &        # the workflow + action host
restate deployments register http://localhost:9080
PYTHONPATH=.:../../tesser-py RESTATE_INGRESS=http://localhost:8080 \
  python -m srv.cli.main o1 gadget 2                  # places the order, starts the workflow
curl localhost:8080/restate/workflow/Ordering/o1/output # {"order_id": "o1", "total_cents": 2000}
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
- Errors: a `DomainError` or a `BadInvocation` in a handler becomes a
  `TerminalError` (no retry) with the kind's status; anything else propagates
  and Restate retries the invocation.
