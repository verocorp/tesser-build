from __future__ import annotations

import json  # tesser:debt TB062
import typing

import tesser.application as ts

import ordering.domain as domain
import tesser.errors as errors


class OrderSnapshot(ts.Serde):  # tesser:debt TB052

    def serialize(self, order: domain.Order) -> bytes:
        return json.dumps(
            {
                "order_id": str(order.identity),
                "sku": str(order.sku),
                "quantity": int(order.quantity),
            }
        ).encode()

    def deserialize(self, buf: bytes) -> domain.Order:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order_id"), str)
            and isinstance(snapshot.get("sku"), str)
            and isinstance(snapshot.get("quantity"), int)
            and not isinstance(snapshot.get("quantity"), bool)
        ):
            raise errors.invalid("malformed_order_snapshot", "an order snapshot is order_id, sku, and quantity")
        return domain.Order(
            domain.OrderSpec(
                order_id=snapshot["order_id"],
                sku=snapshot["sku"],
                quantity=snapshot["quantity"],
            )
        )


class OrderOrchestratorRequest(ts.Request):  # tesser:debt TB052

    def __init__(self, order: domain.Order) -> None:  # tesser:debt TB080
        self.order = order


class OrderOrchestratorRequestSnapshot(ts.Serde):  # tesser:debt TB052

    def serialize(self, order_orchestrator_request: OrderOrchestratorRequest) -> bytes:
        return OrderSnapshot().serialize(order_orchestrator_request.order)

    def deserialize(self, buf: bytes) -> OrderOrchestratorRequest:
        return OrderOrchestratorRequest(order=OrderSnapshot().deserialize(buf))


class StartOrderOrchestratorResponse(ts.Response):  # tesser:debt TB052

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class OrderOrchestratorResponse(ts.Response):  # tesser:debt TB052

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents


class OrderOrchestratorResponseSnapshot(ts.Serde):  # tesser:debt TB052

    def serialize(self, order_orchestrator_response: OrderOrchestratorResponse) -> bytes:
        return json.dumps(
            {
                "order_id": order_orchestrator_response.order_id,
                "total_cents": order_orchestrator_response.total_cents,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> OrderOrchestratorResponse:
        snapshot = json.loads(buf)
        return OrderOrchestratorResponse(
            order_id=snapshot["order_id"], total_cents=snapshot["total_cents"]
        )


class OrderOrchestratorRunner(ts.Relay, typing.Protocol):  # tesser:debt TB052

    async def start_order_orchestrator(
        self, order_orchestrator_request: OrderOrchestratorRequest
    ) -> StartOrderOrchestratorResponse: ...
