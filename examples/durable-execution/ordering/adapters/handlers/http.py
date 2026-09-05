from __future__ import annotations

import json

import tesser.adapters as ts

import ordering.client.client as client
import protocol.http as http


class Handler(ts.Handler):

    def __init__(self, client: client.Client) -> None:
        self._client = client

    async def place(self, request: http.HttpRequest) -> http.HttpResponse:
        placed = await self._client.place(
            client.PlaceRequest(
                order_id=request.text("order_id"),
                sku=request.text("sku"),
                quantity=request.integer("quantity"),
                note=request.text("note"),
            )
        )
        return http.HttpResponse(
            status_code=202, body=json.dumps({"order_id": placed.order_id}).encode()
        )
