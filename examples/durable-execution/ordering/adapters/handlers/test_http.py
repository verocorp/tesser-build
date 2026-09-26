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
        self.paid: list[client.MakeOrderPaymentRequest] = []

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

    async def make_order_payment(
        self, make_order_payment_request: client.MakeOrderPaymentRequest
    ) -> client.MakeOrderPaymentResponse:
        self.paid.append(make_order_payment_request)
        return client.MakeOrderPaymentResponse(
            order_id=make_order_payment_request.order_id,
            total_cents=250 * make_order_payment_request.quantity,
            payment_reference=f"pay-{make_order_payment_request.order_id}",
        )


@ts.fake
class FakeRefusingOrderingClient(client.OrderingClient):

    def __init__(self, error: Exception) -> None:
        self.error = error

    async def submit_order(
        self, submit_order_request: client.SubmitOrderRequest
    ) -> client.SubmitOrderResponse:
        raise self.error

    async def place_order(
        self, place_order_request: client.PlaceOrderRequest
    ) -> client.PlaceOrderResponse:
        raise self.error

    async def make_order_payment(
        self, make_order_payment_request: client.MakeOrderPaymentRequest
    ) -> client.MakeOrderPaymentResponse:
        raise self.error


@ts.assembly
def order_request() -> protocol.HttpRequest:
    return protocol.HttpRequest(body=b'{"order_id": "o1", "sku": "widget", "quantity": 2}')


@ts.assembly
def purchase_request() -> protocol.HttpRequest:
    return protocol.HttpRequest(
        body=b'{"order_id": "o1", "sku": "widget", "quantity": 2, "payment_method": "card-4242"}'
    )


class TestHandler:

    def test_paying_for_an_order_answers_with_its_id_total_and_payment_reference(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        http_response = asyncio.run(
            handler.make_order_payment(purchase_request())
        )
        assert http_response.status_code == 200
        assert json.loads(http_response.body) == {
            "order_id": "o1",
            "total_cents": 500,
            "payment_reference": "pay-o1",
        }

    def test_paying_carries_the_body_fields_to_the_client(self) -> None:
        fake_ordering_client = FakeOrderingClient()
        asyncio.run(
            handlers.Handler(fake_ordering_client).make_order_payment(
                purchase_request()
            )
        )
        assert [
            (p.order_id, p.sku, p.quantity, p.payment_method)
            for p in fake_ordering_client.paid
        ] == [("o1", "widget", 2, "card-4242")]
        assert fake_ordering_client.placed == []
        assert fake_ordering_client.submitted == []

    def test_a_missing_payment_method_is_a_bad_request_when_paying(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        with pytest.raises(protocol.BadRequest):
            asyncio.run(handler.make_order_payment(order_request()))

    def test_a_placed_order_answers_with_its_id_and_total(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        http_response = asyncio.run(handler.place_order(order_request()))
        assert http_response.status_code == 200
        assert json.loads(http_response.body) == {"order_id": "o1", "total_cents": 500}

    def test_place_order_carries_the_body_fields_to_the_client(self) -> None:
        fake_ordering_client = FakeOrderingClient()
        asyncio.run(
            handlers.Handler(fake_ordering_client).place_order(
                order_request()
            )
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
        http_response = asyncio.run(handler.submit_order(order_request()))
        assert http_response.status_code == 202
        assert json.loads(http_response.body) == {"order_id": "o1"}

    def test_submit_order_carries_the_body_fields_to_the_client(self) -> None:
        fake_ordering_client = FakeOrderingClient()
        asyncio.run(
            handlers.Handler(fake_ordering_client).submit_order(
                order_request()
            )
        )
        assert [(p.order_id, p.sku, p.quantity) for p in fake_ordering_client.submitted] == [
            ("o1", "widget", 2)
        ]

    def test_a_missing_field_is_a_bad_request(self) -> None:
        handler = handlers.Handler(FakeOrderingClient())
        with pytest.raises(protocol.BadRequest):
            asyncio.run(handler.submit_order(protocol.HttpRequest(body=b'{"order_id": "o1"}')))

    def test_a_rejected_order_is_422_carrying_the_contexts_wording(self) -> None:
        handler = handlers.Handler(
            FakeRefusingOrderingClient(
                client.OrderRejected("quantity_below_one", "an order is for at least one unit")
            )
        )
        http_response = asyncio.run(handler.place_order(order_request()))
        assert http_response.status_code == 422
        assert json.loads(http_response.body) == {"detail": "an order is for at least one unit"}

    def test_a_product_price_that_was_not_found_is_422_carrying_the_contexts_wording(
        self,
    ) -> None:
        handler = handlers.Handler(
            FakeRefusingOrderingClient(client.ProductPriceNotFound("no price for sku 'nope'"))
        )
        http_response = asyncio.run(handler.place_order(order_request()))
        assert http_response.status_code == 422
        assert json.loads(http_response.body) == {"detail": "no price for sku 'nope'"}

    def test_an_order_that_was_not_confirmed_is_422_carrying_the_contexts_wording(self) -> None:
        handler = handlers.Handler(
            FakeRefusingOrderingClient(client.OrderNotConfirmed("no price for sku 'nope'"))
        )
        http_response = asyncio.run(
            handler.make_order_payment(purchase_request())
        )
        assert http_response.status_code == 422
        assert json.loads(http_response.body) == {"detail": "no price for sku 'nope'"}

    def test_a_declined_payment_is_409_carrying_the_contexts_wording(self) -> None:
        handler = handlers.Handler(
            FakeRefusingOrderingClient(client.PaymentDeclined("the processor declined the charge"))
        )
        http_response = asyncio.run(
            handler.make_order_payment(purchase_request())
        )
        assert http_response.status_code == 409
        assert json.loads(http_response.body) == {"detail": "the processor declined the charge"}

    def test_an_order_already_started_is_409_carrying_the_contexts_wording(self) -> None:
        handler = handlers.Handler(
            FakeRefusingOrderingClient(
                client.OrderAlreadyStarted("the workflow method was already invoked")
            )
        )
        http_response = asyncio.run(handler.submit_order(order_request()))
        assert http_response.status_code == 409
        assert json.loads(http_response.body) == {
            "detail": "the workflow method was already invoked"
        }

    def test_a_failure_the_context_never_declared_leaves_the_handler(self) -> None:
        handler = handlers.Handler(
            FakeRefusingOrderingClient(RuntimeError("a stack trace nobody should see"))
        )
        with pytest.raises(RuntimeError):
            asyncio.run(handler.place_order(order_request()))
