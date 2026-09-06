from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application as application
import ordering.application.relays as relays
import ordering.client as client


@ts.fake
class FakeOrderOrchestratorRunner(relays.OrderOrchestratorRunner):  # tesser:debt TB072

    def __init__(self) -> None:
        self.started: list[relays.OrderOrchestratorRequest] = []

    async def start_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.StartOrderOrchestratorResponse:
        self.started.append(order_orchestrator_request)
        return relays.StartOrderOrchestratorResponse(
            order_id=str(order_orchestrator_request.order.identity)
        )


@ts.helper
def place_order_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2, note: str = "gift"
) -> client.PlaceOrderRequest:
    return client.PlaceOrderRequest(order_id=order_id, sku=sku, quantity=quantity, note=note)


class TestOrderService:

    def test_placing_answers_the_order_id(self) -> None:
        place_order_response = asyncio.run(
            application.OrderService(FakeOrderOrchestratorRunner()).place_order(
                place_order_request()
            )
        )
        assert place_order_response.order_id == "o1"

    def test_placing_starts_the_orchestrator_for_the_order_it_built(self) -> None:
        fake_order_orchestrator_runner = FakeOrderOrchestratorRunner()  # tesser:debt TB085
        asyncio.run(
            application.OrderService(fake_order_orchestrator_runner).place_order(
                place_order_request(order_id="o2", sku="gadget", quantity=3, note="fragile")
            )
        )
        assert [
            (str(s.order.identity), str(s.order.sku), int(s.order.quantity), str(s.order.note))
            for s in fake_order_orchestrator_runner.started
        ] == [("o2", "gadget", 3, "fragile")]
