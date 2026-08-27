from __future__ import annotations

import typing

import tesser.adapters as ts

import ordering.client.client as client
import protocol.cli as cli

_PLACE_USAGE: typing.Final[str] = "usage: place <order_id> <sku> <quantity>"


class Handler(ts.Handler):

    def __init__(self, client: client.Client) -> None:
        self._client = client

    def place(self, request: cli.CliRequest) -> cli.CliResponse:
        order_id = request.arg(0, "order_id", _PLACE_USAGE)
        sku = request.arg(1, "sku", _PLACE_USAGE)
        quantity = request.integer(2, "quantity", _PLACE_USAGE)
        placed = self._client.place(client.PlaceRequest(order_id=order_id, sku=sku, quantity=quantity))
        return cli.CliResponse(exit_code=0, line=cli.Line(text=placed.order_id))
