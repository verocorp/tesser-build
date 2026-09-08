from __future__ import annotations

import json

import tesser.adapters as ts

import ordering.client as client
import protocol as protocol


class Handler(ts.Handler):

    def __init__(self, ordering_client: client.OrderingClient) -> None:
        self._ordering_client = ordering_client

    async def submit_order(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        submit_order_response = await self._ordering_client.submit_order(
            client.SubmitOrderRequest(
                order_id=http_request.text("order_id"),
                sku=http_request.text("sku"),
                quantity=http_request.integer("quantity"),
            )
        )
        return protocol.HttpResponse(
            status_code=202, body=json.dumps({"order_id": submit_order_response.order_id}).encode()
        )

    async def place_order(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        place_order_response = await self._ordering_client.place_order(
            client.PlaceOrderRequest(
                order_id=http_request.text("order_id"),
                sku=http_request.text("sku"),
                quantity=http_request.integer("quantity"),
            )
        )
        return protocol.HttpResponse(
            status_code=200,
            body=json.dumps(
                {
                    "order_id": place_order_response.order_id,
                    "total_cents": place_order_response.total_cents,
                }
            ).encode(),
        )
