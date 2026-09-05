from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application.order_service as order_service
import ordering.application.ports.order_workflow as order_workflow
import ordering.client.client as client


@ts.fake
class FakeOrderWorkflow(order_workflow.OrderWorkflow):

    def __init__(self) -> None:
        self.started: list[order_workflow.StartRequest] = []

    async def start(self, request: order_workflow.StartRequest) -> order_workflow.StartResponse:
        self.started.append(request)
        return order_workflow.StartResponse(order_id=request.order_id)


@ts.helper
def place_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2, note: str = "gift"
) -> client.PlaceRequest:
    return client.PlaceRequest(order_id=order_id, sku=sku, quantity=quantity, note=note)


class TestOrderService:

    def test_placing_answers_the_order_id(self) -> None:
        service = order_service.OrderService(FakeOrderWorkflow())
        placed = asyncio.run(service.place(place_request()))
        assert placed.order_id == "o1"

    def test_placing_starts_the_workflow_for_the_order(self) -> None:
        workflows = FakeOrderWorkflow()
        asyncio.run(
            order_service.OrderService(workflows).place(
                place_request(order_id="o2", sku="gadget", quantity=3, note="fragile")
            )
        )
        assert [(s.order_id, s.sku, s.quantity, s.note) for s in workflows.started] == [
            ("o2", "gadget", 3, "fragile")
        ]
