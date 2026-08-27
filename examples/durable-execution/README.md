# durable-execution — one context whose workflow runs on Restate

The chain, top to bottom, with where each link lives:

| Step | Placement | Code |
|---|---|---|
| a CLI host places an order | `srv/cli/main.py` | `CliHost` → `ordering/adapters/handlers/cli.py` |
| the initial application service | `ordering/application/order_service.py` | `OrderService.place` builds the `Order` aggregate |
| it starts the workflow through a port | `ordering/application/ports/order_workflow.py` | `OrderWorkflow.start(StartRequest) -> StartResponse` |
| the Restate SDK sends the workflow | `ordering/adapters/gateways/restate_workflow.py` | `RestateOrderWorkflow.start` → `RestateIngress.send` → `client.generic_send(WORKFLOW, RUN, body, key=order_id)` |
| Restate's server calls the workflow handler | `srv/restate/main.py` | `RestateHost` mounts `@workflow.main()` → `ordering/adapters/handlers/restate.py` `WorkflowHandler.run` |
| the orchestrator | `ordering/application/order_orchestrator.py` | `OrderOrchestrator.run` builds the `Order`, prices it through a port |
| the port call is a journaled step | `ordering/adapters/repositories/restate.py` | `RestateCatalogRepository.price` runs the real repository inside `ctx.run_typed("price", …)` |
| the real lookup | `ordering/adapters/repositories/memory.py` | `MemoryCatalogRepository.price` |
| the price comes back and ends the workflow | | `PriceResponse.cents` → `Order.total(PriceSpec)` → `RunResponse.total_cents` |

Restate never touches the domain, and the application never touches Restate.
`OrderOrchestrator` depends on `CatalogRepository`, nothing else; what makes
its call durable is which implementation of that port it was handed.

## What the engine is, in this anatomy

A durable-execution engine is two things at once, and both already have a
placement:

- **Inbound, it is a host.** Restate's server calls `RestateHost`, which
  routes to a handler like any other host (`srv.md`). `BytesSerde` on both
  sides keeps the body opaque bytes so the handler owns content.
- **Outbound, it is an adapter over a port.** Starting the workflow is a
  gateway (`RestateOrderWorkflow`) over the `OrderWorkflow` port. Making a
  step durable is a *wrapping* adapter: `RestateCatalogRepository`
  implements `CatalogRepository` by running another `CatalogRepository`
  inside `ctx.run_typed`, and owns turning the port DTO into the journaled
  bytes and back (`serialization.md` rule 9 — the engine's payload converter
  serializes port DTOs, in the adapter). A domain error inside the step is
  journaled as a *result* and raised again on the way out, so a replay
  reproduces it without re-running the lookup; anything else raises out of
  the step and Restate retries it.

What the engine adds that the anatomy did not have is **an invocation
scope**: `ctx` exists only for the length of one handler call, and every
journaled step must go through it. So the component hands out an
invocation-scoped client — `Ordering.workflow(run)` returns an
`Orchestrator` wired with a fresh `RestateCatalogRepository` — and the host
calls it at the top of each invocation with `ctx.run_typed` adapted to a
plain `Callable[[str, Callable[[], Coroutine[..., bytes]]], Awaitable[bytes]]`.
Nothing is bound into a once-wired object, and the adapter's tests hand in
a nested coroutine instead of doubling the SDK's context class.

## The one address that crosses the tree

`WORKFLOW`/`RUN` (`Ordering`/`run`) are declared in the gateway that sends
to them and in `srv/restate/main.py`'s route table. That leg is a genuine
cross-process wire — the CLI process asks Restate to invoke the host process
— so the name is the same kind of shared fact as a URL an HTTP gateway posts
to. A gateway cannot import `srv` (TB063) or `protocol` (TB066), so the SDK's
typed path (`client.workflow_send(handler_fn, …)`, which derives the names
from the decorated handler object) is out of reach from the gateway; the
srv test boots the real host and reads `/discover`, which is where a drift
would surface. There is no second address: the durable step is in-process.

## Async where the engine owns the loop, sync where it does not

The workflow side (`CatalogRepository`, `Orchestrator`, `WorkflowHandler`)
is `async` because Restate runs the handler on its event loop and every
journaled call is awaited. The ingress side (`OrderWorkflow`, `OrderService`)
is sync: the CLI process has no loop, so `RestateOrderWorkflow.start` runs
the SDK's async ingress client under `asyncio.run`.

## Running it

```
pip install -r requirements-dev.txt
docker run -d --name restate -p 18080:8080 -p 19070:9070 docker.io/restatedev/restate:latest
PYTHONPATH=.:../../tesser-py RESTATE_INGRESS=http://localhost:18080 \
  python -m srv.restate.main 0.0.0.0:9080 &                     # the workflow host
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
- The Temporal mirror is the next increment: the same context, a second
  host, `client.ExecuteWorkflow` behind `OrderWorkflow`, and a
  `TemporalCatalogRepository` whose step is an activity.
