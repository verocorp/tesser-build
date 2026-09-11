from __future__ import annotations

import json
import typing

import tesser.application as ts

import ordering.application.snapshots as snapshots
import ordering.application.ports as ports
import ordering.domain as domain


class OrderOrchestratorRequest(ts.Request):

    def __init__(self, order: domain.Order) -> None:
        self.order = order


class OrderOrchestratorRequestSnapshot(ts.Serde):

    def serialize(self, order_orchestrator_request: OrderOrchestratorRequest) -> bytes:
        return snapshots.OrderSnapshot().serialize(order_orchestrator_request.order)

    def deserialize(self, buf: bytes) -> OrderOrchestratorRequest:
        return OrderOrchestratorRequest(order=snapshots.OrderSnapshot().deserialize(buf))


class StartOrderOrchestratorResponse(ts.Response):

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class OrderOrchestratorResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents


class OrderOrchestratorResponseSnapshot(ts.Serde):

    def serialize(self, order_orchestrator_response: OrderOrchestratorResponse) -> bytes:
        return json.dumps(
            {
                "order_id": order_orchestrator_response.order_id,
                "total_cents": order_orchestrator_response.total_cents,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> OrderOrchestratorResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order_id"), str)
            and snapshot["order_id"]
            and isinstance(snapshot.get("total_cents"), int)
            and not isinstance(snapshot.get("total_cents"), bool)
            and snapshot["total_cents"] >= 0
        ):
            raise ports.EngineRejected(  # tesser:debt TB082
                "an order orchestrator response is an order_id and a total in cents"
            )
        return OrderOrchestratorResponse(
            order_id=snapshot["order_id"], total_cents=snapshot["total_cents"]
        )


class OrderOrchestratorRunner(ts.Relay, typing.Protocol):

    async def start_order_orchestrator(
        self, order_orchestrator_request: OrderOrchestratorRequest
    ) -> StartOrderOrchestratorResponse: ...

    async def run_order_orchestrator(
        self, order_orchestrator_request: OrderOrchestratorRequest
    ) -> OrderOrchestratorResponse: ...
