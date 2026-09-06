from __future__ import annotations

import asyncio
import json

import pytest
import tesser.testing as ts

import ordering.adapters.handlers as handlers
import ordering.client as client
import protocol as protocol


@ts.fake
class FakeOrderingClient(client.OrderingClient):

    def __init__(self) -> None:
        self.placed: list[client.PlaceRequest] = []

    async def place(self, place_request: client.PlaceRequest) -> client.PlaceResponse:
        self.placed.append(place_request)
        return client.PlaceResponse(order_id=place_request.order_id)


class TestHandler:

    def test_a_placed_order_is_accepted_with_its_id(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        body = b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        http_response = asyncio.run(handler.place(protocol.HttpRequest(body=body)))
        assert http_response.status_code == 202
        assert json.loads(http_response.body) == {"order_id": "o1"}

    def test_place_carries_the_body_fields_to_the_client(self) -> None:
        fake_ordering_client = FakeOrderingClient()
        body = b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        asyncio.run(handlers.Handler(fake_ordering_client).place(protocol.HttpRequest(body=body)))
        assert [(p.order_id, p.sku, p.quantity) for p in fake_ordering_client.placed] == [
            ("o1", "widget", 2)
        ]

    def test_a_missing_field_is_a_bad_request(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        with pytest.raises(protocol.BadRequest):
            asyncio.run(handler.place(protocol.HttpRequest(body=b'{"order_id": "o1"}')))
