from __future__ import annotations

import enum  # tesser:debt TB062
import json
import typing

import tesser.application as ts


class TakePaymentRequest(ts.Request):

    def __init__(self, order_id: str, cents: int, payment_method: str) -> None:
        self.order_id = order_id
        self.cents = cents
        self.payment_method = payment_method


class TakePaymentRequestSnapshot(ts.Serde):

    def serialize(self, take_payment_request: TakePaymentRequest) -> bytes:
        return json.dumps(
            {
                "order_id": take_payment_request.order_id,
                "cents": take_payment_request.cents,
                "payment_method": take_payment_request.payment_method,
            }
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
            and isinstance(snapshot.get("payment_method"), str)
            and snapshot["payment_method"]
        ):
            raise ValueError(  # tesser:debt TB082
                "a take payment request is an order_id, an amount in cents, and a payment method"
            )
        return TakePaymentRequest(
            order_id=snapshot["order_id"],
            cents=snapshot["cents"],
            payment_method=snapshot["payment_method"],
        )


class TakePaymentOutcome(enum.Enum):  # tesser:debt TB052
    TAKEN = "taken"
    DECLINED = "declined"


class Payment(ts.Response):

    def __init__(self, reference: str, cents: int) -> None:
        self.reference = reference
        self.cents = cents


class TakePaymentResponse(ts.Response):

    def __init__(
        self,
        outcome: TakePaymentOutcome,
        order_id: str,
        payments: tuple[Payment, ...],
        reasons: tuple[str, ...],
    ) -> None:
        self.outcome = outcome
        self.order_id = order_id
        self.payments = payments
        self.reasons = reasons


class TakePaymentResponseSnapshot(ts.Serde):

    def serialize(self, take_payment_response: TakePaymentResponse) -> bytes:
        return json.dumps(
            {
                "outcome": take_payment_response.outcome.value,
                "order_id": take_payment_response.order_id,
                "payments": [  # tesser:debt TB082
                    {"reference": payment.reference, "cents": payment.cents}
                    for payment in take_payment_response.payments
                ],
                "reasons": list(take_payment_response.reasons),  # tesser:debt TB082
            }
        ).encode()

    def deserialize(self, buf: bytes) -> TakePaymentResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order_id"), str)
            and snapshot["order_id"]
            and isinstance(snapshot.get("payments"), list)
            and isinstance(snapshot.get("reasons"), list)
            and all(isinstance(reason, str) and reason for reason in snapshot["reasons"])  # tesser:debt TB082
            and all(  # tesser:debt TB082
                isinstance(payment, dict)
                and isinstance(payment.get("reference"), str)
                and payment["reference"]
                and isinstance(payment.get("cents"), int)
                and not isinstance(payment.get("cents"), bool)
                and payment["cents"] >= 0
                for payment in snapshot["payments"]
            )
        ):
            raise ValueError(  # tesser:debt TB082
                "a take payment response is an outcome, an order_id, "
                "the payments it took, and its reasons"
            )
        try:  # tesser:debt TB082
            take_payment_outcome = TakePaymentOutcome(snapshot.get("outcome"))  # tesser:debt TB082 TB085
        except ValueError as value_error:
            raise ValueError("a take payment response names a taking outcome") from value_error  # tesser:debt TB082
        return TakePaymentResponse(
            outcome=take_payment_outcome,
            order_id=snapshot["order_id"],
            payments=tuple(  # tesser:debt TB082
                Payment(reference=payment["reference"], cents=payment["cents"])
                for payment in snapshot["payments"]
            ),
            reasons=tuple(snapshot["reasons"]),  # tesser:debt TB082
        )


class TakePaymentRelay(ts.Relay, typing.Protocol):

    async def run_take_payment(
        self, take_payment_request: TakePaymentRequest
    ) -> TakePaymentResponse: ...
