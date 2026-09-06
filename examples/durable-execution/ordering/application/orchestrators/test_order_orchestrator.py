from __future__ import annotations

import asyncio
import collections.abc as abc
import typing

import tesser.testing as ts

import ordering.application.orchestrators as orchestrators
import ordering.application.ports as ports


@ts.fake
class FakeJobContext(ts.JobContext):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I
    ) -> O:
        return await step(None, request)


@ts.fake
class FakeQuoting(ports.Quoting):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    async def quote(
        self, job_context: ts.JobContext, quote_request: ports.QuoteRequest
    ) -> ports.QuoteResponse:
        self.quoted.append(quote_request.sku)
        return ports.QuoteResponse(cents=250)


@ts.helper
def start_request(order_id: str = "o1", sku: str = "widget", quantity: int = 3) -> ports.StartRequest:
    return ports.StartRequest(order_id=order_id, sku=sku, quantity=quantity)


class TestOrderOrchestrator:

    def test_running_totals_the_quoted_price_over_the_quantity(self) -> None:
        order_orchestrator = orchestrators.OrderOrchestrator(FakeJobContext(), FakeQuoting())
        run_response = asyncio.run(order_orchestrator.run(start_request()))
        assert run_response.order_id == "o1"
        assert run_response.total_cents == 750

    def test_running_quotes_the_ordered_sku(self) -> None:
        fake_quoting = FakeQuoting()
        asyncio.run(
            orchestrators.OrderOrchestrator(FakeJobContext(), fake_quoting).run(
                start_request(sku="gadget")
            )
        )
        assert fake_quoting.quoted == ["gadget"]
