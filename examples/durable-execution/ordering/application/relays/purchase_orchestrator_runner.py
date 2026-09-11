from __future__ import annotations

import json
import typing

import tesser.application as ts

import ordering.application.snapshots as snapshots
import ordering.domain as domain
import tesser.errors as errors


class PurchaseOrchestratorRequest(ts.Request):

    def __init__(self, order: domain.Order) -> None:
        self.order = order


class PurchaseOrchestratorRequestSnapshot(ts.Serde):

    def serialize(self, purchase_orchestrator_request: PurchaseOrchestratorRequest) -> bytes:
        return snapshots.OrderSnapshot().serialize(purchase_orchestrator_request.order)

    def deserialize(self, buf: bytes) -> PurchaseOrchestratorRequest:
        return PurchaseOrchestratorRequest(order=snapshots.OrderSnapshot().deserialize(buf))


class PurchaseOrchestratorResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int, payment_reference: str) -> None:
        self.order_id = order_id
        self.total_cents = total_cents
        self.payment_reference = payment_reference


class PurchaseOrchestratorResponseSnapshot(ts.Serde):

    def serialize(self, purchase_orchestrator_response: PurchaseOrchestratorResponse) -> bytes:
        return json.dumps(
            {
                "order_id": purchase_orchestrator_response.order_id,
                "total_cents": purchase_orchestrator_response.total_cents,
                "payment_reference": purchase_orchestrator_response.payment_reference,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> PurchaseOrchestratorResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order_id"), str)
            and snapshot["order_id"]
            and isinstance(snapshot.get("total_cents"), int)
            and not isinstance(snapshot.get("total_cents"), bool)
            and snapshot["total_cents"] >= 0
            and isinstance(snapshot.get("payment_reference"), str)
            and snapshot["payment_reference"]
        ):
            raise errors.invalid(
                "malformed_purchase_orchestrator_response_snapshot",
                "a purchase orchestrator response is an order_id, a total in cents, and a payment reference",
            )
        return PurchaseOrchestratorResponse(
            order_id=snapshot["order_id"],
            total_cents=snapshot["total_cents"],
            payment_reference=snapshot["payment_reference"],
        )


class PurchaseOrchestratorRunner(ts.Relay, typing.Protocol):

    async def run_purchase_orchestrator(
        self, purchase_orchestrator_request: PurchaseOrchestratorRequest
    ) -> PurchaseOrchestratorResponse: ...
