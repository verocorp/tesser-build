from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application.orchestrators.order_orchestrator as order_orchestrator
import ordering.application.ports.order_actions as order_actions
import ordering.application.ports.order_workflow as order_workflow


@ts.fake
class FakeOrderActions(order_actions.OrderActions):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    async def quote(self, request: order_actions.QuoteRequest) -> order_actions.QuoteResponse:
        self.quoted.append(request.sku)
        return order_actions.QuoteResponse(cents=250)


@ts.helper
def start_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 3
) -> order_workflow.StartRequest:
    return order_workflow.StartRequest(order_id=order_id, sku=sku, quantity=quantity)


class TestOrderOrchestrator:

    def test_running_totals_the_quoted_price_over_the_quantity(self) -> None:
        orchestrator = order_orchestrator.OrderOrchestrator(FakeOrderActions())
        ran = asyncio.run(orchestrator.run(start_request()))
        assert ran.order_id == "o1"
        assert ran.total_cents == 750

    def test_running_quotes_the_ordered_sku(self) -> None:
        actions = FakeOrderActions()
        asyncio.run(order_orchestrator.OrderOrchestrator(actions).run(start_request(sku="gadget")))
        assert actions.quoted == ["gadget"]
