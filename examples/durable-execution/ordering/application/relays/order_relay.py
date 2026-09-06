from __future__ import annotations

import json
import typing

import tesser.application as ts

import ordering.domain.order as domain


class StartRequest(ts.Request):

    def __init__(self, order: domain.Order) -> None:
        self.order = order


class StartResponse(ts.Response):

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class QuoteRequest(ts.Request):

    def __init__(self, sku: str) -> None:
        self.sku = sku


class QuoteResponse(ts.Response):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class OrderSnapshot(ts.Serde):

    def serialize(self, running: domain.Order) -> bytes:
        return json.dumps(
            {
                "order_id": str(running.identity),
                "sku": str(running.sku),
                "quantity": int(running.quantity),
            }
        ).encode()

    def deserialize(self, buf: bytes) -> domain.Order:
        snapshot = json.loads(buf)
        return domain.Order(
            domain.OrderSpec(
                order_id=snapshot["order_id"],
                sku=snapshot["sku"],
                quantity=snapshot["quantity"],
            )
        )


class OrderRelay(ts.Relay, typing.Protocol):

    async def start(self, request: StartRequest) -> StartResponse: ...

    async def quote(self, request: QuoteRequest) -> QuoteResponse: ...
