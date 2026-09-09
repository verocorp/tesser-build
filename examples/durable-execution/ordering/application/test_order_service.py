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
        self.ran: list[relays.OrderOrchestratorRequest] = []

    async def start_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.StartOrderOrchestratorResponse:
        self.started.append(order_orchestrator_request)
        return relays.StartOrderOrchestratorResponse(
            order_id=str(order_orchestrator_request.order.identity)
        )

    async def run_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.OrderOrchestratorResponse:
        self.ran.append(order_orchestrator_request)
        return relays.OrderOrchestratorResponse(
            order_id=str(order_orchestrator_request.order.identity),
            total_cents=250 * int(order_orchestrator_request.order.quantity),
        )


@ts.helper
def submit_order_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> client.SubmitOrderRequest:
    return client.SubmitOrderRequest(order_id=order_id, sku=sku, quantity=quantity)


@ts.helper
def place_order_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> client.PlaceOrderRequest:
    return client.PlaceOrderRequest(order_id=order_id, sku=sku, quantity=quantity)


class TestOrderService:

    def test_submitting_answers_the_order_id(self) -> None:
        submit_order_response = asyncio.run(
            application.OrderService(FakeOrderOrchestratorRunner()).submit_order(
                submit_order_request()
            )
        )
        assert submit_order_response.order_id == "o1"

    def test_submitting_starts_the_orchestrator_for_the_order_it_built(self) -> None:
        fake_order_orchestrator_runner = FakeOrderOrchestratorRunner()  # tesser:debt TB085
        asyncio.run(
            application.OrderService(fake_order_orchestrator_runner).submit_order(
                submit_order_request(order_id="o2", sku="gadget", quantity=3)
            )
        )
        assert [
            (str(s.order.identity), str(s.order.sku), int(s.order.quantity))
            for s in fake_order_orchestrator_runner.started
        ] == [("o2", "gadget", 3)]

    def test_placing_answers_the_order_id_and_the_total(self) -> None:
        place_order_response = asyncio.run(
            application.OrderService(FakeOrderOrchestratorRunner()).place_order(
                place_order_request(quantity=3)
            )
        )
        assert place_order_response.order_id == "o1"
        assert place_order_response.total_cents == 750

    def test_placing_runs_the_orchestrator_for_the_order_it_built_and_waits(self) -> None:
        fake_order_orchestrator_runner = FakeOrderOrchestratorRunner()  # tesser:debt TB085
        asyncio.run(
            application.OrderService(fake_order_orchestrator_runner).place_order(
                place_order_request(order_id="o2", sku="gadget", quantity=3)
            )
        )
        assert [
            (str(r.order.identity), str(r.order.sku), int(r.order.quantity))
            for r in fake_order_orchestrator_runner.ran
        ] == [("o2", "gadget", 3)]
        assert fake_order_orchestrator_runner.started == []
