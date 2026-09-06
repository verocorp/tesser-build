from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application.orchestrators.order_orchestrator as order_orchestrator
import ordering.application.relays.order_relay as order_relay
import ordering.domain.order as order


@ts.fake
class FakeOrderRelay(order_relay.OrderRelay):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    async def start(self, request: order_relay.StartRequest) -> order_relay.StartResponse:
        return order_relay.StartResponse(order_id=str(request.order.identity))

    async def quote(self, request: order_relay.QuoteRequest) -> order_relay.QuoteResponse:
        self.quoted.append(request.sku)
        return order_relay.QuoteResponse(cents=250)


@ts.helper
def start_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 3
) -> order_relay.StartRequest:
    return order_relay.StartRequest(
        order=order.Order(order.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestOrderOrchestrator:

    def test_running_totals_the_quoted_price_over_the_quantity(self) -> None:
        orchestrator = order_orchestrator.OrderOrchestrator(FakeOrderRelay())
        ran = asyncio.run(orchestrator.run(start_request()))
        assert ran.order_id == "o1"
        assert ran.total_cents == 750

    def test_running_quotes_the_ordered_sku(self) -> None:
        relay = FakeOrderRelay()
        asyncio.run(order_orchestrator.OrderOrchestrator(relay).run(start_request(sku="gadget")))
        assert relay.quoted == ["gadget"]
