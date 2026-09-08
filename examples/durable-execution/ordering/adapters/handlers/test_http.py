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
        self.submitted: list[client.SubmitOrderRequest] = []

    async def submit_order(
        self, submit_order_request: client.SubmitOrderRequest
    ) -> client.SubmitOrderResponse:
        self.submitted.append(submit_order_request)
        return client.SubmitOrderResponse(order_id=submit_order_request.order_id)


class TestHandler:

    def test_a_submitted_order_is_accepted_with_its_id(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        body = b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        http_response = asyncio.run(handler.submit_order(protocol.HttpRequest(body=body)))
        assert http_response.status_code == 202
        assert json.loads(http_response.body) == {"order_id": "o1"}

    def test_submit_order_carries_the_body_fields_to_the_client(self) -> None:
        fake_ordering_client = FakeOrderingClient()
        body = b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        asyncio.run(
            handlers.Handler(fake_ordering_client).submit_order(protocol.HttpRequest(body=body))
        )
        assert [(p.order_id, p.sku, p.quantity) for p in fake_ordering_client.submitted] == [
            ("o1", "widget", 2)
        ]

    def test_a_missing_field_is_a_bad_request(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        with pytest.raises(protocol.BadRequest):
            asyncio.run(handler.submit_order(protocol.HttpRequest(body=b'{"order_id": "o1"}')))
