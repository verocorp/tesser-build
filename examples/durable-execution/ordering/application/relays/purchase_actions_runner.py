from __future__ import annotations

import json  # tesser:debt TB062
import typing

import tesser.application as ts


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
        return TakePaymentRequest(order_id=snapshot["order_id"], cents=snapshot["cents"])


class TakePaymentResponse(ts.Response):  # tesser:debt TB052

    def __init__(self, reference: str, cents: int) -> None:
        self.reference = reference
        self.cents = cents


class TakePaymentResponseSnapshot(ts.Serde):  # tesser:debt TB052

    def serialize(self, take_payment_response: TakePaymentResponse) -> bytes:
        return json.dumps(
            {"reference": take_payment_response.reference, "cents": take_payment_response.cents}
        ).encode()

    def deserialize(self, buf: bytes) -> TakePaymentResponse:
        snapshot = json.loads(buf)
        return TakePaymentResponse(reference=snapshot["reference"], cents=snapshot["cents"])


class PurchaseActionsRunner(ts.JobContext, typing.Protocol):  # tesser:debt TB052

    async def run_take_payment(
        self, take_payment_request: TakePaymentRequest
    ) -> TakePaymentResponse: ...
