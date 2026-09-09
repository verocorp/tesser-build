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
        self.placed: list[client.PlaceOrderRequest] = []
        self.purchased: list[client.PurchaseRequest] = []

    async def submit_order(
        self, submit_order_request: client.SubmitOrderRequest
    ) -> client.SubmitOrderResponse:
        self.submitted.append(submit_order_request)
        return client.SubmitOrderResponse(order_id=submit_order_request.order_id)

    async def place_order(
        self, place_order_request: client.PlaceOrderRequest
    ) -> client.PlaceOrderResponse:
        self.placed.append(place_order_request)
        return client.PlaceOrderResponse(
            order_id=place_order_request.order_id, total_cents=250 * place_order_request.quantity
        )

    async def purchase(self, purchase_request: client.PurchaseRequest) -> client.PurchaseResponse:
        self.purchased.append(purchase_request)
        return client.PurchaseResponse(
            order_id=purchase_request.order_id,
            total_cents=250 * purchase_request.quantity,
            payment_reference=f"pay-{purchase_request.order_id}",
        )


class TestHandler:

    def test_a_purchase_answers_with_its_id_total_and_payment_reference(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        body = b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        http_response = asyncio.run(handler.purchase(protocol.HttpRequest(body=body)))
        assert http_response.status_code == 200
        assert json.loads(http_response.body) == {
            "order_id": "o1",
            "total_cents": 500,
            "payment_reference": "pay-o1",
        }

    def test_purchase_carries_the_body_fields_to_the_client(self) -> None:
        fake_ordering_client = FakeOrderingClient()
        body = b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        asyncio.run(
            handlers.Handler(fake_ordering_client).purchase(protocol.HttpRequest(body=body))
        )
        assert [(p.order_id, p.sku, p.quantity) for p in fake_ordering_client.purchased] == [
            ("o1", "widget", 2)
        ]
        assert fake_ordering_client.placed == []
        assert fake_ordering_client.submitted == []

    def test_a_missing_field_is_a_bad_request_when_purchasing(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        with pytest.raises(protocol.BadRequest):
            asyncio.run(handler.purchase(protocol.HttpRequest(body=b'{"order_id": "o1"}')))

    def test_a_placed_order_answers_with_its_id_and_total(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        body = b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        http_response = asyncio.run(handler.place_order(protocol.HttpRequest(body=body)))
        assert http_response.status_code == 200
        assert json.loads(http_response.body) == {"order_id": "o1", "total_cents": 500}

    def test_place_order_carries_the_body_fields_to_the_client(self) -> None:
        fake_ordering_client = FakeOrderingClient()
        body = b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        asyncio.run(
            handlers.Handler(fake_ordering_client).place_order(protocol.HttpRequest(body=body))
        )
        assert [(p.order_id, p.sku, p.quantity) for p in fake_ordering_client.placed] == [
            ("o1", "widget", 2)
        ]
        assert fake_ordering_client.submitted == []

    def test_a_missing_field_is_a_bad_request_when_placing(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        with pytest.raises(protocol.BadRequest):
            asyncio.run(handler.place_order(protocol.HttpRequest(body=b'{"order_id": "o1"}')))

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
