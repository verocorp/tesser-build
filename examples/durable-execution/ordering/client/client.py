from __future__ import annotations

import typing

import tesser.context as ts


class PlaceOrderRequest(ts.Request):

    def __init__(self, order_id: str, sku: str, quantity: int, note: str) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity
        self.note = note


class PlaceOrderResponse(ts.Response):

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class OrderingClient(ts.Client, typing.Protocol):

    async def place_order(self, place_order_request: PlaceOrderRequest) -> PlaceOrderResponse: ...
