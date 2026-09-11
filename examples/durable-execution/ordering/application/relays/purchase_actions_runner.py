from __future__ import annotations

import json
import typing

import tesser.application as ts

import ordering.application.ports as ports


class TakePaymentRequest(ts.Request):

    def __init__(self, order_id: str, cents: int) -> None:
        self.order_id = order_id
        self.cents = cents


class TakePaymentRequestSnapshot(ts.Serde):

    def serialize(self, take_payment_request: TakePaymentRequest) -> bytes:
        return json.dumps(
            {"order_id": take_payment_request.order_id, "cents": take_payment_request.cents}
        ).encode()

    def deserialize(self, buf: bytes) -> TakePaymentRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order_id"), str)
            and snapshot["order_id"]
            and isinstance(snapshot.get("cents"), int)
            and not isinstance(snapshot.get("cents"), bool)
            and snapshot["cents"] >= 0
        ):
            raise ports.EngineRejected(  # tesser:debt TB082
                "a take payment request is an order_id and an amount in cents"
            )
        return TakePaymentRequest(order_id=snapshot["order_id"], cents=snapshot["cents"])


class TakePaymentResponse(ts.Response):

    def __init__(self, order_id: str, reference: str, cents: int) -> None:
        self.order_id = order_id
        self.reference = reference
        self.cents = cents


class TakePaymentResponseSnapshot(ts.Serde):

    def serialize(self, take_payment_response: TakePaymentResponse) -> bytes:
        return json.dumps(
            {
                "order_id": take_payment_response.order_id,
                "reference": take_payment_response.reference,
                "cents": take_payment_response.cents,
            }
        ).encode()

    def deserialize(self, buf: bytes) -> TakePaymentResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order_id"), str)
            and snapshot["order_id"]
            and isinstance(snapshot.get("reference"), str)
            and snapshot["reference"]
            and isinstance(snapshot.get("cents"), int)
            and not isinstance(snapshot.get("cents"), bool)
            and snapshot["cents"] >= 0
        ):
            raise ports.EngineRejected(  # tesser:debt TB082
                "a take payment response is the order_id, a reference, "
                "and the amount charged in cents"
            )
        return TakePaymentResponse(
            order_id=snapshot["order_id"], reference=snapshot["reference"], cents=snapshot["cents"]
        )


class PurchaseActionsRunner(ts.Relay, typing.Protocol):

    async def run_take_payment(
        self, take_payment_request: TakePaymentRequest
    ) -> TakePaymentResponse: ...
