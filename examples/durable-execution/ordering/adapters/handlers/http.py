from __future__ import annotations

import json
import typing

import tesser.adapters as ts

import ordering.client as client
import protocol as protocol


class Handler(ts.Handler):

    def __init__(self, ordering_client: client.OrderingClient) -> None:
        self._ordering_client = ordering_client

    async def submit_order(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        try:
            submit_order_response = await self._ordering_client.submit_order(
                client.SubmitOrderRequest(
                    order_id=http_request.text("order_id"),
                    sku=http_request.text("sku"),
                    quantity=http_request.integer("quantity"),
                )
            )
        except client.ERRORS as error:
            match error:
                case client.OrderRejected():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.ProductPriceNotFound():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.OrderNotConfirmed():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.PaymentDeclined():
                    return protocol.HttpResponse.problem(409, error.message)
                case client.OrderAlreadyStarted():
                    return protocol.HttpResponse.problem(409, error.message)
                case _ as never:
                    typing.assert_never(never)
        return protocol.HttpResponse(
            status_code=202, body=json.dumps({"order_id": submit_order_response.order_id}).encode()
        )

    async def place_order(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        try:
            place_order_response = await self._ordering_client.place_order(
                client.PlaceOrderRequest(
                    order_id=http_request.text("order_id"),
                    sku=http_request.text("sku"),
                    quantity=http_request.integer("quantity"),
                )
            )
        except client.ERRORS as error:
            match error:
                case client.OrderRejected():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.ProductPriceNotFound():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.OrderNotConfirmed():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.PaymentDeclined():
                    return protocol.HttpResponse.problem(409, error.message)
                case client.OrderAlreadyStarted():
                    return protocol.HttpResponse.problem(409, error.message)
                case _ as never:
                    typing.assert_never(never)
        return protocol.HttpResponse(
            status_code=200,
            body=json.dumps(
                {
                    "order_id": place_order_response.order_id,
                    "total_cents": place_order_response.total_cents,
                }
            ).encode(),
        )

    async def pay_for_order(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        try:
            pay_for_order_response = await self._ordering_client.pay_for_order(
                client.PayForOrderRequest(
                    order_id=http_request.text("order_id"),
                    sku=http_request.text("sku"),
                    quantity=http_request.integer("quantity"),
                    payment_method=http_request.text("payment_method"),
                )
            )
        except client.ERRORS as error:
            match error:
                case client.OrderRejected():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.ProductPriceNotFound():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.OrderNotConfirmed():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.PaymentDeclined():
                    return protocol.HttpResponse.problem(409, error.message)
                case client.OrderAlreadyStarted():
                    return protocol.HttpResponse.problem(409, error.message)
                case _ as never:
                    typing.assert_never(never)
        return protocol.HttpResponse(
            status_code=200,
            body=json.dumps(
                {
                    "order_id": pay_for_order_response.order_id,
                    "total_cents": pay_for_order_response.total_cents,
                    "payment_reference": pay_for_order_response.payment_reference,
                }
            ).encode(),
        )
