from __future__ import annotations

import json  # tesser:debt TB062
import typing

import tesser.application as ts

import tesser.errors as errors


class TakePaymentRequest(ts.Request):  # tesser:debt TB052

    def __init__(self, order_id: str, cents: int) -> None:
        self.order_id = order_id
        self.cents = cents


class TakePaymentRequestSnapshot(ts.Serde):  # tesser:debt TB052

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
            raise errors.invalid(
                "malformed_take_payment_request_snapshot",
                "a take payment request is an order_id and an amount in cents",
            )
        return TakePaymentRequest(order_id=snapshot["order_id"], cents=snapshot["cents"])


class TakePaymentResponse(ts.Response):  # tesser:debt TB052

    def __init__(self, order_id: str, reference: str, cents: int) -> None:
        self.order_id = order_id
        self.reference = reference
        self.cents = cents


class TakePaymentResponseSnapshot(ts.Serde):  # tesser:debt TB052

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
            raise errors.invalid(
                "malformed_take_payment_response_snapshot",
                "a take payment response is the order_id, a reference, and the amount charged in cents",
            )
        return TakePaymentResponse(
            order_id=snapshot["order_id"], reference=snapshot["reference"], cents=snapshot["cents"]
        )


class PurchaseActionsRunner(ts.JobContext, typing.Protocol):  # tesser:debt TB052

    async def run_take_payment(
        self, take_payment_request: TakePaymentRequest
    ) -> TakePaymentResponse: ...
