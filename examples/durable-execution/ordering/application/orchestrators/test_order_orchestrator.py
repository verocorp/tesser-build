from __future__ import annotations

import asyncio
import collections.abc as abc
import typing

import tesser.testing as ts

import ordering.application.orchestrators.order_orchestrator as order_orchestrator
import ordering.application.ports.order_workflow as order_workflow
import ordering.application.ports.quoting as quoting


@ts.fake
class FakeJobContext(ts.JobContext):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I
    ) -> O:
        return await step(None, request)


@ts.fake
class FakeQuoting(quoting.Quoting):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    async def quote(self, job: ts.JobContext, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        self.quoted.append(request.sku)
        return quoting.QuoteResponse(cents=250)


@ts.helper
def start_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 3
) -> order_workflow.StartRequest:
    return order_workflow.StartRequest(order_id=order_id, sku=sku, quantity=quantity)


class TestOrderOrchestrator:

    def test_running_totals_the_quoted_price_over_the_quantity(self) -> None:
        orchestrator = order_orchestrator.OrderOrchestrator(FakeJobContext(), FakeQuoting())
        ran = asyncio.run(orchestrator.run(start_request()))
        assert ran.order_id == "o1"
        assert ran.total_cents == 750

    def test_running_quotes_the_ordered_sku(self) -> None:
        quotes = FakeQuoting()
        asyncio.run(
            order_orchestrator.OrderOrchestrator(FakeJobContext(), quotes).run(start_request(sku="gadget"))
        )
        assert quotes.quoted == ["gadget"]
