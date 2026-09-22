from __future__ import annotations

import contextlib
import typing

import tesser.adapters as ts
import restate

import ordering.application.orchestrators as orchestrators
import ordering.application.relays as relays


class RestateInvocationOrderActionsRelay(ts.Runner):

    def __init__(self, restate_workflow_context: restate.WorkflowContext) -> None:
        self._restate_workflow_context = restate_workflow_context

    async def run_price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return relays.PriceProductResponseSnapshot().deserialize(
            await self._restate_workflow_context.generic_call(
                "OrderActions",
                "price_product",
                relays.PriceProductRequestSnapshot().serialize(price_product_request),
            )
        )


class RestateOrderWorkflow(ts.Runner):

    @contextlib.asynccontextmanager
    async def invocation(
        self, restate_workflow_context: restate.WorkflowContext
    ) -> typing.AsyncIterator[orchestrators.OrderOrchestrator]:
        yield orchestrators.OrderOrchestrator(
            RestateInvocationOrderActionsRelay(restate_workflow_context)
        )
