from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application.order_service as order_service
import ordering.application.relays.order_relay as order_relay
import ordering.client.client as client


@ts.fake
class FakeOrderRelay(order_relay.OrderRelay):

    def __init__(self) -> None:
        self.started: list[order_relay.StartRequest] = []

    async def start(self, request: order_relay.StartRequest) -> order_relay.StartResponse:
        self.started.append(request)
        return order_relay.StartResponse(order_id=str(request.order.identity))


@ts.helper
def place_request(order_id: str = "o1", sku: str = "widget", quantity: int = 2) -> client.PlaceRequest:
    return client.PlaceRequest(order_id=order_id, sku=sku, quantity=quantity)


class TestOrderService:

    def test_placing_answers_the_order_id(self) -> None:
        service = order_service.OrderService(FakeOrderRelay())
        placed = asyncio.run(service.place(place_request()))
        assert placed.order_id == "o1"

    def test_placing_starts_the_workflow_for_the_order_it_built(self) -> None:
        relay = FakeOrderRelay()
        asyncio.run(order_service.OrderService(relay).place(place_request(order_id="o2", sku="gadget", quantity=3)))
        assert [
            (str(s.order.identity), str(s.order.sku), int(s.order.quantity)) for s in relay.started
        ] == [("o2", "gadget", 3)]
