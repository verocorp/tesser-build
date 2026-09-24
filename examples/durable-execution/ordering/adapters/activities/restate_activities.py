from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import ordering.application.client as client
import ordering.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"


class RestatePriceProductRequestSerde(ts.Serde, restate_serde.Serde[relays.PriceProductRequest]):

    def serialize(self, price_product_request: relays.PriceProductRequest | None) -> bytes:
        if price_product_request is None:
            return b""
        return relays.PriceProductRequestSnapshot().serialize(price_product_request)

    def deserialize(self, buf: bytes) -> relays.PriceProductRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PriceProductRequestSnapshot().deserialize(buf)


class RestatePriceProductResponseSerde(ts.Serde, restate_serde.Serde[relays.PriceProductResponse]):

    def serialize(self, price_product_response: relays.PriceProductResponse | None) -> bytes:
        if price_product_response is None:
            return b""
        return relays.PriceProductResponseSnapshot().serialize(price_product_response)

    def deserialize(self, buf: bytes) -> relays.PriceProductResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PriceProductResponseSnapshot().deserialize(buf)


class RestatePriceProduct(ts.Activity):

    def __init__(
        self,
        order_actions_service: restate.Service,
        ordering_application_client: client.OrderingApplicationClient,
    ) -> None:
        @order_actions_service.handler(
            input_serde=RestatePriceProductRequestSerde(),
            output_serde=RestatePriceProductResponseSerde(),
        )
        async def price_product(
            restate_context: restate.Context, price_product_request: relays.PriceProductRequest
        ) -> relays.PriceProductResponse:
            return ordering_application_client.price_product(price_product_request)

        self.handler = price_product


class RestateTakePaymentRequestSerde(ts.Serde, restate_serde.Serde[relays.TakePaymentRequest]):

    def serialize(self, take_payment_request: relays.TakePaymentRequest | None) -> bytes:
        if take_payment_request is None:
            return b""
        return relays.TakePaymentRequestSnapshot().serialize(take_payment_request)

    def deserialize(self, buf: bytes) -> relays.TakePaymentRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.TakePaymentRequestSnapshot().deserialize(buf)


class RestateTakePaymentResponseSerde(ts.Serde, restate_serde.Serde[relays.TakePaymentResponse]):

    def serialize(self, take_payment_response: relays.TakePaymentResponse | None) -> bytes:
        if take_payment_response is None:
            return b""
        return relays.TakePaymentResponseSnapshot().serialize(take_payment_response)

    def deserialize(self, buf: bytes) -> relays.TakePaymentResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.TakePaymentResponseSnapshot().deserialize(buf)


class RestateTakePayment(ts.Activity):

    def __init__(
        self,
        purchase_actions_service: restate.Service,
        purchase_application_client: client.PurchaseApplicationClient,
    ) -> None:
        @purchase_actions_service.handler(
            input_serde=RestateTakePaymentRequestSerde(),
            output_serde=RestateTakePaymentResponseSerde(),
        )
        async def take_payment(
            restate_context: restate.Context, take_payment_request: relays.TakePaymentRequest
        ) -> relays.TakePaymentResponse:
            return purchase_application_client.take_payment(take_payment_request)

        self.handler = take_payment
