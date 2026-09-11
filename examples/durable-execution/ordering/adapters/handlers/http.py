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
                case client.Rejected():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.Missing():
                    return protocol.HttpResponse.problem(404, error.message)
                case client.Conflict():
                    return protocol.HttpResponse.problem(409, error.message)
                case client.Unavailable():
                    return protocol.HttpResponse.problem(503, "unavailable")
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
                case client.Rejected():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.Missing():
                    return protocol.HttpResponse.problem(404, error.message)
                case client.Conflict():
                    return protocol.HttpResponse.problem(409, error.message)
                case client.Unavailable():
                    return protocol.HttpResponse.problem(503, "unavailable")
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

    async def purchase(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        try:
            purchase_response = await self._ordering_client.purchase(
                client.PurchaseRequest(
                    order_id=http_request.text("order_id"),
                    sku=http_request.text("sku"),
                    quantity=http_request.integer("quantity"),
                )
            )
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.HttpResponse.problem(422, error.message)
                case client.Missing():
                    return protocol.HttpResponse.problem(404, error.message)
                case client.Conflict():
                    return protocol.HttpResponse.problem(409, error.message)
                case client.Unavailable():
                    return protocol.HttpResponse.problem(503, "unavailable")
                case _ as never:
                    typing.assert_never(never)
        return protocol.HttpResponse(
            status_code=200,
            body=json.dumps(
                {
                    "order_id": purchase_response.order_id,
                    "total_cents": purchase_response.total_cents,
                    "payment_reference": purchase_response.payment_reference,
                }
            ).encode(),
        )
