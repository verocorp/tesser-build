from __future__ import annotations

import typing

import tesser.context as ts


class PlaceRequest(ts.Request):

    def __init__(self, order_id: str, sku: str, quantity: int) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity


class PlaceResponse(ts.Response):

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class Client(ts.Client, typing.Protocol):

    async def place(self, request: PlaceRequest) -> PlaceResponse: ...
