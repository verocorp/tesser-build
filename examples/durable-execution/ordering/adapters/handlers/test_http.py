from __future__ import annotations

import asyncio
import json

import pytest
import tesser.testing as ts

import ordering.adapters.handlers.http as http_handlers
import ordering.client.client as client
import protocol.http as http


@ts.fake
class FakeClient(client.Client):

    def __init__(self) -> None:
        self.placed: list[client.PlaceRequest] = []

    async def place(self, request: client.PlaceRequest) -> client.PlaceResponse:
        self.placed.append(request)
        return client.PlaceResponse(order_id=request.order_id)


class TestHandler:

    def test_a_placed_order_is_accepted_with_its_id(self) -> None:
        handler = http_handlers.Handler(FakeClient())
        body = b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        response = asyncio.run(handler.place(http.HttpRequest(body=body)))
        assert response.status_code == 202
        assert json.loads(response.body) == {"order_id": "o1"}

    def test_place_carries_the_body_fields_to_the_client(self) -> None:
        fake = FakeClient()
        body = b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        asyncio.run(http_handlers.Handler(fake).place(http.HttpRequest(body=body)))
        assert [(p.order_id, p.sku, p.quantity) for p in fake.placed] == [("o1", "widget", 2)]

    def test_a_missing_field_is_a_bad_request(self) -> None:
        handler = http_handlers.Handler(FakeClient())
        with pytest.raises(http.BadRequest):
            asyncio.run(handler.place(http.HttpRequest(body=b'{"order_id": "o1"}')))
