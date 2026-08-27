from __future__ import annotations

import typing

import tesser.application as ts


class StartRequest(ts.Request):

    def __init__(self, order_id: str, sku: str, quantity: int) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity


class StartResponse(ts.Response):

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class OrderWorkflow(ts.Port, typing.Protocol):

    async def start(self, request: StartRequest) -> StartResponse: ...
