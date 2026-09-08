from __future__ import annotations

import typing

import tesser.context as ts


class SubmitOrderRequest(ts.Request):

    def __init__(self, order_id: str, sku: str, quantity: int) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity


class SubmitOrderResponse(ts.Response):

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class OrderingClient(ts.Client, typing.Protocol):

    async def submit_order(self, submit_order_request: SubmitOrderRequest) -> SubmitOrderResponse: ...
