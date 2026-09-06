from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application as application
import ordering.application.ports as ports
import ordering.client as client


@ts.fake
class FakeOrderWorkflow(ports.OrderWorkflow):

    def __init__(self) -> None:
        self.started: list[ports.StartRequest] = []

    async def start(self, start_request: ports.StartRequest) -> ports.StartResponse:
        self.started.append(start_request)
        return ports.StartResponse(order_id=start_request.order_id)


@ts.helper
def place_request(order_id: str = "o1", sku: str = "widget", quantity: int = 2) -> client.PlaceRequest:
    return client.PlaceRequest(order_id=order_id, sku=sku, quantity=quantity)


class TestOrderService:

    def test_placing_answers_the_order_id(self) -> None:
        order_service = application.OrderService(FakeOrderWorkflow())
        place_response = asyncio.run(order_service.place(place_request()))
        assert place_response.order_id == "o1"

    def test_placing_starts_the_workflow_for_the_order(self) -> None:
        fake_order_workflow = FakeOrderWorkflow()
        asyncio.run(
            application.OrderService(fake_order_workflow).place(
                place_request(order_id="o2", sku="gadget", quantity=3)
            )
        )
        assert [(s.order_id, s.sku, s.quantity) for s in fake_order_workflow.started] == [
            ("o2", "gadget", 3)
        ]
