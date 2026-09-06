from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application.orchestrators as orchestrators
import ordering.application.relays as relays  # tesser:debt TB070
import ordering.domain as domain


@ts.fake
class FakeOrderActionsRunner(relays.OrderActionsRunner):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    async def run_prepare_quote(
        self, prepare_quote_request: relays.PrepareQuoteRequest
    ) -> relays.PrepareQuoteResponse:
        self.quoted.append(prepare_quote_request.sku)
        return relays.PrepareQuoteResponse(cents=250)


@ts.helper
def order_orchestrator_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 3
) -> relays.OrderOrchestratorRequest:
    return relays.OrderOrchestratorRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestOrderOrchestrator:

    def test_running_totals_the_quoted_price_over_the_quantity(self) -> None:
        order_orchestrator_response = asyncio.run(
            orchestrators.OrderOrchestrator(FakeOrderActionsRunner()).run(
                order_orchestrator_request()
            )
        )
        assert order_orchestrator_response.order_id == "o1"
        assert order_orchestrator_response.total_cents == 750

    def test_running_prepares_a_quote_for_the_ordered_sku(self) -> None:
        fake_order_actions_runner = FakeOrderActionsRunner()
        asyncio.run(
            orchestrators.OrderOrchestrator(fake_order_actions_runner).run(
                order_orchestrator_request(sku="gadget")
            )
        )
        assert fake_order_actions_runner.quoted == ["gadget"]
