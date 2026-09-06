from __future__ import annotations

import json
import typing

import tesser.application as ts

import ordering.domain.order as domain


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


class StartRequest(ts.Request):

    def __init__(self, order: domain.Order) -> None:
        self.order = order


class StartRequestSnapshot(ts.Serde):

    def serialize(self, request: StartRequest) -> bytes:
        return OrderSnapshot().serialize(request.order)

    def deserialize(self, buf: bytes) -> StartRequest:
        return StartRequest(order=OrderSnapshot().deserialize(buf))


class StartResponse(ts.Response):

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class RunResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents


class RunResponseSnapshot(ts.Serde):

    def serialize(self, response: RunResponse) -> bytes:
        return json.dumps(
            {"order_id": response.order_id, "total_cents": response.total_cents}
        ).encode()

    def deserialize(self, buf: bytes) -> RunResponse:
        snapshot = json.loads(buf)
        return RunResponse(
            order_id=snapshot["order_id"], total_cents=snapshot["total_cents"]
        )


class OrderRelay(ts.Relay, typing.Protocol):

    async def start(self, request: StartRequest) -> StartResponse: ...
