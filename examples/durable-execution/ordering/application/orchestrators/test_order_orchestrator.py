from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application.orchestrators.order_orchestrator as order_orchestrator
import ordering.application.relays.order_job_context as order_job_context
import ordering.application.relays.order_relay as order_relay
import ordering.domain.order as order


@ts.fake
class FakeOrderJobContext(order_job_context.OrderJobContext):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    async def quote(
        self, request: order_job_context.QuoteRequest
    ) -> order_job_context.QuoteResponse:
        self.quoted.append(request.sku)
        return order_job_context.QuoteResponse(cents=250)


@ts.helper
def start_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 3
) -> order_relay.StartRequest:
    return order_relay.StartRequest(
        order=order.Order(order.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestOrderOrchestrator:

    def test_running_totals_the_quoted_price_over_the_quantity(self) -> None:
        orchestrator = order_orchestrator.OrderOrchestrator(FakeOrderJobContext())
        ran = asyncio.run(orchestrator.run(start_request()))
        assert ran.order_id == "o1"
        assert ran.total_cents == 750

    def test_running_quotes_the_ordered_sku(self) -> None:
        job = FakeOrderJobContext()
        asyncio.run(order_orchestrator.OrderOrchestrator(job).run(start_request(sku="gadget")))
        assert job.quoted == ["gadget"]
